from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class Waits(WebDriverWait):
    """Explicit waits for dynamic mobile UI state.

    Accepts the same driver, timeout, and polling options as WebDriverWait.
    Locators are (strategy, value) tuples. Unmet conditions raise
    TimeoutException; inherited until() supports custom conditions.
    """

    def visible(self, locator):
        """Return an element once it is displayed."""
        return self.until(EC.visibility_of_element_located(locator))

    def present(self, locator):
        """Return an element once it exists, even if it is hidden."""
        return self.until(EC.presence_of_element_located(locator))

    def clickable(self, locator):
        """Return an element once it is displayed and enabled."""
        return self.until(EC.element_to_be_clickable(locator))

    def invisible(self, locator) -> bool:
        """Wait until an element is hidden or absent, e.g. a loading spinner."""
        return bool(self.until(EC.invisibility_of_element_located(locator)))

    def text_present(self, locator, text: str) -> bool:
        """Wait until the element's text contains the requested substring."""
        return self.until(EC.text_to_be_present_in_element(locator, text))

    def stale(self, element) -> bool:
        """Wait until a previously located element is detached."""
        return self.until(EC.staleness_of(element))
