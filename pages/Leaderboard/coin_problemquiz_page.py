"""Page object for opening and validating a problem-based quiz."""

import re

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException

from pages.base_page import BasePage


class CoinProblemQuizPage(BasePage):
    """Navigate to Problem Practice and inspect its pre-attempt screen."""

    COURSE_SWITCHER = (AppiumBy.ACCESSIBILITY_ID, "Tap here to switch your course.")
    HOME = (AppiumBy.ACCESSIBILITY_ID, "Home")
    BACK = (AppiumBy.XPATH, "//android.widget.ImageView[@clickable='true'][1]")
    HELP = (AppiumBy.XPATH, "//*[@content-desc='?' or @text='?']")

    TITLE = (AppiumBy.XPATH, "//*[contains(@content-desc,'Importance of Chemistry') or contains(@text,'Importance of Chemistry')]")
    QUIZ_KIND = (AppiumBy.XPATH, "//*[@content-desc='Problem Practice' or @text='Problem Practice']")
    QUESTION_COUNT = (AppiumBy.XPATH, "//*[contains(@content-desc,'Questions') or contains(@text,'Questions')]")
    VIEW_TOPICS = (AppiumBy.XPATH, "//*[@content-desc='View topics' or @text='View topics']")
    CORRECT_CARD = (AppiumBy.XPATH, "//*[contains(@content-desc,'Correct') and contains(@content-desc,'+4')]")
    UNKNOWN_CARD = (AppiumBy.XPATH, "//*[contains(@content-desc,\"I don’t know\") and contains(@content-desc,'+0')]")
    WRONG_CARD = (AppiumBy.XPATH, "//*[contains(@content-desc,'Wrong') and contains(@content-desc,'-1')]")
    ADAPT_INFO = (AppiumBy.XPATH, "//*[contains(@content-desc,'Adapt Practice') or contains(@text,'Adapt Practice')]")
    START = (AppiumBy.XPATH, "//*[@content-desc='Start Test' or @text='Start Test' or @content-desc='Start' or @text='Start']")
    RESUME = (AppiumBy.XPATH, "//*[@content-desc='Resume Test' or @text='Resume Test']")
    REVIEW = (AppiumBy.XPATH, "//*[@content-desc='Review' or @text='Review' or @content-desc='Review Test' or @text='Review Test']")
    QUESTION_SCREEN = (AppiumBy.XPATH, "//*[contains(@content-desc,'Question 1') or contains(@text,'Question 1')]")

    def _label_locator(self, label):
        escaped = label.replace("'", "\\'")
        return (
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().descriptionContains("{escaped}")',
        )

    def _scroll_to(self, locator, attempts=5):
        for _ in range(attempts):
            elements = self.driver.find_elements(*locator)
            if elements and elements[0].is_displayed():
                return elements[0]
            size = self.driver.get_window_size()
            self.driver.execute_script("mobile: scrollGesture", {
                "left": 20,
                "top": int(size["height"] * 0.25),
                "width": size["width"] - 40,
                "height": int(size["height"] * 0.65),
                "direction": "down",
                "percent": 0.8,
            })
        return self.element(locator)

    def select_course(self, course_name):
        if self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, course_name):
            return
        self.click(self.COURSE_SWITCHER)
        self.click((AppiumBy.ACCESSIBILITY_ID, course_name))
        self.element((AppiumBy.ACCESSIBILITY_ID, course_name))

    def open_named_item(self, label):
        locator = self._label_locator(label)
        element = self._scroll_to(locator)
        self.driver.execute_script("mobile: clickGesture", {"elementId": element.id})

    def open_problem_quiz(self, subject, chapter, subtopic):
        self.click(self.HOME)
        self.open_named_item(subject)
        self.open_named_item(chapter)
        self.open_named_item(subtopic)
        self.open_named_item("Problem Based Questions")
        self.wait_until_loaded()

    def wait_until_loaded(self):
        self.element(self.TITLE)
        self.element(self.QUIZ_KIND)
        self.element(self.QUESTION_COUNT)

    @staticmethod
    def _text(element):
        return (element.get_attribute("content-desc") or
                element.get_attribute("text") or element.text or "").strip()

    def title(self):
        return self._text(self.element(self.TITLE))

    def question_count(self):
        value = self._text(self.element(self.QUESTION_COUNT))
        match = re.search(r"(\d+)\s*Questions?", value, re.IGNORECASE)
        if not match:
            raise AssertionError(f"Question count is missing from {value!r}")
        return int(match.group(1))

    def primary_action(self):
        for state, locator in (("start", self.START), ("resume", self.RESUME),
                               ("review", self.REVIEW)):
            if self.is_visible(locator, timeout=1):
                return state, locator
        raise AssertionError("Expected Start Test, Resume Test, or Review button")

    def assert_overview(self, expected):
        assert expected["title"].casefold() in self.title().casefold()
        assert self.question_count() == expected["questions"]
        for locator in (self.BACK, self.HELP, self.VIEW_TOPICS, self.CORRECT_CARD,
                        self.UNKNOWN_CARD, self.WRONG_CARD, self.ADAPT_INFO):
            assert self.is_visible(locator), f"Missing overview element: {locator}"

    def assert_attempt_action(self, attempt_state):
        actual, _ = self.primary_action()
        expected = {
            "first": "start",
            "in_progress": "resume",
            "completed": "review",
        }[attempt_state]
        assert actual == expected, f"Expected {expected!r} action, found {actual!r}"

    def tap_primary_action(self):
        state, locator = self.primary_action()
        self.click(locator)
        if state in {"start", "resume"}:
            try:
                self.element(self.QUESTION_SCREEN)
            except TimeoutException as error:
                raise AssertionError("Quiz question UI did not open") from error
        return state
