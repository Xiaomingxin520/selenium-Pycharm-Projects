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
        print(f"✅ 搜索结果页跳转成功: {current_url}")