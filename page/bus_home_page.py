from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class BusHomePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)

    def select_depart_city_station(self, city_name="深圳", station_name="深圳湾（香港段上）"):
        import time

        # 1. 点击出发城市标签
        el = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='出發城市/站點']")))
        print(f"找到出发标签: {el.tag_name} text={el.text}")
        el.click()
        time.sleep(2)
        self.driver.save_screenshot("debug_step1_clicked.png")

        # 2. 打印页面所有 li 元素（找城市列表）
        lis = self.driver.find_elements(By.TAG_NAME, "li")
        print(f"页面共有 {len(lis)} 个 li 元素")
        for li in lis[:20]:  # 打印前20个
            text = li.text.strip()
            data_id = li.get_attribute("data-city-id")
            if text or data_id:
                print(f"  li: text='{text}' data-city-id='{data_id}' class='{li.get_attribute('class')}'")

        self.driver.save_screenshot("debug_step2_popup.png")

        # 3. 打印所有 span 含"深圳"的
        spans = self.driver.find_elements(By.XPATH, "//span[contains(text(),'深圳')]")
        print(f"找到 {len(spans)} 个包含'深圳'的 span")
        for sp in spans:
            print(f"  span: text='{sp.text}' data-station-id='{sp.get_attribute('data-station-id')}'")

        raise Exception("DEBUG: 停在这里，看截图和输出")