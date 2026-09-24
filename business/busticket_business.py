from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from page.bus_home_page import BusHomePage


class BusticketBusiness:
    def __init__(self, driver):
        self.driver = driver

    def enter_bus_and_search(self, depart_city="深圳", depart_station="深圳湾（香港段上）"):
        # 1. 打开官网并点击大巴票入口
        self.driver.get("https://www.testhopetrip.dabapiao.com/")
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/bus']"))).click()

        # 2. 等待 /bus 页面加载完成
        wait.until(EC.visibility_of_element_located((By.XPATH, "//span[text()='出發城市/站點']")))

        # 3. 选择出发站点
        bus_home = BusHomePage(self.driver)
        bus_home.select_depart_city_station(depart_city, depart_station)
