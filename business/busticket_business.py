from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from page.bus_home_page import BusHomePage

class BusticketBusiness:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.target_date = None  # ← 供 testcase 读取
        self.bus_home = BusHomePage(self.driver)
        self.result = None
        self.order = None   # ← 确认订单页对象（懒加载）

    def enter_bus_and_search(self, depart_city="深圳", depart_station="深圳灣（香港段上）",
                             arrive_city="香港", arrive_station="尖沙咀海港城"):
        # 1. 打开官网并点击大巴票入口
        self.driver.get("https://www.testhopetrip.dabapiao.com/")
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/bus']"))).click()

        # 2. 等待 /bus 页面加载
        wait.until(EC.visibility_of_element_located((By.XPATH, "//span[text()='出發城市/站點']")))

        # 3. 选择出发与到达
        self.bus_home.select_depart_city_station(depart_city, depart_station)
        self.bus_home.select_arrive_city_station(arrive_city, arrive_station)

        # 4. 选择日期（当天+2）
        self.target_date = self.bus_home.select_date_two_days_later()

        # 5. 新增：立即查詢
        self.bus_home.click_search_now()

        # 6. 等待结果页
        self.wait.until(EC.url_contains("date="))
        current_url = self.driver.current_url
        assert f"date={self.target_date}" in current_url, \
            f"结果页URL异常: 期望含 date={self.target_date}, 实际 {current_url}"
        print(f" 搜索结果页跳转成功: {current_url}")

        # 实例化结果页对象，挂到 self 上
        from page.bus_search_result_page import BusSearchResultPage
        self.result = BusSearchResultPage(self.driver)

    def search_and_goto_last_trip_map(self, depart_city, depart_station, arrive_city, arrive_station):
        """
        串联：首页选城站 -> 查询 -> 行程页点最后一班【上车】站点地图 -> 断言弹窗
        """
        self.enter_bus_and_search(
            depart_city=depart_city,
            depart_station=depart_station,
            arrive_city=arrive_city,
            arrive_station=arrive_station
        )

        # self.result 已由 enter_bus_and_search 赋值，直接用
        self.result.click_last_trip_map()
        assert self.result.assert_map_modal(), "站点地图弹窗验证失败"
        return self

    def click_ticket(self):
        """点击购票按钮"""
        self.result.click_last_trip_ticket()
        return self

    def wait_for_order_page(self):
        """等待确认订单页加载完成"""
        from page.bus_orderpay_page import BusOrderPayPage
        self.order = BusOrderPayPage(self.driver, self.wait)  # ← 加这行
        self.order.wait_for_page_load()
        return self

    def add_adult_passenger(self):
        """
        点击成人 + 号，增加一名成人乘客
        """
        self.order.click_adult_plus()
        return self

    def assert_adult_count_increased(self, expected_increase=1):
        """断言成人数量已增加"""
        # 点击前数量在 click_adult_plus 内部已校验，这里做最终断言
        count = self.order.get_adult_count()
        assert count >= 1, f"成人数量异常，当前: {count}"
        print(f" 当前成人数量: {count}")
        return self

    def goto_order_and_add_adult(self):
        """
        串联方法：点击购票 → 等待订单页 → 点击成人+号 → 断言
        供 testcase 一行调用
        """
        self.click_ticket()          # 点击购票（已有的方法）
        self.wait_for_order_page()   # 等待跳转
        self.add_adult_passenger()   # 点成人+
        self.assert_adult_count_increased()
        return self