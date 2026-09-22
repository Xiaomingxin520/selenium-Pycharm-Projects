from page.login_page import LoginPage
import time
class LoginBusiness:

    @staticmethod
    def loginBusiness(driver, phone="", password="", email="", area_code="+86", login_mode="auto"):
        """
        统一登录业务封装
        :param login_mode:
            "auto"  → 有email走邮箱，有phone走手机（默认）
            "email" → 强制走邮箱（用例29/30用）
            "phone" → 强制走手机
        """
        page = LoginPage(driver)

        # ===== 判断登录方式 =====
        use_email = False

        if login_mode == "email":
            use_email = True
        elif login_mode == "phone":
            use_email = False
        elif login_mode == "auto":
            # 有email且非空 → 邮箱；有phone且非空 → 手机；都空 → 默认走邮箱（适配29/30）
            email_valid = email and str(email).strip() not in ["<null>", "", "None"]
            phone_valid = phone and str(phone).strip() not in ["<null>", "", "None"]
            if email_valid:
                use_email = True
            elif phone_valid:
                use_email = False
            else:
                # 都空 → 用例29/30期望校验邮箱 → 强制走邮箱
                use_email = True

        if use_email:
            # ========== 邮箱登录 ==========
            page.click_login_register()
            page.switch_to_email_tab()
            if email and str(email).strip() not in ["<null>", "", "None"]:
                page.enter_email(str(email).strip())
            if password and str(password).strip() not in ["<null>", ""]:
                page.enter_password(str(password).strip())
            page.check_agreement()
            time.sleep(1)
            page.click_login_button()

        else:
            # ========== 手机号登录（原有逻辑不变） ==========
            page.click_login_register()
            if area_code:
                page.select_area_code(area_code)
            if phone and str(phone).strip() not in ["<null>", "", "None"]:
                page.enter_mobile(str(phone).strip())
            if password and str(password).strip() not in ["<null>", ""]:
                page.enter_password(str(password).strip())
            page.check_agreement()
            time.sleep(1)
            page.click_login_button()