# testRunner.py
# 框架统一执行入口：pytest -> Allure -> 企微通知
# Selenium(test_case) / Playwright(test_case_pw) 双引擎共存，靠 marker 分流
import argparse
import datetime
import json
import os
import shutil
import subprocess
import time
import platform
from pathlib import Path

import requests
import pytest

BASE_PROJECT_NAME = "港版项目自动化测试"
REPORT_HTML_DIR = Path("reports/html")
REPORT_HISTORY_DIR = Path("reports/allure-history/history")
RESULT_JSON = Path("reports/test_result.json")
ALLURE_VERSION = os.getenv("ALLURE_VERSION", "2.11.0")
BASE_URL = os.getenv("BASE_URL", "https://www.testhopetrip.dabapiao.com/")
WEBHOOK_URL = os.getenv(
    "WECOM_WEBHOOK",
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=29a3a994-f6a1-443e-b0aa-5ace281842ac",
)

SELENIUM_DIR = "test_case"
PLAYWRIGHT_DIR = "test_case_pw"

MODULE_CONFIG = {
    "bus":     {"marker": "bus",    "name": "大巴票模块", "engine": "auto"},
    "login":   {"marker": "login",  "name": "登录模块",   "engine": "auto"},
    "ferry":   {"marker": "ferry",  "name": "船票模块",   "engine": "auto"},
    "smoke":   {"marker": "smoke",  "name": "冒烟模块",   "engine": "auto"},
    "pw":      {"marker": "",       "name": "Playwright全量", "engine": "pw"},
    "selenium":{"marker": "",       "name": "Selenium全量",  "engine": "selenium"},
    "all":     {"marker": "",       "name": "全量模块",   "engine": "both"},
}


def generate_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _py_version() -> str:
    import sys
    return ".".join(str(x) for x in sys.version_info[:3])


def create_environment_properties(raw_dir: Path, module_name: str, engine: str) -> None:
    env_file = raw_dir / "environment.properties"
    lines = [
        f"projectName={BASE_PROJECT_NAME} - {module_name}",
        f"pythonVersion={_py_version()}",
        f"allureVersion={ALLURE_VERSION}",
        f"baseUrl={BASE_URL}",
        f"engine={engine}",
        f"executionTime={time.strftime('%Y-%m-%d %H:%M:%S')}",
        "author=Test_Team",
        f"osName={platform.system()}",
        f"osVersion={platform.release()}",
        "browserName=Chrome",
        "browserSize=1920x1080",
        f"module={module_name}",
    ]
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            lines.append(f"playwrightVersion={p.chromium.version}")
    except Exception:
        lines.append("playwrightVersion=N/A")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_history_to_raw(raw_dir: Path) -> None:
    if REPORT_HISTORY_DIR.exists():
        shutil.copytree(REPORT_HISTORY_DIR, raw_dir / "history", dirs_exist_ok=True)


def persist_history_from_html() -> None:
    src = REPORT_HTML_DIR / "history"
    if src.exists():
        shutil.copytree(src, REPORT_HISTORY_DIR, dirs_exist_ok=True)


def customize_allure_report(module_name: str) -> None:
    index_html = REPORT_HTML_DIR / "index.html"
    summary_json = REPORT_HTML_DIR / "widgets" / "summary.json"

    if index_html.exists():
        content = index_html.read_text(encoding="utf-8")
        content = content.replace(
            "<title>Allure Report</title>",
            f"<title>{BASE_PROJECT_NAME} - {module_name} 测试报告</title>",
        )
        index_html.write_text(content, encoding="utf-8")

    if summary_json.exists():
        try:
            data = json.loads(summary_json.read_text(encoding="utf-8"))
            data["reportName"] = f"{BASE_PROJECT_NAME} - {module_name} 自动化测试报告"
            summary_json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            print(f"Allure summary.json 改写跳过: {exc}")


def generate_allure_html(raw_dir: Path) -> bool:
    try:
        proc = subprocess.run(
            ["allure", "generate", str(raw_dir), "-o", str(REPORT_HTML_DIR), "--clean"],
            shell=(platform.system() == "Windows"),
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(f"allure generate 返回 {proc.returncode}: {(proc.stderr or '')[:300]}")
            return False
        return (REPORT_HTML_DIR / "index.html").exists()
    except FileNotFoundError:
        print("未找到 allure 命令，跳过 HTML 生成（scoop install allure / choco install allure）")
        return False
    except Exception as exc:
        print(f"allure generate 异常: {exc}")
        return False


def read_json_report() -> dict:
    if not RESULT_JSON.exists():
        return {}
    for _ in range(3):
        try:
            return json.loads(RESULT_JSON.read_text(encoding="utf-8"))
        except Exception:
            time.sleep(0.5)
    print("测试结果 JSON 解析失败，通知将使用兜底数据")
    return {}


def _clean(s, limit: int = 0) -> str:
    if s is None:
        return ""
    txt = str(s).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    while "  " in txt:
        txt = txt.replace("  ", " ")
    txt = txt.strip()
    if limit and len(txt) > limit:
        txt = txt[:limit] + "..."
    return txt


def _extract_reason(case: dict) -> str:
    tr = case.get("test_result") or {}
    longrepr = tr.get("longrepr") if isinstance(tr, dict) else None
    if not longrepr:
        longrepr = case.get("longrepr") or ""
    if isinstance(longrepr, dict):
        longrepr = longrepr.get("reprtraceback") or longrepr.get("message") or str(longrepr)
    txt = _clean(longrepr)
    for marker in ("AssertionError", "TimeoutError", "Element is not", "waiting for locator"):
        if marker in txt:
            idx = txt.find(marker)
            txt = txt[idx:idx + 220]
            break
    return txt or "无具体原因"


def build_notice(start_time, end_time, module_name, keyword, engine_label, data) -> tuple:
    duration = int((end_time - start_time).total_seconds())
    summary = data.get("summary", {}) if data else {}
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("error", 0)
    skipped = summary.get("skipped", 0)
    total = summary.get("total", 0)

    if total == 0:
        status = "未收集到用例（检查 -m / -k 过滤条件）"
    elif failed == 0 and errors == 0:
        status = "全部通过"
    else:
        status = f"存在 {failed} 条失败 / {errors} 条错误"

    failed_tests = []
    if data:
        failed_tests = [t for t in data.get("tests", []) if t.get("outcome") in ("failed", "error")]

    text_lines = [
        "【自动化测试运行提醒】",
        f"项目：{BASE_PROJECT_NAME}",
        f"模块：{module_name}（引擎：{engine_label}）",
        f"状态：{status}",
        f"结果：通过 {passed} / 失败 {failed} / 错误 {errors} / 跳过 {skipped} / 总计 {total}",
        f"耗时：{duration} 秒",
        f"时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%H:%M:%S')}",
    ]

    md = [
        "### 自动化测试运行提醒",
        f"> **项目**：{_clean(BASE_PROJECT_NAME)}",
        f"> **模块**：{_clean(module_name)}",
        f"> **引擎**：{engine_label}",
    ]
    if keyword:
        md.append(f"> **关键词**：{_clean(keyword, 80)}")
    md += [
        f"> **状态**：{_clean(status)}",
        f"> **结果**：通过 {passed} / 失败 {failed} / 错误 {errors} / 跳过 {skipped} / 总计 {total}",
        f"> **耗时**：{duration} 秒",
        "",
    ]

    if failed_tests:
        md.append("### 失败详情")
        for case in failed_tests[:3]:
            nodeid = _clean(case.get("nodeid", "未知用例"))
            display = nodeid.split("::")[-1] if "::" in nodeid else nodeid
            reason = _extract_reason(case)
            md.append(f"**{_clean(display, 60)}**")
            md.append(f"> {_clean(reason, 200)}")
        if len(failed_tests) > 3:
            md.append(f"> ...还有 {len(failed_tests) - 3} 条未展示")
    else:
        md.append("### 全部通过，无失败用例")

    return "\n".join(text_lines), "\n".join(md)


def send_wecom_notification(start_time, module_name, keyword, engine_label, data) -> None:
    end_time = datetime.datetime.now()
    text_content, markdown_content = build_notice(
        start_time, end_time, module_name, keyword, engine_label, data
    )

    def post(payload: dict, tag: str) -> None:
        body_len = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        print(f"  企微 {tag} payload: {body_len} 字节")
        if body_len > 3800:
            print(f"  企微 {tag} 内容超长，已放弃发送（93017 风险）")
            return
        try:
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            result = resp.json()
            if result.get("errcode") == 0:
                print(f" 企微 {tag} 通知发送成功")
            else:
                print(f" 企微 {tag} 返回错误: {resp.text}")
        except Exception as exc:
            print(f" 企微 {tag} 通知失败: {exc}")

    post({"msgtype": "text", "text": {"content": text_content}}, "Text")

    md = markdown_content
    if len(md.encode("utf-8")) > 3500:
        md = md[:2400] + "\n...（内容过长已截断，完整信息看 Allure 报告）"
    post({"msgtype": "markdown", "markdown": {"content": md}}, "Markdown")


def launch_allure_server_background(raw_dir: Path) -> None:
    try:
        subprocess.Popen(
            ["allure", "serve", str(raw_dir)],
            shell=(platform.system() == "Windows"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        print(f"allure serve 启动跳过: {exc}")


def collect_ids(targets, args) -> list:
    """用 pytest --collect-only 预检，拿不到用例直接告警，避免'全绿 0 条'假象。"""
    cmd = ["-p", "no:cacheprovider", "--collect-only", "-q", "--no-header"]
    cmd += targets
    if args.get("marker"):
        cmd += ["-m", args["marker"]]
    if args.get("keyword"):
        cmd += ["-k", args["keyword"]]
    try:
        proc = subprocess.run(
            [os.sys.executable, "-m", "pytest"] + cmd,
            capture_output=True, text=True, check=False,
            cwd=os.getcwd(),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            print(f"用例收集告警（returncode={proc.returncode}）:\n{out[-800:]}")
            return []
        for line in out.splitlines():
            s = line.strip()
            if s.endswith("test item") or s.endswith("tests collected"):
                print(f"  收集到用例: {s}")
        if "no tests collected" in out or "collected 0 items" in out:
            print("  警告：0 条用例被收集，通知会标红提示，请检查 marker / -k")
        return []
    except Exception as exc:
        print(f"用例收集预检跳过: {exc}")
        return []


def run_tests(module: str = "all", headless: bool = False, keyword: str = None,
              engine: str = None, serve: bool = False) -> Path:
    start_time = datetime.datetime.now()
    timestamp = generate_timestamp()
    raw_dir = Path(f"reports/raw_{timestamp}")

    mod_cfg = MODULE_CONFIG.get(module, MODULE_CONFIG["all"])
    mod_display_name = mod_cfg["name"]
    mod_marker = mod_cfg["marker"]
    engine_mode = (engine or mod_cfg.get("engine") or "both").lower()

    if engine_mode == "pw":
        targets, engine_label = [PLAYWRIGHT_DIR], "Playwright"
    elif engine_mode == "selenium":
        targets, engine_label = [SELENIUM_DIR], "Selenium"
    else:
        targets, engine_label = [SELENIUM_DIR, PLAYWRIGHT_DIR], "Selenium+Playwright"

    print("=" * 60)
    print(f" 开始执行自动化测试")
    print(f" 模块：{mod_display_name}   引擎：{engine_label}")
    print(f" 目录：{targets}")
    if mod_marker:
        print(f" 标记：-m {mod_marker}")
    if keyword:
        print(f" 关键词：-k {keyword}")
    print(f" 无头：{headless}")
    print(f" 时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    collect_ids(targets, {"marker": mod_marker, "keyword": keyword})

    if RESULT_JSON.exists():
        try:
            RESULT_JSON.unlink()
        except Exception:
            pass

    raw_dir.mkdir(parents=True, exist_ok=True)
    REPORT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    copy_history_to_raw(raw_dir)

    print("\n正在执行 pytest 用例...")
    pytest_args = [
        *targets,
        f"--alluredir={raw_dir}",
        "--clean-alluredir",
        "-v",
        "--json-report",
        f"--json-report-file={RESULT_JSON}",
        "--json-report-summary",
    ]
    if mod_marker:
        pytest_args += ["-m", mod_marker]
    if keyword:
        pytest_args += ["-k", keyword]
    if headless:
        pytest_args += ["--headless"]

    exit_code = pytest.main(pytest_args)
    print(f"\npytest exit code = {exit_code}"
          f"（0=全通过 1=有失败 2=中断 3=内部错误 4=用法错误 5=未收集到用例）")

    create_environment_properties(raw_dir, mod_display_name, engine_label)

    print("\n正在生成 Allure HTML 报告...")
    if generate_allure_html(raw_dir):
        persist_history_from_html()
        customize_allure_report(mod_display_name)
    else:
        print("Allure HTML 未生成，原始结果保留在：" + str(raw_dir))

    print("\n正在发送企微通知...")
    send_wecom_notification(start_time, mod_display_name, keyword, engine_label, read_json_report())

    if serve:
        print("\n正在后台启动 Allure 服务...")
        launch_allure_server_background(raw_dir)

    report_path = REPORT_HTML_DIR / "index.html"
    print(f"\n报告路径：{report_path}")
    return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动化测试 Runner（Selenium + Playwright）")
    parser.add_argument("--module", "-m", default="all",
                        choices=list(MODULE_CONFIG.keys()),
                        help="bus/login/ferry/smoke/pw/selenium/all（默认 all）")
    parser.add_argument("--engine", "-e", default=None,
                        choices=["auto", "pw", "selenium", "both"],
                        help="覆盖引擎：pw=只跑 test_case_pw，selenium=只跑 test_case，both=两套都跑")
    parser.add_argument("--keyword", "-k", default=None,
                        help="pytest -k 过滤（如 'test_01 or pay_01'）")
    parser.add_argument("--headless", action="store_true", help="无头模式（CI/Jenkins）")
    parser.add_argument("--serve", action="store_true", help="跑完后台 allure serve")
    parser.add_argument("--no-notify", action="store_true", help="不发企微通知（本地调试）")
    args = parser.parse_args()

    if args.no_notify:
        WEBHOOK_URL = ""

    report_path = run_tests(
        module=args.module,
        headless=args.headless,
        keyword=args.keyword,
        engine=args.engine,
        serve=args.serve,
    )
    print(f"\n报告生成路径：{report_path}")