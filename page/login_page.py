# page/login_page.py
import time
import allure
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

class LoginPage:
    # ================= 元素定位器 =================
    # 右上角用户触发区
    USER_TRIGGER = (By.CSS_SELECTOR, '[data-testid="header-user-trigger"]')

    # 下拉菜单项
    MENU_LOGIN_REGISTER = (By.XPATH, '//*[normalize-space()="登入/註冊"]')
    MENU_FAVORITES = (By.XPATH, '//*[normalize-space()="收藏列表"]')
    MENU_HELP_CENTER = (By.XPATH, '//*[normalize-space()="幫助中心"]')

    # 登录弹窗
    LOGIN_MODAL_TITLE = (By.XPATH, '//*[contains(normalize-space(),"歡迎登入") or contains(normalize-space(),"欢迎登入")]')

    # 区号选择相关（用于点击展开下拉框）
    AREA_CODE_CONTAINER = (By.CSS_SELECTOR, "[data-testid='login-input-area-code']")

    # ✅新增
    # 区号另外选择
    # TARGET_AREA_CODE_OPTION = (By.XPATH,"//div[@class='ant-select-item-option-content']")

    # 输入账号场景
    MOBILE_INPUT = (By.XPATH,'//input[@placeholder="請輸入手機號" or @placeholder="请输入手机号" or @placeholder="請輸入手機號碼"]')
    PASSWORD_INPUT = (By.XPATH, '//input[@placeholder="請輸入密碼" or @placeholder="请输入密码"]')
    LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[data-testid="login-btn-submit"]') # 推荐用 data-testid定位属性登入按钮

    # ✅新增
    # 精准定位：直接锁定 input 标签的 data-testid
    AGREEMENT_CHECKBOX_INPUT = (By.CSS_SELECTOR, "input[data-testid='login-checkbox-agreement']")

    # 备用定位：定位整个可点击的 label 容器（如果 JS 失效，可用此元素进行常规点击）
    # AGREEMENT_CHECKBOX_LABEL = (By.CSS_SELECTOR, "label.ant-checkbox-wrapper[data-testid='login-checkbox-agreement']")

    # 登录成功/失败相关，可按实际再调整
    LOGIN_SUCCESS_TOAST = (By.XPATH, "//div[contains(@class,'ant-message-success') and contains(.,'登入成功')]") #即时反馈：AntD Toast 弹窗（首选，速度快，专为登录接口反馈设计）
    LOGIN_ERROR_TOAST = (By.XPATH, "//div[contains(@class,'ant-message-error') ]")
    FORM_ERROR = (By.XPATH, '//div[contains(@class,"form-item-error")]') #表单级错误提示（用于参数校验失败，如空密码、非法手机号）
    USER_INFO = (By.XPATH, '//div[contains(@class,"user-info")]')  #页面级状态变更：登录后的用户信息（用于后置校验或流程衔接）

    def __init__(self, driver, timeout=10):
        """
        初始化 LoginPage 类
        :param driver: Selenium WebDriver 实例
        :param timeout: 显式等待默认超时时间
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    # ================= 内部工具 =================

    def _wait_visible(self, locator):
        """
        等待元素可见
        """
        return self.wait.until(EC.visibility_of_element_located(locator))

    def _wait_clickable(self, locator):
        """
        等待元素可点击
        """
        return self.wait.until(EC.element_to_be_clickable(locator))

    def click(self, locator):
        """
        通用点击方法
        """
        el = self._wait_clickable(locator)
        el.click()
        return el

    def input_text(self, locator, text):
        """
        通用输入方法
        """
        el = self._wait_visible(locator)
        el.clear()
        el.send_keys(text)
        return el

    # ================= 页面操作 =================

    def open_user_menu(self):
        """
        打开右上角用户菜单（头像下拉框）
        """
        try:
            self._wait_visible(self.MENU_LOGIN_REGISTER)
            return
        except TimeoutException:
            pass

        trigger = self._wait_clickable(self.USER_TRIGGER)

        # 滚动到可视区域，防止被遮挡
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
            trigger
        )

        try:
            trigger.click()
        except Exception:
            # JS 点击兜底
            self.driver.execute_script("arguments[0].click();", trigger)

        self._wait_visible(self.MENU_LOGIN_REGISTER)

    def click_login_register(self):
        """
        点击“登入/註冊”按钮，打开登录弹窗
        """
        self.open_user_menu()
        self.click(self.MENU_LOGIN_REGISTER)
        self._wait_visible(self.LOGIN_MODAL_TITLE)

    # ✅新增
    # ================= 页面操作：模拟真人敲键盘事件（对抗 AntD） =================
    def select_area_code(self, target_code="+86"):
        """
        键盘流选择区号（基于默认+852的顺序）
        +852(默认) -> ↑:+86 | ↓:+853 | ↓↓:+886
        """
        try:
            container = self._wait_clickable(self.AREA_CODE_CONTAINER)
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
            container.click()

            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".ant-select-dropdown")))
            time.sleep(0.3)

            # 标准化区号格式
            target_code_str = str(target_code).strip()
            if not target_code_str.startswith("+"):
                target_code_str = f"+{target_code_str}"

            actions = ActionChains(self.driver).move_to_element(container).click()

            if target_code_str == "+86":
                actions.send_keys(Keys.ARROW_UP)
            elif target_code_str == "+853":
                actions.send_keys(Keys.ARROW_DOWN)
            elif target_code_str == "+886":
                actions.send_keys(Keys.ARROW_DOWN).send_keys(Keys.ARROW_DOWN)

            actions.send_keys(Keys.ENTER).perform()
            print(f"✅ 键盘操作选择区号: {target_code_str} 成功")
            return True

        except Exception as e:
            print(f"❌ 键盘选择区号失败: {e}")
            return False

    def enter_mobile(self, mobile):
        """
        输入手机号
        """
        try:
            mobile_input = self.wait.until(EC.visibility_of_element_located(self.MOBILE_INPUT))
            mobile_input.clear()
            mobile_input.send_keys(mobile)
            print(f"✅ 成功输入手机号: {mobile}")
        except Exception as e:
            print(f"❌ 输入手机号失败: {e}")
            raise e

    def enter_password(self, password):
        """
        输入密码
        """
        try:
            pwd_input = self.wait.until(EC.visibility_of_element_located(self.PASSWORD_INPUT))
            pwd_input.clear()
            pwd_input.send_keys(password)
            print("✅ 成功输入密码")
        except Exception as e:
            print(f"❌ 输入密码失败: {e}")
            raise e

    # ✅新增
    def check_agreement(self):
        """
        强制勾选用户协议（前置操作，防止触发温馨提示弹窗）
        使用 JS 强制修改 checked 属性并触发 change 事件，解决 AntD 拦截问题
        """
        try:
            checkbox_input = self.wait.until(
                EC.presence_of_element_located(self.AGREEMENT_CHECKBOX_INPUT)
            )

            # 滚动到元素可视区域（防止被遮挡）
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox_input)
            time.sleep(0.5)

            # ✅ 核心操作：使用 JavaScript 强制勾选
            # 1. 强制设置 checked 属性为 true
            self.driver.execute_script("arguments[0].checked = true;", checkbox_input)
            # 2. 触发 AntD 的 change 事件，让 UI 状态和文字变色
            self.driver.execute_script("""
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('click', { bubbles: true }));
            """, checkbox_input)

            print("✅ 已成功通过 JS 强制勾选《用户协议》")

        except Exception as e:
            print(f"❌ 勾选协议失败: {e}")
            try:
                allure.attach(self.driver.get_screenshot_as_png(), name="勾选失败截图",
                              attachment_type=allure.attachment_type.PNG)
            except:
                pass
            raise e

    def click_login_button(self):
        """
        点击登录按钮
        """
        try:
            login_btn = self.wait.until(EC.element_to_be_clickable(self.LOGIN_BUTTON))
            login_btn.click()
            print("✅ 成功点击登录按钮")
        except Exception as e:
            print(f"❌ 点击登录按钮失败: {e}")
            # JS 点击兜底
            try:
                self.driver.execute_script("arguments[0].click();", self.driver.find_element(*self.LOGIN_BUTTON))
                print("✅ 已通过 JS 兜底点击登录按钮")
            except:
                raise e

    def get_login_result_toast(self, timeout=5):  #捕获 AntD Toast 登录结果，返回：'success' / 'error' / None
        """
        捕获 AntD Toast 登录结果
        :return: 'success' / 'error' / None
        """
        try:
            # 先等 Toast 出现
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "ant-message-notice-content"))
            )

            # 判断成功
            if self.driver.find_elements(By.XPATH,"//div[contains(@class,'ant-message-success') and contains(.,'登入成功')]"):
                return "success"

            # 判断失败
            if self.driver.find_elements(By.XPATH,"//div[contains(@class,'ant-message-error') and contains(.,'請輸入')]"):
                return "error"

        except TimeoutException:
            pass
        except Exception as e:
            print(f"⚠️ Toast 捕获异常: {e}")

        return None

    def is_login_success_by_toast(self):
        """
        根据 Toast 判断登录是否成功
        """
        result = self.get_login_result_toast()
        if result == "success":
            print("✅ 捕获到「登入成功」Toast")
            return True
        return False

    # ================= 业务场景整合 =================
    def login_via_dropdown(self, mobile, password, area_code="+86"):
        """
        首页右上角头像 -> 登入/註冊 -> 弹窗输入账号密码 -> 勾选协议 -> 点击登入
        """
        self.click_login_register() #入口
        self.select_area_code(area_code) #选择区号
        self.enter_mobile(mobile)  #输入手机号
        self.enter_password(password)  #输入密码
        self.check_agreement()    #✅登录前直接勾选协议，避免触发温馨提示弹窗
        self.click_login_button()  #登入按钮

    def is_login_modal_visible(self):
        """
        判断登录弹窗是否可见
        """
        try:
            self._wait_visible(self.LOGIN_MODAL_TITLE)
            return True
        except TimeoutException:
            return False

    # ================= 断言区 =================

    def is_login_success(self):
        """
        判断登录是否成功（通过用户信息元素）
        """
        try:
            self._wait_visible(self.USER_INFO)
            return True
        except TimeoutException:
            return False

    def get_form_error_text(self):
        """
        获取表单级错误提示文本
        """
        try:
            return self._wait_visible(self.FORM_ERROR).text
        except TimeoutException:
            return ""