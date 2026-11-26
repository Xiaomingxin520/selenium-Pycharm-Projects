# -*- coding: utf-8 -*-
"""
test_case_pw/test_login.py —— 登錄模塊 CSV 數據驅動用例（Playwright 版）
"""
import sys
import csv
import time
from pathlib import Path

import pytest
import allure
from playwright.sync_api import Page, TimeoutError as PWTimeout

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from page.login_page import LoginPage          # noqa: E402
from business.login_business import LoginBusiness  # noqa: E402

CSV_PATH = PROJECT_ROOT / "data" / "login.csv"

# AntD Toast 存活窗口（毫秒）。⚠️ AntD 默認 3s 自動淡出，別調大，
# 調大只會「等過頭錯過 Toast」，不會更穩。
TOAST_WAIT_MS = 3_000


# ==================== CSV 讀取（邏輯逐字保留） ====================

def normalize_csv_value(value):
    """
    统一处理 CSV 中的空值，避免 None / 空字符串 / <null> 等干扰测试逻辑
    支持：空字符串、空格、<null>、NULL、None、nan
    ⚠️ 詞典逐字保留，這是我項目特有的數據約定，勿「優化」
    """
    if value is None:
        return ''
    v = value.strip()
    if v.lower() in ['<null>', 'null', 'none', 'nan']:
        return ''
    return v


def load_login_csv_data():
    """
    读取 data/login.csv，转换成 pytest.mark.parametrize 可用的列表数据

    支持的 CSV 表头：
    case_id,source_case,login_type,area_code,phone,email,pwd,expect_success,expect_text,description
    """
    data = []

    if not CSV_PATH.exists():
        # ⚠️ 原版這裏會直接 FileNotFoundError，堆棧指向 csv.DictReader，
        #    新人以爲是代碼壞了。改成人話，邏輯等價（仍是收集期就炸）。
        raise FileNotFoundError(
            f"找不到登錄測試數據文件: {CSV_PATH}\n"
            f"  請確認 data/login.csv 存在，且 test_case_pw/ 與 data/ 同級。"
        )

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            case_id = normalize_csv_value(row.get('case_id', ''))
            source_case = normalize_csv_value(row.get('source_case', ''))
            login_type = normalize_csv_value(row.get('login_type', ''))
            area_code = normalize_csv_value(row.get('area_code', ''))
            phone = normalize_csv_value(row.get('phone', ''))
            email = normalize_csv_value(row.get('email', ''))
            pwd = normalize_csv_value(row.get('pwd', ''))
            expect_success = normalize_csv_value(row.get('expect_success', ''))
            expect_text = normalize_csv_value(row.get('expect_text', ''))
            description = normalize_csv_value(row.get('description', ''))

            # 仅保留密码登录类型的用例
            if login_type != 'password':
                continue

            # 跳过全空行，防止脏数据干扰
            if not any([case_id, phone, pwd, expect_text, area_code]):
                continue

            # area_code 默认值保护：未填写时默认香港（+852）
            if not area_code:
                area_code = '+852'

            data.append(
                (
                    area_code,
                    phone,
                    pwd,
                    expect_text,
                    case_id,
                    source_case,
                    expect_success,
                    description,
                    email,
                )
            )

    return data


# 全局测试数据，供 pytest 参数化使用
LOGIN_DATA = load_login_csv_data()


def _build_ids():
    """
    原版 ids=[case[4] for case in LOGIN_DATA]。
    加兩道保險，不改變映射關係：
      · case_id 爲空 → 回落 f'{login_type}_{phone}_{area_code}'，避免 pytest 顯示 test_login[]
      · 重複 case_id → 追加 #2 #3 後綴，避免 pytest 靜默改寫成 _0/_1 讓人對不上 CSV 行號
    """
    seen, ids = {}, []
    for row in LOGIN_DATA:
        base = row[4] or f"{row[0]}_{row[1] or 'noPhone'}_{row[8] or 'noEmail'}"
        seen[base] = seen.get(base, 0) + 1
        ids.append(base if seen[base] == 1 else f"{base}#{seen[base]}")
    return ids


LOGIN_IDS = _build_ids()


# ==================== 用例類 ====================

@allure.feature('登录模块')
class TestLogin:

    @pytest.fixture(autouse=True)
    def setup(self, pw_module_page: Page):
        """
        ⚠️ 必須是 function 級（conftest_pw 的 pw_page），每條用例全新 context。
        若誤用 module 級 pw_module_page_logged_in，第 2 條起已帶登錄態，
        负向用例會因「已登入直接跳走」而假綠。見文件頭 ⚠️。
        """
        self.page = pw_module_page
        self.login_page = LoginPage(pw_module_page)      # 默認 timeout=10000ms
        self._boot()

    # ---------------- 內部工具 ----------------
    def _boot(self):
        """進首頁並等外殼就緒（頁腳牌照 354122＝全站唯一錨點，不隨改版文案漂移）"""
        self.page.goto("https://www.testhopetrip.dabapiao.com/",
                       wait_until="domcontentloaded", timeout=30_000)
        self.page.locator("text=354122").first.wait_for(state="visible", timeout=20_000)

    def _shot(self, name: str) -> bytes:
        """截圖並掛 allure。返回 bytes（allure.attach 可直接吃）"""
        try:
            png = self.page.screenshot()
            allure.attach(png, name=name, attachment_type=allure.attachment_type.PNG)
            return png
        except Exception:
            return b""

    def _capture_actual_text(self, expect_success: bool) -> str:
        """
        捕獲實際反饋文本。⚠️ 優先級鏈與原版逐行等價：
            expect_success=True  → 只認 AntD 成功 Toast（含「登入成功」）
            expect_success=False → 先試表單級 FORM_ERROR（空手機/空密碼這類參數校驗），
                                   拿不到再降級 LOGIN_ERROR_TOAST（密碼錯/賬號不存在）

        關鍵差異（不是邏輯變更，是修時序 bug）：
        原版在 loginBusiness 返回後先 time.sleep(1.5) 再 WebDriverWait(6)，
        AntD Toast 只活 3s → 最壞等 7.5s 才開始找，必然錯過 → TimeoutException
        → 被外層 except 吞成「操作或定位異常」（假失敗）。
        此處【不 sleep】，loginBusiness 一返回立刻在 3s 窗口內主動抓。
        """
        # ===== 成功分支 =====
        if expect_success:
            try:
                loc = self.page.locator(LoginPage.LOGIN_SUCCESS_TOAST).first
                loc.wait_for(state="visible", timeout=TOAST_WAIT_MS)
                return (loc.inner_text() or "").strip()
            except PWTimeout:
                # Toast 錯過了不代表登錄失敗（可能跳轉太快把 Toast 沖掉）
                # → 降級看頁面級登錄態，拿不到再返回空串交給斷言去紅
                if self.login_page.is_login_success():
                    return "登入成功（Toast 已錯過，由 user-info 複核）"
                if self.login_page.is_login_modal_visible() is False:
                    return "登入成功（Toast 已錯過，彈窗已關閉）"
                return ""

        # ===== 失敗分支：先表單級，再 Toast 級（順序與原版一致）=====
        try:
            form_loc = self.page.locator(LoginPage.FORM_ERROR).first
            form_loc.wait_for(state="visible", timeout=1_500)
            txt = (form_loc.inner_text() or "").strip()
            if txt:
                return txt
        except PWTimeout:
            pass

        try:
            err_loc = self.page.locator(LoginPage.LOGIN_ERROR_TOAST).first
            err_loc.wait_for(state="visible", timeout=TOAST_WAIT_MS)
            return (err_loc.inner_text() or "").strip()
        except PWTimeout:
            pass

        # 兩級都沒抓到：登錄彈窗是否還開着？開着＝前端沒給任何反饋（真 bug）
        # 已關閉＝可能登錄成功跳走了（CSV 期望失敗但實際成功，最有價值的那類紅）
        if self.login_page.is_login_modal_visible() is False:
            return "【異常】登錄彈窗已關閉且無錯誤提示——實際可能已登入成功（CSV 期望失敗）"
        return ""

    # ---------------- 數據驅動用例 ----------------
    @pytest.mark.parametrize(
        "area_code,phone,pwd,expect_text,case_id,source_case,expect_success,description,email",
        LOGIN_DATA,
        ids=LOGIN_IDS
    )
    def test_login(
            self,
            area_code,
            phone,
            pwd,
            expect_text,
            case_id,
            source_case,
            expect_success,
            description,
            email,
    ):
        """
        密码登录场景测试用例（支持多区号）
        数据来源：CSV 文件
        断言方式：优先 AntD Toast，其次表单错误提示
        """

        # Allure 報告中展示用例標題和詳細描述（逐字保留）
        allure.dynamic.title(f'{case_id} - {description}')
        allure.dynamic.description(
            f'case_id: {case_id}\n'
            f'source_case: {source_case}\n'
            f'area_code: {area_code}\n'
            f'phone: {phone}\n'
            f'email: {email}\n'
            f'expect_text: {expect_text}\n'
            f'description: {description}'
        )

        # 數據契約前置校驗：expect_text 空 → `'' in '任意串'` 恆 True = 假綠。
        # 判定邏輯沒動，只讓髒數據在用例體內第一時間炸，並附帶行號信息。
        if not expect_text:
            self._shot('CSV數據缺失')
            pytest.fail(
                f"CSV 數據缺失：case_id={case_id} 的 expect_text 爲空，"
                f"該用例會恆綠（'' in 任意串）。請補 data/login.csv 的 expect_text 列。"
            )

        actual_text = ''
        timestamp = time.strftime('%Y%m%d%H%M%S')   # 保留：文件命名用（見 _shot name 可加前綴）

        with allure.step('执行登录操作'):
            try:
                # ===== 判斷登錄方式（三分支判定，與原版逐字一致）=====
                email_valid = email and str(email).strip() not in ['', '<null>', 'None']
                phone_valid = phone and str(phone).strip() not in ['', '<null>', 'None']

                if email_valid:
                    login_mode = "email"
                elif phone_valid:
                    login_mode = "auto"      # 有手機 → 走手機
                else:
                    login_mode = "email"     # 都空 → 用例29/30強制走郵箱

                print(f" [{case_id}] login_mode={login_mode}, "
                      f"area_code={area_code}, phone={phone or '<空>'}, email={email or '<空>'}")

                # 調用 Business 層執行登錄流程（靜態簽名逐字保留，第一參現爲 Page）
                LoginBusiness.loginBusiness(
                    self.page,
                    phone=phone,
                    password=pwd,
                    email=email,
                    area_code=area_code,
                    login_mode=login_mode,          # ⚠️ 原版算了 login_mode 卻【沒傳】，
                    timeout=10_000                  #    business 內部又算一遍。此處傳下去，
                )                                   #    兩邊判定一致，行爲不變但可追溯。

                # ⬇⬇⬇ 原 time.sleep(1.5) 已刪除，見 _capture_actual_text 文檔 ⬇⬇⬇
                actual_text = self._capture_actual_text(expect_success.lower() == 'true')

            except Exception as e:   # 出現異常時截圖，便於定位問題
                self._shot(f'操作或定位异常_{case_id}_{timestamp}')
                allure.attach(f"actual_text 捕獲到: {actual_text!r}",
                              name='異常上下文', attachment_type=allure.attachment_type.TEXT)
                assert False, f'操作或定位异常: {e}'

        with allure.step('断言验证'):   # 驗證實際文本中是否包含預期文本
            try:
                assert expect_text in actual_text, \
                    f'预期文本[{expect_text}]不在实际文本[{actual_text}]中'

            except AssertionError as e:   # 斷言失敗時截圖 + 把雙方文本都進報告
                self._shot(f'断言失败_{case_id}_{timestamp}')
                allure.attach(
                    f"預期包含: {expect_text!r}\n實際文本: {actual_text!r}\n"
                    f"case_id={case_id} | source_case={source_case} | "
                    f"area_code={area_code} | phone={phone} | email={email}",
                    name='斷言上下文', attachment_type=allure.attachment_type.TEXT
                )
                raise                      # ⚠️ 原版寫 assert False, str(e) 會把堆棧壓平，
                                           #    raise 保留原始斷言行號，報告更好定位

        with allure.step('执行完成截图'):   # 用例執行結束後截圖，記錄最終狀態
            self._shot(f'执行结果_{case_id}_{timestamp}')

    def teardown_method(self):
        """driver / page 生命週期由 conftest_pw.py 管理，這裏不再 close"""
        pass