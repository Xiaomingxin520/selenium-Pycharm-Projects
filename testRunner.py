# testRunner.py
# 框架统一执行入口：一键执行 pytest → 生成 Allure 报告 → 发送企微通知
import datetime
import json
import shutil
import subprocess
import time
import platform
from pathlib import Path
import requests
import pytest

# ====================== 全局常量 ======================
PROJECT_NAME = "港版PC端登录自动化测试"   # 项目名称，用于报告标题和企微通知
REPORT_HTML_DIR = Path("reports/html")   # 最终生成的 Allure HTML 报告固定目录
REPORT_HISTORY_DIR = Path("reports/allure-history/history")   # Allure 历史趋势数据目录，用于保留历史执行记录
RESULT_JSON = Path("reports/test_result.json")   # pytest 执行后生成的测试结果 JSON 文件
TEST_CASE_DIR = "test_case"   # 测试用例目录
ALLURE_VERSION = "2.11.0"   # Allure 版本号，写入环境信息
BASE_URL = "https://www.testhopetrip.dabapiao.com/"   # 测试环境基础 URL
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=29a3a994-f6a1-443e-b0aa-5ace281842ac"   # 企业微信机器人 Webhook 地址

# ====================== 工具函数 ======================
def generate_timestamp() -> str:
    """生成时间戳，用于区分每次执行的原始数据目录"""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def create_environment_properties(raw_dir: Path) -> None:
    """创建 environment.properties 文件，用于 Allure 报告展示环境信息"""
    env_file = raw_dir / "environment.properties"
    env_content = f"""projectName={PROJECT_NAME}
    pythonVersion=3.8.5
    allureVersion={ALLURE_VERSION}
    baseUrl={BASE_URL}
    executionTime={time.strftime("%Y-%m-%d %H:%M:%S")}
    author=Test_Team
    osName={platform.system()}
    osVersion={platform.release()}
    browserName=Chrome
    browserVersion=87.0.4280.88
    browserSize=1920x1080
    """
    # 使用 UTF-8-sig 编码写入，防止中文乱码
    env_file.write_text(env_content, encoding="utf-8-sig")

def copy_history_to_raw(raw_dir: Path) -> None:
    """将历史趋势数据复制到本次执行的原始数据目录，保证趋势连续性"""
    if REPORT_HISTORY_DIR.exists():
        shutil.copytree(REPORT_HISTORY_DIR, raw_dir / "history", dirs_exist_ok=True)

def persist_history_from_html() -> None:
    """从生成的 HTML 报告中提取最新的历史数据，供下次执行使用"""
    src = REPORT_HTML_DIR / "history"
    if src.exists():
        shutil.copytree(src, REPORT_HISTORY_DIR, dirs_exist_ok=True)

def customize_allure_report() -> None:
    """自定义 Allure 报告展示内容：修改浏览器标题和报告大标题"""
    index_html = REPORT_HTML_DIR / "index.html"
    summary_json = REPORT_HTML_DIR / "widgets/summary.json"

    # 修改浏览器 Tab 标题
    if index_html.exists():
        content = index_html.read_text(encoding="utf-8")
        content = content.replace(
            "<title>Allure Report</title>",
            f"<title>{PROJECT_NAME} 测试报告</title>"
        )
        index_html.write_text(content, encoding="utf-8")

    # 修改报告内的大标题
    if summary_json.exists():
        data = json.loads(summary_json.read_text())
        data["reportName"] = f"{PROJECT_NAME} 自动化测试报告"
        summary_json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def run_pytest(raw_dir: Path) -> int:
    """执行 pytest 测试用例，并生成 Allure 原始数据"""
    return pytest.main([
        TEST_CASE_DIR,
        f"--alluredir={raw_dir}",
        "--clean-alluredir"
    ])

def generate_allure_html(raw_dir: Path) -> None:
    """根据 Allure 原始数据生成 HTML 报告"""
    subprocess.run(
        ["allure", "generate", str(raw_dir), "-o", str(REPORT_HTML_DIR), "--clean"],
        shell=True,  # Windows 下需要 shell=True
        check=False
    )

# ======================
# ✅ 企微通知（Text + Markdown，失败详情干净）
# ======================
def send_wecom_notification(start_time: datetime.datetime) -> None:
    """发送测试结果到企业微信，包含 Text 保底和 Markdown 详情"""
    end_time = datetime.datetime.now()
    duration = int((end_time - start_time).total_seconds())

    # 如果结果文件不存在，跳过通知
    if not RESULT_JSON.exists():
        print("⚠️ 未找到测试结果文件，跳过企微通知")
        return

    # 读取 pytest 执行结果
    data = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
    passed = data.get("passed", [])
    failed = data.get("failed", [])

    passed_count = len(passed)
    failed_count = len(failed)
    status_text = "全部通过" if failed_count == 0 else f"存在 {failed_count} 条失败"

    # -------- Text 通知（保底，确保一定能收到）--------
    text_content = (
        f"【自动化测试运行提醒】\n"
        f"项目：{PROJECT_NAME}\n"
        f"状态：{status_text}\n"
        f"通过：{passed_count} 条\n"
        f"失败：{failed_count} 条\n"
        f"耗时：{duration} 秒\n"
        f"开始：{start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"结束：{end_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        requests.post(
            WEBHOOK_URL,
            json={"msgtype": "text", "text": {"content": text_content}},
            timeout=10
        )
        print("企微 Text 通知发送成功")
    except Exception as e:
        print(f"企微 Text 通知失败: {e}")

    # -------- Markdown 通知（详情，展示失败用例具体原因）--------
    fail_details = ""
    # 只展示前 5 条失败用例，避免消息过长
    for case in failed[:5]:
        display = case.get("display", "未知用例")
        reason = case.get("reason", "无具体原因")
        fail_details += f"**{display}**\n> {reason}\n\n"

    if failed_count > 5:
        fail_details += f"... 还有 {failed_count - 5} 条未展示\n"

    markdown_content = (
        f"###  自动化测试运行提醒\n\n"
        f"> ** 项目**：{PROJECT_NAME}\n"
        f"> ** 状态**：{status_text}\n"
        f"> ** 结果**：通过 {passed_count} 条 / 失败 {failed_count} 条\n"
        f"> ** 耗时**：{duration} 秒\n\n"
        f"###  失败详情\n"
        f"{fail_details if failed_count > 0 else '🎉 全部通过'}"
    )

    try:
        requests.post(
            WEBHOOK_URL,
            json={"msgtype": "markdown", "markdown": {"content": markdown_content}},
            timeout=10
        )
        print("企微 Markdown 通知发送成功")
    except Exception as e:
        print(f"企微 Markdown 通知失败: {e}")


def launch_allure_server_background(raw_dir: Path) -> None:
    """后台启动 Allure 服务，避免阻塞主流程"""
    subprocess.Popen(
        ["allure", "serve", str(raw_dir)],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# ====================== 主流程 ======================
def run_tests() -> Path:
    """统一测试执行入口，编排整个测试流程"""
    start_time = datetime.datetime.now()
    timestamp = generate_timestamp()
    raw_dir = Path(f"reports/raw_{timestamp}")

    print("=" * 50)
    print(f"开始执行自动化测试 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 清旧结果，防止读取到历史脏数据
    if RESULT_JSON.exists():
        RESULT_JSON.unlink()

    raw_dir.mkdir(parents=True, exist_ok=True)
    REPORT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    # 拷贝历史数据，保证趋势图连续
    copy_history_to_raw(raw_dir)

    print("\n正在执行 pytest 用例...")
    pytest.main([TEST_CASE_DIR, f"--alluredir={raw_dir}", "--clean-alluredir"])

    # 写入环境信息
    create_environment_properties(raw_dir)

    print("\n正在生成 Allure HTML 报告...")
    generate_allure_html(raw_dir)

    # 持久化历史数据
    persist_history_from_html()

    # 定制报告标题
    customize_allure_report()

    # print("\n正在发送企微通知...")
    # send_wecom_notification(start_time)

    # 后台启动 Allure 服务
    launch_allure_server_background(raw_dir)

    print(f"\n报告路径：{REPORT_HTML_DIR / 'index.html'}")
    return REPORT_HTML_DIR / "index.html"

# ====================== 入口 ======================
if __name__ == "__main__":
    # 清理残留的 Chrome 进程，防止端口占用
    # print("🧹 清理残留 Chrome 进程...")
    # os.system('taskkill /f /im chromedriver.exe >nul 2>&1')
    # os.system('taskkill /f /im chrome.exe >nul 2>&1')

    report_path = run_tests()
    print(f"\n报告生成路径：{report_path}")