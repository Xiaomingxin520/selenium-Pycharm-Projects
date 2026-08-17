# conftest.py
# 作用：
# 1. 提供全局 pytest fixture
# 2. 每个测试用例独立启动/关闭浏览器
# 3. 统一浏览器配置、隐式等待、driver 生命周期管理

import json
import pytest
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# ✅ 新增：测试结果收集
# 用于存储所有通过的用例信息
PASSED_CASES = []
# 用于存储所有失败的用例信息
FAILED_CASES = []

# function 级 fixture：每个测试用例单独启动一个 Chrome 浏览器，测试结束后自动 quit，防止进程残留
@pytest.fixture(scope="function")
def driver():
    # 1. 浏览器启动参数配置
    options = Options()

    # ✅ 必须关掉，否则会被检测为 Selenium
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # ✅ 禁用沙箱 & GPU（Windows / CI 都稳）
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    # ✅ 防止首次启动慢
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")

    # 窗口最大化（避免元素不可点击）
    options.add_argument("--start-maximized")

    # 禁用 GPU 加速（防止部分机器渲染异常）
    options.add_argument("--disable-gpu")

    # 非沙箱模式（CI / Docker / 服务器环境常用）
    options.add_argument("--no-sandbox")

    # 解决 Linux / Docker 下共享内存不足问题
    options.add_argument("--disable-dev-shm-usage")

    # 可选：禁用自动化提示条（更贴近真实用户）
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 2. 启动 ChromeDriver
    # 指定本地 ChromeDriver 路径
    service = Service(r"D:\Chromedriver\chromedriver.exe")
    # 实例化 Chrome 浏览器对象
    driver = webdriver.Chrome(service=service, options=options)

    # ✅ 抹掉 navigator.webdriver（防反爬）
    # 通过 Chrome DevTools Protocol 注入 JavaScript，覆盖 webdriver 属性
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        }
    )

    # 隐式等待 10 秒
    driver.implicitly_wait(10)

    # 3. 全局基础配置：打开测试环境
    driver.get("https://www.testhopetrip.dabapiao.com/")
    # 显式等待（WebDriverWait）为主，隐式等待为辅：设置为 0，避免与 WebDriverWait 叠加造成 ~20s 超时
    driver.implicitly_wait(0)

    # 4. 返回 driver 给测试用例
    yield driver

    # 5. 用例结束，清理资源
    driver.quit()

# ✅ 新增：收集每条用例结果（已优化为中文用例名 + 精简原因）
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # 获取测试用例的执行结果
    outcome = yield
    report = outcome.get_result()

    # 只在测试用例执行阶段（call）进行处理
    if report.when == "call":
        # ✅ 优先用 allure.title，其次用 docstring，最后用 nodeid 提取用例显示名称
        display_name = _extract_display_name(item)

        # 判断用例是否通过
        if report.passed:
            PASSED_CASES.append({
                "name": report.nodeid,      # 用例节点 ID
                "display": display_name     # 用例显示名称
            })
        # 判断用例是否失败
        elif report.failed:
            # 提取失败原因（精简版）
            reason = _extract_failure_reason(report)
            FAILED_CASES.append({
                "name": report.nodeid,      # 用例节点 ID
                "display": display_name,    # 用例显示名称
                "reason": reason            # 失败原因
            })

# ✅ 新增：测试结束后把结果写到一个 JSON 文件（供 testRunner 读取）
def pytest_sessionfinish(session, exitstatus):
    # 定义测试结果文件路径
    result_file = Path("reports/test_result.json")
    # 确保 reports 目录存在
    result_file.parent.mkdir(parents=True, exist_ok=True)

    # 将收集到的测试结果写入 JSON 文件
    json.dump({
        "passed": PASSED_CASES,   # 通过的用例列表
        "failed": FAILED_CASES,   # 失败的用例列表
        "exit_code": exitstatus   # pytest 退出码
    }, result_file.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 控制台打印成功写入提示
    print(f"✅ 测试结果已写入: {result_file}")

def _extract_display_name(item) -> str:
    """
    提取中文用例名：
    1. allure.title
    2. 函数 docstring
    3. 参数化 ids
    4. nodeid 兜底
    """
    # 1. allure.title（最优先，通常写在测试用例上方）
    allure_marker = item.get_closest_marker("allure")
    if allure_marker and allure_marker.kwargs.get("title"):
        return allure_marker.kwargs["title"]

    # 2. 函数 docstring（测试用例的文档注释）
    if item.function.__doc__:
        return item.function.__doc__.strip().split("\n")[0]

    # 3. 参数化 ids（pytest.mark.parametrize 中定义的 ids）
    if hasattr(item, "callspec"):
        raw_id = item.callspec.id
        if raw_id:
            return raw_id

    # 4. nodeid 兜底（去掉路径和函数名，保留参数部分）
    name = item.nodeid.split("::")[-1]
    if "[" in name:
        name = name.split("[")[-1].rstrip("]")
    return name

def _extract_failure_reason(report) -> str:
    """
    只取第一行 AssertionError，去掉堆栈和 chromedriver 日志
    """
    # 如果没有长报告（异常信息），返回未知错误
    if not report.longrepr:
        return "未知错误"

    # reprcrash.message 是最干净的断言信息（通常是我们 assert 后面的描述）
    if hasattr(report.longrepr, "reprcrash") and report.longrepr.reprcrash.message:
        msg = report.longrepr.reprcrash.message
        # 如果信息过长，进行截断
        return msg[:120] + "..." if len(msg) > 120 else msg

    # 兜底：取最后一行（通常是最核心的错误信息）
    lines = str(report.longrepr).strip().split("\n")
    # 如果最后一行过长，进行截断
    return lines[-1][:120] + "..." if len(lines[-1]) > 120 else lines[-1]