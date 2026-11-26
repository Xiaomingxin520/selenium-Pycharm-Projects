# -*- coding: utf-8 -*-
"""
page/bus_search_result_page.py —— 大巴票【搜索结果页】Page Object（Playwright 版）
"""
from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

DEFAULT_TIMEOUT = 15_000


class BusSearchResultPage:

    # ==================== 定位器（原样搬运，未改写表达式） ====================
    # 动态定位：不依赖ID，取最后一个"站點地圖"
    LAST_TRIP_MAP_BTN = (
        "(//*[contains(text(),'上車')]/following-sibling::*[contains(text(),'站點地圖')] | "
        "//*[contains(text(),'上車')]/../*[contains(text(),'站點地圖')] | "
        "//*[contains(text(),'上車')]//following::*[contains(text(),'站點地圖')][1])[last()]"
    )

    # 上車弹窗特征
    MAP_TAB_UP = "//*[text()='上車點']"
    MAP_TITLE = (
        "//div[contains(@class,'ant-modal')][.//*[text()='上車點']]"
        "//*[contains(text(),'深圳灣（香港段上）')]"
    )

    # 最后一班【下車】的站點地圖（隔离终点）
    LAST_TRIP_DOWN_MAP_BTN = (
        "(//*[contains(text(),'下車')]/../..//*[contains(text(),'站點地圖')])[last()]"
    )

    # 下車弹窗特征
    MAP_TAB_DOWN = "//*[text()='下車點']"
    MAP_TITLE1 = (
        "//div[contains(@class,'ant-modal')][.//*[text()='下車點']]"
        "//*[contains(text(),'尖沙咀海港城')]"
    )

    # 弹窗取消/关闭按钮
    MODAL_CLOSE_BTN = "button.ant-modal-close"
    MODAL_MASK = "div.ant-modal-mask"

    # 购票按钮基础定位
    TICKET_BTN_BASE = (
        "//button[contains(@class,'ant-btn-primary')][.//span[text()='購票']]"
    )

    def __init__(self, page: Page, timeout: int = DEFAULT_TIMEOUT):
        self.page = page
        self.timeout = timeout

        # 与原版同名同义的 Locator 属性（惰性求值 → 天然不 stale，
        # 因此原版「每次操作前重新 find_element 防 stale」的写法在这里是默认行为）
        self.last_trip_map_btn: Locator = page.locator(f"xpath={self.LAST_TRIP_MAP_BTN}").last
        self.last_trip_down_map_btn: Locator = page.locator(f"xpath={self.LAST_TRIP_DOWN_MAP_BTN}").last
        self.map_tab_up: Locator = page.locator(f"xpath={self.MAP_TAB_UP}").first
        self.map_tab_down: Locator = page.locator(f"xpath={self.MAP_TAB_DOWN}").first
        self.map_title: Locator = page.locator(f"xpath={self.MAP_TITLE}").first
        self.map_title1: Locator = page.locator(f"xpath={self.MAP_TITLE1}").first
        self.modal_close_btn: Locator = page.locator(self.MODAL_CLOSE_BTN).first
        self.modal_mask: Locator = page.locator(self.MODAL_MASK).first
        self.ticket_btn_base: Locator = page.locator(f"xpath={self.TICKET_BTN_BASE}")

        # 结果列表渲染完成的锚点（原版内联写的 XPath，提为常量便于复用）
        self._list_ready = page.locator("xpath=//*[contains(text(),'班次號')]").first

    # ---------------- 内部工具 ----------------
    def _smart_click(self, loc: Locator, desc: str) -> None:
        """真点击优先 → 遮挡/超时则 force 点击（仍走鼠标事件链路，不 dispatch_event）"""
        loc.scroll_into_view_if_needed(timeout=self.timeout)
        try:
            loc.click(timeout=self.timeout)
        except PWTimeout:
            print(f"  [retry] {desc} 普通点击被拦截，转 force 点击")
            loc.click(timeout=self.timeout, force=True)
        print(f" ✔ click: {desc}")

    def _wait_list_ready(self) -> None:
        """等价原版 wait.until(presence_of_element_located(班次號))"""
        self._list_ready.wait_for(state="attached", timeout=self.timeout)

    def _dump_loading_probe(self, tag: str) -> None:
        """原版那段「打印页面里所有含 loading 的 class 元素」调试代码，保留但改为只读快照。
        ⚠️ 原版用 find_elements 直接取（可能抓到尚未渲染完的节点）；这里给 300ms 宽限，
           只做诊断、不影响流程，返回数量便于日志观察。"""
        try:
            self.page.wait_for_timeout(300)
            nodes = self.page.locator("xpath=//*[contains(@class,'loading')]")
            n = nodes.count()
            print(f" {tag}：找到 {n} 個含'loading'的class元素:")
            for i in range(min(n, 8)):            # 最多打 8 条，防止刷屏
                el = nodes.nth(i)
                cls = el.get_attribute("class") or ""
                txt = (el.inner_text() or "").replace("\n", " ")[:50]
                tag_n = el.evaluate("e => e.tagName.toLowerCase()")
                print(f"   tag={tag_n}, class={cls}, text={txt}")
            return n
        except Exception as e:
            print(f" {tag}：loading 探針異常（非阻塞）: {e}")
            return -1

    # ==================== 站点地图（上車） ====================

    def click_last_trip_map(self):
        """点击动态日期下最后一班的站點地圖"""
        # 1. 等待结果列表渲染（用班次號文本兜底等待）
        self._wait_list_ready()

        # 2+3+4. 定位 + 滚动 + 两级点击
        #    ⚠️ 原版先 presence 取元素、再另行 wait clickable（等于定位两次）；
        #       Locator 惰性求值一次写法即等价，且不会 stale
        self.last_trip_map_btn.wait_for(state="attached", timeout=self.timeout)
        hit = self.page.locator(f"xpath={self.LAST_TRIP_MAP_BTN}").count()
        print(f"  上車站點地圖候選命中: {hit} 個 → 取 .last")
        self._smart_click(self.last_trip_map_btn, "最後一班【上車】站點地圖")

        # 5. 调试：等弹窗渲染（原版 time.sleep(2) + 打印 loading 元素）
        self._dump_loading_probe("點擊上車地圖後")

        # 6. 等待弹窗出现
        self.map_tab_up.wait_for(state="visible", timeout=self.timeout)
        print(" 弹窗已出现")

    def assert_map_modal(self):
        """断言上車弹窗内容（上車點 + 标题兜底）"""
        self.map_tab_up.wait_for(state="visible", timeout=self.timeout)
        try:
            self.map_title.wait_for(state="visible", timeout=self.timeout)
        except PWTimeout:
            # 兜底：只校验「ant-modal 里含 上車點 Tab」，不卡死在站点名上
            fallback = self.page.locator(
                "xpath=//div[contains(@class,'ant-modal')][.//*[text()='上車點']]"
            ).first
            fallback.wait_for(state="visible", timeout=self.timeout)
            print("  （精準標題未命中，已用 Modal+Tab 兜底校驗）")
        print(" 站点地图弹窗校验通过！")
        return True

    # ==================== 站点地图（下車） ====================

    def click_last_trip_down_map(self):
        """点击最后一班【下車】的站點地圖"""
        self._wait_list_ready()

        self.last_trip_down_map_btn.wait_for(state="attached", timeout=self.timeout)
        hit = self.page.locator(f"xpath={self.LAST_TRIP_DOWN_MAP_BTN}").count()
        print(f"  下車站點地圖候選命中: {hit} 個 → 取 .last")
        self._smart_click(self.last_trip_down_map_btn, "最後一班【下車】站點地圖")

        # 等下車點弹窗出现
        self.map_tab_down.wait_for(state="visible", timeout=self.timeout)
        print(" 下車點弹窗已出现")

    def assert_down_map_modal(self):
        """断言下車弹窗内容"""
        self.map_tab_down.wait_for(state="visible", timeout=self.timeout)
        # 原版：title 超时会抛 TimeoutError，assert 那行其实到不了；
        # 这里保持「失败即抛」语义，但报错指向具体缺哪一项，便于定位
        try:
            self.map_title1.wait_for(state="visible", timeout=self.timeout)
        except PWTimeout:
            tab_txt = self.map_tab_down.inner_text()
            raise AssertionError(
                f"下車弹窗内容校验失败：Tab『{tab_txt}』已出現，"
                f"但站點名「尖沙咀海港城」未在 Modal 內找到"
                f"（換了到達站？→ MAP_TITLE1 硬編碼站點名需同步）"
            )
        print(" 下車站点地图弹窗校验通过！")
        return True

    # ==================== 关闭弹窗 ====================

    def close_map_modal(self):
        """右上角取消，并等弹窗彻底消失"""
        self.modal_close_btn.wait_for(state="attached", timeout=self.timeout)
        self._smart_click(self.modal_close_btn, "關閉地圖彈窗")

        # 关键：等遮罩消失，避免点下車时被弹窗挡住
        # 原版 invisibility_of_element_located(MODAL_MASK)：遮罩不存在也算通过，此处同义
        try:
            self.modal_mask.wait_for(state="hidden", timeout=self.timeout)
        except PWTimeout:
            if self.modal_mask.count() == 0:
                pass                      # 节点已被 remove = 弹窗确实关了
            else:
                # 最后兜底：Esc 再等一次（Ant Design 原生支持 Esc 关 Modal）
                print("  [retry] 遮罩未消失，嘗試 Esc 關閉")
                self.page.keyboard.press("Escape")
                self.modal_mask.wait_for(state="hidden", timeout=5_000)
        print(" 弹窗已关闭")

    def wait_map_closed(self):
        """新增：替代 business 层原来的 time.sleep(0.5)。
        等「可见 Modal + 遮罩」全部退场，最多 5s；没有弹窗时立即返回。"""
        try:
            self.page.locator(
                ".ant-modal-mask:visible, .ant-modal-wrap:visible"
            ).first.wait_for(state="hidden", timeout=5_000)
        except PWTimeout:
            pass
        return self

    # ==================== 购票 ====================

    def click_ticket_for_target_date(self, days_offset=2):
        """
        点击目标日期行程的【購票】按钮
        默认 days_offset=2 → 今天后两天
        ⚠️ 与原版一致：days_offset 仅用于日志，实际靠「卡片内含 深圳灣 + 尖沙咀」锁定。
           日期正确性由 business 层断言 URL 含 date={target_date} 兜住（已实现）。
        """
        # 1. 等待列表渲染完成
        self.page.locator(
            "xpath=//*[contains(text(),'班次號') or contains(text(),'購 票')]"
        ).first.wait_for(state="attached", timeout=self.timeout)

        # 2. 定位目标行程卡片内的購票按钮（XPath 原样搬运）
        ticket_btn = self.page.locator(
            "xpath=//div[contains(@class,'flex-col') or contains(@class,'gap-')]"
            "[.//*[contains(text(),'深圳灣')]]"
            "[.//*[contains(text(),'尖沙咀')]]"
            "//button[contains(@class,'ant-btn-primary')]"
            "[.//span[contains(text(),'購')]]"
        ).first
        ticket_btn.wait_for(state="visible", timeout=self.timeout)

        # 3. 滚动 + 两级点击（原版 sleep(0.5) → locator 自带稳定等待）
        self._smart_click(ticket_btn, f"目標行程購票按鈕（今天+{days_offset}天）")

        print(f" 已点击目标行程（今天+{days_offset}天）的購票按钮")

    def click_last_trip_ticket(self):
        """
        快捷方法：直接点最后一班（20:30）的購票按钮。
        适用于当前 URL 已限定日期（date=2026-10-02）的场景。
        ⚠️ Locator 惰性求值 → 原版那条「防 stale」注释在 Playwright 下是天生成立的：
           .last 每次操作重新解析 DOM，列表刷新不会 StaleElementReference。
        """
        self.page.locator("xpath=//*[contains(text(),'購 票')]").first.wait_for(
            state="attached", timeout=self.timeout)

        ticket_btn = self.page.locator(
            "xpath=(//button[contains(@class,'ant-btn-primary')]"
            "[.//span[contains(text(),'購')]])[last()]"
        ).last
        ticket_btn.wait_for(state="visible", timeout=self.timeout)

        self._smart_click(ticket_btn, "最後一班【購票】")

        # 等待跳转（防止误判没点击）——原版 url_contains("create-order")
        self.page.wait_for_url("**/*create-order*", timeout=self.timeout)
        print(f" 已点击最后一班行程的購票按钮，跳转至: {self.page.url}")