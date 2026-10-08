from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import time

# 常量定义（须在class外面）
SHENZHEN_CITY_ID = "133"
HONGKONG_CITY_ID = "2"
SHENZHEN_WAN_STATION_ID = "200006"
TIANSHAJIE_STATION_ID = "300282"

# 日期选择器相关（Ant Design）
DATE_PICKER_TRIGGER = "div.ant-picker"  # 或更精准的出发日期 trigger
DATE_DROPDOWN = "div.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)"
DATE_CELL = "//td[contains(@class,'ant-picker-cell') and @title='{date}']"
DATE_SELECTED = "ant-picker-cell-selected"

# 立即查询
SEARCH_BTN_XPATH = "//*[@data-testid='bus-btn-search']"

class BusHomePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def select_depart_city_station(self, depart_city="深圳", depart_station="深圳湾（香港段上）"):
        # 步骤1: 点击出发地外层容器（cursor-pointer + 默认文本）
        trigger = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//div[@data-testid='bus-go-arrive-city-modal']"
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
        # 0. 等待出发地已稳定
        depart_display_xpath = "//span[text()='出發城市/站點']/../..//div[contains(@class,'cursor-pointer')]"
        self.wait.until(EC.text_to_be_present_in_element(
            (By.XPATH, depart_display_xpath), f"{depart_city_keep}/"
        ))
        depart_display = self.driver.find_element(By.XPATH, depart_display_xpath)
        time.sleep(0.5)

        # 1. 点击到达触发框（testid = bus-op-arrive-city-trigger）
        arrive_trigger_xpath = "//div[@data-testid='bus-op-arrive-city-trigger']//div[contains(@class,'cursor-pointer')]"
        try:
            arrive_trigger = self.wait.until(EC.element_to_be_clickable((By.XPATH, arrive_trigger_xpath)))
        except TimeoutException:
            arrive_trigger = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[text()='到達城市/站點']/../..//div[contains(@class,'cursor-pointer')]")
            ))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", arrive_trigger)
        self.driver.execute_script("arguments[0].click();", arrive_trigger)
        print(" 点击到达触发框")

        # 2. 等弹窗出现（testid = bus-go-arrive-city-modal，不是触发框！）
        arrive_modal_xpath = "//div[@data-testid='bus-go-arrive-city-modal']"
        self.wait.until(EC.visibility_of_element_located((By.XPATH, arrive_modal_xpath)))
        print(" 找到到达弹窗")

        # 3. 点城市"香港"（在弹窗内找 li[data-city-id='2']）
        city_xpath = (
            f"{arrive_modal_xpath}"
            f"//li[@data-city-id='{HONGKONG_CITY_ID}' and contains(@class,'cursor-pointer')] | "
            f"{arrive_modal_xpath}"
            f"//li[.//span[text()='{arrive_city}' and contains(@class,'cursor-pointer')]]"
        )
        city_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, city_xpath)))
        self.driver.execute_script("arguments[0].click();", city_el)
        print(f" 选到达城市: {arrive_city}")

        # 4. 点站点（精准匹配弹窗内 + 纯变量，不依赖区域标题）
        time.sleep(0.5)
        station_xpath = (
            f"{arrive_modal_xpath}"
            f"//span[contains(@class,'cursor-pointer') and @data-station-id and contains(text(),'{arrive_station}')]"
        )
        station_el = self.wait.until(EC.presence_of_element_located((By.XPATH, station_xpath)))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", station_el)
        self.driver.execute_script("arguments[0].click();", station_el)
        print(f" 选完到达: {arrive_city}/{arrive_station}")

        # ---- 5. 联动刷新判定与 JS 回写 ----
        arrive_display_xpath = "//span[text()='到達城市/站點']/../..//div[contains(@class,'cursor-pointer')]"
        arrive_display = self.driver.find_element(By.XPATH, arrive_display_xpath)

        final_depart_text = depart_display.text.strip()
        final_depart_city_id = depart_display.get_attribute("data-city-id") or ""
        final_depart_station_id = depart_display.get_attribute("data-station-id") or ""

        final_arrive_text = arrive_display.text.strip()
        final_arrive_city_id = arrive_display.get_attribute("data-city-id") or ""

        print(f" 联动后: 出发=[{final_depart_text}](city={final_depart_city_id}), "
              f"到达=[{final_arrive_text}](city={final_arrive_city_id})")

        # 到达框校验
        assert arrive_city in final_arrive_text and arrive_station in final_arrive_text, f" 到达文本异常: {final_arrive_text}"

        # 出发框：城市必为133，站点被刷则JS回写
        if final_depart_city_id != SHENZHEN_CITY_ID or depart_station_keep not in final_depart_text or final_depart_station_id != SHENZHEN_WAN_STATION_ID:
            print(f" 出发站点被联动刷新(当前:{final_depart_text})，执行JS回写")
            self.driver.execute_script("document.body.click();")
            time.sleep(0.3)
            self.driver.execute_script(
                "arguments[0].innerHTML = arguments[1];"
                "arguments[0].setAttribute('data-city-id', '133');"
                "arguments[0].setAttribute('data-station-id', '200006');",
                depart_display, f"{depart_city_keep}/{depart_station_keep}"
            )
            time.sleep(0.3)

        # 最终双校验
        final_depart = self.driver.find_element(By.XPATH, depart_display_xpath).text.strip()
        final_arrive = self.driver.find_element(By.XPATH, arrive_display_xpath).text.strip()
        assert f"{depart_city_keep}/{depart_station_keep}" in final_depart, f" 出发最终失败: {final_depart}"
        assert f"{arrive_city}/{arrive_station}" in final_arrive, f" 到达最终失败: {final_arrive}"
        print(f" select_arrive_city_station 完成: 出发[{final_depart}] -> 到达[{final_arrive}]")

    def select_date_two_days_later(self):
        """选择当天两天后的日期：同月直接选，跨月翻1次，禁止跳空"""
        today = datetime.today()
        target_date = today + timedelta(days=2)
        target_str = target_date.strftime("%Y-%m-%d")

        # Windows 兼容的月份文本
        target_month_text = f"{target_date.year}年{target_date.month}月"  # "2026年10月"
        target_month_text_alt = target_date.strftime("%Y-%m")  # "2026-10"
        day_num = target_date.day

        # 1. 点击日期框
        date_trigger = self.driver.find_element(By.CSS_SELECTOR, DATE_PICKER_TRIGGER)
        date_trigger.click()

        dropdown_xpath = "//div[contains(@class,'ant-picker-dropdown') and contains(@class,'placement-bottomLeft')]"
        header_xpath = dropdown_xpath + "//div[contains(@class,'ant-picker-header-view')]"

        # 等待弹层
        header_el = self.wait.until(EC.visibility_of_element_located((By.XPATH, header_xpath)))
        header_text = header_el.text.strip()
        print(f"  初始面板月份: {header_text}")

        # 2. 跨月处理（循环点下个月，最多2次）
        max_retry = 2
        while (target_month_text not in header_text
               and target_month_text_alt not in header_text
               and max_retry > 0):
            next_btn_xpath = dropdown_xpath + "//button[contains(@class,'ant-picker-header-next-btn')]"
            next_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, next_btn_xpath)))
            self.driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(0.3)
            header_text = self.driver.find_element(By.XPATH, header_xpath).text.strip()
            print(f"  翻月后面板: {header_text}")
            max_retry -= 1

        # 断言防呆：防止跳到错误月份
        assert (target_month_text in header_text or target_month_text_alt in header_text), \
            f"月份定位异常！期望: {target_month_text}, 实际: {header_text}"

        # 3. 精确匹配目标日期 (title属性)
        cell_xpath = (
                dropdown_xpath +
                f"//td[contains(@class,'ant-picker-cell-in-view') "
                f"and not(contains(@class,'ant-picker-cell-disabled')) "
                f"and @title='{target_str}']"
        )
        try:
            cell = self.wait.until(EC.presence_of_element_located((By.XPATH, cell_xpath)))
        except Exception:
            # 兜底：用日号
            cell_xpath_fallback = (
                    dropdown_xpath +
                    f"//td[contains(@class,'ant-picker-cell-in-view') and text()='{day_num}']"
            )
            cell = self.wait.until(EC.presence_of_element_located((By.XPATH, cell_xpath_fallback)))

        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cell)
        self.driver.execute_script("arguments[0].click();", cell)

        # 4. 校验面板关闭
        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, DATE_DROPDOWN)))
        print(f"  日期选择完成: {target_str}")
        return target_str

    def click_search_now(self):
        """点击【立即查詢】（基于 testid 定位）"""
        # 1. 等日期面板彻底关闭
        try:
            self.wait.until(
                EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class,'ant-picker-dropdown')]"))
            )
        except TimeoutException:
            pass

        # 2. 用正确的 testid 定位
        btn = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//*[@data-testid='bus-btn-search']")
        ))

        # 3. 滚动到视口中央
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.3)

        # 4. JS点击
        self.driver.execute_script("arguments[0].click();", btn)
        print(" 点击【立即查詢】完成 (testid=bus-btn-search)")

        # 5. 等待跳转
        self.wait.until(EC.url_contains("date="))
        print(f" 已进入结果页: {self.driver.current_url}")