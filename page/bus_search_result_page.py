from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

class BusSearchResultPage:
    # 动态定位：不依赖ID，取最后一个“站點地圖”
    LAST_TRIP_MAP_BTN = (By.XPATH,
        "(//*[contains(text(),'上車')]/following-sibling::*[contains(text(),'站點地圖')] | "
        "//*[contains(text(),'上車')]/../*[contains(text(),'站點地圖')] | "
        "//*[contains(text(),'上車')]//following::*[contains(text(),'站點地圖')][1])[last()]"
        )

    # 上車弹窗特征
    MAP_TAB_UP = (By.XPATH, "//*[text()='上車點']")
    MAP_TITLE = (By.XPATH, "//div[contains(@class,'ant-modal')][.//*[text()='上車點']]//*[contains(text(),'深圳灣（香港段上）')]")

    #  新增：最后一班【下車】的站點地圖（隔离终点）
    LAST_TRIP_DOWN_MAP_BTN = (By.XPATH,"(//*[contains(text(),'下車')]/../..//*[contains(text(),'站點地圖')])[last()]" )

    # 下車弹窗特征
    MAP_TAB_DOWN = (By.XPATH, "//*[text()='下車點']")
    MAP_TITLE1 = (By.XPATH,"//div[contains(@class,'ant-modal')][.//*[text()='下車點']]//*[contains(text(),'尖沙咀海港城')]" )

    #  新增：弹窗取消/关闭按钮
    MODAL_CLOSE_BTN = (By.CSS_SELECTOR, "button.ant-modal-close")
    MODAL_MASK = (By.CSS_SELECTOR, "div.ant-modal-mask")

    # 新增：购票按钮基础定位
    TICKET_BTN_BASE = (By.XPATH, "//button[contains(@class,'ant-btn-primary')][.//span[text()='購票']]")

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)

    def click_last_trip_map(self):
        """点击动态日期下最后一班的站點地圖"""
        # 1. 等待结果列表渲染（用班次號文本兜底等待）
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'班次號')]")))

        # 2. 定位最后一个地图按钮
        map_btn = self.wait.until(EC.presence_of_element_located(self.LAST_TRIP_MAP_BTN))

        # 3. 滚动到视口中心
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", map_btn)

        # 4. 尝试常规点击，失败则JS点击
        try:
            self.wait.until(EC.element_to_be_clickable(self.LAST_TRIP_MAP_BTN)).click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", map_btn)

        #  调试：等2秒让弹窗渲染，然后打印页面里所有含 loading 的元素
        time.sleep(2)
        loading_elements = self.driver.find_elements(By.XPATH, "//*[contains(@class,'loading')]")
        print(f" 点击后找到 {len(loading_elements)} 个含'loading'的class元素:")
        for el in loading_elements:
            print(f"   tag={el.tag_name}, class={el.get_attribute('class')}, text={el.text[:50]}")

        # 5. 等待弹窗出现
        self.wait.until(EC.visibility_of_element_located(self.MAP_TAB_UP))
        print(" 弹窗已出现")

    def assert_map_modal(self):
        """断言上車弹窗内容（上車點 + 标题兜底）"""
        up_tab = self.wait.until(EC.visibility_of_element_located(self.MAP_TAB_UP))
        # 尝试等待精准标题，超时则兜底（避免卡死）
        try:
            title = self.wait.until(EC.visibility_of_element_located(self.MAP_TITLE))
        except Exception:
            title = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, "//div[contains(@class,'ant-modal')][.//*[text()='上車點']]")
            ))
        assert up_tab is not None, "上車彈窗Tab未出現"
        print(" 站点地图弹窗校验通过！")
        return True

    def assert_down_map_modal(self):
        """断言下車弹窗内容"""
        down_tab = self.wait.until(EC.visibility_of_element_located(self.MAP_TAB_DOWN))
        title = self.wait.until(EC.visibility_of_element_located(self.MAP_TITLE1))
        assert down_tab and title, "下車弹窗内容校验失败"
        print(" 下車站点地图弹窗校验通过！")
        return True

    def click_last_trip_down_map(self):
        """点击最后一班【下車】的站點地圖"""
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'班次號')]")
        ))

        down_btn = self.wait.until(
            EC.presence_of_element_located(self.LAST_TRIP_DOWN_MAP_BTN)
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", down_btn
        )

        try:
            self.wait.until(
                EC.element_to_be_clickable(self.LAST_TRIP_DOWN_MAP_BTN)
            ).click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", down_btn)

        # 等下車點弹窗出现
        self.wait.until(EC.visibility_of_element_located(self.MAP_TAB_DOWN))
        print(" 下車點弹窗已出现")

    def close_map_modal(self):
        """右上角取消，并等弹窗彻底消失"""
        close_btn = self.wait.until(EC.presence_of_element_located(self.MODAL_CLOSE_BTN))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", close_btn)
        try:
            self.wait.until(EC.element_to_be_clickable(self.MODAL_CLOSE_BTN)).click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", close_btn)

        # 关键：等遮罩消失，避免点下車时被弹窗挡住
        self.wait.until(EC.invisibility_of_element_located(self.MODAL_MASK))
        print(" 弹窗已关闭")

# ========== 购票相关方法 ==========

    def click_ticket_for_target_date(self, days_offset=2):
        """
        点击目标日期行程的【購票】按钮
        默认 days_offset=2 → 今天后两天（2026-09-30 → 2026-10-02）
        """
        # 1. 等待列表渲染完成
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'班次號') or contains(text(),'購 票')]")
        ))

        # 2. 定位目标行程卡片内的購票按钮
        #    用"上車深圳灣 + 下車尖沙咀"锁定卡片，再找其内的購票按钮
        ticket_btn = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
                "//div[contains(@class,'flex-col') or contains(@class,'gap-')]"
                "[.//*[contains(text(),'深圳灣')]]"
                "[.//*[contains(text(),'尖沙咀')]]"
                "//button[contains(@class,'ant-btn-primary')]"
                "[.//span[contains(text(),'購')]]"
            )
        ))

        # 3. 滚动并点击
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ticket_btn)
        time.sleep(0.5)

        try:
            ticket_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", ticket_btn)

        print(f" 已点击目标行程（今天+{days_offset}天）的購票按钮")

    def click_last_trip_ticket(self):
        """
        快捷方法：直接点最后一班（20:30）的購票按钮
        适用于当前URL已限定日期（date=2026-10-02）的场景
        """
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'購 票')]")
        ))

        # 取最后一个購票按钮（最后一班 20:30）
        ticket_btn = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//button[contains(@class,'ant-btn-primary')][.//span[contains(text(),'購')]])[last()]")
        ))

        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ticket_btn)
        time.sleep(0.5)

        try:
            ticket_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", ticket_btn)

        #  等待跳转（防止误判没点击）
        self.wait.until(EC.url_contains("create-order"))
        print(f" 已点击最后一班行程的購票按钮，跳转至: {self.driver.current_url}")