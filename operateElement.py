# operate_element.py
"""
基础操作封装层
作用：
1. 统一 Selenium 操作入口
2. 自动等待 + 自动截图 + Allure 步骤
3. 降低 Page 层复杂度
"""

from functools import wraps
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException
)

import allure


def allure_step(title: str):
    """
    装饰器：自动为操作方法添加 Allure 步骤
    用于在 Allure 报告中展示每个操作的具体步骤名称
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with allure.step(title):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class OperateElement:
    def __init__(self, driver, timeout: int = 10):
        """
        初始化基础操作类
        :param driver: Selenium WebDriver 实例
        :param timeout: 显式等待默认超时时间（秒）
        """
        self.driver = driver
        self.timeout = timeout

    # ======================
    # 内部工具方法（私有方法）
    # ======================
    def _wait(self, locator, condition=EC.element_to_be_clickable):
        """
        统一显式等待入口
        封装 WebDriverWait + ExpectedConditions，减少重复代码
        :param locator: 元素定位器（XPATH）
        :param condition: 等待条件（默认：元素可点击）
        """
        return WebDriverWait(self.driver, self.timeout).until(
            condition((By.XPATH, locator))
        )

    def _attach_screenshot(self, name: str):
        """
        统一截图并附加到 Allure 报告
        用于失败时记录现场信息
        :param name: 截图名称（显示在 Allure 报告中）
        """
        allure.attach(
            self.driver.get_screenshot_as_png(),
            name=name,
            attachment_type=allure.attachment_type.PNG
        )

    # ======================
    # 对外操作方法（Page 层直接调用）
    # ======================
    @allure_step("点击元素")
    def click(self, locator):
        """
        点击元素（带重试机制）
        1. 等待元素可点击
        2. 正常点击
        3. 失败时截图并重试一次（解决 AntD 动画拦截问题）
        """
        try:
            self._wait(locator).click()
        except (TimeoutException, ElementClickInterceptedException):
            self._attach_screenshot("点击元素失败")
            # 重试一次，提升稳定性
            self._wait(locator).click()

    @allure_step("输入内容")
    def send_keys(self, locator, text):
        """
        向输入框输入内容
        1. 等待元素可见
        2. 清空原有内容
        3. 输入新内容
        """
        try:
            el = self._wait(locator)
            el.clear()
            el.send_keys(text)
        except TimeoutException:
            self._attach_screenshot("输入内容失败")
            raise AssertionError(f"无法定位输入框：{locator}")

    @allure_step("获取元素文本")
    def get_text(self, locator):
        """
        获取元素文本内容
        常用于断言或数据校验
        """
        try:
            return self._wait(locator, EC.presence_of_element_located).text
        except TimeoutException:
            self._attach_screenshot("获取文本失败")
            raise

    @allure_step("清除输入框内容")
    def clear(self, locator):
        """
        清除输入框内容
        常用于需要重复输入的场景
        """
        try:
            self._wait(locator).clear()
        except TimeoutException:
            self._attach_screenshot("清除文本失败")
            raise

    @allure_step("文本断言")
    def assert_text(self, locator, expected_text):
        """
        断言元素文本包含指定内容
        失败时会自动截图并抛出明确的断言错误
        """
        element_text = self.get_text(locator)

        if expected_text not in element_text:
            self._attach_screenshot("文本断言失败")
            raise AssertionError(
                f"文本断言失败！\n"
                f"预期包含：{expected_text}\n"
                f"实际文本：{element_text}"
            )