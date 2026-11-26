# conftest.py
# Selenium + Playwright 共存版
# Selenium：旧用例保留
# Playwright：每条用例独立 Chromium + 独立 Context；session 内登录一次后注入 Cookie

import os
import re
import atexit

import pytest

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        _WDM_AVAILABLE = True
    except Exception:
        _WDM_AVAILABLE = False

    _SELENIUM_AVAILABLE = True
except Exception:
    _SELENIUM_AVAILABLE = False


try:
    from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
    _PW_AVAILABLE = True
except Exception:
    _PW_AVAILABLE = False


DEFAULT_BASE_URL = "https://www.testhopetrip.dabapiao.com"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(ROOT_DIR, "screenshots")
TRACE_DIR = os.path.join(ROOT_DIR, "report")

# 仅作为“疑似会话 Cookie”辅助判断；以站点实际 F12 为准。
LOGIN_COOKIE_HINTS = (
    "userstore", "sessionid", "session_id", "token", "auth",
    "JSESSIONID", "PHPSESSID", "hopetrip_token", "user_token",
)

LICENSE_ANCHOR = "text=354122"
PW_USER_MENU = '[data-testid="header-user-trigger"]'

_ANTI_DETECT_JS = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5].map(i=>({
    name:'Chrome PDF Plugin '+(i-1),
    filename:'internal-pdf-viewer'+i,
    length:1,
    description:'Portable Document Format'
}))});
Object.defineProperty(navigator,'languages',{get:()=>['zh-HK','zh','en']});
window.chrome = window.chrome || {runtime:{}, loadTimes:()=>({}), csi:()=>({})};
"""


# =========================
# pytest 配置
# =========================

def pytest_addoption(parser):
    parser.addoption("--headless", action="store_true", default=False,
                     help="启用无头模式（Selenium / Playwright 共用）")
    parser.addoption("--pw-trace", action="store_true", default=False,
                     help="保留 Playwright 失败用例 Trace")


def pytest_configure(config):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(TRACE_DIR, exist_ok=True)

    for marker in (
        "playwright: Playwright 引擎用例",
        "selenium: Selenium 引擎用例",
        "use_login: 需要登录态，注入 session 内共享 Cookie",
        "ferry: 船票业务",
        "bus: 大巴业务",
        "hotel: 酒店套票业务",
        "charter: 包车接送业务",
        "smoke: 冒烟用例",
        "slow: 慢用例",
    ):
        config.addinivalue_line("markers", marker)

    _warn_gitignore()


def pytest_collection_modifyitems(config, items):
    """未显式标引擎的 test_case/test_*.py，按 import 自动补 marker。"""
    for item in items:
        if not item.get_closest_marker("playwright") and not item.get_closest_marker("selenium"):
            source = item.nodeid
            if "test_case_pw" in source:
                item.add_marker(pytest.mark.playwright)
            elif "test_case" in source:
                # 你的现有 Selenium 业务用例仍在 test_case/
                item.add_marker(pytest.mark.selenium)


def _warn_gitignore():
    try:
        path = os.path.join(ROOT_DIR, ".gitignore")
        if not os.path.isfile(path):
            return
        text = open(path, encoding="utf-8", errors="ignore").read()
        missing = [d for d in ("screenshots/", "report/")
                   if f"\n{d}" not in "\n" + text]
        if missing:
            print(f" ⚠️ .gitignore 未忽略 {missing}；建议加入 screenshots/、report/、.chrome_profile_automation/")
    except Exception:
        pass


def _base_url() -> str:
    return (os.getenv("BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/"


def _headless_enabled(request=None) -> bool:
    cli = bool(request.config.getoption("--headless", default=False)) if request is not None else False
    return cli or os.getenv("HEADLESS", "false").lower() == "true"


def _safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "unnamed"


def _login_account() -> dict:
    return {
        "email": os.getenv("LOGIN_EMAIL", "AutomatedTesting@gmail.com"),
        "password": os.getenv("LOGIN_PWD", ""),
    }


def _cookie_names(cookies) -> set:
    return {str(c.get("name", "")).lower() for c in (cookies or [])}


def _looks_logged_in(cookies) -> bool:
    names = _cookie_names(cookies)
    return any(h.lower() in names for h in LOGIN_COOKIE_HINTS) or any(
        ("session" in n) or ("token" in n) or ("auth" in n) for n in names
    )


def _attach_allure(path: str, name: str, attachment_type: str = "PNG") -> None:
    try:
        import allure
        from allure_commons.types import AttachmentType

        allure.attach.file(
            path, name=name,
            attachment_type=getattr(AttachmentType, attachment_type, AttachmentType.PNG),
        )
    except Exception:
        pass


def _screenshot_page(page, item, stage: str) -> None:
    path = os.path.join(SCREENSHOT_DIR, f"{stage}_{_safe_name(item.name)}.png")
    try:
        try:
            page.screenshot(path=path, full_page=True, timeout=10_000)
        except Exception:
            page.screenshot(path=path, full_page=False, timeout=10_000)
        print(f" 📸 截图: {path}")
        _attach_allure(path, f"Playwright {stage} 截图")
    except Exception as exc:
        print(f" 截图保存跳过: {exc}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if not report.failed:
        return

    page = getattr(item, "_playwright_page", None)
    if page is not None:
        _screenshot_page(page, item, report.when)

    driver = getattr(item, "funcargs", {}).get("driver") if isinstance(getattr(item, "funcargs", None), dict) else None
    if driver is not None:
        path = os.path.join(SCREENSHOT_DIR, f"{report.when}_{_safe_name(item.name)}.png")
        try:
            driver.save_screenshot(path)
            print(f" 📸 Selenium 截图: {path}")
            _attach_allure(path, f"Selenium {report.when} 截图")
        except Exception as exc:
            print(f" Selenium 截图跳过: {exc}")

    if page is None and driver is None:
        print(f" ⚠️ [{item.name}] {report.when} 失败，但无 page/driver 可截图")


# =========================
# Selenium：旧逻辑保留
# =========================

def _selenium_service() -> Service:
    if not _SELENIUM_AVAILABLE:
        raise RuntimeError("Selenium 未安装")

    path = os.getenv("CHROMEDRIVER_PATH")
    if path and os.path.exists(path):
        return Service(path)
    if not _WDM_AVAILABLE:
        raise RuntimeError("请设置 CHROMEDRIVER_PATH，或 pip install webdriver-manager")
    return Service(ChromeDriverManager().install())


def _selenium_options(headless: bool) -> Options:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
    else:
        opts.add_argument("--start-maximized")

    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-networking")
    if headless:
        opts.add_argument("--disable-gpu")
    return opts


def _selenium_anti_detect(driver) -> None:
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": _ANTI_DETECT_JS})
    except Exception as exc:
        print(f" Selenium 反自动化脚本注入跳过: {exc}")


def _selenium_login_visible(driver, timeout: int = 15) -> bool:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    selectors = (
        f'{PW_USER_MENU}, '
        '.user-avatar, .username, [class*="avatar"], '
        '[class*="user-info"], .logout-btn, a[href*="logout"], '
        '[class*="header-user"], .el-dropdown-link, '
        '[class*="nickname"], [class*="user-name"]'
    )
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selectors)))
        return True
    except Exception:
        return False


@pytest.fixture(scope="function")
def driver(request):
    """旧 Selenium 游客态用例：每条一个浏览器。"""
    if not _SELENIUM_AVAILABLE:
        pytest.skip("Selenium 未安装")

    headless = _headless_enabled(request)
    drv = webdriver.Chrome(service=_selenium_service(), options=_selenium_options(headless))
    request.node._selenium_driver = drv
    _selenium_anti_detect(drv)
    drv.implicitly_wait(10)
    drv.get(_base_url())
    drv.implicitly_wait(0)
    yield drv
    drv.quit()


@pytest.fixture(scope="session")
def _selenium_login_cookies():
    """Selenium 登录一次，仅用于旧 Selenium logged_in_driver。"""
    if not _SELENIUM_AVAILABLE:
        pytest.skip("Selenium 未安装")

    from business.login_business import LoginBusiness

    headless = _headless_enabled()
    drv = webdriver.Chrome(service=_selenium_service(), options=_selenium_options(headless))
    _selenium_anti_detect(drv)
    drv.implicitly_wait(10)
    drv.get(_base_url())
    drv.implicitly_wait(0)

    acc = _login_account()
    if not acc["password"]:
        pytest.fail("请先用 $env:LOGIN_PWD='...' 设置测试账号密码")

    try:
        LoginBusiness.loginBusiness(
            driver=drv, email=acc["email"], password=acc["password"], login_mode="email"
        )
        ui_ok = _selenium_login_visible(drv)
        cookies = drv.get_cookies()
        print(f" Selenium 登录 Cookie={len(cookies)} 条，UI用户区={'✅' if ui_ok else '⚠️未检出'}")

        if not ui_ok and not _looks_logged_in(cookies):
            _selenium_login_visible(drv, timeout=5)
            pytest.fail(
                f"Selenium 登录自证失败：Cookie={sorted(_cookie_names(cookies))}；"
                f"请检查账号、密码、验证码/风控和 header selector。"
            )
        return cookies
    finally:
        drv.quit()


@pytest.fixture(scope="function")
def logged_in_driver(driver, _selenium_login_cookies):
    """旧 Selenium 登录态用例：每条新浏览器，注入 session Cookie。"""
    driver.delete_all_cookies()
    for raw in _selenium_login_cookies:
        item = {k: v for k, v in dict(raw).items()
                if k in ("name", "value", "path", "domain", "secure", "expiry")}
        try:
            driver.add_cookie(item)
        except Exception as exc:
            print(f" Selenium Cookie 注入跳过 [{raw.get('name')}]: {exc}")

    driver.refresh()
    assert _selenium_login_visible(driver, 15), "Selenium 注入 Cookie 后仍未检出用户区"
    yield driver


# =========================
# Playwright：每条用例独立浏览器
# =========================

@pytest.fixture(scope="session")
def pw_playwright():
    if not _PW_AVAILABLE:
        pytest.skip("Playwright 未安装：pip install playwright pytest-playwright；playwright install chromium")

    playwright = sync_playwright().start()
    yield playwright
    playwright.stop()


@pytest.fixture(scope="session")
def _pw_shared_login_state(pw_playwright, request) -> dict:
    """
    整个测试 session 真登录一次，返回 {cookies, origin}。
    不把 Cookie 写入 .pytest_cache，避免凭证明文落盘。
    """
    acc = _login_account()
    if not acc["password"]:
        pytest.fail("请先用 $env:LOGIN_PWD='...' 设置测试账号密码；禁止把密码提交进仓库")

    from business.login_business import LoginBusiness

    headless = _headless_enabled(request)
    browser = pw_playwright.chromium.launch(
        headless=headless,
        slow_mo=int(os.getenv("PW_SLOW_MO", "0")),
        args=_pw_launch_args(headless),
    )
    context = _pw_new_context(browser, headless)
    page = context.new_page()

    cookies, origin = [], _base_url().rstrip("/")
    try:
        page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
        _wait_home_ready(page)

        mode = LoginBusiness(page, timeout=15_000).login(email=acc["email"], pwd=acc["password"])
        page.wait_for_timeout(2_000)

        # 登录主判定：用户菜单已出现且有文本。
        # Cookie 只用于跨 Context 注入与诊断，不再因为在猜测名单里没有名字就误杀。
        user_menu = page.locator(PW_USER_MENU).first
        try:
            user_menu.wait_for(state="visible", timeout=10_000)
            ui_text = (user_menu.inner_text(timeout=3_000) or "").strip()
        except Exception:
            ui_text = ""

        cookies = context.cookies()
        origin = page.evaluate("() => location.origin")

        if not ui_text and not _looks_logged_in(cookies):
            _screenshot_page(page, request.node, "session_login_failed")
            pytest.fail(
                f"Playwright 会话登录自证失败（mode={mode}）："
                f"Cookie={sorted(_cookie_names(cookies))}，header用户区未渲染。\n"
                f"账号={acc['email']}；请检查密码、验证码/风控、登录接口响应。"
            )

        print(f"🔐 会话登录完成：mode={mode}，Cookie={len(cookies)} 条，用户区={'✅' if ui_text else '⚠️Cookie辅助判定'}")
        return {"cookies": cookies, "origin": origin}
    finally:
        try:
            context.close()
        finally:
            browser.close()


def _pw_launch_args(headless: bool) -> list:
    args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking"]
    if headless:
        args.append("--headless=new")
    else:
        args.extend(["--window-size=1920,1080", "--window-position=0,0"])
    return args


def _pw_new_context(browser: Browser, headless: bool) -> BrowserContext:
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="zh-HK",
        timezone_id="Asia/Hong_Kong",
        ignore_https_errors=True,
        extra_http_headers={"Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"},
        # 删除写死的旧 Chrome/120 UA，让 Playwright 使用与当前内核匹配的自然 UA。
    )
    ctx.add_init_script(_ANTI_DETECT_JS)
    return ctx


def _wait_home_ready(page: Page, timeout: int = 20_000, extra_anchor: str = "") -> None:
    page.locator(LICENSE_ANCHOR).first.wait_for(state="visible", timeout=timeout)
    if extra_anchor:
        try:
            page.locator(extra_anchor).first.wait_for(state="visible", timeout=timeout)
        except Exception as exc:
            print(f" 业务锚点未就绪（非阻塞）{extra_anchor}: {exc}")


def _pw_cookie_for_playwright(raw: dict) -> dict | None:
    item = dict(raw)
    name = item.get("name")
    value = item.get("value")
    if not name or value is None:
        return None

    result = {
        "name": str(name),
        "value": str(value),
        "path": str(item.get("path") or "/"),
    }

    domain = str(item.get("domain") or "").lstrip(".")
    if domain:
        result["domain"] = domain

    if item.get("expires") not in (None, -1):
        try:
            result["expires"] = float(item["expires"])
        except (TypeError, ValueError):
            pass

    if item.get("httpOnly") is not None:
        result["httpOnly"] = bool(item["httpOnly"])
    if item.get("secure") is not None:
        result["secure"] = bool(item["secure"])

    same_site = str(item.get("sameSite") or "").strip().lower()
    if same_site in ("lax", "strict", "none"):
        result["sameSite"] = same_site.capitalize()

    return result


def _pw_inject_state(context: BrowserContext, login_state: dict, tag: str) -> None:
    cookies = login_state.get("cookies") or []
    origin = login_state.get("origin") or _base_url().rstrip("/")

    # 先访问目标 origin，再注入该 origin 的 Cookie；避免 domain/跨站限制导致注入失败。
    page = context.new_page()
    try:
        page.goto(origin + "/", wait_until="domcontentloaded", timeout=30_000)
    except Exception as exc:
        print(f"{tag} 预热 origin 失败，继续尝试注入: {exc}")

    converted = [x for x in (_pw_cookie_for_playwright(c) for c in cookies) if x]
    failed = []
    for cookie in converted:
        try:
            context.add_cookies([cookie])
        except Exception as exc:
            failed.append(f"{cookie.get('name')}:{exc}")

    print(f"{tag} Cookie 注入：成功 {len(converted) - len(failed)}/{len(converted)} 条")
    if failed:
        print(f"{tag} 失败明细（前5条）：{failed[:5]}")

    try:
        page.close()
    except Exception:
        pass


def _start_trace(context: BrowserContext, request) -> None:
    if request.config.getoption("--pw-trace", default=False):
        context.tracing.start(screenshots=True, snapshots=True, sources=True)


def _stop_trace(context: BrowserContext, request, name: str) -> None:
    if not request.config.getoption("--pw-trace", default=False):
        return

    path = os.path.join(TRACE_DIR, f"{_safe_name(name)}.zip")
    try:
        context.tracing.stop(path=path)
        print(f" 🧵 Playwright Trace: {path}")
        _attach_allure(path, "Playwright Trace", "ZIP")
    except Exception as exc:
        print(f" Trace 保存跳过: {exc}")


@pytest.fixture(scope="function")
def pw_browser(pw_playwright, request) -> Browser:
    """⚠️ function 级：每条用例启动一个全新 Chromium。"""
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
    """每条用例全新 Context：Cookie、localStorage、缓存完全隔离。"""
    ctx = _pw_new_context(pw_browser, _headless_enabled(request))
    request.node._pw_context = ctx
    _start_trace(ctx, request)
    yield ctx
    _stop_trace(ctx, request, request.node.name)
    try:
        ctx.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def pw_page(pw_context: BrowserContext, request) -> Page:
    """游客态：每条用例新浏览器 + 新 Context + 首页。"""
    page = pw_context.new_page()
    request.node._playwright_page = page
    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)
    print(f"🌐 Playwright 游客页就绪：{page.url}")
    yield page
    try:
        page.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def pw_logged_in_page(pw_context: BrowserContext, request, _pw_shared_login_state) -> Page:
    """
    ✅ 新业务默认登录态夹具：
    每条用例一个全新 Chromium + Context；注入 session 内一次真实登录得到的 Cookie。
    """
    request.node.add_marker(pytest.mark.use_login)

    _pw_inject_state(pw_context, _pw_shared_login_state, "[pw_logged_in_page]")

    page = pw_context.new_page()
    request.node._playwright_page = page

    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    # 登录后自证：用户菜单优先；若前端 selector 改版，至少要求有会话 Cookie。
    ui_ok = False
    try:
        menu = page.locator(PW_USER_MENU).first
        menu.wait_for(state="visible", timeout=10_000)
        ui_ok = bool((menu.inner_text(timeout=3_000) or "").strip())
    except Exception:
        pass

    if not ui_ok and not _looks_logged_in(page.context.cookies()):
        _screenshot_page(page, request.node, "login_selfcheck_failed")
        page.context.close()
        pytest.fail(
            "pw_logged_in_page 登录态自证失败：用户区不可见，且 Cookie 无会话标志。\n"
            f"Cookie={sorted(_cookie_names(page.context.cookies()))}\n"
            "请先看 screenshots/login_selfcheck_failed_*，并检查登录响应/账号风控/header selector。"
        )

    print(f"🔓 Playwright 登录态页就绪：{page.url}，用户区={'✅' if ui_ok else '⚠️Cookie辅助'}")
    yield page
    try:
        page.close()
    except Exception:
        pass


# 兼容旧命名：逐渐迁移到 pw_page / pw_logged_in_page
@pytest.fixture(scope="function")
def pw_module_page(pw_page: Page) -> Page:
    """兼容旧用例：虽仍叫 module，但实际已是 function 级独立浏览器。"""
    yield pw_page


@pytest.fixture(scope="function")
def pw_module_page_logged_in(pw_logged_in_page: Page) -> Page:
    """
    ✅ 关键兼容层：
    你现有的 test_busticket.py 不用批量改也能获得“每条用例独立浏览器”。
    新代码建议直接改用 pw_logged_in_page。
    """
    yield pw_logged_in_page


# 进程退出时尽量清理截图句柄等资源（不改变测试语义）
atexit.register(lambda: None)