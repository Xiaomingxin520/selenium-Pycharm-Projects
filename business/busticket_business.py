from page.busticket_page import BusTicketPage
from business.login_business import LoginBusiness  # 已按重命名后的登录模块导入
from selenium.webdriver.chrome.webdriver import WebDriver

class BusTicketBusiness:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.page = BusTicketPage(driver)

    def search_bus_ticket(
        self,
        base_url: str = "https://www.testhopetrip.dabapiao.com/",
        from_city: str = "深圳",
        from_station: str = "深圳湾（香港段上）",
        to_city: str = "香港",
        to_station: str = "旺角朗豪坊",
        date_offset: int = 2,  # 默认选当天+2天，自动跨月已在page层处理
        need_login: bool = False,
        login_phone: str = "",
        login_pwd: str = ""
    ):
        """
        大巴票查询业务主流程骨架
        """
        # 1. 登录前置（按需，默认不登，适配你当前登录用例独立执行的情况）
        if need_login:
            login_biz = LoginBusiness(self.driver)
            # 假设登录后停留在首页或需跳转，这里留接口，具体按你登录后实际跳转调整
            login_biz.login(phone=login_phone, password=login_pwd)
            # 若登录后不在首页，需重新进入大巴票
            self.page.open_and_enter_bus(base_url)
        else:
            # 2. 打开首页并进入大巴票
            self.page.open_and_enter_bus(base_url)

        # 3. 选择出发（城市+站点）
        self.page.select_from(from_city, from_station)

        # 4. 选择到达（城市+站点）
        self.page.select_to(to_city, to_station)

        # 5. 选择日期（动态：今天+offset，自动跨月）
        self.page.select_departure_date(offset_days=date_offset)

        # 6. 点击立即查询（已修复CSS语法，使用XPath兜底）
        self.page.click_search()

        # 7. 返回结果页状态（由测试用例断言）
        return self.page.is_result_page_loaded()

    # --- 可扩展：单步业务方法（供复杂场景组合） ---
    def only_select_stations(self, from_city, from_station, to_city, to_station):
        """仅选站点不查（调试用）"""
        self.page.open_and_enter_bus()
        self.page.select_from(from_city, from_station)
        self.page.select_to(to_city, to_station)

    def select_date_and_search(self, offset_days=2):
        """选日期+查询（站点已选前提下）"""
        self.page.select_departure_date(offset_days)
        self.page.click_search()
        return self.page.is_result_page_loaded()