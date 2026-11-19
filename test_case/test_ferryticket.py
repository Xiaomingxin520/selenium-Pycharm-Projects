# test_case/test_ferryticket.py
import os
import pytest
from datetime import datetime, timedelta

from playwright.sync_api import expect
from business.ferryticket_business import FerryTicketBusiness


pytestmark = [pytest.mark.playwright, pytest.mark.ferry, pytest.mark.smoke]

DEPART_CITY = "深圳"
DEPART_PORT = "深圳蛇口碼頭"
ARRIVE_CITY = "香港"
ARRIVE_PORT = "香港國際機場海天碼頭"

BASE_URL = os.getenv("BASE_URL", "https://www.testhopetrip.dabapiao.com/").rstrip("/")
FERRY_URL = BASE_URL + "/ferry"


@pytest.fixture(scope="module")
def ferry_biz(pw_module_page):
    """test_01 与 test_02 共享同一页面状态。"""
    page = pw_module_page
    page.goto(FERRY_URL, wait_until="domcontentloaded", timeout=30_000)

    depart_trigger = page.locator("//div[@data-testid='ferry-go-depart-city-trigger']").first
    expect(depart_trigger).to_be_visible(timeout=15_000)
    print(" 船票页面就绪（出发地 trigger 可点）")

    return FerryTicketBusiness(page)


@pytest.fixture(scope="module")
def ferry_state():
    return {"route_ready": False}


def test_01_select_depart_and_arrive(ferry_biz, ferry_state):
    ferry_biz.select_ferry_route(
        depart_city=DEPART_CITY,
        depart_port=DEPART_PORT,
        arrive_city=ARRIVE_CITY,
        arrive_port=ARRIVE_PORT,
    )

    ferry_biz.verify_selection_result(
        depart_text=f"{DEPART_CITY}/{DEPART_PORT}",
        arrive_text=f"{ARRIVE_CITY}/{ARRIVE_PORT}",
    )

    ferry_state["route_ready"] = True
    print(f" test_01 通过：{DEPART_CITY}/{DEPART_PORT} → {ARRIVE_CITY}/{ARRIVE_PORT}")


def test_02_select_date_and_search(ferry_biz, ferry_state):
    if not ferry_state["route_ready"]:
        pytest.skip("test_01 未通过，跳过依赖路线状态的日期查询用例")

    page = ferry_biz.page
    target_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # 防止单独执行 test_02 或页面意外跳转。
    if "/ferry" not in page.url:
        page.goto(FERRY_URL, wait_until="domcontentloaded", timeout=30_000)
        expect(
            page.locator("//div[@data-testid='ferry-go-depart-city-trigger']").first
        ).to_be_visible(timeout=15_000)
        ferry_biz.select_ferry_route(DEPART_CITY, DEPART_PORT, ARRIVE_CITY, ARRIVE_PORT)

    # ---------- 选择明天 ----------
    picker = page.locator("div.ant-picker").first
    picker.scroll_into_view_if_needed()
    picker.click()

    dropdown = page.locator("div.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)").first
    expect(dropdown).to_be_visible(timeout=10_000)

    cell = dropdown.locator(
        f"//td[contains(@class,'ant-picker-cell') and @title='{target_date}']"
    ).first
    expect(cell).to_be_visible(timeout=10_000)

    if "ant-picker-cell-disabled" in (cell.get_attribute("class") or ""):
        raise AssertionError(f"目标日期 {target_date} 不可选：可能已截单或无班次")

    cell.click()
    expect(dropdown).to_be_hidden(timeout=10_000)
    expect(picker).to_contain_text(target_date, timeout=10_000)
    print(f" 已选日期：{target_date}")

    # ---------- 立即查询 ----------
    search_btn = page.locator("//*[@data-testid='ferry-btn-search']").first
    expect(search_btn).to_be_visible(timeout=10_000)
    search_btn.scroll_into_view_if_needed()
    search_btn.click(timeout=10_000)
    print(" 已点击【立即查询】")

    # 不依赖 networkidle：盼游首页可能有埋点长连接，业务结果出现更可靠。
    result_state = page.locator("text=/班次|航班|暫無|沒有|無可訂|可訂/").first
    expect(result_state).to_be_visible(timeout=20_000)

    # 查询后路线不能被清空。
    ferry_biz.verify_selection_result(
        depart_text=f"{DEPART_CITY}/{DEPART_PORT}",
        arrive_text=f"{ARRIVE_CITY}/{ARRIVE_PORT}",
    )

    assert "ferry" in page.url.lower(), f"查询后页面异常跳转：{page.url}"
    assert target_date in page.locator("body").inner_text(), \
        f"查询后页面未显示目标日期：{target_date}"

    print(" test_02 通过：日期选择 + 查询成功，且路线保持")