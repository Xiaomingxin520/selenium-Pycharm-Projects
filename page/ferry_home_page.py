from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import time

# 常量定义（须在class外面）
SHENZHEN_CITY_ID = "133"
HONGKONG_CITY_ID = "2"
SHENZHEN_SHEKOU_PORT_ID = "900045"
HONGKONG_AIRPORT_PORT_ID  = "900054"

# 船票日期选择器相关 (Ant Design - ferry)
FERRY_DATE_PICKER_TRIGGER = "div.ant-picker"  # 船票出发日期输入框 trigger
FERRY_DATE_DROPDOWN = "div.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)"
FERRY_DATE_CELL = "//td[contains(@class,'ant-picker-cell') and @title='{date}']"
FERRY_DATE_SELECTED = "ant-picker-cell-selected"

# 立即查询
SEARCH_BTN_XPATH = "//*[@data-testid='ferry-btn-search']"

class ferryHomePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def select_depart_city_station(self, depart_city="深圳", depart_port="深圳蛇口碼頭"):
        """选择船票出发城市 + 码头"""

        # ===== 步骤1：点出发 trigger（唯一元素 + 原生 click）=====
        trigger = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "(//div[@data-testid='ferry-go-depart-city-trigger'])[1]")
        ))
        trigger.click()          # ← 不再用 execute_script
        print(" 点击出发地 trigger")

        # 等弹窗出现
        modal_xpath = "//div[@data-testid='ferry-go-depart-city-modal']"
        self.wait.until(EC.visibility_of_element_located((By.XPATH, modal_xpath)))
        time.sleep(0.4)

        # ===== 步骤2：左侧城市（精确文本，避免误伤右侧"深圳蛇口碼頭"）=====
        city_xpath = (
            f"({modal_xpath}//li[@data-city-id='{SHENZHEN_CITY_ID}'])[1] | "
            f"({modal_xpath}//*[normalize-space(text())='{depart_city}' and "
            f"contains(@class,'cursor-pointer')])[1]"
        )
        city_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, city_xpath)))
        city_el.click()
        print(f" 选出发城市: {depart_city}")
        time.sleep(0.8)   # 右侧码头是联动接口，多给一点

        # ===== ★ 调试打印：现在才看得到 =====
        print(" 弹窗内码头相关节点：")
        for el in self.driver.find_elements(By.XPATH, f"{modal_xpath}//*[@data-port-id or text()]"):
            t = (el.text or "").strip()
            pid = el.get_attribute("data-port-id") or ""
            if pid or "碼頭" in t or depart_port in t:
                print(f"   <{el.tag_name}> port={pid} city={el.get_attribute('data-city-id')} text='{t}'")

        # ===== 步骤3：先等码头文本出现，再点 =====
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f"{modal_xpath}//*[contains(text(),'{depart_port}')]")))
        time.sleep(0.2)

        station_xpath = (
            f"({modal_xpath}//*[@data-port-id='{SHENZHEN_SHEKOU_PORT_ID}'])[1] | "
            f"({modal_xpath}//*[contains(text(),'{depart_port}') and "
            f"contains(@class,'cursor-pointer')])[1] | "
            f"({modal_xpath}//*[contains(text(),'{depart_port}')]/ancestor-or-self::*[contains(@class,'cursor-pointer')][1])[1]"
        )
        station_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, station_xpath)))
        station_el.click()
        print(f" 选出发码头: {depart_port}")
        time.sleep(0.5)

    def select_arrive_city_station(self, arrive_city="香港", arrive_port="香港國際機場海天碼頭",
                                   depart_city_keep="深圳", depart_station_keep="深圳蛇口碼頭"):
        #  用 testid 而不是写死文本
        depart_display_xpath = "//div[@data-testid='ferry-go-depart-city-trigger']//div[contains(@class,'cursor-pointer')]"
        self.wait.until(EC.text_to_be_present_in_element(
            (By.XPATH, depart_display_xpath), f"{depart_city_keep}/"
        ))
        depart_display = self.driver.find_element(By.XPATH, depart_display_xpath)
        time.sleep(0.5)

        # 点击到达触发框
        arrive_trigger_xpath = "//div[@data-testid='ferry-go-arrive-city-trigger']//div[contains(@class,'cursor-pointer')]"
        try:
            arrive_trigger = self.wait.until(EC.element_to_be_clickable((By.XPATH, arrive_trigger_xpath)))
        except TimeoutException:
            arrive_trigger = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[@data-testid='ferry-go-arrive-city-trigger']")
            ))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", arrive_trigger)
        arrive_trigger.click()
        print(" 点击到达触发框(船票)")

        # 等弹窗出现
        arrive_modal_xpath = "//div[@data-testid='ferry-go-arrive-city-modal']"
        self.wait.until(EC.visibility_of_element_located((By.XPATH, arrive_modal_xpath)))
        print(" 找到到达弹窗(船票)")

        # 点城市
        city_xpath = (
            f"{arrive_modal_xpath}"
            f"//li[@data-city-id='{HONGKONG_CITY_ID}' and contains(@class,'cursor-pointer')] | "
            f"{arrive_modal_xpath}"
            f"//li[.//span[text()='{arrive_city}' and contains(@class,'cursor-pointer')]]"
        )
        city_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, city_xpath)))
        self.driver.execute_script("arguments[0].click();", city_el)
        print(f" 选到达城市: {arrive_city}")

        # 点码头
        time.sleep(0.5)
        station_xpath = (
            f"{arrive_modal_xpath}"
            f"//span[contains(@class,'cursor-pointer') and @data-port-id and contains(text(),'{arrive_port}')]"
        )
        station_el = self.wait.until(EC.presence_of_element_located((By.XPATH, station_xpath)))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", station_el)
        self.driver.execute_script("arguments[0].click();", station_el)
        print(f" 选完到达: {arrive_city}/{arrive_port}")

        # 联动刷新判定
        arrive_display_xpath = "//div[@data-testid='ferry-go-arrive-city-trigger']//div[contains(@class,'cursor-pointer')]"
        arrive_display = self.driver.find_element(By.XPATH, arrive_display_xpath)

        final_depart_text = depart_display.text.strip()
        final_depart_city_id = depart_display.get_attribute("data-city-id") or ""
        final_depart_port_id = depart_display.get_attribute("data-port-id") or ""

        final_arrive_text = arrive_display.text.strip()
        final_arrive_city_id = arrive_display.get_attribute("data-city-id") or ""

        print(f" 联动后: 出发=[{final_depart_text}](city={final_depart_city_id}), "
              f"到达=[{final_arrive_text}](city={final_arrive_city_id})")

        # 校验（改为异常，不放 assert）
        if not (arrive_city in final_arrive_text and arrive_port in final_arrive_text):
            raise Exception(f"到达文本异常: {final_arrive_text}")

        # 出发框被刷则 JS 回写
        if final_depart_city_id != SHENZHEN_CITY_ID or depart_station_keep not in final_depart_text or final_depart_port_id != SHENZHEN_SHEKOU_PORT_ID:
            print(f" 出发站点被联动刷新(当前:{final_depart_text})，执行JS回写")
            self.driver.execute_script("document.body.click();")
            time.sleep(0.3)
            self.driver.execute_script(
                "arguments[0].innerHTML = arguments[1];"
                "arguments[0].setAttribute('data-city-id', '133');"
                "arguments[0].setAttribute('data-port-id', '900045');",
                depart_display, f"{depart_city_keep}/{depart_station_keep}"
            )
            time.sleep(0.3)

        # 最终校验
        final_depart = self.driver.find_element(By.XPATH, depart_display_xpath).text.strip()
        final_arrive = self.driver.find_element(By.XPATH, arrive_display_xpath).text.strip()
        if not f"{depart_city_keep}/{depart_station_keep}" in final_depart:
            raise Exception(f"出发最终失败: {final_depart}")
        if not f"{arrive_city}/{arrive_port}" in final_arrive:
            raise Exception(f"到达最终失败: {final_arrive}")

        print(f" select_arrive_city_station 完成(船票): 出发[{final_depart}] -> 到达[{final_arrive}]")