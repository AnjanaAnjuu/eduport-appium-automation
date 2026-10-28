"""Page object for Home Search and its result filters."""

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException

from pages.base_page import BasePage


class HomeSearchPage(BasePage):
    """Interactions shared by the Home and Search screens.

    Defaults target the accessibility labels exposed by the Flutter build. Any
    build-specific IDs can be supplied through ``selectors`` as two-item
    ``[strategy, value]`` locator sequences.
    """

    DEFAULTS = {
        "home": (AppiumBy.ACCESSIBILITY_ID, "Home"),
        "home_search": (AppiumBy.XPATH, "//*[contains(@content-desc,'Search courses and topics')]"),
        "back": (AppiumBy.XPATH, "(//android.widget.ImageView[@clickable='true' and (not(@content-desc) or @content-desc='')])[1]"),
        "search_field": (AppiumBy.XPATH, "//android.widget.EditText"),
        "browse_subjects": (AppiumBy.ACCESSIBILITY_ID, "Browse Subjects"),
        "browse_resources": (AppiumBy.ACCESSIBILITY_ID, "Browse Resources"),
        "no_results": (AppiumBy.ACCESSIBILITY_ID, "No matching search results."),
        "recent_searches": (AppiumBy.ACCESSIBILITY_ID, "Recent Searches"),
        "loading": (AppiumBy.XPATH, "//*[@content-desc='Loading' or @text='Loading']"),
        "network_error": (AppiumBy.XPATH, "//*[contains(@content-desc,'internet') or contains(@text,'internet') or contains(@content-desc,'network') or contains(@text,'network')]"),
    }
    CATEGORIES = ("All", "Chapters", "Topics", "Subtopics", "Resources")

    def __init__(self, driver, selectors=None, timeout=15):
        super().__init__(driver, timeout)
        self.selectors = {**self.DEFAULTS, **(selectors or {})}

    @staticmethod
    def _xpath_literal(value):
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"

    def locator(self, name):
        locator = self.selectors.get(name)
        if not isinstance(locator, (list, tuple)) or len(locator) != 2:
            raise ValueError(f"Configure a valid locator for {name!r}")
        return tuple(locator)

    def displayed(self, name, timeout=3):
        return self.is_visible(self.locator(name), timeout)

    def text(self, name):
        element = self.element(self.locator(name))
        return (element.get_attribute("content-desc") or
                element.get_attribute("text") or element.text or "")

    def open(self):
        self.element(self.locator("home"))
        self.click(self.locator("home_search"))
        self.wait_loaded()

    def go_home(self):
        """Return from any Search destination without assuming its Back label."""
        for _ in range(6):
            if self.displayed("home_search", timeout=1):
                return
            home = self.driver.find_elements(*self.locator("home"))
            if home and home[0].is_displayed():
                home[0].click()
            else:
                self.driver.back()
        self.element(self.locator("home_search"))

    def wait_loaded(self):
        try:
            self.element(self.locator("search_field"))
        except TimeoutException as error:
            labels = [item.get_attribute("content-desc") for item in
                      self.driver.find_elements(AppiumBy.XPATH, "//*[@content-desc]")]
            raise AssertionError(f"Search field was not found; visible labels: {labels}") from error
        self.element(self.locator("back"))

    def back_to_home(self):
        self.click(self.locator("back"))
        self.element(self.locator("home"))

    def placeholder(self):
        field = self.element(self.locator("search_field"))
        return (field.get_attribute("hint") or field.get_attribute("content-desc") or
                field.get_attribute("text") or "")

    def search(self, keyword, wait_for_results=True):
        self.enter_text(self.locator("search_field"), keyword)
        if self.driver.is_keyboard_shown():
            self.driver.hide_keyboard()
        if wait_for_results:
            self.wait.until(lambda _: self.displayed("no_results", 1) or bool(self.results()),
                            message=f"No settled search response for {keyword!r}")

    def clear_search(self):
        field = self.element(self.locator("search_field"))
        field.clear()
        self.wait.until(
            lambda _: not (field.get_attribute("text") or "").strip(),
            message="Search field was not cleared",
        )

    def category_locator(self, category):
        if category not in self.CATEGORIES:
            raise ValueError(f"Unknown search category: {category}")
        return (AppiumBy.ACCESSIBILITY_ID, category)

    def select_category(self, category):
        self.click(self.category_locator(category))
        self.wait_until_not_loading()

    def category_selected(self, category):
        element = self.element(self.category_locator(category))
        return str(element.get_attribute("selected")).lower() == "true" or "selected" in (
            element.get_attribute("content-desc") or "").casefold()

    def named_locator(self, label):
        literal = self._xpath_literal(label)
        return (AppiumBy.XPATH,
                f"//*[contains(@content-desc,{literal}) or contains(@text,{literal})]")

    def open_named(self, label):
        self.click(self.named_locator(label))

    def named_visible(self, label, timeout=5):
        return self.is_visible(self.named_locator(label), timeout)

    def items(self, selector_name):
        return [item for item in self.driver.find_elements(*self.locator(selector_name))
                if item.is_displayed()]

    def results(self):
        return self.items("result_items") if "result_items" in self.selectors else []

    @staticmethod
    def label(element):
        return (element.get_attribute("content-desc") or
                element.get_attribute("text") or element.text or "").strip()

    def result_labels(self):
        return [self.label(item) for item in self.results()]

    def result_types(self):
        """Read result type/status from a dedicated child/attribute when exposed."""
        output = []
        child_locator = self.selectors.get("result_type_child")
        for result in self.results():
            value = ""
            if child_locator:
                children = result.find_elements(*tuple(child_locator))
                value = self.label(children[-1]) if children else value
            output.append(value.strip())
        return output

    def wait_until_not_loading(self, timeout=20):
        try:
            return self.wait.invisible(self.locator("loading"))
        except TimeoutException as error:
            raise AssertionError("Search results did not finish loading") from error

    def assert_unique_complete_results(self, expected_labels):
        self.wait_until_not_loading()
        actual = self.result_labels()
        assert len(actual) == len(set(actual)), "Duplicate search results were displayed"
        assert set(expected_labels) <= set(actual), "Expected search results are incomplete"
