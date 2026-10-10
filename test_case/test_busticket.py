import pytest
from business.busticket_business import BusticketBusiness
from datetime import datetime, timedelta

@pytest.mark.bus
def test_bus_select_depart_station(driver):
    """
    前置：conftest.py 已提供 driver
    场景：官网首页点击大巴票 -> /bus -> 选择出发城市(深圳) + 站点(深圳湾香港段上)
    断言：出发输入框最终显示目标站点（先跑通交互，不做完整下单）
    """
    biz = BusticketBusiness(driver)

    # 当前仅传出发地，到达地/日期等后续待补全（business层已留好占位）
    biz.enter_bus_and_search(
        depart_city="深圳",
        depart_station="深圳灣（香港段上）",
        arrive_city="香港",
        arrive_station="尖沙咀海港城"
    )

    # 校验 URL 带 date=当天+2
    expected_date = biz.target_date
    if not expected_date:
        expected_date = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")

    current_url = driver.current_url

    # 兼容 URL 中可能含其他参数，仅校验包含
    assert f"date={expected_date}" in current_url, \
        f"URL缺少日期参数: 期望 date={expected_date}, 实际 {current_url}"
    print(f"日期校验通过: date={expected_date}")

    # 上車點弹窗 → 取消
    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal()
    biz.result.close_map_modal()

    # 下車點弹窗 → 取消
    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal()
    biz.result.close_map_modal()

    # 点击购票
    biz.result.click_last_trip_ticket()
    assert "create-order" in driver.current_url, " 未跳转到下单页"
    print(" 购票跳转断言通过！")

# @pytest.mark.bus
# def test_bus_add_adult_on_order_page(driver):
#     biz = BusticketBusiness(driver)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_and_add_adult()
#     print(" 成人+号全链路测试通过！")
#
# @pytest.mark.bus
# def test_bus_add_child_on_order_page(driver):
#     biz = BusticketBusiness(driver)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_and_add_child()
#     print(" 兒童+号全链路测试通过！")
#
#
# @pytest.mark.bus
# def test_bus_add_elder_on_order_page(driver):
#     biz = BusticketBusiness(driver)
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
# ])
# def test_bus_passenger_combinations(driver, adult, child, elder, case_name):
#     print(f"\n 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
#
#     biz = BusticketBusiness(driver)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_page()
#     biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)
#
#     print(f" {case_name} 场景测试通过！")


# ========== 后续接 CSV 时，只需改这里 ==========
# @pytest.mark.bus
# def test_bus_passenger_from_csv(driver, passenger_combination):
#     adult, child, elder, case_name, _ = passenger_combination
#     biz = BusticketBusiness(driver)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_page()
#     biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)
#     print(f" {case_name} 场景测试通过！")

@pytest.mark.bus
def test_bus_select_depart_station_with_login(logged_in_driver):
    """
    登录态场景：官网首页点击大巴票 -> /bus -> 选择出发城市(深圳) + 站点(深圳湾香港段上)
    断言：出发输入框最终显示目标站点 + 日期参数 + 购票跳转
    """
    biz = BusticketBusiness(logged_in_driver)

    biz.enter_bus_and_search(
        depart_city="深圳",
        depart_station="深圳灣（香港段上）",
        arrive_city="香港",
        arrive_station="尖沙咀海港城"
    )

    # 校验 URL 带 date=当天+2
    expected_date = biz.target_date
    if not expected_date:
        expected_date = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")

    current_url = logged_in_driver.current_url
    assert f"date={expected_date}" in current_url, \
        f"URL缺少日期参数: 期望 date={expected_date}, 实际 {current_url}"
    print(f" 登录态-日期校验通过: date={expected_date}")

    # 上車點弹窗 → 取消
    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal()
    biz.result.close_map_modal()

    # 下車點弹窗 → 取消
    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal()
    biz.result.close_map_modal()

    # 点击购票
    biz.result.click_last_trip_ticket()
    assert "create-order" in logged_in_driver.current_url, " 未跳转到下单页"
    print(" 登录态-购票跳转断言通过！")

@pytest.mark.bus
@pytest.mark.parametrize("adult,child,elder,case_name", [
    (1, 0, 0, "登录态-只成人"),
    (0, 1, 0, "登录态-只儿童"),
    (0, 0, 1, "登录态-只长者"),
    (1, 1, 0, "登录态-只成人儿童"),
    (1, 0, 1, "登录态-只成人长者"),
    (0, 1, 1, "登录态-只儿童长者"),
    (1, 1, 1, "登录态-三者全选"),
    (0, 0, 0, "登录态-无乘客"),
])
def test_bus_passenger_combinations_with_login(logged_in_driver, adult, child, elder, case_name):
    """登录态：8组乘客组合参数化下单"""
    print(f"\n 登录态场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")

    biz = BusticketBusiness(logged_in_driver)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()
    biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)

    print(f" 登录态-{case_name} 场景测试通过！")

# ========== 登录态 CSV 数据驱动（后续启用，取消注释即可）==========
# @pytest.mark.bus
# def test_bus_passenger_from_csv_with_login(logged_in_driver, passenger_combination):
#     email, pwd, adult, child, elder, case_name, _ = passenger_combination
#     print(f"\n 登录态 CSV 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
#     biz = BusticketBusiness(logged_in_driver)
#     biz.enter_bus_and_search()
#     biz.handle_map_modals()
#     biz.goto_order_page()
#     biz.add_passengers_and_submit(adult=adult, child=child, elder=elder)
#     print(f" 登录态-{case_name} 场景测试通过！")

@pytest.mark.bus
def test_bus_order_with_fields_adult_only(logged_in_driver):
    """登录态：只选1成人，填写全部下单字段后提交"""
    biz = BusticketBusiness(logged_in_driver)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()
    biz.add_passengers_fill_fields_and_submit(
        adult=1, child=0, elder=0,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    )
    print(" 登录态-只成人+填写字段+提交 测试通过！")

@pytest.mark.bus
@pytest.mark.parametrize("adult,child,elder,case_name", [
    (1, 0, 0, "登录态-只成人+字段"),
    (0, 1, 0, "登录态-只儿童+字段"),
    (0, 0, 1, "登录态-只长者+字段"),
    (1, 1, 0, "登录态-成人儿童+字段"),
    (1, 0, 1, "登录态-成人长者+字段"),
    (0, 1, 1, "登录态-儿童长者+字段"),
    (1, 1, 1, "登录态-三者全选+字段"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_bus_order_with_fields_combinations(logged_in_driver, adult, child, elder, case_name):
    """登录态：各乘客组合 + 填写下单字段 + 提交"""
    print(f"\n 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")
    biz = BusticketBusiness(logged_in_driver)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()
    biz.add_passengers_fill_fields_and_submit(
        adult=adult, child=child, elder=elder,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    )
    print(f" {case_name} 测试通过！")

# 验证跳转confirm-order
@pytest.mark.bus
def test_bus_submit_and_confirm_page(logged_in_driver):
    """登录态：1成人下单，提交后验证跳转到 confirm-order 确认页"""
    biz = BusticketBusiness(logged_in_driver)
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

@pytest.mark.bus
@pytest.mark.parametrize("adult,child,elder,case_name", [
    (1, 0, 0, "登录态-只成人-提交跳转"),
    (0, 1, 0, "登录态-只儿童-提交跳转"),
    (0, 0, 1, "登录态-只长者-提交跳转"),
    (1, 1, 0, "登录态-成人儿童-提交跳转"),
    (1, 0, 1, "登录态-成人长者-提交跳转"),
    (0, 1, 1, "登录态-儿童长者-提交跳转"),
    (1, 1, 1, "登录态-三者全选-提交跳转"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_bus_submit_and_confirm_combinations(logged_in_driver, adult, child, elder, case_name):
    """登录态：各乘客组合 → 提交 → 验证跳转 confirm-order"""
    print(f"\n 场景: {case_name} | 成人={adult}, 兒童={child}, 長者={elder}")

    biz = BusticketBusiness(logged_in_driver)
    biz.enter_bus_and_search()
    biz.handle_map_modals()
    biz.goto_order_page()

    group_id = biz.add_passengers_fill_fields_and_submit_with_confirm(
        adult=adult, child=child, elder=elder,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    )

    assert group_id is not None, f"{case_name} 提交后未获取到 groupId"
    print(f" {case_name} 提交跳转测试通过！groupId={group_id}")