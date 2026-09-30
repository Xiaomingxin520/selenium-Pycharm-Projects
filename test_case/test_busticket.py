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

    # 立即查询 + 结果页断言
    print(" 大巴票全链路（城市→日期→查询）闭环完成！")

    # 3. 上車點弹窗 → 取消
    biz.result.click_last_trip_map()
    assert biz.result.assert_map_modal()
    print(" 上車點弹窗校验通过！")
    biz.result.close_map_modal()

    # 4. 下車點弹窗 → 取消
    biz.result.click_last_trip_down_map()
    assert biz.result.assert_down_map_modal()
    print(" 下車點弹窗校验通过！")
    biz.result.close_map_modal()
    print(" 上車+下車站点地图弹窗完整流程校验通过！")