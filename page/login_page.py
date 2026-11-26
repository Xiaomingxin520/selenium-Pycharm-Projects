# -*- coding: utf-8 -*-
"""
page/login_page.py —— 登入／註冊 Page Object（Playwright 版）
"""
import allure
from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

DEFAULT_TIMEOUT = 10_000


class LoginPage:

    # ================= 元素定位器（原样搬运） =================
    # 右上角用户触发区
    USER_TRIGGER = '[data-testid="header-user-trigger"]'

    # 下拉菜单项
    MENU_LOGIN_REGISTER = 'xpath=//*[normalize-space()="登入/註冊"]'
    MENU_FAVORITES = 'xpath=//*[normalize-space()="收藏列表"]'
    MENU_HELP_CENTER = 'xpath=//*[normalize-space()="幫助中心"]'

    # 登录弹窗
    LOGIN_MODAL_TITLE = (
        'xpath=//*[contains(normalize-space(),"歡迎登入") '
        'or contains(normalize-space(),"欢迎登入")]'
    )

    # 区号选择相关（用于点击展开下拉框）
    AREA_CODE_CONTAINER = "[data-testid='login-input-area-code']"
    AREA_CODE_DROPDOWN = ".ant-select-dropdown:not(.ant-select-dropdown-hidden)"

    # TARGET_AREA_CODE_OPTION = "xpath=//div[@class='ant-select-item-option-content']"

    # 输入手机号账号场景
    MOBILE_INPUT = (
        'xpath=//input[@placeholder="請輸入手機號" '
        'or @placeholder="请输入手机号" or @placeholder="請輸入手機號碼"]'
    )
    PASSWORD_INPUT = 'xpath=//input[@placeholder="請輸入密碼" or @placeholder="请输入密码"]'
    LOGIN_BUTTON = 'button[data-testid="login-btn-submit"]'

    # 输入电邮账号场景
    LOGIN_TAB_EMAIL = '[data-testid="login-tab-email"]'
    EMAIL_INPUT = (
        'xpath=//input[@placeholder="請輸入電子郵箱賬號" '
        'or @placeholder="请输入电子邮箱账号" or contains(@placeholder,"邮箱")]'
    )
    PASSWORD_INPUT1 = 'input[placeholder*="密碼"]'
    LOGIN_BUTTON1 = 'button[data-testid="login-btn-submit"]'

    # 精准定位：直接锁定 input 标签的 data-testid
    AGREEMENT_CHECKBOX_INPUT = "input[data-testid='login-checkbox-agreement']"
    # 备用：整个可点击的 label 容器（JS 失效时用）
    AGREEMENT_CHECKBOX_LABEL = "label.ant-checkbox-wrapper[data-testid='login-checkbox-agreement']"

    # 登录成功/失败相关
    LOGIN_SUCCESS_TOAST = (
        "xpath=//div[contains(@class,'ant-message-success') and contains(.,'登入成功')]"
    )
    LOGIN_ERROR_TOAST = "xpath=//div[contains(@class,'ant-message-error')]"
    FORM_ERROR = 'xpath=//div[contains(@class,"form-item-error")]'
    USER_INFO = 'xpath=//div[contains(@class,"user-info")]'

    def __init__(self, page: Page, timeout: int = 10_000):
        """
        :param page: Playwright Page（⚠️ 非 Selenium WebDriver）
        :param timeout: 默认超时（毫秒）。旧版传秒(10)，这里统一毫秒；
                        若 business 层写的是 LoginPage(page, 10) 会被当成 10ms，
                        → 请把调用处改为 LoginPage(page) 或 LoginPage(page, 10_000)
        """
        self.page = page
        self.timeout = timeout

        # 与原版同名的 Locator 属性（惰性求值 → 天然防 stale）
        self.user_trigger: Locator = page.locator(self.USER_TRIGGER).first
        self.menu_login_register: Locator = page.locator(self.MENU_LOGIN_REGISTER).first
        self.login_modal_title: Locator = page.locator(self.LOGIN_MODAL_TITLE).first
        self.area_code_container: Locator = page.locator(self.AREA_CODE_CONTAINER).first
        self.mobile_input: Locator = page.locator(self.MOBILE_INPUT).first
        self.password_input: Locator = page.locator(self.PASSWORD_INPUT).first
        self.login_button: Locator = page.locator(self.LOGIN_BUTTON).first
        self.login_tab_email: Locator = page.locator(self.LOGIN_TAB_EMAIL).first
        self.email_input: Locator = page.locator(self.EMAIL_INPUT).first
        self.password_input1: Locator = page.locator(self.PASSWORD_INPUT1).first
        self.login_button1: Locator = page.locator(self.LOGIN_BUTTON1).first
        self.agreement_checkbox_input: Locator = page.locator(self.AGREEMENT_CHECKBOX_INPUT).first
        self.agreement_checkbox_label: Locator = page.locator(self.AGREEMENT_CHECKBOX_LABEL).first
        self.login_success_toast: Locator = page.locator(self.LOGIN_SUCCESS_TOAST).first
        self.login_error_toast: Locator = page.locator(self.LOGIN_ERROR_TOAST).first
        self.form_error: Locator = page.locator(self.FORM_ERROR).first
        self.user_info: Locator = page.locator(self.USER_INFO).first
        self.toast_host: Locator = page.locator(".ant-message-notice-content").first

    # ================= 内部工具（替代 _wait_visible / _wait_clickable / click / input_text） =================

    def _wait_visible(self, loc: Locator) -> Locator:
        """等价原 _wait_visible：返回该 Locator（Playwright Locator 不可缓存 element，
        返回 locator 本身即可，后续操作会重新解析）"""
        loc.wait_for(state="visible", timeout=self.timeout)
        return loc

    def _wait_clickable(self, loc: Locator) -> Locator:
        """等价 EC.element_to_be_clickable：visible + enabled。
        Playwright 的 click() 本来就做 5 重可操作性检查，这里只做前置断言以保留原调用语义。"""
        loc.wait_for(state="visible", timeout=self.timeout)
        if loc.is_disabled():
            raise PWTimeout(f"元素可見但處於 disabled 狀態: {loc}")
        return loc

    def _smart_click(self, loc: Locator, desc: str) -> None:
        """真点击优先 → 遮挡/超时则 force（仍走鼠标事件链，不 dispatch_event）"""
        loc.scroll_into_view_if_needed(timeout=self.timeout)
        try:
            loc.click(timeout=self.timeout)
        except PWTimeout:
            print(f"  [retry] {desc} 普通点击被拦截，转 force 点击")
            loc.click(timeout=self.timeout, force=True)
        print(f" ✔ click: {desc}")

    def click(self, loc: Locator) -> Locator:
        """通用点击方法（签名与原版一致：入参 locator，返回 locator）"""
        el = self._wait_clickable(loc)
        self._smart_click(el, "generic click")
        return el

    def input_text(self, loc: Locator, text) -> Locator:
        """通用输入：fill() = focus + selectAll + 清空 + 键入，
        且会走 React 受控组件的 value setter —— 比 clear()+send_keys() 对 AntD 更稳"""
        loc.wait_for(state="visible", timeout=self.timeout)
        loc.scroll_into_view_if_needed(timeout=self.timeout)
        loc.fill(str(text), timeout=self.timeout)
        return loc

    def _attach_shot(self, name: str) -> None:
        """失败截图挂 allure（等价 get_screenshot_as_png）"""
        try:
            allure.attach(self.page.screenshot(), name=name,
                          attachment_type=allure.attachment_type.PNG)
        except Exception:
            pass

    # ================= 页面操作 =================

    def open_user_menu(self):
        """打开右上角用户菜单（头像下拉框）。幂等：已展开则直接返回。"""
        # 原版开头那道「菜单已开就 return」的幂等保护，语义保留（改用 is_visible 不吃异常）
        if self.menu_login_register.is_visible(timeout=800):
            return

        trigger = self._wait_clickable(self.user_trigger)
        self._smart_click(trigger, "右上角用户菜单")

        self.menu_login_register.wait_for(state="visible", timeout=self.timeout)

    def click_login_register(self):
        """点击「登入/註冊」，打开登录弹窗"""
        self.open_user_menu()
        self.click(self.menu_login_register)
        self.login_modal_title.wait_for(state="visible", timeout=self.timeout)
        print(" 登录弹窗已打开")

    #  ================= 页面操作：模拟真人敲键盘事件（对抗 AntD） =================

    def select_area_code(self, target_code="+86"):
        """
        键盘流选择区号（基于默认 +852 的顺序）：+852(默认) -> ↑:+86 | ↓:+853 | ↓↓:+886
        ⚠️ 依赖下拉项「渲染顺序」，与原版同一假设，未改。
           新增：按完键后复核 aria-selected 那项文本，防前端插项导致静默选错区号。
        """
        try:
            container = self._wait_clickable(self.area_code_container)
            container.scroll_into_view_if_needed(timeout=self.timeout)
            container.click(timeout=self.timeout)

            dropdown = self.page.locator(self.AREA_CODE_DROPDOWN).first
            dropdown.wait_for(state="visible", timeout=self.timeout)
            self.page.wait_for_timeout(300)   # 等价原 sleep(0.3)：等下拉展开动画落定

            # 标准化区号格式
            target_code_str = str(target_code).strip()
            if not target_code_str.startswith("+"):
                target_code_str = f"+{target_code_str}"

            # ↓↓↓ 键盘流：逐键等价 ActionChains · move_to_element → click → send_keys → perform
            container.focus()
            if target_code_str == "+86":
                self.page.keyboard.press("ArrowUp")
            elif target_code_str == "+853":
                self.page.keyboard.press("ArrowDown")
            elif target_code_str == "+886":
                self.page.keyboard.press("ArrowDown")
                self.page.keyboard.press("ArrowDown")
            self.page.keyboard.press("Enter")

            # ↓↓↓ 新增兜底校验（不改行为，只加告警）：确认真的选中了目标区号
            try:
                selected = dropdown.locator(
                    ".ant-select-item-option-selected, [aria-selected='true']"
                ).first.inner_text(timeout=2_000).strip()
                if target_code_str not in selected:
                    shown = container.inner_text().strip()
                    print(f"  ⚠️ 区号可能选错：期望含 {target_code_str}，"
                          f"高亮项='{selected}'，输入框显示='{shown}'"
                          f"（前端是否在中间插了新区号？select_area_code 依赖顺序假设）")
                else:
                    print(f" 键盘操作选择区号: {target_code_str} 成功 ✓")
            except PWTimeout:
                # 下拉已收起属正常（Enter 后 AntD 立即关闭），改读容器回显
                shown = container.inner_text().strip()
                if target_code_str in shown:
                    print(f" 键盘操作选择区号: {target_code_str} 成功")
                else:
                    print(f"  ⚠️ 区号回显复核未通过：期望 {target_code_str}，实际显示 '{shown}'")

            return True

        except Exception as e:
            print(f" 键盘选择区号失败: {e}")
            self._attach_shot("区号选择失败")
            return False

    def enter_mobile(self, mobile):
        """输入手机号"""
        try:
            self.input_text(self.mobile_input, mobile)
            print(f" 成功输入手机号: {mobile}")
        except Exception as e:
            print(f" 输入手机号失败: {e}")
            self._attach_shot("输入手机号失败")
            raise

    def enter_password(self, password):
        """输入密码"""
        try:
            # 密码框用 fill 同样安全（Playwright 不经过 OS 剪贴板，不会进 CI 日志）
            self.input_text(self.password_input, password)
            print(" 成功输入密码")
        except Exception as e:
            print(f" 输入密码失败: {e}")
            self._attach_shot("输入密码失败")
            raise

    # ================= 邮箱登录操作 =================

    def switch_to_email_tab(self):
        """切换到邮箱登录 Tab"""
        try:
            tab = self._wait_clickable(self.login_tab_email)
            tab.click(timeout=self.timeout)
            self.page.wait_for_timeout(300)   # 等价原 sleep(0.3)：等 Tab 切换动画
            print(" 已切换到邮箱登录 Tab")
        except Exception as e:
            print(f" 切换邮箱 Tab 失败: {e}")
            self._attach_shot("切换邮箱Tab失败")
            raise

    def enter_email(self, email):
        """输入邮箱地址（纯输入，无区号复杂度）"""
        try:
            self.input_text(self.email_input, email)
            print(f" 成功输入邮箱: {email}")
        except Exception as e:
            print(f" 输入邮箱失败: {e}")
            self._attach_shot("输入邮箱失败")
            raise

    def check_agreement(self, force_js: bool = False):
        """
        勾选《用户协议》。

        默认（force_js=False）：locator.check() 真实鼠标点击。
            Playwright 会自动点到关联的 <label>，原生解决「原生 input 被 opacity:0 藏起来」
            的遮挡问题 —— 这正是旧版不得不用 JS 的原因，现在不需要了。
            而且走真实点击才能测出「协议勾不上 → 登入按钮被拦」这个业务校验。

        force_js=True：还原旧版行为（JS 强写 checked + dispatch change/click）。
            仅当真遇上极端场景（自绘 checkbox / 事件绑在奇怪的容器上）才用，
            属于逃生舱，不是默认路径。
        """
        try:
            cb = self.agreement_checkbox_input
            cb.scroll_into_view_if_needed(timeout=self.timeout)

            if cb.is_checked():
                print(" 協議已勾選（跳過）")
                return

            if force_js:
                # ↓ 旧版逻辑原样保留，只是换成 Playwright 的 evaluate 语法
                cb.evaluate("""el => {
                    el.checked = true;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('click',  { bubbles: true }));
                }""")
                print(" 已成功通过 JS 强制勾选《用户协议》（force_js 逃生舱）")
            else:
                # 优先点 label（Ant Design 的标准可点区域）；点不到再直接 check input
                try:
                    self.agreement_checkbox_label.check(timeout=self.timeout)
                except PWTimeout:
                    cb.check(timeout=self.timeout, force=True)
                print(" 已成功勾選《用戶協議》（真實點擊）")

            # 复核：React state 是否真的认了这一下（旧版没有这道校验，是它最脆的地方）
            self.page.wait_for_timeout(200)
            if not cb.is_checked():
                raise AssertionError(
                    "勾選後 checkbox 仍為未選中 —— React state 可能已回滾。"
                    "可臨時改傳 force_js=True 驗證是否為渲染遮擋問題。"
                )

        except Exception as e:
            print(f" 勾选协议失败: {e}")
            self._attach_shot("勾选协议失败截图")
            raise

    def click_login_button(self):
        """点击登录按钮"""
        try:
            self._smart_click(self.login_button, "登入按鈕")
            print(" 成功点击登录按钮")
        except Exception as e:
            print(f" 点击登录按钮失败: {e}")
            try:
                # 兜底：同 locator force 点击（等价旧版 JS click，但仍在 Playwright 输入链内）
                self.login_button.click(force=True, timeout=5_000)
                print(" 已通过 force 兜底点击登录按钮")
            except Exception:
                self._attach_shot("登录按钮点击失败")
                raise e

    def get_login_result_toast(self, timeout=5):
        """
        捕获 AntD Toast 登录结果
        :return: 'success' / 'error' / None
        ⚠️ 一处放宽：旧版 error 判定要求 Toast 文本含「請輸入」，
           导致「密碼錯誤／賬號不存在／風控」这类 error Toast 全部落到 None，
           用例红了也看不出原因。这里改为「任意 ant-message-error 即 error」，
           并把 Toast 原文打进日志，语义与本方法名一致。
        """
        try:
            self.toast_host.wait_for(state="visible", timeout=timeout * 1000)
            text = (self.toast_host.inner_text() or "").strip()
            cls = self.toast_host.get_attribute("class") or ""

            if "ant-message-success" in cls or "登入成功" in text:
                print(f"  Toast(success): {text}")
                return "success"

            if "ant-message-error" in cls:
                print(f"  Toast(error): {text}")
                return "error"

            print(f"  Toast(其他): class={cls} text={text}")
        except PWTimeout:
            pass
        except Exception as e:
            print(f" Toast 捕获异常: {e}")
        return None

    def is_login_success_by_toast(self):
        """根据 Toast 判断登录是否成功"""
        if self.get_login_result_toast() == "success":
            print(" 捕获到「登入成功」Toast")
            return True
        return False

    # ================= 业务场景整合（签名全保留） =================

    def login_via_dropdown(self, mobile, password, area_code="+86"):
        """首页右上角头像 → 登入/註冊 → 弹窗输入账号密码 → 勾选协议 → 点击登入"""
        self.click_login_register()      # 入口
        self.select_area_code(area_code) # 选择区号
        self.enter_mobile(mobile)        # 输入手机号
        self.enter_password(password)    # 输入密码
        self.check_agreement()           # 登录前直接勾选协议，避免触发温馨提示弹窗
        self.click_login_button()        # 登入按钮

    def login_via_email(self, email, password):
        """邮箱登录完整流程：切Tab → 输邮箱 → 输密码 → 勾协议 → 点击登录"""
        self.click_login_register()      # 打开登录弹窗
        self.switch_to_email_tab()       # 切到邮箱 Tab
        self.enter_email(email)          # 输入邮箱
        self.enter_password(password)    # 输入密码（复用手机号场景的密码框定位）
        self.check_agreement()           # 勾选协议（复用）
        self.click_login_button()        # 点击登录

    def is_login_modal_visible(self):
        """判断登录弹窗是否可见"""
        try:
            self._wait_visible(self.login_modal_title)
            return True
        except PWTimeout:
            return False

    # ================= 断言区 =================

    def is_login_success(self):
        """判断登录是否成功（通过用户信息元素）"""
        try:
            self._wait_visible(self.user_info)
            return True
        except PWTimeout:
            return False

    def get_form_error_text(self):
        """获取表单级错误提示文本"""
        try:
            return (self._wait_visible(self.form_error).inner_text() or "").strip()
        except PWTimeout:
            return ""