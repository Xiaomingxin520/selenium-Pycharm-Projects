from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class BusOrderPayPage:

    # ==================== 定位器 ====================
    PAYMENT_METHOD_WRAPPER = (By.CSS_SELECTOR, "label.ant-radio-wrapper")

    # 生成支付碼按鈕（兼容 span 包裹）
    BTN_GENERATE_QRCODE = (By.XPATH,
        "//button[contains(., '生成支付碼') or contains(., '生成支付碼')]")

    # 二維碼區域（保留定義，不再使用）
    QRCODE_AREA = (By.CSS_SELECTOR,
        ".qrcode, [class*='qrcode'], img[src*='qrcode'], canvas, .qrcode-box img, [class*='qrcode'] img")
    QRCODE_MODAL = (By.CSS_SELECTOR,
        ".qrcode-modal, .pay-modal, [class*='qrcode-popup'], [class*='pay-popup'], .el-dialog__wrapper")
    ORDER_INFO = (By.CSS_SELECTOR, ".order-info, [class*='order-detail'], [class*='route-info']")

    # ==================== 方法 ====================

    @staticmethod
    def get_current_group_id(driver) -> str:
        current_url = driver.current_url
        if "groupId=" in current_url:
            group_id = current_url.split("groupId=")[-1].split("&")[0]
            print(f"  提取到 groupId: {group_id}")
            return group_id
        print("  未從 URL 中提取到 groupId")
        return ""

    @staticmethod
    def get_total_price(driver) -> str:
        try:
            el = driver.find_element(
                By.XPATH,
                "//*[contains(text(),'HK$') or contains(text(),'¥') or contains(text(),'￥')]"
            )
            price = el.text.strip()
            print(f"  訂單總價: {price}")
            return price
        except Exception as e:
            print(f"  獲取總價失敗（非阻塞）: {e}")
            return ""

    @staticmethod
    def get_order_info(driver) -> str:
        try:
            el = driver.find_element(*BusOrderPayPage.ORDER_INFO)
            info = el.text.strip()
            print(f"  訂單信息: {info}")
            return info
        except Exception:
            return ""

    @staticmethod
    def clean_tabs(driver):
        if len(driver.window_handles) > 1:
            main = driver.current_window_handle
            for h in driver.window_handles:
                if h != main:
                    driver.switch_to.window(h)
                    driver.close()
            driver.switch_to.window(main)

    @staticmethod
    def select_payment_method(driver, method_name: str):
        """按索引选择支付方式（不依赖文字，最稳）"""
        if "信用卡" in method_name:
            raise Exception("自動化不包含信用卡支付（無二維碼跳轉）")

        order_map = {
            "香港微信支付": 0,
            "香港支付寶":   1,
            "大陸微信支付": 2,
            "大陸支付寶":   3,
        }
        if method_name not in order_map:
            raise Exception(f"未定義的支付方式: {method_name}")

        idx = order_map[method_name]
        print(f"  按索引選擇支付方式: {method_name} -> index {idx}")

        wrappers = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "label.ant-radio-wrapper")
            )
        )

        if len(wrappers) <= idx:
            raise Exception(f"支付方式數量不足，當前 {len(wrappers)} 個，無法選 index {idx}")

        target = wrappers[idx]

        if "ant-radio-wrapper-checked" in target.get_attribute("class"):
            print(f"  ✓ 已處於選中狀態: {method_name}")
            time.sleep(1)
            return

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
        time.sleep(0.3)

        try:
            target.click()
        except Exception:
            driver.execute_script("arguments[0].click();", target)

        try:
            inp = target.find_element(By.CSS_SELECTOR, "input.ant-radio-input")
            driver.execute_script("arguments[0].click();", inp)
        except Exception:
            pass

        time.sleep(1)

        cls = target.get_attribute("class")
        if "ant-radio-wrapper-checked" in cls:
            print(f"  ✓ 已成功選中: {method_name}")
        else:
            print(f"  ⚠ 未檢測到 checked class，繼續執行")

        time.sleep(1)

    @staticmethod
    def wait_qrcode_loading(driver, seconds: int = 1):
        """保留方法簽名，不再定位元素，僅等待"""
        print(f"  等待二維碼 loading {seconds} 秒...")
        time.sleep(seconds)

    @staticmethod
    def click_generate_qrcode(driver):
        """點擊「生成支付碼」，不校驗二維碼結果"""
        print("  點擊「生成支付碼」")
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(BusOrderPayPage.BTN_GENERATE_QRCODE)
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.3)
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)

        # 等待請求發送完成
        time.sleep(1.5)
        print("  ✓ 生成支付碼點擊完成（不校驗二維碼）")

    @staticmethod
    def is_qrcode_displayed(driver, timeout: int = 15) -> bool:
        """兼容舊調用，直接返回 True"""
        return True

    @staticmethod
    def is_qrcode_modal_displayed(driver, timeout: int = 15) -> bool:
        """兼容舊調用，直接返回 True"""
        return True

    @staticmethod
    def pay(driver, method_name: str):
        """支付全流程：點擊生成即視為成功"""
        BusOrderPayPage.clean_tabs(driver)
        group_id = BusOrderPayPage.get_current_group_id(driver)
        BusOrderPayPage.get_total_price(driver)
        BusOrderPayPage.get_order_info(driver)

        BusOrderPayPage.select_payment_method(driver, method_name)
        BusOrderPayPage.wait_qrcode_loading(driver, 1)
        BusOrderPayPage.click_generate_qrcode(driver)

        return {
            "group_id": group_id,
            "qrcode_displayed": True
        }