# -*- coding: utf-8 -*-
"""
page/bus_home_page.py —— 大巴票首页 Page Object（Playwright 版）
"""
from datetime import datetime, timedelta

from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

# ---------------- 城市 / 站點 ID（須在 class 外，與原版一致） ----------------
SHENZHEN_CITY_ID = "133"
HONGKONG_CITY_ID = "2"
SHENZHEN_WAN_STATION_ID = "200006"
TIANSHAJIE_STATION_ID = "300282"

# ---------------- 站點 testid（trigger / 按鈕：船票側已實測存在，可信）---------
TRIGGER_DEPART = "bus-go-depart-city-trigger"   # 出發地觸發框（原本缺這個常量）
TRIGGER_ARRIVE = "bus-op-arrive-city-trigger"   # 到達地觸發框（注意是 bus-op- 不是 bus-go-）
BTN_SEARCH = "bus-btn-search"                   # 立即查詢

MODAL_DEPART_TESTID = "bus-go-depart-city-modal"   # 候選名（猜的）
MODAL_ARRIVE_TESTID = "bus-go-arrive-city-modal"   # 候選名（猜的）
BUS_MODAL_USE_TESTID = False                       # ← 實測確認後改 True，主路徑自動切過去
BUS_MODAL_OPEN = "div[role='dialog']:visible"

# ---------------- 彈窗標題關鍵詞（消歧唯一穩定信號，⚠請 F12 覈對）----------
TXT_MODAL_DEPART = "出發"      # 出發地彈窗標題含此詞
TXT_MODAL_ARRIVE = "到達"      # 到達地彈窗標題含此詞（若線上寫「抵達」改這裏）

# ---------------- 兜底文案（testid 失效時啓用；站點爲繁體，與線上一致）--------
TXT_DEPART_LABEL = "出發城市/站點"
TXT_ARRIVE_LABEL = "到達城市/站點"
TXT_ARRIVE_DEFAULT = "香港/旺角油麻地"     # 到達框默認值，用於兜底反查 trigger

DATE_PICKER_TRIGGER = "div.ant-picker"
DATE_DROPDOWN = "div.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)"

DEFAULT_TIMEOUT = 10_000


class BusHomePage:
    def __init__(self, page: Page, timeout: int = DEFAULT_TIMEOUT):
        self.page = page
        self.timeout = timeout
        # 與原版 self.wait 對齊：僅用於 wait_for_url / 自定義條件等少數場景
        page.set_default_timeout(timeout)
        self._testid_warned: set = set()      # ④ 同一個 testid 只告警一次，不刷屏

    # ==================== 內部小工具（替代 OperateElement） ====================

    def _warn_once(self, key: str, msg: str) -> None:
        if key not in self._testid_warned:
            self._testid_warned.add(key)
            print(f" ⚠️ {msg}")

    # ---------- ② 彈窗定位：testid（可選）→ antd 結構 + 標題消歧 ----------

    def _open_modal(self, trigger: Locator, title_kw: str,
                    testid: str = "", desc: str = "") -> Locator:
        """
        點 trigger → 等 antd 彈窗【真正可見】→ 校標題關鍵詞 → 返回彈窗 root locator。

        ⚠️ 這是本文件最重要的一個方法：它把「點出發卻等到達彈窗」這類串臺錯誤，
           從 10s 後一句 TimeoutError，變成 3s 內指名道姓的斷言失敗。

        :param trigger:   已定位好的觸發框 locator（調用方負責，保留原兜底鏈）
        :param title_kw:  彈窗標題必須包含的關鍵詞（TXT_MODAL_DEPART / ARRIVE）
        :param testid:    若前端已確認加了 testid，傳進來走主路徑；否則走 antd 結構
        :param desc:      日誌用描述
        """
        self._safe_click(trigger, desc or f"打開「{title_kw}」彈窗 trigger")

        # --- 等彈窗出現：testid 優先（已實測確認時），否則 antd 結構 ---
        if BUS_MODAL_USE_TESTID and testid:
            modal = self.page.locator(f"[data-testid='{testid}']:visible").first
            try:
                modal.wait_for(state="visible", timeout=self.timeout)
            except PWTimeout:
                # testid 猜錯了不能靜默降到結構路徑——那會把「前端改了 testid」
                # 這件該知道的事蓋住。打人話，再降級。
                self._warn_once(
                    testid,
                    f"testid `{testid}` 10s 內未出現 → 該 testid 可能【前端未加/已改名】。\n"
                    f"     已降級到 antd 結構定位（div[role=dialog]:visible）繼續跑；\n"
                    f"     請跑附錄 A 的實彈清單腳本，把真實 testid 回填到常量區並打開 "
                    f"BUS_MODAL_USE_TESTID。"
                )
                modal = self.page.locator(BUS_MODAL_OPEN).first
                modal.wait_for(state="visible", timeout=self.timeout)
        else:
            modal = self.page.locator(BUS_MODAL_OPEN).first
            try:
                modal.wait_for(state="visible", timeout=self.timeout)
            except PWTimeout:
                # 附上「現在頁面上到底有什麼 dialog」的現場，別讓人對着空日誌猜
                dump = self.page.evaluate(
                    "() => [...document.querySelectorAll('[role=dialog],.ant-modal-root')].map("
                    "  e => ({testid: e.dataset.testid||'(無)', "
                    "          cls: e.className.toString().slice(0,60), "
                    "          disp: getComputedStyle(e).display}))"
                )
                raise AssertionError(
                    f" 點擊「{desc or title_kw}」trigger 後 {self.timeout}ms 內【沒有任何彈窗出現】\n"
                    f"  頁面現存 dialog 節點: {dump}\n"
                    f"  → 若列表爲空：trigger 壓根沒打開彈窗（點錯元素 / 被遮罩吃掉了）\n"
                    f"  → 若列表有節點但 disp=none：彈窗開了又被立即關掉（多半是觸發了兩次點擊）"
                ) from None

        # --- ② 消歧：標題必須含關鍵詞。這一行是本方法的靈魂 ---
        try:
            self.page.locator(f"{BUS_MODAL_OPEN} .ant-modal-title").first.wait_for(
                state="visible", timeout=5_000)
            title_text = self._norm(
                self.page.locator(f"{BUS_MODAL_OPEN} .ant-modal-title").first.inner_text())
        except PWTimeout:
            title_text = "(取不到標題)"

        if title_kw not in title_text:
            # 不 force、不降級：這就是「點 A 等 B」，必須紅，且紅得能看懂
            all_testids = self.page.evaluate(
                "() => [...document.querySelectorAll('[data-testid]')]"
                ".map(e=>e.dataset.testid).filter(t=>t.startsWith('bus-'))"
            )
            raise AssertionError(
                f" 彈窗串臺：點的是「{desc or title_kw}」trigger，但彈出來的標題是「{title_text}」\n"
                f"  → 檢查 trigger 定位是否指到了對面的框（出發/到達寫反）\n"
                f"  頁面上所有 bus-* testid: {all_testids}\n"
                f"  提示：若標題文案不是「{title_kw}」請改常量 TXT_MODAL_DEPART/ARRIVE，"
                f"別改這行斷言。"
            )
        print(f" ✔ 彈窗已就緒（標題含「{title_kw}」：{title_text}）")
        return modal

    def _modal(self) -> Locator:
        """
        【降級用·主路徑已不用】當前可見的城市/站點彈窗。
        保留是爲了兼容可能還在調這個方法的外部代碼；新代碼請走 _open_modal()。
        ⚠️ 原版這裏把 MODAL_DEPART / MODAL_ARRIVE 賦了同一個值，導致出發流程
           等在 arrive 標識符上 → 本次 CI 紅的根因。現改爲 antd 結構主路徑。
        """
        if BUS_MODAL_USE_TESTID:
            return self.page.locator(
                f"[data-testid='{MODAL_DEPART_TESTID}']:visible, {BUS_MODAL_OPEN}"
            ).first
        return self.page.locator(BUS_MODAL_OPEN).first

    def _trigger_box(self, label: str) -> Locator:
        """按左側標籤文案反查觸發框容器（兜底用，testid 優先）。"""
        return self.page.locator(
            f"span:text-is('{label}')").locator(
            "xpath=ancestor::div[contains(@class,'cursor-pointer')][1]"
        )

    def _display(self, label: str) -> Locator:
        """觸發框裏「已選值」那塊 div（帶 data-city-id / data-station-id）。"""
        return self._trigger_box(label).locator("div.cursor-pointer").first

    @staticmethod
    def _norm(text) -> str:
        return (text or "").replace("\u3000", " ").strip()

    def _safe_click(self, loc: Locator, desc: str, force: bool = False) -> None:
        """真點擊優先；僅對已知被 Ant Design 僞元素遮擋的 <li>/<span> 用 force。
        不做 dispatch_event —— 那會跳過遮擋校驗，測不出「用戶點不到」的缺陷。"""
        loc.scroll_into_view_if_needed(timeout=self.timeout)
        try:
            loc.click(timeout=self.timeout, force=force)
        except PWTimeout:
            if force:
                # force 都點不動 = 真被擋住或不在視口，這是要報的缺陷，別再吞
                raise AssertionError(
                    f" 強制點擊仍失敗：{desc}（元素存在但命中測試不通過 —— "
                    f"多半有透明遮罩 layer 蓋在上面，屬前端缺陷）"
                ) from None
            self._warn_once(desc, f"普通點擊被攔截，轉 force 點擊：{desc}")
            loc.click(timeout=self.timeout, force=True)
        print(f" ✔ click: {desc}")

    # ==================== 1. 出發地 ====================

    def select_depart_city_station(self, depart_city="深圳",
                                   depart_station="深圳灣（香港段上）"):
        # --- 步驟1: 定位並點開出發地彈窗 ---
        # 主：testid（船票側同命名規律已實測存在）；兜底：左側標籤文案反查；
        # 再兜底：默認文本「香港/旺角油麻地」所在的可點容器
        trigger = self.page.locator(
            f"[data-testid='{TRIGGER_DEPART}'] div.cursor-pointer, "
            f"[data-testid='{TRIGGER_DEPART}']"
        ).or_(self._trigger_box(TXT_DEPART_LABEL)).or_(
            self.page.locator(f"span:has-text('{TXT_ARRIVE_DEFAULT}')").locator(
                "xpath=ancestor::div[contains(@class,'cursor-pointer')][1]")
        ).first

        if not self.page.locator(f"[data-testid='{TRIGGER_DEPART}']").count():
            self._warn_once(
                TRIGGER_DEPART,
                f"testid `{TRIGGER_DEPART}` 未在 DOM 中命中，已走文案兜底"
                f"（出發框默認值若被改過，兜底也會失效 → 請補 testid）"
            )

        # ② 主路徑：結構 + 標題消歧（不再碰 MODAL_DEPART 那個錯值）
        modal = self._open_modal(
            trigger, TXT_MODAL_DEPART,
            testid=MODAL_DEPART_TESTID,
            desc="打開出發地彈窗"
        )

        # --- 步驟2: 左側城市（data-city-id 最穩，文案僅兜底）---
        city = modal.locator(
            f"li[data-city-id='{SHENZHEN_CITY_ID}'].cursor-pointer"
        ).or_(modal.locator(f"li.cursor-pointer:text-is('{depart_city}')")).first
        self._safe_click(city, f"选出发城市: {depart_city}", force=True)

        # 等「選中態」落地 = 右側站點列表已完成聯動渲染（比 sleep 準）
        try:
            modal.locator("li[data-city-id][aria-selected='true'], li.active").first.wait_for(
                state="attached", timeout=self.timeout)
        except PWTimeout:
            self._warn_once("city-selected",
                            "城市選中態（aria-selected/active）未檢出，繼續走站點定位；"
                            "若下一步站點找不到，多半是聯動沒觸發")

        # --- 步驟3: 右側站點 ---
        station = modal.locator(
            f"span[data-station-id='{SHENZHEN_WAN_STATION_ID}'].cursor-pointer"
        ).or_(modal.locator(
            f"span.cursor-pointer:has-text('{depart_station}')")).first
        self._safe_click(station, f"选出发站点: {depart_station}", force=True)

        # 彈窗收起 = 選擇被前端接受（比 sleep 可靠）
        modal.wait_for(state="hidden", timeout=self.timeout)
        print(f" 出发地已选定: {depart_city}/{depart_station}")

    # ==================== 2. 到達地（含聯動回補） ====================

    def select_arrive_city_station(self, arrive_city="香港", arrive_station="尖沙咀海港城",
                                   depart_city_keep="深圳",
                                   depart_station_keep="深圳灣（香港段上）"):
        dep_display = self._display(TXT_DEPART_LABEL)

        # 等出發地已穩定（原版 text_to_be_present_in_element）
        dep_display.filter(has_text=depart_city_keep).wait_for(
            state="visible", timeout=self.timeout)

        # --- 點到達觸發框：testid 主，標籤文案兜底 ---
        arrive_trigger = self.page.locator(
            f"[data-testid='{TRIGGER_ARRIVE}'] div.cursor-pointer, "
            f"[data-testid='{TRIGGER_ARRIVE}']"
        ).or_(self._trigger_box(TXT_ARRIVE_LABEL)).first

        if not self.page.locator(f"[data-testid='{TRIGGER_ARRIVE}']").count():
            self._warn_once(
                TRIGGER_ARRIVE,
                f"testid `{TRIGGER_ARRIVE}` 未在 DOM 中命中（注意是 bus-op- 不是 bus-go-），"
                f"已走文案兜底"
            )

        # ② 主路徑：同樣走「結構 + 標題消歧」，這裏就不可能再寫成出發了
        modal = self._open_modal(
            arrive_trigger, TXT_MODAL_ARRIVE,
            testid=MODAL_ARRIVE_TESTID,
            desc="打開到達地彈窗"
        )
        print(" 找到到达弹窗")

        # --- 選到達城市：香港(2) ---
        city = modal.locator(
            f"li[data-city-id='{HONGKONG_CITY_ID}'].cursor-pointer"
        ).or_(modal.locator(f"li:has(> span:text-is('{arrive_city}'))")).first
        self._safe_click(city, f"选到达城市: {arrive_city}", force=True)

        # --- 選到達站點：精準到 data-station-id，不依賴區域標題 ---
        station = modal.locator(
            f"span[data-station-id='{TIANSHAJIE_STATION_ID}']"
        ).or_(modal.locator(
            f"span.cursor-pointer[data-station-id]:has-text('{arrive_station}')")).first
        try:
            station.wait_for(state="visible", timeout=self.timeout)
        except PWTimeout:
            # 聯動後站點列表重掛載是常態，給一次「等列表穩定後重取」的機會
            self._warn_once("arrive-station",
                            f"站點 `{arrive_station}`(id={TIANSHAJIE_STATION_ID}) 首輪未可見，"
                            f"等聯動列表穩定後重取一次")
            modal.locator("span[data-station-id]").first.wait_for(
                state="visible", timeout=self.timeout)
            station = modal.locator(
                f"span[data-station-id='{TIANSHAJIE_STATION_ID}']"
            ).or_(modal.locator(
                f"span.cursor-pointer[data-station-id]:has-text('{arrive_station}')")).first
            station.wait_for(state="visible", timeout=self.timeout)

        self._safe_click(station, f"选完到达: {arrive_city}/{arrive_station}", force=True)
        modal.wait_for(state="hidden", timeout=self.timeout)

        # --- 聯動後回讀真實 DOM（不再 JS 篡改）---
        arr_display = self._display(TXT_ARRIVE_LABEL)
        final_depart_text = self._norm(dep_display.inner_text())
        final_depart_city_id = dep_display.get_attribute("data-city-id") or ""
        final_depart_station_id = dep_display.get_attribute("data-station-id") or ""
        final_arrive_text = self._norm(arr_display.inner_text())
        final_arrive_city_id = arr_display.get_attribute("data-city-id") or ""
        final_arrive_station_id = arr_display.get_attribute("data-station-id") or ""
        print(f" 联动后: 出发=[{final_depart_text}](city={final_depart_city_id},"
              f"station={final_depart_station_id}), "
              f"到达=[{final_arrive_text}](city={final_arrive_city_id},"
              f"station={final_arrive_station_id})")

        assert arrive_city in final_arrive_text and arrive_station in final_arrive_text, \
            f" 到达文本异常: {final_arrive_text}"

        # --- 出發被聯動衝掉 → 真的重新選回來（替代原來的 innerHTML 回寫）---
        if (final_depart_city_id != SHENZHEN_CITY_ID
                or depart_station_keep not in final_depart_text
                or final_depart_station_id != SHENZHEN_WAN_STATION_ID):
            print(f" ⚠ 出发站点被联动刷新(当前:{final_depart_text})，"
                  f"重新选择回写（真实点击，非 DOM 篡改）")
            self.select_depart_city_station(depart_city_keep, depart_station_keep)
            # 回補後到達框可能被再次影響，複覈一次
            final_arrive_text = self._norm(arr_display.inner_text())
            assert arrive_city in final_arrive_text and arrive_station in final_arrive_text, \
                f" 回补出发后到达被冲掉: {final_arrive_text}"

        # --- 最終雙校驗（讀真實 DOM）---
        self.assert_route_ready(depart_city_keep, depart_station_keep,
                                arrive_city, arrive_station)
        print(f" select_arrive_city_station 完成: "
              f"出发[{self._norm(dep_display.inner_text())}] -> "
              f"到达[{self._norm(arr_display.inner_text())}]")

    # ==================== ⑦ 雙框回讀單一入口 ====================

    def assert_route_ready(self, depart_city_keep="深圳",
                           depart_station_keep="深圳灣（香港段上）",
                           arrive_city="香港", arrive_station="尖沙咀海港城") -> dict:
        """
        讀【真實 DOM】(data-city-id / data-station-id + 文本)，返回四方元組並斷言。
        給 business / 用例層用：結果頁查詢後校驗「路線沒被清空」也調這個，
        免得 4 行 assert 在三個文件裏各抄一份、改一處漏兩處。
        """
        dep = self._display(TXT_DEPART_LABEL)
        arr = self._display(TXT_ARRIVE_LABEL)
        info = {
            "depart_text": self._norm(dep.inner_text()),
            "depart_city_id": dep.get_attribute("data-city-id") or "",
            "depart_station_id": dep.get_attribute("data-station-id") or "",
            "arrive_text": self._norm(arr.inner_text()),
            "arrive_city_id": arr.get_attribute("data-city-id") or "",
            "arrive_station_id": arr.get_attribute("data-station-id") or "",
        }
        assert f"{depart_city_keep}/{depart_station_keep}" in info["depart_text"], \
            f" 出发最终失败: {info['depart_text']}（期望含 {depart_city_keep}/{depart_station_keep}）"
        assert f"{arrive_city}/{arrive_station}" in info["arrive_text"], \
            f" 到达最终失败: {info['arrive_text']}（期望含 {arrive_city}/{arrive_station}）"
        return info

    # ==================== 3. 日期（兩天後，禁跳空） ====================

    def select_date_two_days_later(self):
        """選當天+2天：同月直接點，跨月最多翻 2 次；翻不到位直接斷言失敗，絕不跳空選錯日。"""
        target = datetime.today() + timedelta(days=2)
        target_str = target.strftime("%Y-%m-%d")
        month_cn = f"{target.year}年{target.month}月"      # "2026年11月"（locale=zh-HK 亦兼容）
        month_iso = target.strftime("%Y-%m")               # "2026-11"
        day_num = target.day

        self.page.locator(DATE_PICKER_TRIGGER).first.click()
        dropdown = self.page.locator(DATE_DROPDOWN).first
        header = dropdown.locator(".ant-picker-header-view")
        header.wait_for(state="visible", timeout=self.timeout)
        header_text = self._norm(header.inner_text())
        print(f"  初始面板月份: {header_text}")

        # 跨月翻頁，最多 2 次（+2 天最多跨 1 個月，給 2 次是容錯）
        turned = 0
        for _ in range(2):
            if month_cn in header_text or month_iso in header_text:
                break
            nxt = dropdown.locator("button.ant-picker-header-next-btn")
            try:
                nxt.wait_for(state="visible", timeout=self.timeout)
                nxt.click(timeout=self.timeout)
            except PWTimeout:
                raise AssertionError(
                    f" 翻月按鈕 .ant-picker-header-next-btn 點不動 —— 目標 {month_cn} "
                    f"但面板停在 {header_text}。可能是日期區間被後端限制（如只可訂 60 天內），"
                    f"或面板結構改版。當前 URL: {self.page.url}"
                ) from None
            header_text = self._norm(header.inner_text(timeout=self.timeout))
            turned += 1
            print(f"  翻月后面板: {header_text}")

        assert month_cn in header_text or month_iso in header_text, \
            f" 月份定位異常！翻了 {turned} 次仍不匹配。期望: {month_cn} / {month_iso}, 實際: {header_text}"

        # 精確命中 title="YYYY-MM-DD"，排除置灰的上月/下月補位格
        cell = dropdown.locator(
            f"td.ant-picker-cell-in-view:not(.ant-picker-cell-disabled)[title='{target_str}']"
        ).first
        try:
            cell.wait_for(state="visible", timeout=self.timeout)
        except PWTimeout:
            # 兜底：按日號取「當期月」裏的第 day_num 格（仍限定 in-view，防跳空）
            self._warn_once("date-fallback",
                            f"title='{target_str}' 未命中，改用日號 {day_num} 定位"
                            f"（注意：這條兜底可能選錯日，若 CI 日期對不上先查這裏）")
            cell = dropdown.locator(
                f"td.ant-picker-cell-in-view:not(.ant-picker-cell-disabled) >> "
                f"text=/^{day_num}$/"
            ).first
            cell.wait_for(state="visible", timeout=self.timeout)

        cell.scroll_into_view_if_needed()
        cell.click(timeout=self.timeout)   # 真點擊：Ant 單元格無遮擋，不需要 force

        # 面板關閉 = 值已被接受
        self.page.locator(DATE_DROPDOWN).first.wait_for(state="hidden", timeout=self.timeout)
        self._picked_date = target_str     # 供 business/用例層覈對（選了哪天）
        print(f"  日期选择完成: {target_str}")
        return target_str   # ← 契約：原版也 return

    # ==================== 4. 立即查詢 ====================

    def click_search_now(self):
        """點【立即查詢】並等結果頁。契約：以 URL 含 date= 爲完成標誌，與原版一致。"""
        # 日期面板必須先收起，否則會吃掉這次點擊
        self.page.locator("div.ant-picker-dropdown").filter(
            has_not_class="ant-picker-dropdown-hidden"
        ).first.wait_for(state="hidden", timeout=self.timeout)

        btn = self.page.locator(f"[data-testid='{BTN_SEARCH}']").first

        # ⑥ 先確認按鈕可點：Ant 表單未校驗通過時按鈕是 disabled，
        #    直接 click 會自動重試到超時，報錯只說 TimeoutError，很難看懂。
        try:
            btn.wait_for(state="visible", timeout=self.timeout)
        except PWTimeout:
            raise AssertionError(
                f" 【立即查詢】按鈕(testid={BTN_SEARCH}) 10s 未出現 —— "
                f"testid 可能未加/已改名。頁面 bus-* testid: "
                f"{self.page.evaluate(chr(40)+'() => [...document.querySelectorAll(String.fromCharCode(91)+' + chr(39) + 'data-testid' + chr(39) + ')]').__self__ and 'see_log' or 'x'}"
            ) from None

        if btn.is_disabled():
            # 按鈕灰掉 = 表單還沒填完，這是有價值的信號，別 force 硬點
            route = self._safe_route_peek()
            raise AssertionError(
                f" 【立即查詢】按鈕處於 disabled —— 表單校驗未通過（多半是出發/到達"
                f"其中之一被聯動清空了）。當前路線快照: {route}"
            )

        btn.scroll_into_view_if_needed()
        try:
            btn.click(timeout=self.timeout)          # 真點擊；被攔截會重試
        except PWTimeout:
            self._warn_once("search-force", "【立即查詢】普通點擊被攔截，轉 force")
            btn.click(timeout=self.timeout, force=True)
        print(" 点击【立即查詢】完成 (testid=bus-btn-search)")

        try:
            self.page.wait_for_url("**/*date=*", timeout=20_000)
        except PWTimeout:
            raise AssertionError(
                f" 點完【立即查詢】20s 內 URL 仍無 date= 參數：{self.page.url}\n"
                f"  → 可能表單校驗攔了（看上面有沒有 AntD 錯誤 Toast）"
                f"  → 也可能點到了別的按鈕，截圖已由 conftest hook 保存"
            ) from None
        print(f" 已进入结果页: {self.page.url}")

    # ---------------- 內部：出錯時的路線快照（只讀，不拋） ----------------

    def _safe_route_peek(self) -> dict:
        try:
            return self.assert_route_ready.__wrapped__(self) if False else {
                "depart": self._norm(self._display(TXT_DEPART_LABEL).inner_text()),
                "arrive": self._norm(self._display(TXT_ARRIVE_LABEL).inner_text()),
            }
        except Exception as exc:
            return {"(讀取失敗)": str(exc)}