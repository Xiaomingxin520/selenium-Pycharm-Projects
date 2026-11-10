# business/ferryticket_business.py  船票业务调用层
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 导入对应的 Page 层（根据你的实际路径）
from page.ferry_home_page import ferryHomePage

# 复用你顶部定义的常量（建议与 ferry_home_page 保持一致或从常量文件导入）
SHENZHEN_CITY_ID = "133"
HONGKONG_CITY_ID = "2"
SHENZHEN_SHEKOU_PORT_ID = "900045"
HONGKONG_AIRPORT_PORT_ID = "900054"

class FerryTicketBusiness:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.ferry_page = ferryHomePage(driver)

    def select_ferry_route(self,
                           depart_city="深圳",
                           depart_port="深圳蛇口碼頭",
                           arrive_city="香港",
                           arrive_port="香港國際機場海天碼頭"):
        """
        核心业务：选择船票出发地 + 到达地（含联动兜底）
        """
        # 1. 选出发
        self.ferry_page.select_depart_city_station(depart_city, depart_port)
        time.sleep(0.5)

        # 2. 选到达（内部已包含出发地联动刷新的 JS 回写兜底）
        self.ferry_page.select_arrive_city_station(
            arrive_city=arrive_city,
            arrive_port=arrive_port,
            depart_city_keep=depart_city,
            depart_station_keep=depart_port
        )
        time.sleep(0.5)

    def search_ferry_ticket(self,
                            depart_city="深圳",
                            depart_port="深圳蛇口碼頭",
                            arrive_city="香港",
                            arrive_port="香港國際機場海天碼頭"):
        """
        完整冒烟流程：选路线 + 点击立即查询
        """
        self.select_ferry_route(depart_city, depart_port, arrive_city, arrive_port)

        # 点击查询（使用你定义的 SEARCH_BTN_XPATH）
        search_btn = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[@data-testid='ferry-btn-search']")
        ))
        search_btn.click()
        print(" 已执行船票路线选择并点击【立即查询】")

    def verify_selection_result(self, depart_text, arrive_text):
        """
        校验最终页面显示的出发/到达文本
        """
        body = self.driver.page_source
        assert depart_text in body, f"出发地校验失败，未找到: {depart_text}"
        assert arrive_text in body, f"到达地校验失败，未找到: {arrive_text}"
        print(f" 业务校验通过: 出发[{depart_text}] -> 到达[{arrive_text}]")