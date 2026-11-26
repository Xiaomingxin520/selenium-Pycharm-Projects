# -*- coding: utf-8 -*-
"""
business/ferryticket_business.py  船票业务调用层（Playwright 版）
"""
from playwright.sync_api import expect

from page.ferry_home_page import ferryHomePage   # ← 小寫 f/h，與 Page 層類名一致

# 常量（與 page/ferry_home_page.py 保持一致，原樣保留）
SHENZHEN_CITY_ID = "133"
HONGKONG_CITY_ID = "2"
SHENZHEN_SHEKOU_PORT_ID = "900045"
HONGKONG_AIRPORT_PORT_ID = "900054"

FERRY_SEARCH_BTN = "//*[@data-testid='ferry-btn-search']"
FERRY_DEPART_DISPLAY = (
    "//div[@data-testid='ferry-go-depart-city-trigger']"
    "//div[contains(@class,'cursor-pointer')]"
)
FERRY_ARRIVE_DISPLAY = (
    "//div[@data-testid='ferry-go-arrive-city-trigger']"
    "//div[contains(@class,'cursor-pointer')]"
)

DEFAULT_TIMEOUT = 10_000


class FerryTicketBusiness:
    def __init__(self, page, timeout: int = DEFAULT_TIMEOUT):
        """
        接收 Playwright 的 page 對象，不再依賴 Selenium driver
        :param timeout: 毫秒（與大巴 business / 全部 page 層單位一致）
        """
        self.page = page
        self.timeout = timeout
        self.target_date = None          # 船票 page 層未選日期 → 恆 None，預留位（對齊大巴屬性面）
        self.ferry_page = ferryHomePage(page)

    # ---------------- 內部工具 ----------------
    def _click_search_and_wait(self):
        """
        點【立即查詢】並等結果頁落地。與大巴 page 層 click_search_now() 同構：
          ① 等 Ant Design 日期面板徹底收起（否則它會吃掉這次點擊）
          ② 真點擊 → 被遮擋時轉 force（不用 dispatch_event）
          ③ 等 URL 出現 date= 參數 = 路由跳轉完成
        """
        # ① 日期面板必須先收起
        try:
            self.page.locator("div.ant-picker-dropdown").filter(
                has_not_class="ant-picker-dropdown-hidden"
            ).first.wait_for(state="hidden", timeout=self.timeout)
        except Exception:
            pass   # 面板本就沒開過 → 直接走，與大巴版同義

        # ② 點擊（真點擊優先）
        search_btn = self.page.locator(FERRY_SEARCH_BTN).first
        search_btn.scroll_into_view_if_needed(timeout=self.timeout)
        try:
            search_btn.click(timeout=self.timeout)
        except Exception:
            print("  [retry] 查詢按鈕普通點擊被攔截，轉 force 點擊")
            search_btn.click(timeout=self.timeout, force=True)
        print(" 已點擊【立即查詢】(ferry-btn-search)")

        # ③ 等跳轉落地（不校驗具體日期值：船票走前端默認日期，見 TODO③）
        self.page.wait_for_url("**/*date=*", timeout=20_000)
        print(f" 船票結果頁已加載: {self.page.url}")
        return self

    # ========== 核心業務：選路線 ==========
    def select_ferry_route(self,
                           depart_city="深圳",
                           depart_port="深圳蛇口碼頭",
                           arrive_city="香港",
                           arrive_port="香港國際機場海天碼頭"):
        """
        核心业务：选出发 + 选到达（真实联动，无 JS 回写）
        方法签名与原 Selenium 版完全一致，TestCase 无感切换
        """
        # 1. 选出发（Page 层已含自动等待，无需 sleep）
        self.ferry_page.select_depart_city_station(depart_city, depart_port)

        # 2. 选到达（内部依赖真实 UI 联动，异常直接抛，不伪装 DOM）
        self.ferry_page.select_arrive_city_station(
            arrive_city=arrive_city,
            arrive_port=arrive_port,
            depart_city_keep=depart_city,
            depart_station_keep=depart_port,
        )
        return self

    # ========== 完整冒烟：选路线 + 点立即查询 ==========
    def search_ferry_ticket(self,
                            depart_city="深圳",
                            depart_port="深圳蛇口碼頭",
                            arrive_city="香港",
                            arrive_port="香港國際機場海天碼頭"):
        """完整冒烟：选路线 + 点立即查询（含等结果页落地）"""
        self.select_ferry_route(depart_city, depart_port, arrive_city, arrive_port)
        self._click_search_and_wait()
        print(" 已执行船票路线选择并点击【立即查询】")
        return self

    # ========== 校驗觸發框真實文本 ==========
    def verify_selection_result(self, depart_text, arrive_text):
        """
        校验触发框的真实展示文本（非 page_source 瞎匹配）
        签名保持两参数，与 TestCase 调用一致。
        斷言文案與原版逐字一致，僅把 assert 換成 raise Exception，
        與船票 page 層「改爲異常，不放 assert」的風格統一。
        """
        # 先等兩個 trigger 文本都穩定，避免打在跳轉中的舊 DOM 上
        depart_loc = self.page.locator(FERRY_DEPART_DISPLAY).first
        arrive_loc = self.page.locator(FERRY_ARRIVE_DISPLAY).first
        expect(depart_loc).to_contain_text(depart_text)
        expect(arrive_loc).to_contain_text(arrive_text)

        depart_display = depart_loc.inner_text().strip()
        arrive_display = arrive_loc.inner_text().strip()

        if depart_text not in depart_display:
            raise Exception(
                f"出发地校验失败，期望包含[{depart_text}]，实际[{depart_display}]")
        if arrive_text not in arrive_display:
            raise Exception(
                f"到达地校验失败，期望包含[{arrive_text}]，实际[{arrive_display}]")
        print(f" 业务校验通过: 出发[{depart_display}] -> 到达[{arrive_display}]")
        return self

    # ========== 便捷斷言：URL 日期參數回顯（可選，用例按需調）==========
    def verify_search_url_has_date(self, expect_date=None):
        """
        校驗結果頁 URL 的 date= 參數。
        :param expect_date: 傳入 'YYYY-MM-DD' 則精確校驗；None 則只校驗參數存在。
        ⚠️ 船票 page 層目前不選日期，故默認只校「參數存在」。
           等 TODO③ 補上 select_date_two_days_later() 後，用例改傳 self.target_date 即可精確校。
        """
        url = self.page.url
        if "date=" not in url:
            raise Exception(f"結果頁 URL 未帶 date= 參數: {url}")
        if expect_date:
            got = url.split("date=")[-1].split("&")[0]
            if got != expect_date:
                raise Exception(f"URL 日期不符: 期望 {expect_date}, 實際 {got}")
        print(f" URL 日期參數校驗通過: {url}")
        return self