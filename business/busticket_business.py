from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from page.bus_home_page import BusHomePage
from page.bus_search_result_page import BusSearchResultPage
from page.bus_orderconfirmation_page import BusOrderConfirmationPage
import time

class BusticketBusiness:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.target_date = None
        self.bus_home = BusHomePage(self.driver)
        self.result = None
        self.order = None

    # ========== 搜索 ==========
    def enter_bus_and_search(self, depart_city="深圳", depart_station="深圳灣（香港段上）",
                             arrive_city="香港", arrive_station="尖沙咀海港城"):
        self.driver.get("https://www.testhopetrip.dabapiao.com/")
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/bus']"))).click()
        wait.until(EC.visibility_of_element_located((By.XPATH, "//span[text()='出發城市/站點']")))

        self.bus_home.select_depart_city_station(depart_city, depart_station)
        self.bus_home.select_arrive_city_station(arrive_city, arrive_station)
        self.target_date = self.bus_home.select_date_two_days_later()
        self.bus_home.click_search_now()

        self.wait.until(EC.url_contains("date="))
        assert f"date={self.target_date}" in self.driver.current_url
        print(f" 搜索结果页跳转成功: {self.driver.current_url}")

        self.result = BusSearchResultPage(self.driver)

    # ========== 地图弹窗（标准前置）==========
    def handle_map_modals(self):
        """处理上下车地图弹窗，结果页点购票前必做"""
        self.result.click_last_trip_map()
        assert self.result.assert_map_modal(), "上車地圖弹窗校验失败"
        self.result.close_map_modal()
        time.sleep(0.5)

        self.result.click_last_trip_down_map()
        assert self.result.assert_down_map_modal(), "下車地圖弹窗校验失败"
        self.result.close_map_modal()
        time.sleep(0.5)

    # ========== 购票 → 订单页 ==========
    def goto_order_page(self):
        """点击购票 → 等待订单页加载"""
        self.result.click_last_trip_ticket()  # ← 已改防stale版
        self.order = BusOrderConfirmationPage(self.driver, self.wait)
        self.order.wait_for_page_load()
        return self

    # ========== 统一添加乘客 + 提交 ==========
    def add_passengers_and_submit(self, adult=0, child=0, elder=0):
        """
        订单页：按数量添加乘客 → 提交订单，支持任意组合，一条方法覆盖所有场景
        """
        if not self.order:
            raise Exception(" 请先调用 goto_order_page()")

        # 添加
        for _ in range(adult):
            self.order.click_adult_plus(); time.sleep(0.3)
        for _ in range(child):
            self.order.click_child_plus(); time.sleep(0.3)
        for _ in range(elder):
            self.order.click_elder_plus(); time.sleep(0.3)

        # 断言
        time.sleep(1)
        a = self.order.get_adult_count()
        c = self.order.get_child_count()
        e = self.order.get_elder_count()
        assert a >= adult, f"成人数量不符: 期望>={adult}, 实际={a}"
        assert c >= child, f"兒童数量不符: 期望>={child}, 实际={c}"
        assert e >= elder, f"長者数量不符: 期望>={elder}, 实际={e}"
        print(f" 乘客添加完成：成人={a}, 兒童={c}, 長者={e}")

        # 提交
        self.order.click_submit_order()
        return self

    # ========== 兼容旧用例的快捷方法 ==========
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

    # ========== 登录态下单==========
    def login_and_goto_order(self, email="AutomatedTesting@gmail.com", pwd="123456"):
        """
        登录态场景统一入口：登录 → 搜索 → 弹窗 → 订单页
        复用已有 LoginBusiness，不重复造轮子
        """
        from business.login_business import LoginBusiness

        login_biz = LoginBusiness(self.driver)
        login_biz.login(email, pwd)

        # 登录后回到首页（确保搜索上下文正确）
        self.driver.get("https://www.testhopetrip.dabapiao.com/")
        time.sleep(1)

        # 复用已有搜索 + 弹窗 + 跳转流程
        self.enter_bus_and_search()
        self.handle_map_modals()
        self.goto_order_page()
        return self

    def login_and_add_passengers_and_submit(self, email="AutomatedTesting@gmail.com", pwd="123456",
                                            adult=0, child=0, elder=0):
        """
        登录态场景：一步到位（登录 → 搜索 → 选座 → 添加乘客 → 提交），适合测试用例直接调用，减少重复编排
        """
        self.login_and_goto_order(email, pwd)
        self.add_passengers_and_submit(adult=adult, child=child, elder=elder)
        return self

    def add_passengers_fill_fields_and_submit(
            self, adult=0, child=0, elder=0,
            name_cn="自動化測試", phone="96526666",
            email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    ):
        """完整下单流程：添加乘客 → 填写下单字段 → 提交订单"""
        if not self.order:
            raise Exception(" 请先调用 goto_order_page()")

        # 1. 添加乘客 + 提交（复用已有方法，但提交前拦截）
        # 先加人+断言
        for _ in range(adult):
            self.order.click_adult_plus();
            time.sleep(0.3)
        for _ in range(child):
            self.order.click_child_plus();
            time.sleep(0.3)
        for _ in range(elder):
            self.order.click_elder_plus();
            time.sleep(0.3)

        time.sleep(1)
        a = self.order.get_adult_count()
        c = self.order.get_child_count()
        e = self.order.get_elder_count()
        assert a >= adult and c >= child and e >= elder
        print(f" 乘客添加完成：成人={a}, 兒童={c}, 長者={e}")

        # 2. 填写下单字段
        self.order.fill_order_fields(name_cn=name_cn, phone=phone, email=email, remark=remark)

        # 3. 提交订单
        self.order.click_submit_order()
        print(" 订单已提交")
        return self

    def add_passengers_fill_fields_and_submit_with_confirm(
        self, adult=0, child=0, elder=0,
        name_cn="自動化測試", phone="96526666",
        email="AutomatedTesting@gmail.com", remark="自動化測試備註"
    ):
        """
        完整下单流程：添加乘客 → 填写字段 → 提交订单 → 验证跳转到 confirm-order 页，返回 groupId
        """
        if not self.order:
            raise Exception(" 请先调用 goto_order_page()")

        # 1. 添加乘客
        for _ in range(adult):
            self.order.click_adult_plus(); time.sleep(0.3)
        for _ in range(child):
            self.order.click_child_plus(); time.sleep(0.3)
        for _ in range(elder):
            self.order.click_elder_plus(); time.sleep(0.3)

        # 断言数量
        time.sleep(1)
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

        # 4. 断言已进入确认页
        self.order.assert_confirm_order_page()

        print(f" 下单成功，groupId={group_id}")
        return group_id

# ========== 支付闭环（追加）=========
    def pay_on_confirm_page(self, payment_method="香港微信支付", wait_qrcode=True):
        """
        在 confirm-order 页面完成支付操作
        :param payment_method: 支付方式名称（香港微信支付/香港支付宝/大陆微信/大陆支付宝/信用卡）
        :param wait_qrcode: 是否等待二维码生成
        :return: dict 包含 group_id, qrcode_displayed
        """
        from page.bus_orderpay_page import BusOrderPayPage

        # 确保当前在支付页面
        assert "confirm-order" in self.driver.current_url, \
            f"当前不在支付页面，URL: {self.driver.current_url}"

        # 调用 Page 层完成支付（选支付方式 + 点击生成支付码）
        result = BusOrderPayPage.pay(self.driver, payment_method)

        # 兜底提取 groupId
        group_id = result.get("group_id") or self._extract_group_id(self.driver.current_url)
        result["group_id"] = group_id

        if wait_qrcode:
            assert result["qrcode_displayed"], \
                f"{payment_method} - 二维码未生成，支付码生成失败"

        print(f"  支付完成: 方式={payment_method}, groupId={group_id}, "
              f"二维码={'已生成' if result['qrcode_displayed'] else '未生成'}")
        return result

    def full_flow_with_payment(
            self, depart_city="深圳", depart_station="深圳灣（香港段上）",
            arrive_city="香港", arrive_station="尖沙咀海港城",
            adult=1, child=0, elder=0,
            name_cn="自動化測試", phone="96526666",
            email="AutomatedTesting@gmail.com", remark="自動化測試備註",
            payment_method="香港微信支付"
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
        # Step 5: 支付（选香港微信 + 生成支付码）
        pay_result = self.pay_on_confirm_page(payment_method=payment_method)

        print(f"\n 全流程闭环完成: groupId={group_id}, "
              f"支付方式={payment_method}, 二维码={'✓' if pay_result['qrcode_displayed'] else '✗'}")

        return {
            "group_id": group_id,
            "payment_method": payment_method,
            "qrcode_displayed": pay_result["qrcode_displayed"]
        }

    def full_flow_login_with_payment(
            self, email="AutomatedTesting@gmail.com", pwd="123456",
            depart_city="深圳", depart_station="深圳灣（香港段上）",
            arrive_city="香港", arrive_station="尖沙咀海港城",
            adult=1, child=0, elder=0,
            name_cn="自動化測試", phone="96526666",
            order_email="AutomatedTesting@gmail.com", remark="自動化測試備註",
            payment_method="香港微信支付"
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
        pay_result = self.pay_on_confirm_page(payment_method=payment_method)

        print(f"\n 登录态全流程闭环完成: groupId={group_id}, "
              f"支付方式={payment_method}, 二维码={'✓' if pay_result['qrcode_displayed'] else '✗'}")

        return {
            "group_id": group_id,
            "payment_method": payment_method,
            "qrcode_displayed": pay_result["qrcode_displayed"]
        }

    @staticmethod
    def _extract_group_id(url):
        """兜底提取 groupId"""
        if "groupId=" in url:
            return url.split("groupId=")[-1].split("&")[0]
        return ""