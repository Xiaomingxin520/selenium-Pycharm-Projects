# business/ferryticket_business.py  船票业务调用层（Playwright 版）
from playwright.sync_api import expect
from page.ferry_home_page import ferryHomePage   # ← 小写 f、小写 h，与 Page 层类名一致

# 常量（与 page/ferry_home_page.py 保持一致）
SHENZHEN_CITY_ID = "133"
HONGKONG_CITY_ID = "2"
SHENZHEN_SHEKOU_PORT_ID = "900045"
HONGKONG_AIRPORT_PORT_ID = "900054"

class FerryTicketBusiness:
    def __init__(self, page):
        """
        接收 Playwright 的 page 对象，不再依赖 Selenium driver
        """
        self.page = page
        self.ferry_page = ferryHomePage(page)

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

    def search_ferry_ticket(self,
                            depart_city="深圳",
                            depart_port="深圳蛇口碼頭",
                            arrive_city="香港",
                            arrive_port="香港國際機場海天碼頭"):
        """完整冒烟：选路线 + 点立即查询"""
        self.select_ferry_route(depart_city, depart_port, arrive_city, arrive_port)

        search_btn = self.page.locator("//*[@data-testid='ferry-btn-search']").first
        search_btn.scroll_into_view_if_needed()
        search_btn.click()
        print(" 已执行船票路线选择并点击【立即查询】")

    def verify_selection_result(self, depart_text, arrive_text):
        """
        校验触发框的真实展示文本（非 page_source 瞎匹配）
        签名保持两参数，与 TestCase 调用一致
        """
        depart_display = self.page.locator(
            "//div[@data-testid='ferry-go-depart-city-trigger']//div[contains(@class,'cursor-pointer')]"
        ).first.inner_text().strip()
        arrive_display = self.page.locator(
            "//div[@data-testid='ferry-go-arrive-city-trigger']//div[contains(@class,'cursor-pointer')]"
        ).first.inner_text().strip()

        assert depart_text in depart_display, \
            f"出发地校验失败，期望包含[{depart_text}]，实际[{depart_display}]"
        assert arrive_text in arrive_display, \
            f"到达地校验失败，期望包含[{arrive_text}]，实际[{arrive_display}]"
        print(f" 业务校验通过: 出发[{depart_display}] -> 到达[{arrive_display}]")