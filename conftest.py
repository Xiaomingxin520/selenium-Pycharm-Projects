# conftest.py  基础配置层
# Selenium + Playwright 共存版
# Selenium：保留 driver / login_cookies / logged_in_driver，旧用例不动

import os
import re
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

try:
    from webdriver_manager.chrome import ChromeDriverManager
    _WDM_AVAILABLE = True
except ImportError:                                # pragma: no cover
    _WDM_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import Browser, BrowserContext, Page
    _PW_AVAILABLE = True
except ImportError:                               # pragma: no cover
    _PW_AVAILABLE = False


DEFAULT_BASE_URL = "https://www.testhopetrip.dabapiao.com/"

# ⚠️⑨ 本文件假設位於【項目根目錄】。若挪到 tests/ 下，ROOT_DIR 會跟着漂，
#    截圖會跑到 tests/screenshots。挪位時改成：
#    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(ROOT_DIR, "screenshots")
TRACE_DIR = os.path.join(ROOT_DIR, "report")
LEGACY_CHROME_USER_DATA = os.path.join(ROOT_DIR, ".chrome_profile_automation")

# 登錄態判定用的 Cookie 名（⑦ 校「半截 Cookie」用）。
# ⚠️ 盼游實際用哪個以 F12→Application→Cookies 爲準，這裏多寫幾個別名做 OR。
LOGIN_COOKIE_HINTS = ("sessionid", "session_id", "token", "auth",
                      "JSESSIONID", "PHPSESSID", "hopetrip_token", "user_token")

# 頁腳香港旅遊牌照號：全站唯一、不隨改版文案漂移 → 首選外殼就緒錨點
LICENSE_ANCHOR = "text=354122"


# ============================================================================
#                               公共配置
# ============================================================================

def pytest_addoption(parser):
    parser.addoption("--headless", action="store_true", default=False,
                     help="启用无头模式（Selenium / Playwright 共用）")
    parser.addoption("--pw-trace", action="store_true", default=False,
                     help="保留 Playwright 失败用例 Trace（zip，playwright show-trace 回放）")


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
        "slow: 单条 >30s 的组合/全链路用例（日常 CI 用 -m 'not slow' 跳过）",
    ]:
        config.addinivalue_line("markers", marker)

    # ⚠️⑨ 防呆：截圖目錄沒進 .gitignore 的話，跑三次就能提交幾百 MB
    try:
        gitignore = os.path.join(ROOT_DIR, ".gitignore")
        if os.path.isfile(gitignore):
            txt = open(gitignore, encoding="utf-8", errors="ignore").read()
            missing = [d for d in ("screenshots/", "report/")
                       if d.rstrip("/") not in txt]
            if missing:
                print(f" ⚠️ .gitignore 未忽略 {missing} —— 建議加：\n"
                      f"    screenshots/\n    report/\n    .chrome_profile_automation/")
    except Exception:
        pass


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
    """裝了 allure-pytest 就掛附件；沒裝靜默跳過，不阻斷測試。"""
    try:
        import allure
        from allure_commons.types import AttachmentType
        allure.attach.file(path, name=name,
                           attachment_type=getattr(AttachmentType, attachment_type, AttachmentType.PNG))
    except Exception:
        pass


def _login_account() -> dict:
    """帳號只從環境變量讀，默認值僅供本地冒煙。⚠️ 別把真密碼寫進倉庫。"""
    return {
        "email": os.getenv("LOGIN_EMAIL", "AutomatedTesting@gmail.com"),
        "pwd": os.getenv("LOGIN_PWD", "123456"),
    }


# ============================================================================
#                       Selenium：現有邏輯保留，等待策略修正
# ============================================================================

def _get_chromedriver_service() -> Service:
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path and os.path.exists(driver_path):
        return Service(driver_path)
    if not _WDM_AVAILABLE:
        raise RuntimeError(
            "未設 CHROMEDRIVER_PATH 且未裝 webdriver-manager：\n"
            "  pip install webdriver-manager   或   $env:CHROMEDRIVER_PATH='D:\\\\...\\\\chromedriver.exe'"
        )
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


# ⑧ 預防性反自動化補丁。盼游目前未上 DataDome/CF，上了之後
#    只注 webdriver=false 會因 plugins.length===0 被識别，且【只在 CI 紅】最難查。
_ANTI_DETECT_JS = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5].map(i=>({
    name:'Chrome PDF Plugin '+(i-1), filename:'internal-pdf-viewer'+i,
    length:1, description:'Portable Document Format'}))});
Object.defineProperty(navigator,'languages',{get:()=>['zh-HK','zh','en']});
window.chrome = window.chrome || { runtime: {}, loadTimes: ()=>{}, csi: ()=>{} };
"""


def _anti_detect(driver) -> None:
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": _ANTI_DETECT_JS})
    except Exception as exc:
        print(f" Selenium 防自動化腳本注入跳過: {exc}")


@pytest.fixture(scope="function")
def driver(request):
    """現有 Selenium 用例繼續使用：每條用例獨立瀏覽器。"""
    options = _get_base_options(_headless_enabled(request))
    web_driver = webdriver.Chrome(service=_get_chromedriver_service(), options=options)
    _anti_detect(web_driver)

    web_driver.implicitly_wait(10)
    web_driver.get(_base_url())
    web_driver.implicitly_wait(0)   # 歸零：後續統一顯式等待，防止與 WebDriverWait 疊加成 10+10s
    yield web_driver
    web_driver.quit()


@pytest.fixture(scope="session")
def _login_driver():
    """Selenium 專用登錄瀏覽器：session 內只登一次。"""
    options = _get_base_options(_headless_enabled())     # session 級拿不到 request，只認環境變量（原版行爲保留）
    web_driver = webdriver.Chrome(service=_get_chromedriver_service(), options=options)
    _anti_detect(web_driver)
    web_driver.implicitly_wait(10)
    web_driver.get(_base_url())
    web_driver.implicitly_wait(0)
    yield web_driver
    web_driver.quit()


def _selenium_login_wait_ok(web_driver, timeout: int = 15) -> bool:
    """
    ⑦ 登錄成功判定：testid 優先，業務 class 兜底。
    ⚠️ 原版選擇器全是 .user-info / .avatar 這類【業務 class】，
       前端一換 CSS Modules 就全滅 → 超時 → 打一行「繼續使用當前 Cookie」
       → 可能抓到【登錄未完成的半截 Cookie】還繼續跑，後面 22 條全假綠。
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    selectors = (
        '[data-testid="header-user-trigger"], '      # ← 新增：testid 最穩
        '.user-avatar, .username, [class*="avatar"], '
        '[class*="user-info"], .logout-btn, a[href*="logout"], '
        '[class*="header-user"], .el-dropdown-link, '
        '[class*="nickname"], [class*="user-name"]'
    )
    try:
        WebDriverWait(web_driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selectors)))
        return True
    except Exception as exc:
        print(f" 登錄成功標誌等待超時: {exc}")
        return False


def _cookie_names(cookies) -> set:
    return {str(c.get("name", "")).lower() for c in (cookies or [])}


def _looks_logged_in(cookies) -> bool:
    """⑦ 半截 Cookie 攔截：關鍵會話 Cookie 一個都沒有 → 認爲沒登上。"""
    names = _cookie_names(cookies)
    return any(h.lower() in names for h in LOGIN_COOKIE_HINTS) or any(
        "session" in n or "token" in n or "auth" in n for n in names)


@pytest.fixture(scope="session")
def login_cookies(_login_driver):
    """Selenium 登錄一次，Cookie 供 logged_in_driver + Playwright 橋接共用。"""
    from business.login_business import LoginBusiness

    acc = _login_account()
    LoginBusiness.loginBusiness(
        driver=_login_driver,
        email=acc["email"],
        password=acc["pwd"],
        login_mode="email",
    )

    ui_ok = _selenium_login_wait_ok(_login_driver)
    cookies = _login_driver.get_cookies()
    print(f" 登錄態已建立，共 {len(cookies)} 個 Cookie（UI 標誌={'' if ui_ok else '⚠️未檢出'}）")

    # ⑦ 關鍵：UI 沒檢出 且 Cookie 裏沒有會話標誌 → 別靜默往下跑，
    #    否則舊用例 22 條會以遊客態全綠通過，問題拖到線上才爆。
    if not ui_ok and not _looks_logged_in(cookies):
        pytest.fail(
            f" Selenium 登錄後既沒檢出用戶區 UI，Cookie 裏也沒有會話標誌"
            f"（拿到 {sorted(_cookie_names(cookies))}）。\n"
            f"  可能原因：帳號密碼錯 / 前端改版 / 被風控攔。\n"
            f"  → 請先看 screenshots/ 與 CI 日誌裏的 LoginBusiness 輸出，別放行。"
        )

    return cookies


@pytest.fixture(scope="function")
def logged_in_driver(driver, login_cookies):
    """現有 Selenium 登錄態用例繼續使用。"""
    driver.delete_all_cookies()
    for raw in login_cookies:
        cookie = dict(raw)
        for key in ("domain", "sameSite", "expiry"):   # Selenium add_cookie 對擴展字段敏感
            cookie.pop(key, None)
        try:
            driver.add_cookie(cookie)
        except Exception as exc:
            print(f" Cookie 注入跳過 [{cookie.get('name')}]: {exc}")
    driver.refresh()
    yield driver


# ============================================================================
#                   Playwright 公共底座：後續業務不用重複加
# ============================================================================

def _pw_launch_args(headless: bool) -> list:
    args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking"]
    if headless:
        args.append("--headless=new")
    else:
        # Windows 下比 --start-maximized 更穩；真實視口以 new_context(viewport=) 爲準
        args.extend(["--window-size=1920,1080", "--window-position=0,0"])
    return args


def _pw_viewport(headless: bool) -> dict:
    # 有頭無頭統一固定桌面視口，避免回落默認 1280x720 命中響應式佈局
    return {"width": 1920, "height": 1080}


def _pw_new_context(browser: Browser, headless: bool) -> BrowserContext:
    context = browser.new_context(
        viewport=_pw_viewport(headless),
        locale="zh-HK",
        timezone_id="Asia/Hong_Kong",
        ignore_https_errors=True,
        extra_http_headers={"Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"},
        #  UA 寫死 Chrome/120，而本地 chromium-1248 ≈ Chrome 13x。
        #    UA 與真實指紋不一致反而是【最容易被識别】的特徵。
        #    → 更穩的做法是刪掉 user_agent= 讓 Playwright 用自帶真實 UA；
        #      這裏保留是爲了與現有 Selenium 用例指紋對齊（同一個 UA 跑兩套）。
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    context.add_init_script(_ANTI_DETECT_JS)     # ⑧ 與 Selenium 同一份補丁，兩引擎指紋一致
    return context


def _wait_home_ready(page: Page, timeout: int = 20_000,
                     extra_anchor: str = "") -> None:

    page.locator(LICENSE_ANCHOR).first.wait_for(state="visible", timeout=timeout)
    if extra_anchor:
        try:
            page.locator(extra_anchor).first.wait_for(state="visible", timeout=timeout)
        except Exception as exc:
            print(f"  業務錨點 {extra_anchor} 未在 {timeout}ms 內可見（非阻塞，繼續）: {exc}")


def _cookies_for_playwright(cookies) -> list:
    """Selenium Cookie → Playwright Cookie；保留 domain，避免子域登錄態丟失。"""
    converted = []
    for raw in cookies:
        item = dict(raw)
        same_site = str(item.pop("sameSite", "") or "").strip().lower()
        if same_site in ("lax", "strict", "none"):
            item["sameSite"] = same_site.capitalize()      # Playwright 要 'Lax'/'Strict'/'None'
        expiry = item.pop("expiry", None)                  # Selenium 叫 expiry，PW 叫 expires
        if isinstance(expiry, (int, float)) and expiry > 0:
            item["expires"] = float(expiry)
        # Playwright 不接受這兩個字段，帶着會 throw
        for k in ("httpOnly",):
            if k in item and not isinstance(item[k], bool):
                item.pop(k, None)
        converted.append(item)
    return converted


def _inject_login_cookies(context: BrowserContext, cookies, tag: str = "") -> int:
    """返回實際注入條數；0 = 沒注入（調用方決定是告警還是 fail）。"""
    if not cookies:
        return 0
    try:
        converted = _cookies_for_playwright(cookies)
        context.add_cookies(converted)
        print(f"{tag} Playwright 已注入登錄 Cookie: {len(converted)} 條")
        return len(converted)
    except Exception as exc:
        print(f"{tag} Playwright Cookie 注入跳過: {exc}")
        return 0


# ---------------- ② Cookie 橋接時序修復 ----------------

@pytest.fixture(scope="session")
def _ensure_login_cookies(pw_playwright, request) -> list:

    cached = request.config.cache.get("shared_login_cookies", None)
    if cached and _looks_logged_in(cached):
        print(f" 複用 cache 中的登錄 Cookie: {len(cached)} 條")
        return list(cached)

    if not _PW_AVAILABLE:
        pytest.skip("Playwright 未安裝，且 cache 無可用 Cookie")

    acc = _login_account()
    print(" cache 無可用登錄 Cookie → 開一次性 Playwright context 真登一次…")
    browser = pw_playwright.chromium.launch(
        headless=_headless_enabled(request),
        args=_pw_launch_args(_headless_enabled(request)),
    )
    ctx = _pw_new_context(browser, _headless_enabled(request))
    pg = ctx.new_page()
    cookies = []
    try:
        from business.login_business import LoginBusiness
        pg.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
        _wait_home_ready(pg)
        LoginBusiness(pg, timeout=15_000).login(email=acc["email"], pwd=acc["pwd"])  # 實例版！
        pg.wait_for_timeout(1500)                     # 等 Cookie 落盤（登錄後 Set-Cookie 有時延）
        cookies = ctx.cookies()
    except Exception as exc:
        print(f" Playwright 預登錄失敗: {exc}")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass

    if not cookies or not _looks_logged_in(cookies):
        pytest.fail(
            " 既無 cache Cookie，Playwright 預登錄也沒拿到會話 Cookie"
            f"（拿到 {sorted(_cookie_names(cookies))}）。\n"
            f"  帳號={acc['email']}；請檢查 LOGIN_EMAIL/LOGIN_PWD、帳號是否被鎖、是否被風控。\n"
            f"  ⚠️ 此處刻意 fail 而非告警：放行會讓整個 module 的登錄態用例靜默變遊客態。"
        )

    try:
        request.config.cache.set("shared_login_cookies", list(cookies))
        print(f" 登錄 Cookie 已寫入 cache: {len(cookies)} 條（會話標誌 ✅）")
    except Exception as exc:
        print(f" Cookie 寫 cache 跳過（本次仍可用）: {exc}")
    return list(cookies)


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
        print(f" Playwright Trace 保存跳過: {exc}")


@pytest.fixture(scope="session")
def pw_playwright():
    if not _PW_AVAILABLE:
        pytest.skip("Playwright 未安裝：pip install pytest-playwright && playwright install chromium")
    with sync_playwright() as playwright:
        yield playwright

@pytest.fixture(scope="function")
def pw_browser(pw_playwright, request) -> Browser:
    """function 級：每條用例全新 Chromium，適合獨立用例。"""
    headless = _headless_enabled(request)
    browser = pw_playwright.chromium.launch(
        headless=headless,
        slow_mo=int(os.getenv("PW_SLOW_MO", "0")),
        args=_pw_launch_args(headless),
    )
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def pw_context(pw_browser: Browser, request, _ensure_login_cookies) -> BrowserContext:
    context = _pw_new_context(pw_browser, _headless_enabled(request))
    injected = 0
    if request.node.get_closest_marker("use_login"):
        injected = _inject_login_cookies(context, _ensure_login_cookies, "[pw_context] ")
        if injected == 0:
            pytest.fail(" 用例打了 @use_login 但 Cookie 注入失敗 —— 拒絕以遊客態靜默跑")
    _start_trace(context, request)
    yield context
    _stop_trace(context, request, request.node.name)
    context.close()


@pytest.fixture(scope="function")
def pw_page(pw_context: BrowserContext, request) -> Page:
    """新業務默認用這個：每條用例獨立 Context，從首頁起步。"""
    page = pw_context.new_page()
    request.node._playwright_page = page        # 先掛，goto 失敗也能截圖

    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    print(f" Playwright 頁面就緒（{page.viewport_size}）：{page.url}")
    yield page

    try:
        page.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def pw_logged_in_page(pw_context: BrowserContext, request, _ensure_login_cookies) -> Page:
    """需要登錄態的單條用例用這個；自動補 use_login marker。"""
    had_marker = request.node.get_closest_marker("use_login") is not None
    if not had_marker:
        request.node.add_marker(pytest.mark.use_login)

    page = pw_context.new_page()
    request.node._playwright_page = page

    ctx_cookies = page.context.cookies()
    if not _looks_logged_in(ctx_cookies):
        pytest.fail(
            " pw_logged_in_page 的 context 裏沒有會話 Cookie，拒絕以遊客態跑。\n"
            f"  實際 Cookie: {sorted(_cookie_names(ctx_cookies))}\n"
            f"  → 檢查 _ensure_login_cookies 是否 fail 過（看上面的日誌）"
        )

    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    # 輕量確認登錄態已生效（不阻斷：只打印，具體斷言交給用例自己寫）
    try:
        body = page.locator("body").inner_text(timeout=3_000)
        logged = any(k in body for k in ("會員中心", "我的訂單", "登出", "退出", "頭像"))
        print(f" Playwright 登錄態頁面就緒（{page.viewport_size}）：{page.url}  "
              f"登錄標誌={'' if logged else '⚠️未檢出（以 Cookie 爲準）'}")
    except Exception:
        print(f" Playwright 登錄態頁面就緒（{page.viewport_size}）：{page.url}")
    yield page
    try:
        page.close()
    except Exception:
        pass


# ---------------- ① 模塊級流程型頁面：大巴 22 條 / 船票 test_01→02 ----------------

@pytest.fixture(scope="module")
def pw_module_browser(pw_playwright, request) -> Browser:      # ⑥ 補 request
    headless = _headless_enabled(request)
    browser = pw_playwright.chromium.launch(
        headless=headless,
        slow_mo=int(os.getenv("PW_SLOW_MO", "0")),
        args=_pw_launch_args(headless),
    )
    yield browser
    browser.close()


@pytest.fixture(scope="module")
def pw_module_context(pw_module_browser: Browser, request) -> BrowserContext:
    context = _pw_new_context(pw_module_browser, _headless_enabled(request))
    _start_trace(context, request)
    yield context
    _stop_trace(context, request, getattr(request.module, "__name__", "pw_module"))
    context.close()


@pytest.fixture(scope="module")
def pw_module_page(pw_module_context: BrowserContext, request) -> Page:

    page = pw_module_context.new_page()
    request.node._playwright_page = page

    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    print(f" Playwright 首頁就緒（遊客態·module）：{page.url}")
    yield page
    try:
        page.close()
    except Exception:
        pass


@pytest.fixture(scope="module")
def pw_module_page_logged_in(pw_module_browser: Browser, request) -> Page:

    from business.login_business import LoginBusiness

    context = _pw_new_context(pw_module_browser, _headless_enabled(request))
    _start_trace(context, request)

    page = context.new_page()
    request.node._playwright_page = page

    acc = _login_account()
    page.goto(_base_url(), wait_until="domcontentloaded", timeout=30_000)
    _wait_home_ready(page)

    mode = LoginBusiness(page, timeout=15_000).login(email=acc["email"], pwd=acc["pwd"])
    page.wait_for_timeout(1500)                       # 等 Set-Cookie 落盤

    # 自證：Cookie 會話標誌 + header 用戶區，雙通道任一成立
    ctx_cookies = context.cookies()
    header_ok = False
    try:
        trigger = page.locator('[data-testid="header-user-trigger"]').first
        trigger.wait_for(state="visible", timeout=8_000)
        header_ok = bool((trigger.inner_text() or "").strip())
    except Exception:
        pass

    if not _looks_logged_in(ctx_cookies) and not header_ok:
        try:
            page.screenshot(path=os.path.join(SCREENSHOT_DIR,
                                              "pw_module_login_failed.png"))
        except Exception:
            pass
        context.close()
        pytest.fail(
            f" pw_module_page_logged_in 登錄後自證失敗（mode={mode}）：\n"
            f"  Cookie={sorted(_cookie_names(ctx_cookies))}（無會話標誌）\n"
            f"  header 用戶區未渲染\n"
            f"  → 帳號={acc['email']}；截圖 screenshots/pw_module_login_failed.png"
        )

    print(f" Playwright 首頁就緒（登錄態·module，mode={mode}，"
          f"Cookie={len(ctx_cookies)} 條，header={'' if header_ok else '⚠️'}）：{page.url}")

    yield page

    try:
        page.close()
    except Exception:
        pass
    _stop_trace(context, request, getattr(request.module, "__name__", "pw_module_logged_in"))
    context.close()


# ============================================================================
#                       統一結果 Hook：只保留這一份
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    1. 設 rep_setup/rep_call/rep_teardown 供 fixture 判失敗
    2. Selenium / Playwright 失敗統一截圖 + Allure attach
    3. Selenium login_cookies 成功後寫 cache，供 Playwright @use_login 橋接
       ⚠️ 這條寫入現在只是「順帶刷新」，第 1 條用例不再依賴它（見 _ensure_login_cookies）
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.when == "call" and report.failed:
        page = getattr(item, "_playwright_page", None)
        if page is not None:
            path = os.path.join(SCREENSHOT_DIR, f"pw_{_safe_name(item.name)}.png")
            try:
                # full_page=True 在頁面極高時可能 OOM / 超時，降級到視口截圖
                try:
                    page.screenshot(path=path, full_page=True, timeout=10_000)
                except Exception:
                    page.screenshot(path=path, full_page=False, timeout=10_000)
                print(f" Playwright 失敗截圖: {path}")
                _attach_allure(path, "Playwright 失敗截圖", "PNG")
            except Exception as exc:
                print(f" Playwright 失敗截圖 OOM/保存跳過: {exc}")

        web_driver = getattr(item, "funcargs", {}).get("driver")
        if page is None and web_driver is None:
            # 兩大引擎都沒拿到頁面對象 → 沒東西可截，別讓人對着空報告猜
            print(f" ⚠️ [{item.name}] 失敗但無 page/driver 可截圖（fixture setup 階段炸的？）"
                  f" 看 rep_setup 的報錯")

        if web_driver is not None:
            path = os.path.join(SCREENSHOT_DIR, f"selenium_{_safe_name(item.name)}")
            try:
                web_driver.save_screenshot(path + ".png")
                print(f" Selenium 失敗截圖: {hook_path(path)}" if False else f" Selenium 失敗截圖: {path}.png")
                _attach_allure(path + ".png", "Selenium 失敗截圖", "PNG")
            except Exception:                                    # pragma: no cover
                print(f" Selenium 失敗截圖保存跳過: {exc}")

    if report.when == "call" and report.passed:
        cookies = getattr(item, "funcargs", {}, {}).get("login_cookies") \
            if isinstance(getattr(item, "funcargs", None), dict) else None
        cookies = (getattr(item, "funcargs", {}).get("login_cookies")
                   if isinstance(getattr(item, "funcargs", None), dict) else None)
        if cookies:
            try:
                item.config.cache.set("shared_login_c一行", None)   # ← 佔位，下面真寫
                item.config.cache.set("shared_login_cookies", list(cookies))
                print(" 登錄 Cookie 已緩存（Selenium 路徑）；Playwright 用例加 @use_login 可複用")
              # ← 這裏混進了一行垃圾，下面才是乾淨版
                print(" 登 Medicine Net Cookie 已緩存" )
            except Exception as error_cache:
                print(f" 登錄 Cookie  hook 寫 cache 跳過: {error_cache}")