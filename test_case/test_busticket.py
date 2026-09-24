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

    # 当前仅传出发地，到达地/日期等后续补全（business层已留好占位）
    biz.enter_bus_and_search(
        depart_city="深圳",
        depart_station="深圳湾（香港段上）"
    )