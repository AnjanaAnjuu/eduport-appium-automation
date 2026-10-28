"""Analysis dashboard: Effort Index card and its entry points."""
import re

from appium.webdriver.common.appiumby import AppiumBy
from pages.base_page import BasePage


class EffortIndexPage(BasePage):
    DEFAULTS = {
        'analysis_tab': (AppiumBy.ACCESSIBILITY_ID, 'Analysis'),
        'analysis_title': (AppiumBy.ACCESSIBILITY_ID, 'Analysis'),
        'effort_card': (AppiumBy.XPATH, "//*[contains(@content-desc,'Daily Effort Tracker')]"),
        'effort_index': (AppiumBy.XPATH, "//*[contains(@content-desc,'Effort index')]"),
        'more': (AppiumBy.ACCESSIBILITY_ID, 'More'),
        'info': (AppiumBy.XPATH, "//*[contains(@content-desc,'Daily Effort Tracker')]/following::*[@content-desc='?'][1]"),
    }

    def __init__(self, driver, selectors=None, timeout=15):
        super().__init__(driver, timeout)
        self.selectors = {**self.DEFAULTS, **(selectors or {})}

    def locator(self, name):
        return tuple(self.selectors[name])

    def read(self, name):
        item = self.element(self.locator(name))
        return item.get_attribute('content-desc') or item.get_attribute('text') or item.text or ''

    def open(self):
        self.click(self.locator('analysis_tab'))
        self.element(self.locator('effort_card'))

    def index(self):
        label = self.read('effort_index')
        match = re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*Effort index', label, re.I)
        if not match:
            raise AssertionError(f'Effort index missing from {label!r}')
        return float(match.group(1))

    def open_tracker(self):
        self.click(self.locator('more'))

    def open_info(self):
        self.click(self.locator('info'))
