# conftest.py
# Selenium + Playwright 共存版
# Selenium：保留 driver / login_cookies / logged_in_driver，旧用例不动
# Playwright：提供公共 pw_page / pw_module_page / pw_logged_in_page，后续业务无需重复新增浏览器 fixture
# Jenkins：BASE_URL / HEADLESS / PW_SLOW_MO / CHROMEDRIVER_PATH
# 命令：pytest --headless 或 $env:HEADLESS="true"

import os
import re
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import Browser, BrowserContext, Page
    _PW_AVAILABLE = True
except ImportError:                       # pragma: no cover
    _PW_AVAILABLE = False

DEFAULT_BASE_URL = "https://www.testhopetrip.dabapiao.com/"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(ROOT_DIR, "screenshots")
TRACE_DIR = os.path.join(ROOT_DIR, "report")
LEGACY_CHROME_USER_DATA = os.path.join(ROOT_DIR, ".chrome_profile_automation")


# ============================================================================
#                               公共配置
# ============================================================================

def pytest_addoption(parser):
    parser.addoption("--headless", action="store_true", default=False,
                     help="启用无头模式（Selenium / Playwright 共用）")
    parser.addoption("--pw-trace", action="store_true", default=False,
                     help="保留 Playwright 失败用例 Trace（zip，可用 playwright show-trace 回放）")


def pytest_configure(config):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(TRACE_DIR, exist_ok=True)

    for marker in [
        "playwright: Playwright 引擎用例",
        "selenium: Selenium 引擎用例",
        "use_login: 需要登录态，自动注入共享 Cookie",
        "ferry: 船票业务",
        "bus: 大巴业务",
        "hotel: 酒店套票业务",
        "charter: 包车接送业务",
        "smoke: 冒烟用例",
    ]:
        config.addinivalue_line("markers", marker)


def _base_url() -> str:
    return os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/") + "/"


def _headless_enabled(request=None) -> bool:
    cli = False
    if request is not None:
        try:
            cli = bool(request.config.getoption("--headless", default=False))
        except Exception:
            cli = False
    return cli or os.getenv("HEADLESS", "false").lower() == "true"


def _safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "unnamed"


def _attach_allure(path: str, name: str, attachment_type: str = "PNG") -> None:
    """装了 allure-pytest 就挂附件；没装静默跳过，不阻断测试。"""
    try:
        import allure
        from allure_commons.types import AttachmentType
        allure.attach.file(path, name=name,
                           attachment_type=getattr(AttachmentType, attachment_type, AttachmentType.PNG))
    except Exception:
        pass


# ============================================================================
#                       Selenium：现有逻辑保留，等待策略修正
# ============================================================================

def _get_chromedriver_service() -> Service:
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path and os.path.exists(driver_path):
        return Service(driver_path)
    return Service(ChromeDriverManager().install())


def _get_base_options(headless: bool = False) -> Options:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    if headless:
        options.add_argument("--disable-gpu")
    return options


def _anti_detect(driver) -> None:
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"},
        )
    except Exception as exc:
        print(f" Selenium 防自动化脚本注入跳过: {exc}")


@pytest.fixture(scope="function")
def driver(request):
    """现有 Selenium 用例继续使用：每条用例独立浏览器。"""
    options = _get_base_options(_headless_enabled(request))
    service = _get_chromedriver_service()
    web_driver = webdriver.Chrome(service=service, options=options)
    _anti_detect(web_driver)

    web_driver.implicitly_wait(10)
    web_driver.get(_base_url())
    web_driver.implicitly_wait(0)   # 归零：后续统一显式等待，防止与 WebDriverWait 叠加

    yield web_driver
    web_driver.quit()


@pytest.fixture(scope="session")
def _login_driver():
    """Selenium 专用登录浏览器：session 内只登录一次。"""
    options = _get_base_options(_headless_enabled())
    service = _get_chromedriver_service()
    web_driver = webdriver.Chrome(service=service, options=options)
    _anti_detect(web_driver)
    web_driver.implicitly_wait(10)
    web_driver.get(_base_url())
    web_driver.implicitly_wait(0)
    yield web_driver
    web_driver.quit()


@pytest.fixture(scope="session")
def login_cookies(_login_driver):
    """Selenium 登录一次，Cookie 供 logged_in_driver + Playwright 桥接共用。"""
    from business.login_business import LoginBusiness
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    LoginBusiness.loginBusiness(
        driver=_login_driver,
        email=os.getenv("LOGIN_EMAIL", "AutomatedTesting@gmail.com"),
        password=os.getenv("LOGIN_PWD", "123456"),
        login_mode="email",
    )

    try:
        WebDriverWait(_login_driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 ".user-avatar, .username, [class*='avatar'], "
                 "[class*='user-info'], .logout-btn, a[href*='logout'], "
                 "[class*='header-user'], .el-dropdown-link, "
                 "[class*='nickname'], [class*='user-name']")
            )
        )
    except Exception as exc:
        print(f" 登录成功标志等待超时（继续使用当前 Cookie）: {exc}")

    cookies = _login_driver.get_cookies()
    print(f" 登录态已建立，共 {len(cookies)} 个 Cookie")
    return cookies


@pytest.fixture(scope="function")
def logged_in_driver(driver, login_cookies):
    """现有 Selenium 登录态用例继续使用。"""
    driver.delete_all_cookies()
    for raw in login_cookies:
        cookie = dict(raw)
        for key in ("domain", "sameSite", "expiry"):   # Selenium add_cookie 对扩展字段敏感
            cookie.pop(key, None)
        try:
            driver.add_cookie(cookie)
        except Exception as exc:
            print(f" Cookie 注入跳过 [{cookie.get('name')}]: {exc}")
    driver.refresh()
    yield driver


# ============================================================================
#                   Playwright 公共底座：后续业务不用重复加
# ============================================================================

def _pw_launch_args(headless: bool) -> list:
    args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking"]
    if headless:
        args.append("--headless=new")
    else:
        # Windows 下比 --start-maximized 更稳；真实视口以 new_context(viewport=) 为准
        args.extend(["--window-size=1920,1080", "--window-position=0,0"])
    return args


def _pw_viewport(headless: bool):
    # 有头无头统一固定桌面视口，避免 None 回落默认 1280x720 命中响应式布局
    return {"width": 1920, "height": 1080}


def _pw_new_context(browser: Browser, headless: bool) -> BrowserContext:
    context = browser.new_context(
        viewport=_pw_viewport(headless),
        locale="zh-HK",
        timezone_id="Asia/Hong_Kong",
        ignore_https_errors=True,
        extra_http_headers={"Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    context.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    )
    return context


def _wait_home_ready(page: Page, timeout: int = 20_000) -> None:
    """
    等盼游首页真正挂载完成。
    只认 nav/header 内的「船票」导航，避免命中正文里的"船票搜索歷史""船務公司線路"等文案。
    """
    page.locator('nav a:has-text("船票"), header a:has-text("船票")').first.wait_for(
        state="visible", timeout=timeout
    )


def _cookies_for_playwright(cookies) -> list:
    """Selenium Cookie → Playwright Cookie；保留 domain，避免子域登录态丢失。"""
    converted = []
    for raw in cookies:
        item = dict(raw)
        same_site = str(item.pop("sameSite", "") or "").strip().lower()
        if same_site in ("lax", "strict", "none"):
            item["sameSite"] = same_site.capitalize()
        expiry = item.pop("expiry", None)
        if isinstance(expiry, (int, float)) and expiry > 0:
            item["expires"] = float(expiry)
        converted.append(item)
    return converted


def _inject_login_cookies(request, context: BrowserContext) -> None:
    if request.node.get_closest_marker("use_login") is None:
        return
    cookies = request.config.cache.get("shared_login_cookies", None)
    if not cookies:
        print(" 提示：未找到共享登录 Cookie。请先跑一次带 login_cookies 的 Selenium 登录用例。")
        return
    try:
        context.add_cookies(_cookies_for_playwright(cookies))
        print(f" Playwright 已注入登录 Cookie: {len(cookies)} 条")
    except Exception as exc:
        print(f" Playwright Cookie 注入跳过: {exc}")


def _start_trace(context: BrowserContext, request) -> None:
    if request.config.getoption("--pw-trace", default=False):
        context.tracing.start(screenshots=True, snapshots=True, sources=True)


def _stop_trace(context: BrowserContext, request, name: str) -> None:
    if not request.config.getoption("--pw-trace", default=False):
        return
    path = os.path.join(TRACE_DIR, f"{_safe_name(name)}.zip")
    try:
        context.tracing.stop(path=path)
        print(f" Playwright Trace: {path}")
        _attach_allure(path, "Playwright Trace", "ZIP")
    except Exception as exc:
        print(f" Playwright Trace 保存跳过: {exc}")


@pytest.fixture(scope="session")
def pw_playwright():
    if not _PW_AVAILABLE:
        pytest.skip("Playwright 未安装：pip install pytest-playwright && playwright install chromium")
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="function")
def pw_browser(pw_playwright, request) -> Browser:
    """function 级：每条用例全新 Chromium，适合独立用例。"""
    headless = _headless_enabled(request)
    browser = pw_playwright.chromium.launch(
        headless=headless,
        slow_mo=int(os.getenv("PW_SLOW_MO", "0")),
        args=_pw_launch_args(headless),
    )
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def pw_context(pw_browser: Browser, request) -> BrowserContext:
    context = _pw_new_context(pw_browser, _headless_enabled(request))
    _inject_login_cookies(request, context)      # 用例打 @pytest.mark.use_login 才注入
    _start_trace(context, request)
    yield context
    _stop_trace(context, request, request.node.name)
    context.close()


@pytest.fixture(scope="function")
def pw_page(pw_context: BrowserContext, request) -> Page:
    """新业务默认用这个：每条用例独立 Context，从首页起步。"""
    page = pw_context.new_page()
    request.node._playwright_page = page        # 先挂，goto 失败也能截图

    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    print(f" Playwright 页面就绪（{page.viewport_size}）：{page.url}")
    yield page


@pytest.fixture(scope="function")
def pw_logged_in_page(pw_context: BrowserContext, request) -> Page:
    """需要登录态的新用例用这个；自动补 use_login marker。"""
    if request.node.get_closest_marker("use_login") is None:
        request.node.add_marker(pytest.mark.use_login)
        _inject_login_cookies(request, pw_context)   # Context 已带 Cookie，下面首个请求自然带上

    page = pw_context.new_page()
    request.node._playwright_page = page

    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    # 轻量确认登录态已生效（不阻断：只打印，具体断言交给用例自己写）
    try:
        body = page.locator("body").inner_text(timeout=3_000)
        logged = any(k in body for k in ("會員中心", "我的訂單", "登出", "退出"))
        print(f" Playwright 登录态页面就绪（{page.viewport_size}）：{page.url}  登录标志={'✅' if logged else '⚠️未检出'}")
    except Exception:
        print(f" Playwright 登录态页面就绪（{page.viewport_size}）：{page.url}")
    yield page


# ---------------- 模块级流程型页面：船票/大巴分步流程共用 ----------------

@pytest.fixture(scope="module")
def pw_module_browser(pw_playwright) -> Browser:
    headless = _headless_enabled()
    browser = pw_playwright.chromium.launch(
        headless=headless,
        slow_mo=int(os.getenv("PW_SLOW_MO", "0")),
        args=_pw_launch_args(headless),
    )
    yield browser
    browser.close()


@pytest.fixture(scope="module")
def pw_module_context(pw_module_browser: Browser, request) -> BrowserContext:
    context = _pw_new_context(pw_module_browser, _headless_enabled())
    _inject_login_cookies(request, context)
    _start_trace(context, request)
    yield context
    module_name = getattr(request.module, "__name__", "pw_module")
    _stop_trace(context, request, module_name)
    context.close()


@pytest.fixture(scope="module")
def pw_module_page(pw_module_context: BrowserContext, request) -> Page:
    """
    模块内多用例共享页面状态：test_01 选路线 → test_02 选日期查询。
    只负责打开首页；具体业务入口（/ferry、/bus）由各测试模块自己的 xxx_biz fixture 跳转，
    避免把业务路径写进公共 conftest。
    普通独立用例请用 pw_page。
    """
    page = pw_module_context.new_page()
    request.node._playwright_page = page

    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    print(f" Playwright 首页就绪（{page.viewport_size}）：{page.url}")
    yield page


# ============================================================================
#                       统一结果 Hook：只保留这一份
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    1. 设 rep_setup/rep_call/rep_teardown 供 fixture 判失败
    2. Selenium / Playwright 失败统一截图 + Allure attach
    3. Selenium login_cookies 成功后写 cache，供 Playwright @use_login 桥接
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.when == "call" and report.failed:
        page = getattr(item, "_playwright_page", None)
        if page is not None:
            path = os.path.join(SCREENSHOT_DIR, f"pw_{_safe_name(item.name)}.png")
            try:
                page.screenshot(path=path, full_page=True)
                print(f" Playwright 失败截图: {path}")
                _attach_allure(path, "Playwright 失败截图", "PNG")
            except Exception as exc:
                print(f" Playwright 失败截图保存跳过: {exc}")

        web_driver = getattr(item, "funcargs", {}).get("driver")
        if web_driver is not None:
            path = os.path.join(SCREENSHOT_DIR, f"selenium_{_safe_name(item.name)}.png")
            try:
                web_driver.save_screenshot(path)
                print(f" Selenium 失败截图: {path}")
                _attach_allure(path, "Selenium 失败截图", "PNG")
            except Exception as exc:
                print(f" Selenium 失败截图保存跳过: {exc}")

    if report.when == "call" and report.passed:
        cookies = getattr(item, "funcargs", {}).get("login_cookies")
        if cookies:
            try:
                item.config.cache.set("shared_login_cookies", list(cookies))
                print(" 登录 Cookie 已缓存；Playwright 用例加 @pytest.mark.use_login 即可复用")
            except Exception as exc:
                print(f" 登录 Cookie 缓存跳过: {exc}")


@pytest.fixture(autouse=True, scope="session")
def _cleanup_legacy_chrome_lock():
    """
    会话开始时清一次历史固定 Profile 的 Chrome 单例锁。
    只删锁文件，不删目录——避免误删有人为配置的登录态/缓存。
    """
    if os.path.isdir(LEGACY_CHROME_USER_DATA):
        for lock_name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            lock_path = os.path.join(LEGACY_CHROME_USER_DATA, lock_name)
            try:
                if os.path.exists(lock_path) or os.path.islink(lock_path):
                    os.remove(lock_path)
            except Exception as exc:
                print(f" 历史 Chrome 锁清理跳过 [{lock_name}]: {exc}")
    yield