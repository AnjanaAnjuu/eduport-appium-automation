from selenium.common.exceptions import TimeoutException

from utils.waits import Waits


class BasePage:
    """Shared element interactions and waits for mobile page objects."""

    def __init__(self, driver, timeout: int = 15):
        self.driver = driver
        self.wait = Waits(driver, timeout)

    def element(self, locator):
        return self.wait.visible(locator)

    def click(self, locator) -> None:
        element = self.wait.clickable(locator)
        self.driver.execute_script('mobile: clickGesture', {'elementId': element.id})

    def enter_text(self, locator, text: str) -> None:
        field = self.element(locator)
        field.click()
        field.clear()
        field.send_keys(text)

    def is_visible(self, locator, timeout: int = 3) -> bool:
        try:
            Waits(self.driver, timeout).visible(locator)
            return True
        except TimeoutException:
            return False

    @staticmethod
    def is_element_within_screen(element, window_size: dict) -> bool:
        location, size = element.location, element.size
        return (
            location["x"] >= 0
            and location["y"] >= 0
            and location["x"] + size["width"] <= window_size["width"]
            and location["y"] + size["height"] <= window_size["height"]
        )
