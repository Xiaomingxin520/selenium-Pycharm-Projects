from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import time


class BusOrderPayPage:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait
        self.url_contains = "create-order"

        # 提交按钮
        self.submit_order_btn = (By.XPATH, "//button[.//span[contains(text(),'提交订单')] or .//span[contains(text(),'提交訂單')]]")

        #  所有加号图标（统一用这个，不要再用 adult_plus_btn）
        self.plus_icons = (By.CSS_SELECTOR, ".anticon-plus")

        # 成人数量标签（备用）
        self.adult_count_label = (By.XPATH,
            "//span[contains(@class,'anticon-plus')]/parent::div/parent::div/div[2]")

        # ========== 下单字段定位器（新增）==========
        # 中文名输入框
        self.chinese_name_input = (By.XPATH,
            "//input[contains(@placeholder,'中文名') or contains(@placeholder,'請輸入您的中文名')]")

        # 中转英按钮（img[alt='拼接着'] 或 包含"中转英"文字）
        self.translate_btn = (By.XPATH,
            "//img[contains(@alt,'拼接') or contains(@alt,'轉') or contains(@alt,'转')]"
            " | //*[contains(text(),'中轉英') or contains(text(),'中转英')]"
            " | //button[contains(text(),'中轉英') or contains(text(),'中转英')]")

        # 拼音姓输入框
        self.surname_input = (By.XPATH,
            "//input[contains(@placeholder,'姓') and not(contains(@placeholder,'中文'))]")

        # 拼音名输入框
        self.given_name_input = (By.XPATH,
            "//input[contains(@placeholder,'名') and not(contains(@placeholder,'中文'))]")

        # 手机号
        self.phone_input = (By.XPATH,
            "//input[contains(@placeholder,'手機號') or contains(@placeholder,'手机号')]")

        # 邮箱
        self.email_input = (By.XPATH,
            "//input[contains(@placeholder,'电邮') or contains(@placeholder,'郵箱') or contains(@placeholder,'Email')]")

        # 备注
        self.remark_textarea = (By.XPATH,
            "//textarea[contains(@placeholder,'备注') or contains(@placeholder,'備註')]")

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

    # ========== 下单字段填写（新增，全部防stale）==========

    def _safe_send_keys(self, locator, value, field_name=""):
        """防stale通用输入：每次重新定位 + clear + send_keys"""
        for attempt in range(3):
            try:
                el = self.wait.until(EC.element_to_be_clickable(locator))
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.3)
                el.clear()
                el.send_keys(value)
                if field_name:
                    print(f"  已填写{field_name}: {value}")
                return
            except StaleElementReferenceException:
                if attempt == 2:
                    raise
                print(f"  {field_name} stale，重试 {attempt + 1}/3")
                time.sleep(0.5)

    def fill_chinese_name(self, name_cn="張三"):
        """填写中文名"""
        self._safe_send_keys(self.chinese_name_input, name_cn, "中文名")

    def click_translate_to_english(self):
        """点击中转英按钮，触发自动拼音转换"""
        for attempt in range(3):
            try:
                btn = self.wait.until(EC.element_to_be_clickable(self.translate_btn))
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.3)
                try:
                    btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", btn)
                print("  已点击中转英按钮")
                # 等待拼音回填完成
                time.sleep(1.5)
                return
            except StaleElementReferenceException:
                if attempt == 2:
                    raise
                time.sleep(0.5)

    def fill_phone(self, phone="96526666"):
        """填写手机号"""
        self._safe_send_keys(self.phone_input, phone, "手机号")

    def fill_email(self, email="test@gmail.com"):
        """填写邮箱"""
        self._safe_send_keys(self.email_input, email, "邮箱")

    def fill_remark(self, remark="测试备注"):
        """填写备注"""
        self._safe_send_keys(self.remark_textarea, remark, "备注")

    def fill_order_fields(self, name_cn="張三", phone="96526666",
                         email="test@gmail.com", remark="测试备注"):
        """
        统一填写所有下单字段（完整链路）：
        中文名 → 中转英（自动回填姓/名拼音）→ 手机号 → 邮箱 → 备注
        """
        self.fill_chinese_name(name_cn)
        self.click_translate_to_english()
        self.fill_phone(phone)
        self.fill_email(email)
        self.fill_remark(remark)
        print("  下单字段全部填写完成")
        return self

    # 订单确认页 URL 标识（groupId 动态，只校验路径前缀）
    CONFIRM_ORDER_URL_CONTAINS = "confirm-order"

    def click_submit_order_and_wait_confirm(self, timeout=15):
        """
        点击提交订单 → 等待跳转到 confirm-order 页面
        返回 groupId（动态提取，供后续业务使用）
        """
        btn = self.wait.until(EC.element_to_be_clickable(self.submit_order_btn))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.3)
        try:
            btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", btn)

        print(" 已点击提交订单，等待跳转确认页...")

        # 等待 URL 包含 confirm-order（groupId 动态，不硬编码）
        self.wait.until(EC.url_contains(self.CONFIRM_ORDER_URL_CONTAINS))
        time.sleep(1)  # 等页面稳定

        current_url = self.driver.current_url
        print(f" 已跳转到订单确认页: {current_url}")

        # 提取 groupId
        group_id = self._extract_group_id_from_url(current_url)
        if group_id:
            print(f"  提取到 groupId: {group_id}")
        else:
            print("  ⚠️ 未能从 URL 中提取 groupId")

        return group_id

    def _extract_group_id_from_url(self, url=None):
        """从 confirm-order?groupId=xxx 的 URL 中提取 groupId"""
        import re
        from urllib.parse import urlparse, parse_qs

        target_url = url or self.driver.current_url
        try:
            parsed = urlparse(target_url)
            params = parse_qs(parsed.query)
            group_id = params.get("groupId", [None])[0]
            return group_id
        except Exception as e:
            print(f"  提取 groupId 异常: {e}")
            return None

    def assert_confirm_order_page(self):
        """断言当前已进入订单确认页（groupId 不校验具体值，只校验路径）"""
        current_url = self.driver.current_url
        assert self.CONFIRM_ORDER_URL_CONTAINS in current_url, \
            f"未跳转到订单确认页: {current_url}"
        print(f" 订单确认页断言通过: {current_url}")
        return self