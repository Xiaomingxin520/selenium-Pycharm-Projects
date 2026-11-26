# -*- coding: utf-8 -*-
"""
business/busticket_business.py —— 大巴票业务编排层（Playwright 版）
"""
from page.bus_home_page import BusHomePage
from page.bus_search_result_page import BusSearchResultPage
from page.bus_orderconfirmation_page import BusOrderConfirmationPage

HOME_URL = "https://www.testhopetrip.dabapiao.com/"
DEFAULT_TIMEOUT = 10_000


class BusticketBusiness:
    def __init__(self, page, timeout: int = DEFAULT_TIMEOUT):
        """
        :param page: Playwright Page（由 conftest 的 pw_module_page / pw_page 注入）
                     不是 Selenium WebDriver
        :param timeout: 毫秒。page 層統一透傳，改這一處即全局生效
        """
        self.page = page
        self.timeout = timeout
        self.target_date = None
        self.result = None            # BusSearchResultPage
        self.order = None             # BusOrderConfirmationPage

        self.bus_home = BusHomePage(page, timeout=timeout)

    # ---------------- 內部工具 ----------------
    @property
    def url(self) -> str:
        """替代原 driver.current_url"""
        return self.page.url

    def _goto_home(self):
        """回首頁並等外殼就緒。替代 driver.get + time.sleep(1)。
        用頁腳牌照號 354122 做錨（全站唯一、不隨改版文案漂移）。"""
        self.page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30_000)
        self.page.locator("text=354122").first.wait_for(state="visible", timeout=self.timeout)
        return self

    # ========== 搜索 ==========
    def enter_bus_and_search(self, depart_city="深圳", depart_station="深圳灣（香港段上）",
                             arrive_city="香港", arrive_station="尖沙咀海港城"):
        self._goto_home()

        # 進大巴頻道：testid/href 主，文案兜底（原版 a[href='/bus'] 保留為第一優先）
        bus_entry = self.page.locator(
            "a[href='/bus'], [data-testid='nav-bus'], a:has-text('大巴票')"
        ).first
        bus_entry.click(timeout=self.timeout)

        # 等大巴頻道表單渲染完（原版 visibility_of(出發城市/站點)）
        self.page.locator("span:text-is('出發城市/站點')").first.wait_for(
            state="visible", timeout=self.timeout)

        # ↓↓↓ 以下四步調用契約與舊版逐字一致 ↓↓↓
        self.bus_home.select_depart_city_station(depart_city, depart_station)
        self.bus_home.select_arrive_city_station(arrive_city, arrive_station)
        self.target_date = self.bus_home.select_date_two_days_later()
        self.bus_home.click_search_now()      # 內部已等 URL 含 date=

        # 結果頁二次校驗（原版邏輯原樣保留）
        self.page.wait_for_url(f"**/*date={self.target_date}*", timeout=20_000)
        assert f"date={self.target_date}" in self.page.url, \
            f" 日期參數未回顯到 URL: {self.page.url}"
        print(f" 搜索结果页跳转成功: {self.page.url}")

        self.result = BusSearchResultPage(self.page, timeout=self.timeout)
        return self

    # ========== 地图弹窗（标准前置）==========
    def handle_map_modals(self):
        """处理上下车地图弹窗，结果页点购票前必做"""
        self.result.click_last_trip_map()
        assert self.result.assert_map_modal(), "上車地圖弹窗校验失败"
        self.result.close_map_modal()
        self.result.wait_map_closed()          # ← 原 time.sleep(0.5)

        self.result.click_last_trip_down_map()
        assert self.result.assert_down_map_modal(), "下車地圖弹窗校验失败"
        self.result.close_map_modal()
        self.result.wait_map_closed()          # ← 原 time.sleep(0.5)
        print(" 上下車地圖弹窗均已校验并关闭")
        return self

    # ========== 购票 → 订单页 ==========
    def goto_order_page(self):
        """点击购票 → 等待订单页加载"""
        # 原版註釋「已改防stale版」：Playwright locator 惰性求值 → 天生不 stale，直接調即可
        self.result.click_last_trip_ticket()
        self.order = BusOrderConfirmationPage(self.page, timeout=self.timeout)  # ← 單參！
        self.order.wait_for_page_load()
        return self

    # ========== 统一添加乘客 + 提交 ==========
    def add_passengers_and_submit(self, adult=0, child=0, elder=0):
        """
        订单页：按数量添加乘客 → 提交订单，支持任意组合，一条方法覆盖所有场景
        """
        if not self.order:
            raise RuntimeError("请先调用 goto_order_page()")

        # 添加（page 層每個 click 後自行等計數器穩定，無需 sleep）
        for _ in range(adult):
            self.order.click_adult_plus()
        for _ in range(child):
            self.order.click_child_plus()
        for _ in range(elder):
            self.order.click_elder_plus()

        # 断言（讀真實 DOM，不 sleep）
        a = self.order.get_adult_count()
        c = self.order.get_child_count()
        e = self.order.get_elder_count()
        assert a >= adult, f"成人数量不符: 期望>={adult}, 实际={a}"
        assert c >= child, f"兒童数量不符: 期望>={child}, 实际={c}"
        assert e >= elder, f"長者数量不符: 期望>={elder}, 实际={e}"
        print(f" 乘客添加完成：成人={a}, 兒童={c}, 長者={e}")

        self.order.click_submit_order()
        return self

    # ========== 兼容旧用例的快捷方法（簽名全保留）==========
    def goto_order_and_add_adult(self):
        self.goto_order_page()
        self.add_passengers_and_submit(adult=1)
        return self

    def goto_order_and_add_child(self):
        self.goto_order_page()
        self.add_passengers_and_submit(child=1)
        return self

    def goto_order_and_add_elder(self):
        self.goto_order_page()
        self.add_passengers_and_submit(elder=1)
        return self

    def goto_order_and_add_multiple(self, adult=1, child=1, elder=1):
        self.goto_order_page()
        self.add_passengers_and_submit(adult=adult, child=child, elder=elder)
        return self

    # ========== 登录态下单 ==========
    def login_and_goto_order(self, email="AutomatedTesting@gmail.com", pwd="123456"):
        """
        登录态场景统一入口：登录 → 搜索 → 弹窗 → 订单页
        复用已有 LoginBusiness，不重复造轮子
        """
        from business.login_business import LoginBusiness

        login_biz = LoginBusiness(self.page, timeout=self.timeout)  # ← 傳 page；timeout 毫秒
        login_biz.login(email, pwd)

        # 登录后回到首页（确保搜索上下文正确）——替代 driver.get + sleep(1)
        self._goto_home()

        # 复用已有搜索 + 弹窗 + 跳转流程
        self.enter_bus_and_search()
        self.handle_map_modals()
        self.goto_order_page()
        return self

    def login_and_add_passengers_and_submit(self, email="AutomatedTesting@gmail.com", pwd="123456",
                                            adult=0, child=0, elder=0):
        """
        登录态场景：一步到位（登录 → 搜索 → 选座 → 添加乘客 → 提交），适合测试用例直接调用
        """
        self.login_and_goto_order(email, pwd)
        self.add_passengers_and_submit(adult=adult, child=child, elder=elder)
        return self

    # ========== 添加乘客 → 填字段 → 提交（不進確認頁）==========
    def add_passengers_fill_fields_and_submit(
            self, adult=0, child=0, elder=0,
            name_cn="自動化測試", phone="96526666",
            email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    ):
        """完整下单流程：添加乘客 → 填写下单字段 → 提交订单"""
        if not self.order:
            raise RuntimeError("请先调用 goto_order_page()")

        # 1. 添加乘客
        for _ in range(adult):
            self.order.click_adult_plus()
        for _ in range(child):
            self.order.click_child_plus()
        for _ in range(elder):
            self.order.click_elder_plus()

        # 斷言（⚠️ 原版三個條件擠在一條 assert，炸了看不出是哪類錯；
        #        此處拆成三行，與本文件另外兩個同類方法對齊。判定條件未改）
        a = self.order.get_adult_count()
        c = self.order.get_child_count()
        e = self.order.get_elder_count()
        assert a >= adult, f"成人数量不符: 期望>={adult}, 实际={a}"
        assert c >= child, f"兒童数量不符: 期望>={child}, 实际={c}"
        assert e >= elder, f"長者数量不符: 期望>={elder}, 实际={e}"
        print(f" 乘客添加完成：成人={a}, 兒童={c}, 長者={e}")

        # 2. 填写下单字段（中文名 → 中轉英 → 手機 → 郵箱 → 備註，順序不可調）
        self.order.fill_order_fields(name_cn=name_cn, phone=phone, email=email, remark=remark)

        # 3. 提交订单
        self.order.click_submit_order()
        print(" 订单已提交")
        return self

    # ========== 添加乘客 → 填字段 → 提交 → 確認頁 ==========
    def add_passengers_fill_fields_and_submit_with_confirm(
            self, adult=0, child=0, elder=0,
            name_cn="自動化測試", phone="96526666",
            email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    ):
        """
        完整下单流程：添加乘客 → 填写字段 → 提交订单 → 验证跳转到 confirm-order 页，返回 groupId
        """
        if not self.order:
            raise RuntimeError("请先调用 goto_order_page()")

        # 1. 添加乘客
        for _ in range(adult):
            self.order.click_adult_plus()
        for _ in range(child):
            self.order.click_child_plus()
        for _ in range(elder):
            self.order.click_elder_plus()

        # 断言数量
        a = self.order.get_adult_count()
        c = self.order.get_child_count()
        e = self.order.get_elder_count()
        assert a >= adult, f"成人数量不符: 期望>={adult}, 实际={a}"
        assert c >= child, f"兒童数量不符: 期望>={child}, 实际={c}"
        assert e >= elder, f"長者数量不符: 期望>={elder}, 实际={e}"
        print(f" 乘客添加完成：成人={a}, 兒童={c}, 長者={e}")

        # 2. 填写下单字段
        self.order.fill_order_fields(name_cn=name_cn, phone=phone, email=email, remark=remark)

        # 3. 提交订单 + 等待跳转确认页
        group_id = self.order.click_submit_order_and_wait_confirm()

        # 4. 断言已进入确认页（內部另校 groupId 非空，防「路徑對了參數丟了」的假綠）
        self.order.assert_confirm_order_page()

        print(f" 下单成功，groupId={group_id}")
        return group_id

    # ========== 支付闭环 ==========
    def pay_on_confirm_page(self, payment_method="香港微信支付", wait_qrcode=True,
                            strict_qrcode=False):
        """
        在 confirm-order 页面完成支付操作
        :param payment_method: 支付方式（香港微信支付/香港支付寶/大陸微信支付/大陸支付寶；信用卡會 raise）
        :param wait_qrcode: 是否等待二维码生成
        :param strict_qrcode: False=沿用舊版「點擊即視為成功」；True=真校验二維碼區域可見。
                              全量綠後建議把默認改成 True，收回這道被架空的斷言。
        :return: dict 包含 group_id, qrcode_displayed
        """
        from page.bus_orderpay_page import BusOrderPayPage

        # 确保当前在支付页面
        assert "confirm-order" in self.page.url, \
            f"当前不在支付页面，URL: {self.page.url}"

        # 调用 Page 层完成支付（清標籤 → 取 groupId/總價 → 選支付方式 → 生成支付碼）
        pay_page = BusOrderPayPage(self.page, timeout=self.timeout)   # ← 實例，非 static
        result = pay_page.pay(payment_method, strict_qrcode=strict_qrcode)
        # 懶人等價寫法（一行不改也能跑）：
        # result = BusOrderPayPage.pay_static(self.page, payment_method)

        # 兜底提取 groupId
        group_id = result.get("group_id") or self._extract_group_id(self.page.url)
        result["group_id"] = group_id

        if wait_qrcode:
            assert result["qrcode_displayed"], \
                f"{payment_method} - 二维码未生成，支付码生成失败"

        print(f"  支付完成: 方式={payment_method}, groupId={group_id}, "
              f"二维码={'已生成' if result['qrcode_displayed'] else '未生成'}"
              f"{'' if strict_qrcode else '（未 strict 校驗，點擊即視為成功）'}")
        return result

    # ========== 全流程闭环（游客态）==========
    def full_flow_with_payment(
            self, depart_city="深圳", depart_station="深圳灣（香港段上）",
            arrive_city="香港", arrive_station="尖沙咀海港城",
            adult=1, child=0, elder=0,
            name_cn="自動化測試", phone="96526666",
            email="AutomatedTesting@gmail.com", remark="自動化測試備註",
            payment_method="香港微信支付",
            strict_qrcode=False
    ):
        """
        大巴票全流程闭环（一步到位）：
        搜索 → 地图弹窗 → 订单页 → 加乘客 → 填字段 → 提交 → 支付
        适合测试用例直接调用，一行代码跑完整个链路
        """
        # Step 1: 搜索
        self.enter_bus_and_search(
            depart_city=depart_city, depart_station=depart_station,
            arrive_city=arrive_city, arrive_station=arrive_station
        )
        # Step 2: 地图弹窗
        self.handle_map_modals()
        # Step 3: 进入订单页
        self.goto_order_page()
        # Step 4: 添加乘客 + 填写字段 + 提交订单 → 返回 groupId
        group_id = self.add_passengers_fill_fields_and_submit_with_confirm(
            adult=adult, child=child, elder=elder,
            name_cn=name_cn, phone=phone, email=email, remark=remark
        )
        # Step 5: 支付（选支付方式 + 生成支付码）
        pay_result = self.pay_on_confirm_page(payment_method=payment_method,
                                              strict_qrcode=strict_qrcode)

        print(f"\n 全流程闭环完成: groupId={group_id}, "
              f"支付方式={payment_method}, "
              f"二维码={'✓' if pay_result['qrcode_displayed'] else '✗'}")

        return {
            "group_id": group_id,
            "payment_method": payment_method,
            "qrcode_displayed": pay_result["qrcode_displayed"]
        }

    # ========== 全流程闭环（登录态）==========
    def full_flow_login_with_payment(
            self, email="AutomatedTesting@gmail.com", pwd="123456",
            depart_city="深圳", depart_station="深圳灣（香港段上）",
            arrive_city="香港", arrive_station="尖沙咀海港城",
            adult=1, child=0, elder=0,
            name_cn="自動化測試", phone="96526666",
            order_email="AutomatedTesting@gmail.com", remark="自動化測試備註",
            payment_method="香港微信支付",
            strict_qrcode=False
    ):
        """
        登录态全流程闭环：
        登录 → 搜索 → 弹窗 → 订单页 → 加乘客 → 填字段 → 提交 → 支付
        """
        # Step 1: 登录 + 搜索 + 弹窗 + 订单页
        self.login_and_goto_order(email, pwd)
        # Step 2: 添加乘客 + 填写字段 + 提交 → 跳转支付页
        group_id = self.add_passengers_fill_fields_and_submit_with_confirm(
            adult=adult, child=child, elder=elder,
            name_cn=name_cn, phone=phone, email=order_email, remark=remark
        )
        # Step 3: 支付
        pay_result = self.pay_on_confirm_page(payment_method=payment_method,
                                              strict_qrcode=strict_qrcode)

        print(f"\n 登录态全流程闭环完成: groupId={group_id}, "
              f"支付方式={payment_method}, "
              f"二维码={'✓' if pay_result['qrcode_displayed'] else '✗'}")

        return {
            "group_id": group_id,
            "payment_method": payment_method,
            "qrcode_displayed": pay_result["qrcode_displayed"]
        }

    @staticmethod
    def _extract_group_id(url):
        """兜底提取 groupId（純字符串邏輯，未改動）"""
        if "groupId=" in url:
            return url.split("groupId=")[-1].split("&")[0]
        return ""