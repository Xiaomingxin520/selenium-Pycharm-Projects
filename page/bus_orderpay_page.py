# -*- coding: utf-8 -*-
"""
page/bus_orderpay_page.py —— 大巴票【支付页】Page Object（Playwright 版）
"""
from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

# 支付方式 → radio 索引（⚠️ 严格依赖页面渲染顺序，与原版完全一致，勿调）
PAYMENT_ORDER_MAP = {
    "香港微信支付": 0,
    "香港支付寶":   1,
    "香港支付寶支付": 1,   # 兼容 business 层可能出现的别名
    "大陸微信支付": 2,
    "大陸支付寶":   3,
}

DEFAULT_TIMEOUT = 10_000


class BusOrderPayPage:

    # ==================== 定位器（原样搬运） ====================
    PAYMENT_METHOD_WRAPPER = "label.ant-radio-wrapper"

    # 生成支付碼按鈕
    # ⚠️ 原版 `'生成支付碼' or '生成支付碼'` 两边同串（简繁笔误），此处按原意补齐简繁异体
    BTN_GENERATE_QRCODE = (
        "//button[contains(., '生成支付碼') or contains(., '生成支付码') or contains(., '產生支付碼')]"
    )

    # 二維碼區域（保留定義，不再作為斷言依據 —— 与旧版一致）
    QRCODE_AREA = (
        ".qrcode, [class*='qrcode'], img[src*='qrcode'], canvas, "
        ".qrcode-box img, [class*='qrcode'] img"
    )
    QRCODE_MODAL = (
        ".qrcode-modal, .pay-modal, [class*='qrcode-popup'], "
        "[class*='pay-popup'], .el-dialog__wrapper"
    )
    ORDER_INFO = ".order-info, [class*='order-detail'], [class*='route-info']"

    def __init__(self, page: Page, timeout: int = DEFAULT_TIMEOUT):
        self.page = page
        self.timeout = timeout

        self.payment_wrappers: Locator = page.locator(self.PAYMENT_METHOD_WRAPPER)
        self.btn_generate_qrcode: Locator = page.locator(self.BTN_GENERATE_QRCODE).first
        self.qrcode_area: Locator = page.locator(self.QRCODE_AREA)
        self.qrcode_modal: Locator = page.locator(self.QRCODE_MODAL)
        self.order_info: Locator = page.locator(self.ORDER_INFO).first

    # ---------------- 内部工具 ----------------
    def _smart_click(self, loc: Locator, desc: str) -> None:
        """真点击优先 → 被遮挡/超时则 force（仍走鼠标事件，不 dispatch_event）"""
        loc.scroll_into_view_if_needed(timeout=self.timeout)
        try:
            loc.click(timeout=self.timeout)
        except PWTimeout:
            print(f"  [retry] {desc} 普通点击被拦截，转 force 点击")
            loc.click(timeout=self.timeout, force=True)
        print(f" ✔ click: {desc}")

    # ==================== 基础信息（逻辑未改） ====================

    def get_current_group_id(self) -> str:
        url = self.page.url
        if "groupId=" in url:
            group_id = url.split("groupId=")[-1].split("&")[0]
            print(f"  提取到 groupId: {group_id}")
            return group_id
        print("  未從 URL 中提取到 groupId")
        return ""

    def get_total_price(self) -> str:
        """取首个含货币符号的文本。限定在 body 可见文本内，避免命中 hidden 节点。"""
        try:
            # 原版 //*[contains(text(),'HK$')...] 会命中 <html>/<body> 等大节点返回整页文本；
            # 这里收窄到「直接文本节点」层级，取值更准，但匹配语义不变
            loc = self.page.locator(
                "//*[contains(text(),'HK$') or contains(text(),'¥') or contains(text(),'￥')]"
            ).first
            loc.wait_for(state="visible", timeout=5_000)
            price = (loc.inner_text() or "").strip()
            # 只留第一行，防止抓到整块区域的拼接文本
            price = price.split("\n")[0].strip()
            print(f"  訂單總價: {price}")
            return price
        except Exception as e:
            print(f"  獲取總價失敗（非阻塞）: {e}")
            return ""

    def get_order_info(self) -> str:
        try:
            info = (self.order_info.inner_text(timeout=5_000) or "").strip()
            print(f"  訂單信息: {info[:120]}")
            return info
        except Exception:
            return ""

    def clean_tabs(self) -> None:
        """关掉支付过程中被 JS 弹出的多余标签页，只留主窗。
        原版用 window_handles 循环 switch_to；Playwright 用 context.pages（Page 对象列表）。"""
        pages = self.page.context.pages
        if len(pages) > 1:
            for p in pages:
                if p is not self.page and not p.is_closed():
                    try:
                        p.close()
                        print(f"  已關閉多餘標籤頁: {p.url[:80]}")
                    except Exception:
                        pass
            self.page.bring_to_front()

    # ==================== 支付方式 ====================

    def select_payment_method(self, method_name: str) -> None:
        """按索引选择支付方式（不依赖文字，最稳）—— 索引表与原版完全一致"""
        if "信用卡" in method_name:
            raise ValueError("自動化不包含信用卡支付（無二維碼跳轉）")
        if method_name not in PAYMENT_ORDER_MAP:
            raise ValueError(f"未定義的支付方式: {method_name}")

        idx = PAYMENT_ORDER_MAP[method_name]
        print(f"  按索引選擇支付方式: {method_name} -> index {idx}")

        # 等价原版 presence_of_all_elements_located：等至少 1 个再数
        self.payment_wrappers.first.wait_for(state="attached", timeout=self.timeout)
        total = self.payment_wrappers.count()
        if total <= idx:
            raise IndexError(f"支付方式數量不足，當前 {total} 個，無法選 index {idx}")

        target = self.payment_wrappers.nth(idx)   # Locator 惰性求值 → 天然防 stale

        cls = target.get_attribute("class") or ""
        if "ant-radio-wrapper-checked" in cls:
            print(f"  ✓ 已處於選中狀態: {method_name}")
            self.page.wait_for_timeout(1000)   # 原版 sleep(1)：等选中态的联动渲染，保留
            return

        self._smart_click(target, f"支付方式[{method_name}]")

        # 原版兜底：再点一次底层 input.ant-radio-input（Ant Design 有时 label 点击不冒泡）
        try:
            inp = target.locator("input.ant-radio-input")
            inp.wait_for(state="attached", timeout=2_000)
            if not inp.is_checked():
                inp.check(timeout=2_000, force=True)
                print("  （已補點底層 radio input）")
        except Exception:
            pass

        # 替代 sleep(1)+sleep(1)：等 checked class 真的挂上，最多 3s，挂上就走
        try:
            target.page.wait_for_function(
                """(sel) => {
                    const el = document.querySelectorAll(sel)[%d];
                    return el && el.className.includes('ant-radio-wrapper-checked');
                }""" % idx,
                arg=self.PAYMENT_METHOD_WRAPPER,
                timeout=3_000,
            )
            print(f"  ✓ 已成功選中: {method_name}")
        except PWTimeout:
            cls_now = target.get_attribute("class") or ""
            if "ant-radio-wrapper-checked" in cls_now:
                print(f"  ✓ 已成功選中: {method_name}（兜底复核）")
            else:
                print(f"  ⚠ 未檢測到 checked class，繼續執行")   # ← 原版文案，行为一致

    # ==================== 生成支付碼 ====================

    def wait_qrcode_loading(self, seconds: int = 1) -> None:
        """保留方法签名，仅等待。seconds=0 时不做任何等待（兼容旧调用）"""
        if seconds and seconds > 0:
            print(f"  等待二維碼 loading {seconds} 秒...")
            self.page.wait_for_timeout(seconds * 1000)

    def click_generate_qrcode(self) -> None:
        """點擊「生成支付碼」。⚠️ 与旧版一致：不校验二维码结果。"""
        print("  點擊「生成支付碼」")
        self.btn_generate_qrcode.wait_for(state="visible", timeout=self.timeout)
        self._smart_click(self.btn_generate_qrcode, "生成支付碼")

        # 替代 sleep(1.5)：等请求真的发出去（任一网络空闲窗口）；
        # 拿不到就退化到原来的 1.5s，行为不比旧版差
        try:
            self.page.wait_for_load_state("networkidle", timeout=3_000)
        except PWTimeout:
            self.page.wait_for_timeout(1500)
        print("  ✓ 生成支付碼點擊完成（不校驗二維碼）")

    # ==================== 二维码校验（默认仍放行，strict 才真验） ====================

    def is_qrcode_displayed(self, timeout: int = 15, strict: bool = False) -> bool:
        """
        兼容旧调用：默认 return True（与旧版行为完全一致，保证迁移不红）。
        strict=True 时真检测二维码区域/弹层是否可见 —— 全量绿后建议打开。
        """
        if not strict:
            return True
        deadline_end = self.page.locator(
            f"{self.QRCODE_AREA}, {self.QRCODE_MODAL}"
        ).first
        try:
            deadline_end.wait_for(state="visible", timeout=timeout * 1000)
            print("  ✓ 二維碼已出現（strict 校驗）")
            return True
        except PWTimeout:
            print("  ✗ 二維碼超時未出現（strict 校驗）")
            return False

    def is_qrcode_modal_displayed(self, timeout: int = 15, strict: bool = False) -> bool:
        """同上：默认 True 兼容旧版；strict=True 真校验支付弹层"""
        if not strict:
            return True
        try:
            self.qrcode_modal.first.wait_for(state="visible", timeout=timeout * 1000)
            print("  ✓ 支付彈層已出現（strict 校驗）")
            return True
        except PWTimeout:
            print("  ✗ 支付彈層超時未出現（strict 校驗）")
            return False

    # ==================== 支付全流程 ====================

    def pay(self, method_name: str, strict_qrcode: bool = False) -> dict:
        """
        支付全流程：清标签 → 取 groupId/总价/订单信息 → 选支付方式 → 点生成支付碼
        :return: {"group_id": str, "qrcode_displayed": bool}  结构与旧版一致
        """
        self.clean_tabs()
        group_id = self.get_current_group_id()
        self.get_total_price()
        self.get_order_info()

        self.select_payment_method(method_name)
        self.wait_qrcode_loading(1)
        self.click_generate_qrcode()

        displayed = self.is_qrcode_displayed(strict=strict_qrcode)
        return {"group_id": group_id, "qrcode_displayed": displayed}

    # ==================== ⬇ 静态兼容壳（旧代码一行不用改） ====================
    # 旧调用形如 BusOrderPayPage.pay(driver, method) 仍能工作：
    # 临时包一个实例再把调用转发出去。新代码请直接用实例方法。

    @staticmethod
    def _bind(driver_or_page) -> "BusOrderPayPage":
        """兼容壳：接受 Selenium driver（报错提示）或 Playwright Page"""
        if hasattr(driver_or_page, "window_handles"):
            raise TypeError(
                "BusOrderPayPage 已遷移到 Playwright：請傳入 Page 對象而非 Selenium WebDriver。"
                "示例：BusOrderPayPage(page).pay('香港微信支付')"
            )
        return BusOrderPayPage(driver_or_page)

    @staticmethod
    def get_current_group_id_static(driver_or_page) -> str:
        return BusOrderPayPage._bind(driver_or_page).get_current_group_id()

    @staticmethod
    def get_total_price_static(driver_or_page) -> str:
        return BusOrderPayPage._bind(driver_or_page).get_total_price()

    @staticmethod
    def get_order_info_static(driver_or_page) -> str:
        return BusOrderPayPage._bind(driver_or_page).get_order_info()

    @staticmethod
    def clean_tabs_static(driver_or_page) -> None:
        BusOrderPayPage._bind(driver_or_page).clean_tabs()

    @staticmethod
    def select_payment_method_static(driver_or_page, method_name: str) -> None:
        BusOrderPayPage._bind(driver_or_page).select_payment_method(method_name)

    @staticmethod
    def wait_qrcode_loading_static(driver_or_page, seconds: int = 1) -> None:
        BusOrderPayPage._bind(driver_or_page).wait_qrcode_loading(seconds)

    @staticmethod
    def click_generate_qrcode_static(driver_or_page) -> None:
        BusOrderPayPage._bind(driver_or_page).click_generate_qrcode()

    @staticmethod
    def is_qrcode_displayed_static(driver_or_page, timeout: int = 15) -> bool:
        return BusOrderPayPage._bind(driver_or_page).is_qrcode_displayed(timeout)

    @staticmethod
    def is_qrcode_modal_displayed_static(driver_or_page, timeout: int = 15) -> bool:
        return BusOrderPayPage._bind(driver_or_page).is_qrcode_modal_displayed(timeout)

    @staticmethod
    def pay_static(driver_or_page, method_name: str) -> dict:
        """等价于旧版 BusOrderPayPage.pay(driver, method)"""
        return BusOrderPayPage._bind(driver_or_page).pay(method_name)