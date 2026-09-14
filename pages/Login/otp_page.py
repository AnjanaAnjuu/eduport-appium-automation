import re

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException

from pages.base_page import BasePage
from pages.Login.login_page import LoginPage
from utils.waits import Waits


class OtpTypePage(BasePage):
    """Page object for the four-digit OTP verification screen."""

    SCREEN = LoginPage.OTP_SCREEN
    TITLE = SCREEN
    INSTRUCTION = (AppiumBy.ACCESSIBILITY_ID, "We have sent a verification code to")
    MOBILE_NUMBER = LoginPage.OTP_MOBILE_NUMBER
    EDIT_MOBILE_NUMBER = MOBILE_NUMBER
    HELP_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Help")
    OTP_ERROR = (AppiumBy.ACCESSIBILITY_ID, "otp_error")
    RESEND_TEXT = (AppiumBy.XPATH, "//*[contains(@content-desc, 'Resend')]")
    VERIFIED_SCREEN = (
        AppiumBy.XPATH,
        "//*[@content-desc='Home'] | //*[@content-desc='ANALYSE']",
    )
    # The four visual boxes share one native input in this Flutter build.
    OTP_FIELDS = ((AppiumBy.CLASS_NAME, "android.widget.EditText"),)

    def wait_until_loaded(self) -> None:
        try:
            self.element(self.SCREEN)
        except TimeoutException as error:
            login_buttons = self.driver.find_elements(*LoginPage.CONTINUE_BUTTON)
            if any(button.is_displayed() for button in login_buttons):
                message = (
                    "OTP navigation failed: the app is still on the login screen "
                    "after Send OTP. The verification screen was not opened; "
                    "this is not evidence of an incorrect OTP locator. "
                    "Check the OTP request response/app logs before retrying."
                )
            else:
                message = (
                    "OTP verification heading was not visible. Inspect the failure "
                    "screenshot and current Appium hierarchy to distinguish a "
                    "changed locator from navigation to a different screen."
                )
            raise TimeoutException(message, error.screen, error.stacktrace) from error
        self.element(self.MOBILE_NUMBER)
        for locator in self.OTP_FIELDS:
            self.element(locator)

    def otp_fields(self):
        return [self.element(locator) for locator in self.OTP_FIELDS]

    @staticmethod
    def _value(field) -> str:
        return field.get_attribute("text") or ""

    def enter_otp(self, otp: str) -> None:
        first_field = self.element(self.OTP_FIELDS[0])
        first_field.click()
        first_field.send_keys(otp)

    def enter_otp_one_digit_at_a_time(self, otp: str) -> None:
        field = self.element(self.OTP_FIELDS[0])
        for digit in otp:
            field.send_keys(digit)

    def otp_values(self) -> list[str]:
        return [self._value(field) for field in self.otp_fields()]

    def displayed_mobile_number(self) -> str:
        element = self.element(self.MOBILE_NUMBER)
        text = element.get_attribute("content-desc") or element.text
        return re.sub(r"\s+", "", text)

    def tap_edit_mobile_number(self) -> None:
        self.click(self.EDIT_MOBILE_NUMBER)

    def tap_help(self) -> None:
        self.click(self.HELP_BUTTON)

    def resend_text(self) -> str:
        element = self.element(self.RESEND_TEXT)
        return element.get_attribute("content-desc") or element.text

    def wait_for_resend_to_be_enabled(self, timeout: int = 40):
        def resend_enabled(driver):
            elements = driver.find_elements(*self.RESEND_TEXT)
            if elements and elements[0].is_displayed():
                element = elements[0]
                if element.get_attribute("clickable") == "true":
                    return element
            return False

        return Waits(self.driver, timeout).until(resend_enabled)

    def tap_resend(self) -> None:
        self.click(self.RESEND_TEXT)

    def error_message(self) -> str:
        return self.element(self.OTP_ERROR).text

    def is_verified(self, timeout: int = 10) -> bool:
        return self.is_visible(self.VERIFIED_SCREEN, timeout)

    @staticmethod
    def is_element_within_screen(element, window_size: dict) -> bool:
        location, size = element.location, element.size
        return (
            location["x"] >= 0
            and location["y"] >= 0
            and location["x"] + size["width"] <= window_size["width"]
            and location["y"] + size["height"] <= window_size["height"]
        )
