from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from page.bus_home_page import BusHomePage
import time


class BusticketBusiness:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.target_date = None  # ← 供 testcase 读取

    def enter_bus_and_search(self, depart_city="深圳", depart_station="深圳灣（香港段上）",
                             arrive_city="香港", arrive_station="尖沙咀海港城"):
        # 1. 打开官网并点击大巴票入口
        self.driver.get("https://www.testhopetrip.dabapiao.com/")
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/bus']"))).click()

        # 2. 等待 /bus 页面加载
        wait.until(EC.visibility_of_element_located((By.XPATH, "//span[text()='出發城市/站點']")))

        # 3. 选择出发与到达
        bus_home = BusHomePage(self.driver)
        bus_home.select_depart_city_station(depart_city, depart_station)
        bus_home.select_arrive_city_station(arrive_city, arrive_station)

        # 4. 选择日期（当天+2）
        self.target_date = bus_home.select_date_two_days_later()

        # 后续步骤占位
        # TODO: 点击立即查询