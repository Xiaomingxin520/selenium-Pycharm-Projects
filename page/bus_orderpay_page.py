from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time


class BusOrderPayPage:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait
        self.url_contains = "create-order"

        # 提交按钮
        self.submit_order_btn = (By.XPATH, "//button[.//span[contains(text(),'提交訂單')]]")

        #  所有加号图标（统一用这个，不要再用 adult_plus_btn）
        self.plus_icons = (By.CSS_SELECTOR, ".anticon-plus")

        # 成人数量标签（备用）
        self.adult_count_label = (By.XPATH,
            "//span[contains(@class,'anticon-plus')]/parent::div/parent::div/div[2]")

    # ========== 页面加载 ==========
    def wait_for_page_load(self):
        self.wait.until(EC.url_contains(self.url_contains))
        time.sleep(1)
        self.wait.until(EC.presence_of_element_located(self.submit_order_btn))
        print(f" 进入确认订单页: {self.driver.current_url}")

    # ========== 提交订单 ==========
    def click_submit_order(self):
        btn = self.wait.until(EC.element_to_be_clickable(self.submit_order_btn))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.3)
        try:
            btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", btn)
        print(" 已点击提交订单")

    # ========== 通用点击加号（防stale核心）==========
    def _click_plus_by_index(self, index, name):
        """通用点击加号：每次重新定位 + 防stale"""
        icons = self.wait.until(EC.presence_of_all_elements_located(self.plus_icons))
        if len(icons) <= index:
            raise Exception(f" 找不到{name}的加号，当前仅 {len(icons)} 个加号")

        icon = icons[index]
        click_target = icon.find_element(By.XPATH, "..")  # cursor-pointer 父级

        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", click_target)
        time.sleep(0.3)
        try:
            click_target.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", click_target)

        print(f" 已点击{name} + 号")

    # ========== 通用获取数量（单XPath一步到位，防stale）==========
    def _get_count_by_index(self, index, name):
        """用单条XPath直接定位数量，不缓存中间WebElement"""
        xpath = f"(//span[contains(@class,'anticon-plus')])[{index + 1}]/parent::div/parent::div/div[2]"
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            text = el.text.strip()
            if text.isdigit():
                return int(text)
        except Exception as e:
            print(f"  获取{name}数量异常: {e}")
        return 0

    # ========== 成人 ==========
    def click_adult_plus(self):
        self._click_plus_by_index(0, "成人")

    def get_adult_count(self):
        return self._get_count_by_index(0, "成人")

    # ========== 兒童 ==========
    def click_child_plus(self):
        self._click_plus_by_index(1, "兒童")

    def get_child_count(self):
        return self._get_count_by_index(1, "兒童")

    # ========== 長者 ==========
    def click_elder_plus(self):
        self._click_plus_by_index(2, "長者")

    def get_elder_count(self):
        return self._get_count_by_index(2, "長者")