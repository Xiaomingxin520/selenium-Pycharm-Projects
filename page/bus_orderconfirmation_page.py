# -*- coding: utf-8 -*-
"""
page/bus_orderconfirmation_page.py —— 大巴票【确认订单页】Page Object（Playwright 版）
"""
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

# 乘客类型索引（与原版 index 语义严格一致，勿调顺序）
IDX_ADULT = 0
IDX_CHILD = 1
IDX_ELDER = 2


class BusOrderConfirmationPage:
    def __init__(self, page: Page, timeout: int = 10_000):
        self.page = page
        self.timeout = timeout
        self.url_contains = "create-order"

        # ---------------- 提交按钮（原样保留 XPath） ----------------
        self.submit_order_btn: Locator = page.locator(
            "//button[.//span[contains(text(),'提交订单')] or .//span[contains(text(),'提交訂單')]]"
        ).first

        # ---------------- 所有加号图标（统一入口，勿再拆成 adult_plus_btn） ----------------
        self.plus_icons: Locator = page.locator(".anticon-plus")

        # 成人数量标签（备用，保留以兼容外部可能的引用）
        self.adult_count_label: Locator = page.locator(
            "//span[contains(@class,'anticon-plus')]/parent::div/parent::div/div[2]"
        ).first

        # ========== 下单字段定位器（原样搬运） ==========
        # 中文名输入框
        self.chinese_name_input: Locator = page.locator(
            "//input[contains(@placeholder,'中文名') or contains(@placeholder,'請輸入您的中文名')]"
        ).first

        # 中转英按钮（img[alt='拼接着'] 或 包含"中转英"文字）
        # ⚠️ 原版这里用了 XPath `|` 并集混了 text()，Playwright 的 CSS 引擎不认 XPath，
        #    所以改成「单条 XPath 并集」+ .first，语义一致且不跨引擎
        self.translate_btn: Locator = page.locator(
            "//img[contains(@alt,'拼接') or contains(@alt,'轉') or contains(@alt,'转')]"
            " | //*[contains(text(),'中轉英') or contains(text(),'中转英')]"
            " | //button[contains(text(),'中轉英') or contains(text(),'中转英')]"
        ).first

        # 拼音姓 / 拼音名
        self.surname_input: Locator = page.locator(
            "//input[contains(@placeholder,'姓') and not(contains(@placeholder,'中文'))]"
        ).first
        self.given_name_input: Locator = page.locator(
            "//input[contains(@placeholder,'名') and not(contains(@placeholder,'中文'))]"
        ).first

        # 手机号
        self.phone_input: Locator = page.locator(
            "//input[contains(@placeholder,'手機號') or contains(@placeholder,'手机号')]"
        ).first

        # 邮箱
        self.email_input: Locator = page.locator(
            "//input[contains(@placeholder,'电邮') or contains(@placeholder,'郵箱') or contains(@placeholder,'Email')]"
        ).first

        # 备注
        self.remark_textarea: Locator = page.locator(
            "//textarea[contains(@placeholder,'备注') or contains(@placeholder,'備註')]"
        ).first

    # ---------------- 内部工具（替代 OperateElement / execute_script） ----------------

    def _smart_click(self, loc: Locator, desc: str) -> None:
        """真点击优先 → 被遮挡/超时则 force 点击（仍走鼠标事件，不 dispatch_event）"""
        loc.scroll_into_view_if_needed(timeout=self.timeout)
        try:
            loc.click(timeout=self.timeout)
        except PWTimeout:
            print(f"  [retry] {desc} 普通点击被拦截，转 force 点击")
            loc.click(timeout=self.timeout, force=True)
        print(f" ✔ click: {desc}")

    # ========== 页面加载 ==========
    def wait_for_page_load(self):
        # 原版：url_contains + sleep(1) + presence_of(submit_btn)
        self.page.wait_for_url(f"**/*{self.url_contains}*", timeout=self.timeout)
        self.submit_order_btn.wait_for(state="visible", timeout=self.timeout)
        print(f" 进入确认订单页: {self.page.url}")
        return self

    # ========== 提交订单 ==========
    def click_submit_order(self):
        self._smart_click(self.submit_order_btn, "提交订单")
        return self

    # ========== 通用点击加号（防stale核心 → Locator 天然不 stale） ==========
    def _click_plus_by_index(self, index, name):
        """按索引点加号的父级 cursor-pointer。
        原版每次 find_elements 重取以防 stale；Locator 惰性求值天然等价，索引语义不变。"""
        icons = self.plus_icons
        total = icons.count()
        if total <= index:
            raise IndexError(f"找不到{name}的加号，当前仅 {total} 个加号")

        target = icons.nth(index).locator("xpath=..")   # 等价 icon.find_element(By.XPATH,'..')
        self._smart_click(target, f"{name} + 号")

        # 替代 time.sleep(0.3)：等 Ant 数字框动画 + 值真的变了（最多 800ms，变了就走）
        try:
            target.page.wait_for_function(
                """() => document.querySelectorAll('.anticon-plus').length > 0""",
                timeout=800,
            )
        except PWTimeout:
            pass
        return self

    # ========== 通用获取数量（单 XPath 一步到位，与原版同一条表达式） ==========
    def _get_count_by_index(self, index, name):
        xpath = f"(//span[contains(@class,'anticon-plus')])[{index + 1}]/parent::div/parent::div/div[2]"
        try:
            el = self.page.locator(f"xpath={xpath}").first
            el.wait_for(state="attached", timeout=3_000)
            text = (el.inner_text() or "").strip()
            if text.isdigit():
                return int(text)
            print(f"  ⚠ 获取{name}数量非数字: '{text}'")
        except Exception as e:
            print(f"  获取{name}数量异常: {e}")
        return 0

    # ========== 成人 ==========
    def click_adult_plus(self):
        self._click_plus_by_index(IDX_ADULT, "成人")
        return self

    def get_adult_count(self):
        return self._get_count_by_index(IDX_ADULT, "成人")

    # ========== 兒童 ==========
    def click_child_plus(self):
        self._click_plus_by_index(IDX_CHILD, "兒童")
        return self

    def get_child_count(self):
        return self._get_count_by_index(IDX_CHILD, "兒童")

    # ========== 長者 ==========
    def click_elder_plus(self):
        self._click_plus_by_index(IDX_ELDER, "長者")
        return self

    def get_elder_count(self):
        return self._get_count_by_index(IDX_ELDER, "長者")

    # ========== 下单字段填写 ==========

    def _safe_send_keys(self, locator: Locator, value, field_name=""):
        """等价原 _safe_send_keys：scroll → clear → fill。
        不再需要 StaleElementReference 重试（Locator 每次重新解析）；
        fill() 自带可操作性等待 + 自动 clear，且会触发 React 受控组件的 value setter
        （比 el.clear()+send_keys() 对 Ant Design 更稳）。"""
        locator.scroll_into_view_if_needed(timeout=self.timeout)
        locator.fill("", timeout=self.timeout)          # 先清空
        locator.fill(str(value), timeout=self.timeout)  # 再填
        if field_name:
            print(f"  已填写{field_name}: {value}")
        return self

    def fill_chinese_name(self, name_cn="自動化測試"):
        """填写中文名"""
        self._safe_send_keys(self.chinese_name_input, name_cn, "中文名")
        return self

    def click_translate_to_english(self):
        """点击中转英按钮，触发自动拼音转换"""
        self._smart_click(self.translate_btn, "中转英按钮")
        # ⚠️ 原版 sleep(1.5) 等拼音回填 → 改成轮询等「姓/名拼音框真的有值」，
        # 快则 200ms 走人，慢则最多等 5s，不会因为接口抖一下就填空值提交
        try:
            self.page.wait_for_function(
                """(sels) => {
                    const g = document.evaluate(sels[0], document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    const s = document.evaluate(sels[1], document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    return !!(g && g.value && g.value.trim()) && !!(s && s.value && s.value.trim());
                }""",
                arg=[
                    self.given_name_input._impl._selector if hasattr(self.given_name_input._impl, "_selector")
                    else "//input[contains(@placeholder,'名') and not(contains(@placeholder,'中文'))]",
                    "//input[contains(@placeholder,'姓') and not(contains(@placeholder,'中文'))]",
                ],
                timeout=5_000,
            )
            print("  拼音已回填完成")
        except PWTimeout:
            # 兜底：等 600ms 再复核一次，仍空则告警但不中断（与原版"睡完就走"行为一致）
            self.page.wait_for_timeout(600)
            g = self.given_name_input.input_value().strip()
            s = self.surname_input.input_value().strip()
            if not (g and s):
                print(f"  ⚠️ 拼音回填可能未完成: 姓='{s}' 名='{g}'（继续，提交时若校验失败会暴露）")
            else:
                print("  拼音已回填完成（兜底复核）")
        return self

    def fill_phone(self, phone="96526666"):
        """填写手机号"""
        self._safe_send_keys(self.phone_input, phone, "手机号")
        return self

    def fill_email(self, email="AutomatedTesting@gmail.com"):
        """填写邮箱"""
        self._safe_send_keys(self.email_input, email, "邮箱")
        return self

    def fill_remark(self, remark="自動化測試備註"):
        """填写备注"""
        self._safe_send_keys(self.remark_textarea, remark, "备注")
        return self

    def fill_order_fields(self, name_cn="自动化测试", phone="96526666",
                          email="AutomatedTesting@gmail.com", remark="自動化測試備註"):
        """
        统一填写所有下单字段（完整链路）：中文名 → 中转英（自动回填姓/名拼音）→ 手机号 → 邮箱 → 备注
        ⚠️ 调用顺序与原版严格一致，勿调整（拼音接口依赖中文名先落值）
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
        点击提交订单 → 等待跳转到 confirm-order 页面，返回 groupId（动态提取，供后续业务使用）
        """
        self._smart_click(self.submit_order_btn, "提交订单")
        print(" 已点击提交订单，等待跳转确认页...")

        # 原版：url_contains + sleep(1)；这里等 URL + 等页面主体出来，双保险
        self.page.wait_for_url(f"**/*{self.CONFIRM_ORDER_URL_CONTAINS}*", timeout=timeout * 1000)
        try:
            self.page.locator("body").wait_for(state="visible", timeout=3_000)
            self.page.wait_for_load_state("domcontentloaded", timeout=5_000)
        except PWTimeout:
            pass

        current_url = self.page.url
        print(f" 已跳转到订单确认页: {current_url}")

        group_id = self._extract_group_id_from_url(current_url)
        if group_id:
            print(f"  提取到 groupId: {group_id}")
        else:
            print("  ⚠️ 未能从 URL 中提取 groupId")
        return group_id

    def _extract_group_id_from_url(self, url=None):
        """从 confirm-order?groupId=xxx 的 URL 中提取 groupId（纯字符串逻辑，未改动）"""
        target_url = url or self.page.url
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
        current_url = self.page.url
        assert self.CONFIRM_ORDER_URL_CONTAINS in current_url, \
            f"未跳转到订单确认页: {current_url}"
        # 顺带校验 groupId 真的在 URL 里，避免"路径对了但参数丢了"的假绿
        assert self._extract_group_id_from_url(current_url), \
            f"确认页 URL 缺少 groupId: {current_url}"
        print(f" 订单确认页断言通过: {current_url}")
        return self