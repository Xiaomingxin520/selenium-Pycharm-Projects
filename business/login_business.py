# -*- coding: utf-8 -*-
"""
business/login_business.py —— 登入業務封裝層（Playwright 版）
"""
from page.login_page import LoginPage

# 數據驅動髒值哨兵（與原版逐字一致，抽成常量便於複用）
_DIRTY = ["<null>", "", "None"]

def _as_page(maybe_page):
    """
    兼容殼：入參若是 Selenium WebDriver → 立刻報明確錯誤（而不是在 page.locator 那行
    拋一句莫名其妙的 AttributeError）；是 Playwright Page → 原樣返回。
    """
    if hasattr(maybe_page, "window_handles") or hasattr(maybe_page, "execute_script"):
        raise TypeError(
            "LoginBusiness 已遷移到 Playwright：請傳入 Page 對象而非 Selenium WebDriver。\n"
            "  舊：LoginBusiness.loginBusiness(driver, email='x@y.z')\n"
            "  新：LoginBusiness.loginBusiness(page,   email='x@y.z')\n"
            "page 從 conftest fixture 拿：def test_xxx(pw_module_page: Page): ..."
        )
    return maybe_page


def _valid(v) -> bool:
    """髒值判定，邏輯與原版三處內聯寫法完全等價"""
    if not v:
        return False
    return str(v).strip() not in _DIRTY


class LoginBusiness:

    # ========== 靜態方法版（兼容殼，簽名逐字保留） ==========
    @staticmethod
    def loginBusiness(page, phone="", password="", email="", area_code="+86",
                      login_mode="auto", timeout: int = 10_000) -> str:
        """
        统一登录业务封装

        :param page:        Playwright Page（⚠️ 不再是 Selenium driver）
        :param login_mode:  "auto"  → 有email走邮箱，有phone走手机（默认）
                            "email" → 强制走邮箱（用例29/30用）
                            "phone" → 强制走手机
        :param timeout:     毫秒，透傳給 LoginPage；放末尾以保證舊調用兼容
        :return:            'email' | 'phone'（實際走的分支，純增量）
        """
        page = _as_page(page)                      # ← 傳錯 driver 會在這裏報人話
        lp = LoginPage(page, timeout=timeout)
        mode = None

        # ===== 判断登录方式（三分支判定，原樣保留）=====
        use_email = False

        if login_mode == "email":
            use_email = True
        elif login_mode == "phone":
            use_email = False
        elif login_mode == "auto":
            # 有email且非空 → 邮箱；有phone且非空 → 手机；都空 → 默认走邮箱（适配29/30）
            email_valid = _valid(email)
            phone_valid = _valid(phone)
            if email_valid:
                use_email = True
            elif phone_valid:
                use_email = False
            else:
                use_email = True   # 都空 → 用例29/30期望校验邮箱 → 强制走邮箱
        else:
            # ⚠️ 原版未覆蓋：傳了拼錯的 login_mode 會靜默落到 use_email=False（走手機），
            #    用例紅了極難排查。此處加一句告警，行爲不變（仍按手機走，與原版一致）。
            print(f" ⚠️ 未知 login_mode='{login_mode}'，按 'phone' 處理（可選值：auto/email/phone）")

        # ========== 邮箱登录 ==========
        if use_email:
            mode = "email"
            page.__class__  # noqa: B018  (保持可讀性，無副作用)

            lp.click_login_register()                       # 入口：右上角 → 登入/註冊
            lp.switch_to_email_tab()                        # 切郵箱 Tab

            # ⚠️ 下面兩個 if 的「空值跳過」是原版刻意設計（用例 29/30 要測「留空點登入」的校驗），
            #    千萬別「優化」成必填，否則那兩條負向用例會失去意義。
            if _valid(email):
                lp.enter_email(str(email).strip())
            if password and str(password).strip() not in ["<null>", ""]:
                # ↑ 注意：原版密碼判定不含 "None"（與 email/phone 不同），此處精確保留，
                #   避免把字符串 "None" 當成合法密碼餵進去改變 29/30 的斷言前提
                lp.enter_password(str(password).strip())

            lp.check_agreement()                            # 真實點擊（page 層已改，可 force_js=True 回退）
            # 原 time.sleep(1) 刪除：click_login_button 內部已等 clickable + 兩級點擊
            lp.click_login_button()
            print(f" 登入流程已提交（mode=email, email={str(email).strip() or '<空>'}）")

        # ========== 手机号登录（原逻辑不变） ==========
        else:
            mode = "phone"
            lp.click_login_register()                       # 入口

            if area_code:
                lp.select_area_code(area_code)              # 鍵盤流選區號（↑/↓+Enter，page 層已加複核）
            if _valid(phone):
                lp.enter_mobile(str(phone).strip())
            if password and str(password).strip() not in ["<null>", ""]:
                lp.enter_password(str(password).strip())

            lp.check_agreement()
            # 原 time.sleep(1) 刪除（同上）
            lp.click_login_button()
            print(f" 登入流程已提交（mode=phone, {area_code} {str(phone).strip() or '<空>'}）")

        return mode

    # ========== 實例版（供需要持有 timeout 的調用方使用） ==========
    def __init__(self, page, timeout: int = 10_000):
        """
        實例版構造。BusticketBusiness.login_and_goto_order() 裏應改成：
            LoginBusiness(self.page, timeout=self.timeout).login(email, pwd)
        """
        self.page = _as_page(page)
        self.timeout = timeout
        self.login_page = LoginPage(self.page, timeout=timeout)

    def login(self, email="", pwd="", phone="", password="",
              area_code="+86", login_mode="auto") -> str:
        """
        實例版登入，語義與靜態版完全一致，區別只有：
          · timeout 由構造時持有，不用每次傳
          · 登入後多做一道「header 用戶區已渲染」的登入態複核
            （USER_INFO 的 class "user-info" 是業務 class，前端換 CSS Modules 就炸，
              故不單用它判定，見 page 層 TODO⑤）
        :return: 'email' | 'phone'
        """
        # 兼容兩種叫法：大巴側傳 pwd=，用例側傳 password=，誰有值用誰
        eff_pwd = pwd if str(pwd if pwd is not None else "") != "" else password

        mode = LoginBusiness.loginBusiness(
            self.page,
            phone=phone,
            password=eff_pwd,
            email=email,
            area_code=area_code,
            login_mode=login_mode,
            timeout=self.timeout,
        )

        # ===== 登入態複核（純增量，失敗只告警不 raise，不改變原「提交即返回」語義）=====
        self._verify_login_state()
        return mode

    def _verify_login_state(self) -> None:
        """雙通道複核：Toast(success) 或 header 用戶區渲染，任一命中即認爲已登入。"""
        # 通道 1：AntD Toast（最快，1~2s 內消失，抓不到很正常）
        toast = None
        try:
            toast = self.login_page.get_login_result_toast(timeout=3)
        except Exception as e:
            print(f"  Toast 複核跳過（非阻塞）: {e}")

        # 通道 2：header 用戶區（testid 穩定，不受 CSS Modules 影響）
        header_ok = False
        try:
            from playwright.sync_api import expect as _expect
            trigger = self.page.locator('[data-testid="header-user-trigger"]').first
            _expect(trigger).to_be_visible(timeout=5_000)
            header_txt = (trigger.inner_text() or "").strip()
            header_ok = bool(header_txt)
            if header_ok:
                print(f" 登入態複核通過：header 用戶區已渲染 [{header_txt[:40]}]")
        except Exception:
            pass

        # 通道 3：page 層原有的 .user-info（業務 class，最脆，僅作補充信息）
        ui = None
        try:
            ui = self.login_page.is_login_success()
        except Exception:
            ui = None

        if toast == "success" or header_ok or ui:
            if toast == "error":
                print(" ⚠️ Toast 報 error 但 header 已渲染，請人工確認（可能是並發 Toast 殘留）")
            return

        # 三通道全滅 → 只告警，不 raise。
        # 理由：原版靜態方法「提交即返回」，用例後續自有斷言（is_login_success / URL / 業務步驟），
        # 這裏若強行 raise 會改变既有 29/30 等負向用例的失敗點，違反「邏輯零變更」。
        detail = f"toast={toast}, header={'有' if header_ok else '無'}, user-info={ui}"
        print(f" ⚠️ 登入態三通道複核均未命中（{detail}）—— 由後續用例斷言兜底，此處不中斷")