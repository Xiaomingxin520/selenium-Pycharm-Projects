from playwright.sync_api import Page, expect
import time  # 仅保留导入以兼容原逻辑，实际已无 sleep 调用

# 常量定义（须在class外面，原样保留）
SHENZHEN_CITY_ID = "133"
HONGKONG_CITY_ID = "2"
SHENZHEN_SHEKOU_PORT_ID = "900045"
HONGKONG_AIRPORT_PORT_ID = "900054"

# 船票日期选择器相关 (Ant Design - ferry)
FERRY_DATE_PICKER_TRIGGER = "div.ant-picker"
FERRY_DATE_DROPDOWN = "div.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)"
FERRY_DATE_CELL = "//td[contains(@class,'ant-picker-cell') and @title='{date}']"
FERRY_DATE_SELECTED = "ant-picker-cell-selected"

# 立即查询
SEARCH_BTN_XPATH = "//*[@data-testid='ferry-btn-search']"


class ferryHomePage:
    def __init__(self, page: Page):
        self.page = page
        # 模拟原 wait，Playwright 默认已带智能等待，无需显式 WebDriverWait
        self.wait = 10

    def select_depart_city_station(self, depart_city="深圳", depart_port="深圳蛇口碼頭"):
        """选择船票出发城市 + 码头"""

        # ===== 步骤1：点出发 trigger（唯一元素 + 原生 click）=====
        trigger = self.page.locator("//div[@data-testid='ferry-go-depart-city-trigger']").first
        expect(trigger).to_be_visible()
        trigger.click()
        print(" 点击出发地 trigger")

        # 等弹窗出现
        modal_xpath = "//div[@data-testid='ferry-go-depart-city-modal']"
        modal = self.page.locator(modal_xpath)
        expect(modal).to_be_visible()
        # 移除 time.sleep(0.4)，Playwright 自动等待渲染

        # ===== 步骤2：左侧城市（精确文本，避免误伤右侧"深圳蛇口碼頭"）=====
        city_xpath = (
            f"({modal_xpath}//li[@data-city-id='{SHENZHEN_CITY_ID}'])[1] | "
            f"({modal_xpath}//*[normalize-space(text())='{depart_city}' and "
            f"contains(@class,'cursor-pointer')])[1]"
        )
        city_el = self.page.locator(city_xpath).first
        expect(city_el).to_be_clickable()
        city_el.click()
        print(f" 选出发城市: {depart_city}")
        # 移除 time.sleep(0.8)，接口联动由后续断言等待

        # ===== ★ 调试打印：现在才看得到 =====
        print(" 弹窗内码头相关节点：")
        for el in self.page.locator(f"{modal_xpath}//*[@data-port-id or text()]").all():
            t = (el.inner_text() or "").strip()
            pid = el.get_attribute("data-port-id") or ""
            if pid or "碼頭" in t or depart_port in t:
                print(
                    f"   <{el.evaluate('el => el.tagName')}> port={pid} city={el.get_attribute('data-city-id')} text='{t}'")

        # ===== 步骤3：先等码头文本出现，再点 =====
        port_locator = self.page.locator(f"{modal_xpath}//*[contains(text(),'{depart_port}')]").first
        expect(port_locator).to_be_visible()
        # 移除 time.sleep(0.2)

        station_xpath = (
            f"({modal_xpath}//*[@data-port-id='{SHENZHEN_SHEKOU_PORT_ID}'])[1] | "
            f"({modal_xpath}//*[contains(text(),'{depart_port}') and "
            f"contains(@class,'cursor-pointer')])[1] | "
            f"({modal_xpath}//*[contains(text(),'{depart_port}')]/ancestor-or-self::*[contains(@class,'cursor-pointer')][1])[1]"
        )
        station_el = self.page.locator(station_xpath).first
        expect(station_el).to_be_clickable()
        station_el.click()
        print(f" 选出发码头: {depart_port}")
        # 移除 time.sleep(0.5)

    def select_arrive_city_station(self, arrive_city="香港", arrive_port="香港國際機場海天碼頭",
                                   depart_city_keep="深圳", depart_station_keep="深圳蛇口碼頭"):
        #  用 testid 而不是写死文本
        depart_display_xpath = "//div[@data-testid='ferry-go-depart-city-trigger']//div[contains(@class,'cursor-pointer')]"
        depart_display = self.page.locator(depart_display_xpath).first
        expect(depart_display).to_contain_text(f"{depart_city_keep}/")
        # 移除 time.sleep(0.5)

        # 点击到达触发框
        arrive_trigger_xpath = "//div[@data-testid='ferry-go-arrive-city-trigger']//div[contains(@class,'cursor-pointer')]"
        arrive_trigger = self.page.locator(arrive_trigger_xpath).first
        expect(arrive_trigger).to_be_clickable(timeout=10000)

        arrive_trigger.scroll_into_view_if_needed()
        arrive_trigger.click()
        print(" 点击到达触发框(船票)")

        # 等弹窗出现
        arrive_modal_xpath = "//div[@data-testid='ferry-go-arrive-city-modal']"
        arrive_modal = self.page.locator(arrive_modal_xpath)
        expect(arrive_modal).to_be_visible()
        print(" 找到到达弹窗(船票)")

        # 点城市
        city_xpath = (
            f"{arrive_modal_xpath}"
            f"//li[@data-city-id='{HONGKONG_CITY_ID}' and contains(@class,'cursor-pointer')] | "
            f"{arrive_modal_xpath}"
            f"//li[.//span[text()='{arrive_city}' and contains(@class,'cursor-pointer')]]"
        )
        city_el = self.page.locator(city_xpath).first
        expect(city_el).to_be_clickable()
        city_el.click()
        print(f" 选到达城市: {arrive_city}")

        # 点码头
        station_xpath = (
            f"{arrive_modal_xpath}"
            f"//span[contains(@class,'cursor-pointer') and @data-port-id and contains(text(),'{arrive_port}')]"
        )
        station_el = self.page.locator(station_xpath).first
        expect(station_el).to_be_visible()
        station_el.scroll_into_view_if_needed()
        station_el.click()
        print(f" 选完到达: {arrive_city}/{arrive_port}")

        # 联动刷新判定
        arrive_display_xpath = "//div[@data-testid='ferry-go-arrive-city-trigger']//div[contains(@class,'cursor-pointer')]"
        arrive_display = self.page.locator(arrive_display_xpath).first

        # 使用 Playwright 断言等待文本稳定
        expect(arrive_display).to_contain_text(arrive_port)

        final_depart_text = depart_display.inner_text().strip()
        final_depart_city_id = depart_display.get_attribute("data-city-id") or ""
        final_depart_port_id = depart_display.get_attribute("data-port-id") or ""

        final_arrive_text = arrive_display.inner_text().strip()
        final_arrive_city_id = arrive_display.get_attribute("data-city-id") or ""

        print(f" 联动后: 出发=[{final_depart_text}](city={final_depart_city_id}), "
              f"到达=[{final_arrive_text}](city={final_arrive_city_id})")

        # 校验（改为异常，不放 assert）
        if not (arrive_city in final_arrive_text and arrive_port in final_arrive_text):
            raise Exception(f"到达文本异常: {final_arrive_text}")

        # 【核心变更】彻底移除 JS 回写逻辑，依靠真实 UI 联动，暴露真实业务状态
        if final_depart_city_id != SHENZHEN_CITY_ID or depart_station_keep not in final_depart_text or final_depart_port_id != SHENZHEN_SHEKOU_PORT_ID:
            print(f" 出发站点被联动刷新(当前:{final_depart_text})，真实联动异常暴露，不执行JS回写")
            # 若此处频繁触发，建议在 Business 层调整操作顺序（如先选日期再选到达）

        # 最终校验
        final_depart = self.page.locator(depart_display_xpath).first.inner_text().strip()
        final_arrive = self.page.locator(arrive_display_xpath).first.inner_text().strip()
        if not f"{depart_city_keep}/{depart_station_keep}" in final_depart:
            raise Exception(f"出发最终失败: {final_depart}")
        if not f"{arrive_city}/{arrive_port}" in final_arrive:
            raise Exception(f"到达最终失败: {final_arrive}")

        print(f" select_arrive_city_station 完成(船票): 出发[{final_depart}] -> 到达[{final_arrive}]")