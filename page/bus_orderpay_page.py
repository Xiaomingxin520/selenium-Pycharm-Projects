from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time


class BusOrderPayPage:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

        # 核心元素定位
        self.url_contains = "create-order"
        self.adult_plus_btn = (By.XPATH,
                               "//div[contains(text(),'成人')]/ancestor::div[contains(@class,'flex-col')]//span[contains(@class,'anticon-plus')]/..")
        self.adult_count_label = (By.XPATH,
                                  "//div[contains(text(),'成人')]/ancestor::div[contains(@class,'flex-col')]//span[contains(@class,'cursor-pointer')]")
        self.submit_order_btn = (By.XPATH, "//button[contains(text(),'提交訂單')]")
        self.total_price = (By.XPATH, "//div[contains(text(),'總價')]/following-sibling::div")

    def wait_for_page_load(self):
        """等待确认订单页加载完成（URL + 提交订单按钮）"""
        self.wait.until(EC.url_contains(self.url_contains))
        self.wait.until(EC.presence_of_element_located(self.submit_order_btn))
        print(f"✅ 进入确认订单页: {self.driver.current_url}")

    def click_adult_plus(self):
        """点击成人人数的 + 号"""
        btn = self.wait.until(EC.element_to_be_clickable(self.adult_plus_btn))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.3)
        try:
            btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", btn)
        print("✅ 已点击成人 + 号")

        # 等待总价变化（简单断言人数增加）
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'1')]")))

    def get_adult_count(self):
        """获取当前成人数量（用于断言）"""
        text = self.driver.find_element(*self.adult_count_label).text.strip()
        return int(text) if text.isdigit() else 0

    def click_submit_order(self):
        """点击提交订单（后续支付流程预留）"""
        btn = self.wait.until(EC.element_to_be_clickable(self.submit_order_btn))
        btn.click()
        print("✅ 已点击提交订单")