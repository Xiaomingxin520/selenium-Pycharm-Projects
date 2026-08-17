import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径，确保能 import page / business 等模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import time
import csv
import allure
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

from page.login_page import LoginPage
from business.loginBusiness import LoginBusiness


# CSV 文件路径：存放登录测试数据的文件
CSV_PATH = PROJECT_ROOT / "data" / "login.csv"


def normalize_csv_value(value):
    """
    统一处理 CSV 中的空值，避免 None / 空字符串 / <null> 等干扰测试逻辑
    支持：空字符串、空格、<null>、NULL、None、nan
    """
    if value is None:
        return ''
    v = value.strip()
    if v.lower() in ['<null>', 'null', 'none', 'nan']:
        return ''
    return v


def load_login_csv_data():
    """
    读取 data/login.csv，转换成 pytest.mark.parametrize 可用的列表数据

    支持的 CSV 表头：
    case_id,source_case,login_type,area_code,phone,pwd,expect_success,expect_text,description
    """
    data = []

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            case_id = normalize_csv_value(row.get('case_id', ''))
            source_case = normalize_csv_value(row.get('source_case', ''))
            login_type = normalize_csv_value(row.get('login_type', ''))
            area_code = normalize_csv_value(row.get('area_code', ''))
            phone = normalize_csv_value(row.get('phone', ''))
            pwd = normalize_csv_value(row.get('pwd', ''))
            expect_success = normalize_csv_value(row.get('expect_success', ''))
            expect_text = normalize_csv_value(row.get('expect_text', ''))
            description = normalize_csv_value(row.get('description', ''))

            # 仅保留密码登录类型的用例
            if login_type != 'password':
                continue

            # 跳过全空行，防止脏数据干扰
            if not any([case_id, phone, pwd, expect_text, area_code]):
                continue

            # area_code 默认值保护：未填写时默认香港（+852）
            if not area_code:
                area_code = '+852'

            data.append(
                (
                    area_code,
                    phone,
                    pwd,
                    expect_text,
                    case_id,
                    source_case,
                    expect_success,
                    description
                )
            )

    return data


# 全局测试数据，供 pytest 参数化使用
LOGIN_DATA = load_login_csv_data()


@allure.feature('登录模块')
class TestLogin:

    def setup_method(self):
        """
        每个测试用例执行前：启动浏览器并打开测试地址
        使用 Chrome 浏览器，非无头模式便于调试
        """
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 调试时可关闭无头模式
        chrome_options.add_argument('--window-size=1920,1080')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get('https://www.testhopetrip.dabapiao.com/')
        time.sleep(2)  # 等待页面初步加载完成

    @pytest.mark.parametrize(
        "area_code,phone,pwd,expect_text,case_id,source_case,expect_success,description",
        LOGIN_DATA
    )
    def test_login(
        self,
        area_code,
        phone,
        pwd,
        expect_text,
        case_id,
        source_case,
        expect_success,
        description
    ):
        """
        密码登录场景测试用例（支持多区号）
        数据来源：CSV 文件
        断言方式：优先 AntD Toast，其次表单错误提示
        """

        # Allure 报告中展示用例标题和详细描述
        allure.dynamic.title(f'{case_id} - {description}')
        allure.dynamic.description(
            f'case_id: {case_id}\n'
            f'source_case: {source_case}\n'
            f'area_code: {area_code}\n'
            f'phone: {phone}\n'
            f'expect_text: {expect_text}\n'
            f'description: {description}'
        )

        actual_text = ''
        timestamp = time.strftime('%Y%m%d%H%M%S')

        with allure.step('执行登录操作'):
            try:
                # 调用 Business 层执行登录流程
                LoginBusiness.loginBusiness(
                    self.driver,
                    phone=phone,
                    password=pwd,
                    area_code=area_code
                )

                time.sleep(1.5)  # ✅ 关键等待：确保 AntD Toast 完全渲染出来

                if expect_success.lower() == 'true':
                    # ✅ 登录成功：捕获 AntD 成功 Toast
                    actual_text = WebDriverWait(self.driver, 6).until(
                        EC.visibility_of_element_located(LoginPage.LOGIN_SUCCESS_TOAST)
                    ).text

                else:
                    # ✅ 登录失败：优先表单级错误，其次错误 Toast
                    try:
                        actual_text = self.driver.find_element(*LoginPage.FORM_ERROR).text
                    except Exception:
                        actual_text = WebDriverWait(self.driver, 5).until(
                            EC.visibility_of_element_located(LoginPage.LOGIN_ERROR_TOAST)
                        ).text

            except Exception as e:
                # 出现异常时截图，便于定位问题
                allure.attach(
                    self.driver.get_screenshot_as_png(),
                    name='操作或定位异常',
                    attachment_type=allure.attachment_type.PNG
                )
                assert False, f'操作或定位异常: {e}'

        with allure.step('断言验证'):
            try:
                # 验证实际文本中是否包含预期文本
                assert expect_text in actual_text, \
                    f'预期文本[{expect_text}]不在实际文本[{actual_text}]中'
            except Exception as e:
                # 断言失败时截图
                allure.attach(
                    self.driver.get_screenshot_as_png(),
                    name='断言失败',
                    attachment_type=allure.attachment_type.PNG
                )
                assert False, str(e)

        with allure.step('执行完成截图'):
            # 用例执行结束后截图，记录最终状态
            allure.attach(
                self.driver.get_screenshot_as_png(),
                name='执行结果截图',
                attachment_type=allure.attachment_type.PNG
            )

    def teardown_method(self):
        """
        每个测试用例执行后：关闭浏览器，释放资源
        """
        self.driver.quit()