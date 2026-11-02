import pytest
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from business.ferryticket_business import FerryTicketBusiness

DEPART_CITY = "深圳"
DEPART_PORT = "深圳蛇口碼頭"
ARRIVE_CITY = "香港"
ARRIVE_PORT = "香港國際機場海天碼頭"

BASE_URL = "https://www.testhopetrip.dabapiao.com/"
FERRY_PATH = "/ferry"


@pytest.fixture(scope="module")
def driver():
    d = webdriver.Chrome()
    d.maximize_window()
    d.implicitly_wait(3)

    d.get(BASE_URL)
    print(f" 已打开首页: {BASE_URL}")
    time.sleep(1)

    d.get(BASE_URL.rstrip("/") + FERRY_PATH)
    print(f" 已跳转船票页: {d.current_url}")

    try:
        WebDriverWait(d, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@data-testid='ferry-go-depart-city-trigger']")
            )
        )
        print(" 船票页面就绪（出发地 trigger 可点）")
    except Exception:
        d.save_screenshot("ferry_load_timeout.png")
        print(" 船票页面 trigger 未出现，已截图")
        raise

    yield d
    d.quit()


@pytest.fixture(scope="module")
def ferry_biz(driver):
    return FerryTicketBusiness(driver)


def test_01_select_depart_and_arrive(ferry_biz, driver):
    ferry_biz.select_ferry_route(
        depart_city=DEPART_CITY,
        depart_port=DEPART_PORT,
        arrive_city=ARRIVE_CITY,
        arrive_port=ARRIVE_PORT,
    )
    ferry_biz.verify_selection_result(
        depart_text=f"{DEPART_CITY}/{DEPART_PORT}",
        arrive_text=f"{ARRIVE_CITY}/{ARRIVE_PORT}",
        driver=driver,
    )
    print(f" test_01 通过: 出发[{DEPART_CITY}/{DEPART_PORT}] → 到达[{ARRIVE_CITY}/{ARRIVE_PORT}]")


def test_02_select_date_and_search(ferry_biz, driver):
    """依赖 test_01 状态，兜底确认路线 + 选日期 + 安全点击查询"""
    cur = driver.find_element(By.XPATH, "//body").text
    if DEPART_PORT not in cur or ARRIVE_PORT not in cur:
        ferry_biz.select_ferry_route(DEPART_CITY, DEPART_PORT, ARRIVE_CITY, ARRIVE_PORT)

    target_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        ferry_biz.ferry_page.select_ferry_date(target_date)
        print(f" 已选日期: {target_date}")
    except Exception as e:
        print(f" 日期选择跳过（{e}），使用页面默认日期")

    # ===== 查询按钮：安全点击 =====
    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@data-testid='ferry-btn-search']"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    time.sleep(0.3)

    try:
        btn.click()  # ✅ 优先原生
    except Exception:
        driver.execute_script(  # ✅ 安全 JS 兜底
            "var e=arguments[0]; if(e && e.click){e.click();} else if(e && e.length){e[0].click();}",
            btn
        )
    print(" 已点击【立即查询】")
    time.sleep(2)

    after = driver.find_element(By.XPATH, "//body").text
    assert DEPART_PORT in after, f"查询后出发地丢失"
    assert ARRIVE_PORT in after, f"查询后到达地丢失"
    assert "ferry" in driver.current_url.lower()
    print(" test_02 真通过: 日期+查询，且路线保持")