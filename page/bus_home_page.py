from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class BusHomePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def select_depart_city_station(self, depart_city="深圳", depart_station="深圳湾（香港段上）"):
        # 步骤1: 点击出发地外层容器（cursor-pointer + 默认文本）
        trigger = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//div[contains(@class,'cursor-pointer') and contains(@class,'w-[300px]')] | "
             "//span[contains(text(),'香港/旺角油麻地')]/ancestor::div[contains(@class,'cursor-pointer')] | "
             "//span[text()='出發城市/站點']/../..//*[name()='svg']")
        ))
        trigger.click()

        # 等弹窗渲染
        time.sleep(1)

        # 步骤2: 点击左侧城市
        city_el = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             f"//body//li[(@data-city-id='133' or text()='{depart_city}') and contains(@class,'cursor-pointer')] | "
             f"//body//div[text()='{depart_city}' and contains(@class,'cursor-pointer')]")
        ))
        city_el.click()

        # 步骤3: 点击右侧站点
        station_el = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             f"//body//span[(@data-station-id='200006' or contains(text(),'{depart_station}')) and contains(@class,'cursor-pointer')] | "
             f"//body//li[contains(text(),'{depart_station}')]")
        ))
        station_el.click()

    def select_arrive_city_station(self, arrive_city="香港", arrive_station="尖沙咀海港城",
                                   depart_city_keep="深圳", depart_station_keep="深圳灣（香港段上）"):
        # 0. 等待出发地已稳定（初始状态），并定位出发框用于后续复位
        depart_display_xpath = "//span[text()='出發城市/站點']/../..//div[contains(@class,'cursor-pointer')]"
        self.wait.until(EC.text_to_be_present_in_element(
            (By.XPATH, depart_display_xpath), f"{depart_city_keep}/"
        ))
        depart_trigger = self.driver.find_element(By.XPATH, depart_display_xpath)
        time.sleep(0.5)

        # 1. 【保留原逻辑】找 300px 框，点到达触发框
        triggers = self.driver.find_elements(
            By.XPATH, "//div[contains(@class,'cursor-pointer') and contains(@class,'w-[300px]')]"
        )
        arrive_trigger = None
        for t in triggers:
            try:
                if t.is_displayed() and "出發城市" not in t.text:
                    arrive_trigger = t
                    break
            except Exception:
                continue
        if arrive_trigger is None:
            raise Exception("找不到到达城市触发框！")

        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", arrive_trigger)
        self.driver.execute_script("arguments[0].click();", arrive_trigger)
        time.sleep(1)

        # 2. 锁定右侧到达弹窗
        popover_xpath = (
            "//div[contains(@class,'ant-popover') and "
            "(contains(@class,'bus-arrive-city-station-popover') or contains(.,'到達城市'))]"
        )
        self.wait.until(EC.visibility_of_element_located((By.XPATH, popover_xpath)))
        time.sleep(0.3)

        # 3. 【保留原逻辑】在到达弹窗内点击左侧"香港"（此处必触发前端联动，双弹窗出现）
        city_el = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             f"{popover_xpath}//li[contains(@class,'cursor-pointer') and .//span[text()='{arrive_city}']] | "
             f"{popover_xpath}//span[text()='{arrive_city}' and contains(@class,'cursor-pointer')]"
             )
        ))
        self.driver.execute_script("arguments[0].click();", city_el)
        time.sleep(0.8)

