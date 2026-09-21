from page.login_page import LoginPage
import time
class LoginBusiness:

    @staticmethod
    def loginBusiness(driver, phone="", password="", email="", area_code="+86"):
        """
        统一登录业务封装（支持手机号和邮箱号）
        :param driver: selenium driver 实例
        :param phone: 手机号（CSV 中可能为 <null> 或空字符串）
        :param password: 密码
        :param email: 邮箱地址（为空则走手机号登录）
        :param area_code: 区号，如 "+86", "+852"
        """
        page = LoginPage(driver)

        # ===== 判断登录方式 =====
        if email and str(email).strip() not in ["<null>", "", "None"]:
            # ========== 邮箱登录 ==========
            page.click_login_register()  # 1. 打开登录弹窗
            page.switch_to_email_tab()  # 2. 切到邮箱 Tab
            page.enter_email(str(email).strip())  # 3. 输入邮箱

            if password and str(password).strip() not in ["<null>", ""]:
                page.enter_password(str(password).strip())  # 4. 输入密码

            page.check_agreement()  # 5. 勾选协议
            time.sleep(1)
            page.click_login_button()  # 6. 点击登录

        else:
            # ========== 手机号登录（原有逻辑） ==========
            page.click_login_register()  # 1. 打开登录弹窗

            if area_code:  # 2. 区号选择
                page.select_area_code(area_code)

            if phone and str(phone).strip() not in ["<null>", ""]:
                page.enter_mobile(str(phone).strip())  # 3. 输入手机号

            if password and str(password).strip() not in ["<null>", ""]:
                page.enter_password(str(password).strip())  # 4. 输入密码

            page.check_agreement()  # 5. 勾选协议
            time.sleep(1)
            page.click_login_button()  # 6. 点击登录