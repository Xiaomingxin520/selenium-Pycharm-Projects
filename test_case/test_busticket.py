import pytest
from business.busticket_business import BusticketBusiness


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
    current_url = driver.current_url
    assert f"date={expected_date}" in current_url, \
        f"URL缺少日期参数: 期望 date={expected_date}, 实际 {current_url}"
    print(f" 日期校验通过: date={expected_date}")

    # 3. 上車點弹窗 → 取消
    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal()
    biz.result.close_map_modal()

    # 4. 下車點弹窗 → 取消
    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal()
    biz.result.close_map_modal()

    # 5. 点击购票
    biz.result.click_last_trip_ticket()
    assert "create-order" in driver.current_url, " 未跳转到下单页"
    print(" 购票跳转断言通过！")

@pytest.mark.bus
def test_bus_add_adult_on_order_page(driver):
    """
    场景：完整链路 → 结果页点购票 → 确认订单页 → 点击成人+号 → 断言数量增加
    """
    biz = BusticketBusiness(driver)

    # 1. 搜索（复用已有方法）
    biz.enter_bus_and_search(
        depart_city="深圳",
        depart_station="深圳灣（香港段上）",
        arrive_city="香港",
        arrive_station="尖沙咀海港城"
    )

    # 2. 地图弹窗校验（可选，保留你的原有逻辑）
    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal()
    biz.result.close_map_modal()

    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal()
    biz.result.close_map_modal()

    # 3. 购票 → 跳转订单页 → 点成人+号（核心新增）
    biz.goto_order_and_add_adult()

    print(" 成人+号全链路测试通过！")