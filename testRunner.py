# testRunner.py
# 框架统一执行入口：一键执行 pytest → 生成 Allure 报告 → 发送企微通知
import argparse
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
BASE_PROJECT_NAME = "港版项目自动化测试"   # 模块名称
REPORT_HTML_DIR = Path("reports/html")   # 最终生成的 Allure HTML 报告固定目录
REPORT_HISTORY_DIR = Path("reports/allure-history/history")   # Allure 历史趋势数据目录
RESULT_JSON = Path("reports/test_result.json")   # pytest 执行后生成的测试结果 JSON 文件
TEST_CASE_DIR = "test_case"   # 测试用例目录
ALLURE_VERSION = "2.11.0"   # Allure 版本号
BASE_URL = "https://www.testhopetrip.dabapiao.com/"   # 测试环境基础 URL
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=29a3a994-f6a1-443e-b0aa-5ace281842ac"

# 模块 → pytest marker + 显示名称 映射
MODULE_CONFIG = {
    "bus":      {"marker": "bus",      "name": "大巴票模块"},
    "login":    {"marker": "login",    "name": "登录模块"},
    "all":      {"marker": "",         "name": "全量模块"},
}

# ====================== 工具函数 ======================
def generate_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def create_environment_properties(raw_dir: Path, module_name: str) -> None:
    env_file = raw_dir / "environment.properties"
    env_content = f"""projectName={BASE_PROJECT_NAME} - {module_name}
    pythonVersion=3.8.5
    allureVersion={ALLURE_VERSION}
    baseUrl={BASE_URL}
    executionTime={time.strftime("%Y-%m-%d %H:%M:%S")}
    author=Test_Team
    osName={platform.system()}
    osVersion={platform.release()}
    browserName=Chrome
    browserVersion=auto
    browserSize=1920x1080
    module={module_name}
    """
    env_file.write_text(env_content, encoding="utf-8-sig")

def copy_history_to_raw(raw_dir: Path) -> None:
    if REPORT_HISTORY_DIR.exists():
        shutil.copytree(REPORT_HISTORY_DIR, raw_dir / "history", dirs_exist_ok=True)

def persist_history_from_html() -> None:
    src = REPORT_HTML_DIR / "history"
    if src.exists():
        shutil.copytree(src, REPORT_HISTORY_DIR, dirs_exist_ok=True)

def customize_allure_report(module_name: str) -> None:
    index_html = REPORT_HTML_DIR / "index.html"
    summary_json = REPORT_HTML_DIR / "widgets/summary.json"

    if index_html.exists():
        content = index_html.read_text(encoding="utf-8")
        content = content.replace(
            "<title>Allure Report</title>",
            f"<title>{BASE_PROJECT_NAME} - {module_name} 测试报告</title>"
        )
        index_html.write_text(content, encoding="utf-8")

    if summary_json.exists():
        data = json.loads(summary_json.read_text())
        data["reportName"] = f"{BASE_PROJECT_NAME} - {module_name} 自动化测试报告"
        summary_json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def generate_allure_html(raw_dir: Path) -> None:
    subprocess.run(
        ["allure", "generate", str(raw_dir), "-o", str(REPORT_HTML_DIR), "--clean"],
        shell=True,
        check=False
    )

# ====================== 企微通知 ======================
def send_wecom_notification(start_time: datetime.datetime, module_name: str, keyword: str = None) -> None:
    end_time = datetime.datetime.now()
    duration = int((end_time - start_time).total_seconds())

    if not RESULT_JSON.exists():
        print("未找到测试结果文件，跳过企微通知")
        return

    try:
        data = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"读取测试结果 JSON 失败: {e}")
        return

    # pytest-json-report 的格式
    summary = data.get("summary", {})
    passed_count = summary.get("passed", 0)
    failed_count = summary.get("failed", 0)
    error_count = summary.get("error", 0)
    total_count = summary.get("total", 0)

    status_text = "全部通过" if (failed_count == 0 and error_count == 0) else f"存在 {failed_count} 条失败 / {error_count} 条错误"

    # ====== 工具函数：清理文本，去掉会导致 JSON 问题的字符 ======
    def clean(s):
        if s is None:
            return ""
        return str(s).replace("\r", " ").replace("\n", " ").strip()

    # Text 保底（简短，不易出错）
    text_lines = [
        f"【自动化测试运行提醒】",
        f"项目：{BASE_PROJECT_NAME}",
        f"模块：{module_name}" + (f"（关键词：{keyword}）" if keyword else ""),
        f"状态：{status_text}",
        f"结果：通过 {passed_count} / 失败 {failed_count} / 错误 {error_count} / 总计 {total_count}",
        f"耗时：{duration} 秒",
        f"时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%H:%M:%S')}"
    ]
    text_content = "\n".join(text_lines)

    try:
        requests.post(
            WEBHOOK_URL,
            json={"msgtype": "text", "text": {"content": text_content}},
            timeout=10
        )
        print(" 企微 Text 通知发送成功")
    except Exception as e:
        print(f" 企微 Text 通知失败: {e}")

    # ====== Markdown 详情（严格控制长度，避免 93017）======
    failed_tests = [t for t in data.get("tests", []) if t.get("outcome") in ("failed", "error")]

    # 失败详情（最多 3 条，每条 reason 截断到 100 字）
    fail_details = ""
    for case in failed_tests[:3]:
        nodeid = clean(case.get("nodeid", "未知用例"))
        display = nodeid.split("::")[-1] if "::" in nodeid else nodeid
        # pytest-json-report 的失败原因在 test_result.longrepr
        tr = case.get("test_result", {})
        reason = ""
        if isinstance(tr, dict):
            longrepr = tr.get("longrepr")
            if longrepr:
                reason = clean(longrepr)
        if not reason:
            reason = "无具体原因"
        if len(reason) > 100:
            reason = reason[:100] + "..."
        fail_details += f"**{display}**\n> {reason}\n\n"

    if len(failed_tests) > 3:
        fail_details += f"... 还有 {len(failed_tests) - 3} 条未展示\n"

    # 组装 markdown（总长度控制在 3500 字符以内，留余量给 4096 字节限制）
    filter_line = f"> **关键词**：{clean(keyword)}\n" if keyword else ""
    markdown_lines = [
        f"### 自动化测试运行提醒",
        f"",
        f"> **项目**：{clean(BASE_PROJECT_NAME)}",
        f"> **模块**：{clean(module_name)}",
        filter_line.rstrip(),
        f"> **状态**：{clean(status_text)}",
        f"> **结果**：通过 {passed_count} / 失败 {failed_count} / 错误 {error_count} / 总计 {total_count}",
        f"> **耗时**：{duration} 秒",
        f"",
    ]
    if failed_tests:
        markdown_lines.append(f"### 失败详情")
        markdown_lines.append(f"{fail_details.rstrip()}")
    else:
        markdown_lines.append(f"### 全部通过，无失败用例")

    markdown_content = "\n".join([l for l in markdown_lines if l])  # 去掉空行

    # 超长截断保护
    if len(markdown_content) > 3500:
        markdown_content = markdown_content[:3500] + "\n...（内容过长已截断）"

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": markdown_content}
    }

    # 调试：打印实际发送的内容长度
    payload_str = json.dumps(payload, ensure_ascii=False)
    print(f"  企微 payload 长度: {len(payload_str.encode('utf-8'))} 字节")

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"  企微响应: {resp.status_code} {resp.text}")
        if resp.json().get("errcode") == 0:
            print(" 企微 Markdown 通知发送成功")
        else:
            print(f" 企微返回错误: {resp.text}")
    except Exception as e:
        print(f" 企微 Markdown 通知失败: {e}")

def launch_allure_server_background(raw_dir: Path) -> None:
    subprocess.Popen(
        ["allure", "serve", str(raw_dir)],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# ====================== 主流程 ======================
def run_tests(module: str = "all", headless: bool = False, keyword: str = None) -> Path:
    start_time = datetime.datetime.now()
    timestamp = generate_timestamp()
    raw_dir = Path(f"reports/raw_{timestamp}")

    # 模块配置
    mod_cfg = MODULE_CONFIG.get(module, MODULE_CONFIG["all"])
    mod_display_name = mod_cfg["name"]
    mod_marker = mod_cfg["marker"]

    print("=" * 60)
    print(f" 开始执行自动化测试")
    print(f" 模块：{mod_display_name}")
    if keyword:
        print(f" 关键词过滤：-k {keyword}")
    print(f" 时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 清旧结果
    if RESULT_JSON.exists():
        RESULT_JSON.unlink()

    raw_dir.mkdir(parents=True, exist_ok=True)
    REPORT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    copy_history_to_raw(raw_dir)

    print("\n正在执行 pytest 用例...")

    pytest_args = [
        TEST_CASE_DIR,
        f"--alluredir={raw_dir}",
        "--clean-alluredir",
        "-v",
        "--json-report",
        f"--json-report-file={RESULT_JSON}",
    ]

    # 分模块：指定 marker
    if mod_marker:
        pytest_args.insert(2, "-m")
        pytest_args.insert(3, mod_marker)

    # 关键词过滤
    if keyword:
        pytest_args.insert(2, "-k")
        pytest_args.insert(3, keyword)

    if headless:
        pytest_args.append("--headless")

    pytest.main(pytest_args)

    create_environment_properties(raw_dir, mod_display_name)

    print("\n正在生成 Allure HTML 报告...")
    generate_allure_html(raw_dir)

    persist_history_from_html()
    customize_allure_report(mod_display_name)

    # 发送企微通知
    print("\n正在发送企微通知...")
    send_wecom_notification(start_time, mod_display_name, keyword)

    # 后台启动 Allure 服务
    print("\n正在后台启动 Allure 服务...")
    launch_allure_server_background(raw_dir)

    print(f"\n报告路径：{REPORT_HTML_DIR / 'index.html'}")
    return REPORT_HTML_DIR / "index.html"

# ====================== 入口 ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动化测试 Runner")
    parser.add_argument(
        "--module", "-m",
        default="all",
        choices=["bus", "login", "all"],
        help="指定执行模块: bus=车票, login=登录, all=全量 (默认: all)"
    )
    parser.add_argument(
        "--keyword", "-k",
        default=None,
        help="pytest -k 关键词过滤（如 'confirm'）"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式（CI/Jenkins 使用）"
    )

    args = parser.parse_args()

    # # 清理残留 Chrome 进程（Windows）
    # if platform.system() == "Windows":
    #     os.system('taskkill /f /im chromedriver.exe >nul 2>&1')
    #     os.system('taskkill /f /im chrome.exe >nul 2>&1')

    report_path = run_tests(module=args.module, headless=args.headless, keyword=args.keyword)
    print(f"\n报告生成路径：{report_path}")