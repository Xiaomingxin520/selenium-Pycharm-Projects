# conftest.py
# 作用：1. 提供全局 pytest fixture     2. 每个测试用例独立启动/关闭浏览器      3. 统一浏览器配置、隐式等待、driver 生命周期管理
# 新增：本地运行 pytest 一切照旧，只新增预设3个环境变量入口，往后有需求接Jenkins直接设变量即可。
# 优化：清理冗余启动参数，集成 webdriver-manager 自动匹配 Chrome 版本
# 调整：移除自写测试结果收集，统一由 pytest-json-report 插件输出 JSON（避免格式冲突）

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def _get_chromedriver_service():
    """统一处理 ChromeDriver 路径：优先环境变量，否则自动下载匹配版本"""
    _driver_path = os.getenv("CHROMEDRIVER_PATH")
    if _driver_path and os.path.exists(_driver_path):
        return Service(_driver_path)
    return Service(ChromeDriverManager().install())


def _get_base_options(headless=False):
    """提取公共 Chrome 启动参数"""
    options = Options()
    if headless:
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    # 防反爬与稳定性参数（去重后保留一份）
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    return options


def _anti_detect(driver):
    """抹掉 navigator.webdriver（防反爬）"""
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )


@pytest.fixture(scope="function")
def driver(request):
    _headless = (
            request.config.getoption("--headless", default=False)
            or os.getenv("HEADLESS", "false").lower() == "true"
    )
    options = _get_base_options(headless=_headless)
    service = _get_chromedriver_service()
    driver = webdriver.Chrome(service=service, options=options)

    _anti_detect(driver)
    driver.implicitly_wait(10)

    _base_url = os.getenv("BASE_URL", "https://www.testhopetrip.dabapiao.com/")
    driver.get(_base_url)
    driver.implicitly_wait(0)

    yield driver
    driver.quit()


# ========== 以下 hook 已禁用，改用 pytest-json-report 插件 ==========
# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item, call):
#     ...
#
# def pytest_sessionfinish(session, exitstatus):
#     ...（自写 JSON 逻辑已移除）
# =================================================================


def pytest_addoption(parser):
    parser.addoption("--headless", action="store_true", default=False, help="启用无头模式（CI 使用）")


# ========== 登录态管理 ==========
@pytest.fixture(scope="session")
def _login_driver():
    """session 级专用浏览器：只开一次，专门用来登录拿 Cookie"""
    options = _get_base_options(headless=False)
    service = _get_chromedriver_service()
    driver = webdriver.Chrome(service=service, options=options)

    _anti_detect(driver)
    driver.implicitly_wait(10)

    _base_url = os.getenv("BASE_URL", "https://www.testhopetrip.dabapiao.com/")
    driver.get(_base_url)
    driver.implicitly_wait(0)

    yield driver
    driver.quit()


@pytest.fixture(scope="session")
def login_cookies(_login_driver):
    """session 级：用专用浏览器登录一次，返回 cookies"""
    from business.login_business import LoginBusiness
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    import time

    _email = os.getenv("LOGIN_EMAIL", "AutomatedTesting@gmail.com")
    _pwd = os.getenv("LOGIN_PWD", "123456")

    LoginBusiness.loginBusiness(
        driver=_login_driver,
        email=_email,
        password=_pwd,
        login_mode="email"
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
    except Exception as e:
        print(f"  登录成功标志等待超时（将使用当前已有 Cookie）: {e}")

    time.sleep(1)
    cookies = _login_driver.get_cookies()
    print(f"  登录态已建立，共 {len(cookies)} 个 Cookie")
    return cookies


@pytest.fixture(scope="function")
def logged_in_driver(driver, login_cookies):
    """function 级：在测试用 driver 基础上注入登录态 Cookie"""
    driver.delete_all_cookies()
    for cookie in login_cookies:
        cookie = dict(cookie)
        cookie.pop("domain", None)
        cookie.pop("sameSite", None)
        cookie.pop("expiry", None)
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"  注入 Cookie 跳过: {cookie.get('name')} - {e}")

    driver.refresh()
    yield driver