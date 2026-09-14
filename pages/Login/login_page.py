from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class LoginPage(BasePage):
    """Interactions and assertions for the mobile-number login screen."""

    # The current Flutter build exposes no resource-id/content-desc on the
    # phone field. It is the only EditText on the login screen.
    MOBILE_NUMBER_INPUT = (AppiumBy.CLASS_NAME, "android.widget.EditText")
    COUNTRY_CODE_BUTTON = (
        AppiumBy.XPATH,
        "//android.view.View[@clickable='true' and contains(@content-desc, '+')]",
    )
    CONTINUE_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Send OTP")
    HELP_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Help")
    LOGIN_LOGO = (
        AppiumBy.XPATH,
        "//android.view.View[android.widget.EditText]/android.widget.ImageView[not(@content-desc) or @content-desc=''][1]",
    )
    VALIDATION_MESSAGE = (AppiumBy.ACCESSIBILITY_ID, "mobile_number_error")
    COUNTRY_CODE_LIST = (AppiumBy.ACCESSIBILITY_ID, "Pick your country code")
    OTP_SCREEN = (AppiumBy.ACCESSIBILITY_ID, "OTP Verifications")
    OTP_MOBILE_NUMBER = (
        AppiumBy.XPATH,
        "//android.widget.ImageView[starts-with(@content-desc, 'Change') and contains(@content-desc, '+')]",
    )

    def wait_until_loaded(self) -> None:
        # Android's phone-number hint dialog appears after a cold app launch.
        # Cancel suggestions rather than selecting a device/user phone number.
        cancel_locator = (AppiumBy.ID, "com.google.android.gms:id/cancel")

        def dismiss_hint_or_find_login(driver):
            cancel_buttons = driver.find_elements(*cancel_locator)
            if cancel_buttons and cancel_buttons[0].is_displayed():
                cancel_buttons[0].click()
            fields = driver.find_elements(*self.MOBILE_NUMBER_INPUT)
            return fields and fields[0].is_displayed()

        self.wait.until(dismiss_hint_or_find_login)
        for locator in (
            self.MOBILE_NUMBER_INPUT,
            self.COUNTRY_CODE_BUTTON,
            self.CONTINUE_BUTTON,
            self.HELP_BUTTON,
        ):
            self.element(locator)

    def enter_mobile_number(self, number: str) -> None:
        self.enter_text(self.MOBILE_NUMBER_INPUT, number)

    def mobile_number_value(self) -> str:
        field = self.element(self.MOBILE_NUMBER_INPUT)
        return field.get_attribute("text") or ""

    def mobile_number_prompt(self) -> str:
        field = self.element(self.MOBILE_NUMBER_INPUT)
        return (
            field.get_attribute("hint")
            or field.get_attribute("content-desc")
            or field.get_attribute("text")
            or ""
        )

    def country_code(self) -> str:
        element = self.element(self.COUNTRY_CODE_BUTTON)
        return (
            element.get_attribute("text")
            or element.get_attribute("content-desc")
            or element.text
        )

    def select_country_code(self, country_code: str) -> None:
        import re

        if not re.fullmatch(r"\+\d{1,4}", country_code):
            raise ValueError("Country code must contain + followed by digits")
        self.click(self.COUNTRY_CODE_BUTTON)
        self.element(self.COUNTRY_CODE_LIST)
        search = self.driver.find_elements(AppiumBy.CLASS_NAME, 'android.widget.EditText')
        if search:
            search[0].click()
            search[0].send_keys(country_code)
            if self.driver.is_keyboard_shown():
                self.driver.hide_keyboard()
        for _ in range(15):
            options = self.driver.find_elements(AppiumBy.CLASS_NAME, 'android.view.View')
            for option in options:
                description = option.get_attribute('content-desc') or ''
                if description.strip().splitlines() and description.strip().splitlines()[-1].strip() == country_code and option.is_displayed():
                    self.driver.execute_script('mobile: clickGesture', {'elementId': option.id})
                    self.element(self.COUNTRY_CODE_BUTTON)
                    return
            size = self.driver.get_window_size()
            self.driver.execute_script('mobile: swipeGesture', {
                'left': 40, 'top': int(size['height'] * .4),
                'width': size['width'] - 80, 'height': int(size['height'] * .5),
                'direction': 'up', 'percent': .8,
            })
        raise AssertionError(f'Country code {country_code} not found in picker')

    def can_send_otp(self) -> bool:
        return self.element(self.CONTINUE_BUTTON).get_attribute('clickable') == 'true'

    def tap_continue(self) -> None:
        if self.driver.is_keyboard_shown():
            self.driver.hide_keyboard()
            self.wait.until(lambda d: not d.is_keyboard_shown())
        self.wait.until(lambda _: self.can_send_otp(), message='Send OTP never became clickable')
        self.click(self.CONTINUE_BUTTON)

    def open_whatsapp(self) -> None:
        self.tap_help()
        self.element((AppiumBy.ACCESSIBILITY_ID, 'Reach Us'))
        options = self.driver.find_elements(AppiumBy.XPATH, "//*[contains(@content-desc, 'Whatsapp') or contains(@content-desc, 'WhatsApp')]")
        if not options:
            raise AssertionError('WhatsApp option not exposed in Reach Us sheet')
        options[0].click()

    def tap_help(self) -> None:
        self.click(self.HELP_BUTTON)

    def validation_message(self) -> str:
        return self.element(self.VALIDATION_MESSAGE).text

    def is_otp_page_displayed(self, timeout: int = 10) -> bool:
        return self.is_visible(self.OTP_SCREEN, timeout)

    def otp_mobile_number(self) -> str:
        element = self.element(self.OTP_MOBILE_NUMBER)
        return element.get_attribute("content-desc") or element.text
