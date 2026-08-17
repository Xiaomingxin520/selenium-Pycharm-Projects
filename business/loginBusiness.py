from page.login_page import LoginPage
import time
class LoginBusiness:

    @staticmethod
    def loginBusiness(driver, phone, password, area_code="+86"):
        """
        登录业务封装（仅密码登录）
        :param driver: selenium driver 实例
        :param phone: 手机号（CSV 中可能为 <null> 或带空格的字符串）
        :param password: 密码（CSV 中可能为 <null>）
        :param area_code: 区号，如 "+86", "+852"
        """
        page = LoginPage(driver)

        # 1. 打开登录弹窗
        page.click_login_register()

        # 2.精准控制区号切换时机
        if area_code:
            page.select_area_code(area_code)

        # 3. 输入手机号（兼容 CSV 中的 <null> 或空字符串）
        if phone and str(phone).strip() not in ["<null>", ""]:
            page.enter_mobile(str(phone).strip())  # 空手机号：不输入，直接提交触发前端校验

        # 4. 输入密码（兼容 CSV 中的 <null>）
        if password and str(password).strip() not in ["<null>", ""]:
            page.enter_password(str(password).strip())  # 空密码：不输入，直接提交触发前端校验

        # 5. 输入完信息后，直接勾选协议,这样后续点击登录时，就不会触发“温馨提示”弹窗了
        page.check_agreement()
        time.sleep(1)  # 稍微等待一下 UI 渲染和状态同步

        # 6. 点击登录（未勾选协议时会触发温馨提示弹窗）
        page.click_login_button()

        # 后续可接登录成功断言
        # assert page.is_login_success() is True