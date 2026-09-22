import pytest
from selenium import webdriver
from business.bus_Ticket_business import BusTicketBusiness
from business.login_business import LoginBusiness  # 若需登录前置则保留

# ====================== Fixture（驱动管理） ======================
@pytest.fixture(scope="module")
def driver():
    """模块级浏览器驱动，整个文件共享，提升执行效率"""
    drv = webdriver.Chrome()
    drv.maximize_window()
    yield drv
    drv.quit()

# ====================== 测试用例 ======================
def test_bus_search_default(driver):
    """主线用例：默认参数查询（深圳湾->旺角，日期+2天，自动跨月）"""
    biz = BusTicketBusiness(driver)
    result = biz.search_bus_ticket(
        from_city="深圳",
        from_station="深圳湾（香港段上）",
        to_city="香港",
        to_station="旺角朗豪坊",
        date_offset=2,
        need_login=False  #当前登录用例独立，大巴票默认不登录直接查
    )
    assert result is True, "大巴票查询结果页未成功加载（班次/查询结果标识未出现）"

def test_bus_search_with_login(driver):
    """带登录前置的查询（适配 TC_LOGIN_029/030 等场景延伸）"""
    # 若需强制走邮箱/手机登录后查票，开启 need_login
    biz = BusTicketBusiness(driver)
    result = biz.search_bus_ticket(
        from_city="深圳",
        from_station="深圳湾（香港段上）",
        to_city="香港",
        to_station="旺角朗豪坊",
        date_offset=1,
        need_login=True,
        login_phone="",  # 填入测试账号
        login_pwd=""     # 填入测试密码
    )
    assert result is True

def test_bus_only_select_stations(driver):
    """调试用：仅选站点不查询，验证城市/站点下拉交互"""
    biz = BusTicketBusiness(driver)
    biz.only_select_stations(
        from_city="深圳",
        from_station="深圳湾（香港段上）",
        to_city="香港",
        to_station="旺角朗豪坊"
    )
    # 此处可加断言：URL未变/查询按钮未点，由业务层控制
    assert True  # 占位，实际可断言页面元素状态

def test_bus_date_cross_month(driver):
    """日期跨月验证（如月底跑选下月，page层已处理动态）"""
    biz = BusTicketBusiness(driver)
    result = biz.search_bus_ticket(
        date_offset=10,  # 模拟跨月（当前22号+10=下月1号）
        need_login=False
    )
    assert result is True