"""Page object for the four-screen onboarding carousel."""

from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class OnboardingPage(BasePage):
    """Actions shared by onboarding shown after signup and existing-user login.

    ``page_markers`` may be supplied when the application exposes the screen
    headings from the design as accessibility labels.  Without overrides the
    page object uses the common ``1 of 4`` accessibility semantics.
    """

    SKIP_BUTTON = (
        AppiumBy.XPATH,
        "//*[@content-desc='Skip' or @text='Skip']",
    )
    HOME_SCREEN = (
        AppiumBy.XPATH,
        "//*[@content-desc='Home' or @text='Home']",
    )
    PAGE_TITLES = ("LEARN", "PRACTICE", "ANALYSE", "IMPROVE")
    DEFAULT_PAGE_MARKERS = tuple(
        (
            AppiumBy.XPATH,
            f"//*[contains(@content-desc, '{title}') or contains(@text, '{title}')]",
        )
        for title in PAGE_TITLES
    )
    PERMISSION_ALLOW = (
        AppiumBy.ID,
        "com.android.permissioncontroller:id/permission_allow_button",
    )

    def __init__(self, driver, page_markers=None, timeout=15):
        super().__init__(driver, timeout)
        self.page_markers = tuple(page_markers or self.DEFAULT_PAGE_MARKERS)
        if len(self.page_markers) != 4:
            raise ValueError("Onboarding must have exactly four page markers")

    def wait_until_loaded(self) -> None:
        self.allow_notifications_if_requested()
        self.element(self.SKIP_BUTTON)
        self.wait_for_page(1)

    def allow_notifications_if_requested(self) -> None:
        buttons = self.driver.find_elements(*self.PERMISSION_ALLOW)
        if buttons and buttons[0].is_displayed():
            buttons[0].click()

    def current_page(self) -> int | None:
        for number, marker in enumerate(self.page_markers, start=1):
            if any(element.is_displayed() for element in self.driver.find_elements(*marker)):
                return number
        return None

    def wait_for_page(self, number: int) -> None:
        self._validate_page_number(number)
        self.element(self.page_markers[number - 1])

    def is_page_displayed(self, number: int, timeout=3) -> bool:
        self._validate_page_number(number)
        return self.is_visible(self.page_markers[number - 1], timeout)

    def tap_skip(self) -> None:
        self.click(self.SKIP_BUTTON)
        self.wait_for_home()

    def complete_all_pages(self) -> list[int]:
        """Observe all four auto-advancing pages before the app opens Home."""
        visited = []
        for expected_page in range(1, 5):
            self.wait_for_page(expected_page)
            assert self.current_page() == expected_page
            visited.append(expected_page)
        self.wait_for_home()
        return visited

    def wait_for_home(self) -> None:
        self.element(self.HOME_SCREEN)
        self.wait.invisible(self.SKIP_BUTTON)

    def is_home_displayed(self, timeout=10) -> bool:
        return self.is_visible(self.HOME_SCREEN, timeout)

    @staticmethod
    def _validate_page_number(number: int) -> None:
        if number not in range(1, 5):
            raise ValueError("Onboarding page number must be from 1 to 4")
