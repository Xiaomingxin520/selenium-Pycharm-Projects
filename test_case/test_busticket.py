# -*- coding: utf-8 -*-
"""
test_case_pw/test_busticket.py —— 大巴票用例層（Playwright 版）
"""
from datetime import datetime, timedelta

import pytest
from playwright.sync_api import Page, expect

from business.busticket_business import BusticketBusiness

pytestmark = pytest.mark.bus          # 文件級 mark，與原版每個函數掛 @pytest.mark.bus 等價


# ---------------- 內部工具：日期斷言（消掉兩處重複 + 加兜底告警） ----------------
def _assert_date_in_url(page: Page, biz: BusticketBusiness, tag: str = "") -> str:
    """
    斷言 URL 含 date={biz.target_date}；target_date 爲空時回落 today+2 並【告警】。
    ⚠️ 判定邏輯與原版逐字一致，只多一行告警 print。
    """
    expected_date = biz.target_date
    if not expected_date:
        expected_date = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        print(f" ⚠️ [{tag}] biz.target_date 爲空，回落到本地推算 {expected_date}"
              f" —— 這說明 BusHomePage.select_date_two_days_later() 沒拿到日期，"
              f"屬於 page 層問題，建議排查（跨月/滿房跳日也會觸發）")

    current_url = page.url
    assert f"date={expected_date}" in current_url, \
        f"URL缺少日期参数: 期望 date={expected_date}, 实际 {current_url}"
    print(f"{tag}日期校验通过: date={expected_date}")
    return expected_date


def _assert_map_modals(biz: BusticketBusiness, tag: str = "") -> None:
    """上下車地圖彈窗校驗+關閉。與原版 6 行逐字等價，抽函數純爲消重（用例數不變）。"""
    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal(), "上車地圖弹窗校验失败"
    biz.result.close_map_modal()
    biz.result.wait_map_closed()          # 原 business 裏的 sleep(0.5) 已由這句接管

    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal(), "下車地圖弹窗校验失败"
    biz.result.close_map_modal()
    biz.result.wait_map_closed()


# ==================== 遊客態 ====================

def test_bus_select_depart_station(pw_module_page: Page):
    """
    前置：conftest_pw.py 已提供 pw_module_page（遊客態 module 級 page）
    场景：官网首页点击大巴票 -> /bus -> 选择出发城市(深圳) + 站点(深圳湾香港段上)
    断言：出发输入框最终显示目标站点（先跑通交互，不做完整下单）
    """
    biz = BusticketBusiness(pw_module_page)

    biz.enter_bus_and_search(
        depart_city="深圳",
        depart_station="深圳灣（香港段上）",
        arrive_city="香港",
        arrive_station="尖沙咀海港城"
    )

    _assert_date_in_url(pw_module_page, biz, tag="遊客態-")

    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal()
    biz.result.close_map_modal()
    biz.result.wait_map_closed()

    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal()
    biz.result.close_map_modal()
    biz.result.wait_map_closed()

    biz.result.click_last_trip_ticket()   # 內部已等 URL 含 create-order
    assert "create-order" in pw_module_page.url, " 未跳转到下单页"
    print(" 购票跳转断言通过！")


# @pytest.mark.bus
# def test_bus_add_adult_on_order_page(pw_module_page: Page):
#     biz = BusticketBusiness(pw_module_page)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_and_add_adult()
#     print(" 成人+号全链路测试通过！")
#
# @pytest.mark.bus
# def test_bus_add_child_on_order_page(pw_module_page: Page):
#     biz = BusticketBusiness(pw_module_page)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_and_add_child()
#     print(" 兒童+号全链路测试通过！")
#
# @pytest.mark.bus
# def test_bus_add_elder_on_order_page(pw_module_page: Page):
#     biz = BusticketBusiness(pw_module_page)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_and_add_elder()
#     print(" 長者+号全链路测试通过！")
#
# @pytest.mark.bus
# @pytest.mark.parametrize("adult,child,elder,case_name", [
#     (1, 0, 0, "登录态-只成人"),
#     (0, 1, 0, "登录态-只儿童"),
#     (0, 0, 1, "登录态-只长者"),
#     (1, 1, 0, "登录态-只成人儿童"),
#     (1, 0, 1, "登录态-只成人长者"),
#     (0, 1, 1, "登录态-只儿童长者"),
#     (1, 1, 1, "登录态-三者全选"),
#     (0, 0, 0, "登录态-无乘客"),
# ], ids=lambda x: x if isinstance(x, str) else "")
# def test_bus_passenger_combinations(pw_module_page: Page, adult, child, elder, case_name):
#     print(f"\n 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
#     biz = BusticketBusiness(pw_module_page)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_page()
#     biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)
#     print(f" {case_name} 场景测试通过！")

# ========== 后续接 CSV 时，只需改这里 ==========
# @pytest.mark.bus
# def test_bus_passenger_from_csv(pw_module_page: Page, passenger_combination):
#     adult, child, elder, case_name, _ = passenger_combination
#     biz = BusticketBusiness(pw_module_page)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_page()
#     biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)
#     print(f" {case_name} 场景测试通过！")


# ==================== 登錄態 ====================

def test_bus_select_depart_station_with_login(pw_module_page_logged_in: Page):
    """
    登录态场景：官网首页点击大巴票 -> /bus -> 选择出发城市(深圳) + 站点(深圳湾香港段上)
    断言：出发输入框最终显示目标站点 + 日期参数 + 购票跳转
    """
    biz = BusticketBusiness(pw_module_page_logged_in)

    biz.enter_bus_and_search(
        depart_city="深圳",
        depart_station="深圳灣（香港段上）",
        arrive_city="香港",
        arrive_station="尖沙咀海港城"
    )

    _assert_date_in_url(pw_module_page_logged_in, biz, tag="登錄態-")

    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal()
    biz.result.close_map_modal()
    biz.result.wait_map_closed()

    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal()
    biz.result.close_map_modal()
    biz.result.wait_map_closed()

    biz.result.click_last_trip_ticket()
    assert "create-order" in pw_module_page_logged_in.url, " 未跳转到下单页"
    print(" 登录态-购票跳转断言通过！")


@pytest.mark.parametrize("adult,child,elder,case_name", [
    (1, 0, 0, "登录态-只成人"),
    (0, 1, 0, "登录态-只儿童"),
    (0, 0, 1, "登录态-只长者"),
    (1, 1, 0, "登录态-只成人儿童"),
    (1, 0, 1, "登录态-只成人长者"),
    (0, 1, 1, "登录态-只儿童长者"),
    (1, 1, 1, "登录态-三者全选"),
    (0, 0, 0, "登录态-无乘客"),   # ⚠️ 邊界用例·會真提交 0 人訂單（測後端攔截），勿當筆誤刪
], ids=lambda x: x if isinstance(x, str) else "")
def test_bus_passenger_combinations_with_login(pw_module_page_logged_in: Page,
                                               adult, child, elder, case_name):
    """登录态：8组乘客组合参数化下单"""
    tag = f"登录态-{case_name}" + (" [邊界用例·會真提交]" if (adult, child, elder) == (0, 0, 0) else "")
    print(f"\n 登录态场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search()
    biz.handle_map_modals()          # 內部已含 wait_map_closed()，替代原 sleep(0.5)×2
    biz.goto_order_page()
    biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)
    print(f" {tag} 场景测试通过！")


# ========== 登录态 CSV 数据驱动（后续启用，取消注释即可）==========
# @pytest.mark.bus
# def test_bus_passenger_from_csv_with_login(pw_module_page_logged_in: Page, passenger_combination):
#     email, pwd, adult, child, elder, case_name, _ = passenger_combination
#     print(f"\n 登录态 CSV 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
#     biz = BusticketBusiness(pw_module_page_logged_in)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_page()
#     biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)
#     print(f" {case_name} 场景测试通过！")


def test_bus_order_with_fields_adult_only(pw_module_page_logged_in: Page):
    """登录态：只选1成人，填写全部下单字段后提交"""
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()
    biz.add_passengers_fill_fields_and_submit(
        adult=1, child=0, elder=0,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    )
    print(" 登录态-只成人+填写字段+提交 测试通过！")


@pytest.mark.parametrize("adult,child,elder,case_name", [
    (1, 0, 0, "登录态-只成人+字段"),
    (0, 1, 0, "登录态-只儿童+字段"),
    (0, 0, 1, "登录态-只长者+字段"),
    (1, 1, 0, "登录态-成人儿童+字段"),
    (1, 0, 1, "登录态-成人长者+字段"),
    (0, 1, 1, "登录态-儿童长者+字段"),
    (1, 1, 1, "登录态-三者全选+字段"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_bus_order_with_fields_combinations(pw_module_page_logged_in: Page,
                                            adult, child, elder, case_name):
    """登录态：各乘客组合 + 填写下单字段 + 提交"""
    print(f"\n 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()
    biz.add_passengers_fill_fields_and_submit(
        adult=adult, child=child, elder=elder,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    )
    print(f" {case_name} 测试通过！")


def test_bus_submit_and_confirm_page(pw_module_page_logged_in: Page):
    """登录态：1成人下单，提交后验证跳转到 confirm-order 确认页"""
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()

    group_id = biz.add_passengers_fill_fields_and_submit_with_confirm(
        adult=1, child=0, elder=0,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    )

    assert group_id is not None, "提交后未获取到 groupId"
    assert group_id.isdigit(), f"groupId 不是数字: {group_id}"
    print(f" 登录态-下单跳转确认页测试通过！groupId={group_id}")


@pytest.mark.parametrize("adult,child,elder,case_name", [
    (1, 0, 0, "登录态-只成人-提交跳转"),
    (0, 1, 0, "登录态-只儿童-提交跳转"),
    (0, 0, 1, "登录态-只长者-提交跳转"),
    (1, 1, 0, "登录态-成人儿童-提交跳转"),
    (1, 0, 1, "登录态-成人长者-提交跳转"),
    (0, 1, 1, "登录态-儿童长者-提交跳转"),
    (1, 1, 1, "登录态-三者全选-提交跳转"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_bus_submit_and_confirm_combinations(pw_module_page_logged_in: Page,
                                             adult, child, elder, case_name):
    """登录态：各乘客组合 → 提交 → 验证跳转 confirm-order"""
    print(f"\n 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()

    group_id = biz.add_passengers_fill_fields_and_submit_with_confirm(
        adult=adult, child=child, elder=elder,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    )

    assert group_id is not None, f"{case_name} 提交后未获取到 groupId"
    assert group_id.isdigit(), f"{case_name} groupId 不是数字: {group_id}"
    print(f" {case_name} 提交跳转测试通过！groupId={group_id}")


# ==================== 支付码生成专项用例（按指定顺序：①港微→②港支→③陸微→④陸支）====================
# ⚠️ 順序敏感 + 共享 context：
#    pw_module_page_logged_in 是 module 級 fixture → 4 條跑在同一個 browser context，
#    第 ① 條留下的登錄 cookie / 未完成訂單會帶到第 ②③④ 條。
#    這是原版既成語義，未擅自拆 context（拆了會改變登錄態與執行耗時）。
#    pay_on_confirm_page() 內第一步 clean_tabs() 會順手關掉上一條遺留的支付標籤頁。
#    → 要真「四渠道各自獨立游客態」，見文件尾 TODO① 的 pay_isolated 方案。

def test_bus_pay_01_hk_wechat_generate_qrcode(pw_module_page_logged_in: Page):
    """① 香港微信支付：选择 → 生成支付码 → 验证（用例结束）"""
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search(
        depart_city="深圳", depart_station="深圳灣（香港段上）",
        arrive_city="香港", arrive_station="尖沙咀海港城"
    )
    biz.handle_map_modals()
    biz.goto_order_page()
    group_id = biz.add_passengers_fill_fields_and_submit_with_confirm(adult=1)

    # ⬇ 原版 BusOrderPayPage.pay(driver, m) → 走 business 實例方法，
    #   白撿一道「當前必須在 confirm-order」前置斷言 + groupId 兜底提取
    result = biz.pay_on_confirm_page("香港微信支付")
    assert result["qrcode_displayed"], "香港微信支付码未生成"
    assert result["group_id"] == group_id, \
        f"支付頁 groupId 與下單頁不一致: {result['group_id']} vs {group_id}"
    print("① 香港微信支付码生成成功 ✓")


def test_bus_pay_02_hk_alipay_generate_qrcode(pw_module_page_logged_in: Page):
    """② 香港支付寶：选择 → 生成支付码 → 验证（用例结束）"""
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search(
        depart_city="深圳", depart_station="深圳灣（香港段上）",
        arrive_city="香港", arrive_station="尖沙咀海港城"
    )
    biz.handle_map_modals()
    biz.goto_order_page()
    group_id = biz.add_passengers_fill_fields_and_submit_with_confirm(adult=1)

    result = biz.pay_on_confirm_page("香港支付寶")
    assert result["qrcode_displayed"], "香港支付寶支付码未生成"
    assert result["group_id"] == group_id, \
        f"支付頁 groupId 與下單頁不一致: {result['group_id']} vs {group_id}"
    print("② 香港支付寶支付码生成成功 ✓")


def test_bus_pay_03_cn_wechat_generate_qrcode(pw_module_page_logged_in: Page):
    """③ 大陸微信支付：选择 → 生成支付码 → 验证（用例结束）"""
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search(
        depart_city="深圳", depart_station="深圳灣（香港段上）",
        arrive_city="香港", arrive_station="尖沙咀海港城"
    )
    biz.handle_map_modals()
    biz.goto_order_page()
    group_id = biz.add_passengers_fill_fields_and_submit_with_confirm(adult=1)

    result = biz.pay_on_confirm_page("大陸微信支付")
    assert result["qrcode_displayed"], "大陸微信支付码未生成"
    assert result["group_id"] == group_id, \
        f"支付頁 groupId 與下單頁不一致: {result['group_id']} vs {group_id}"
    print("③ 大陸微信支付码生成成功 ✓")


def test_bus_pay_04_cn_alipay_generate_qrcode(pw_module_page_logged_in: Page):
    """④ 大陸支付寶：选择 → 生成支付码 → 验证（用例结束）"""
    biz = BusticketBusiness(pw_module_page_logged_in)
    biz.enter_bus_and_search(
        depart_city="深圳", depart_station="深圳灣（香港段上）",
        arrive_city="香港", arrive_station="尖沙咀海港城"
    )
    biz.handle_map_modals()
    biz.goto_order_page()
    group_id = biz.add_passengers_fill_fields_and_submit_with_confirm(adult=1)

    result = biz.pay_on_confirm_page("大陸支付寶")
    assert result["qrcode_displayed"], "大陸支付寶支付码未生成"
    assert result["group_id"] == group_id, \
        f"支付頁 groupId 與下單頁不一致: {result['group_id']} vs {group_id}"
    print("④ 大陸支付寶支付码生成成功 ✓")