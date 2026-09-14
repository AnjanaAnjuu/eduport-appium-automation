import os
import re

import pytest
from selenium.webdriver.support.ui import WebDriverWait

from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from utils.keyboard import assert_numeric_keyboard


pytestmark = pytest.mark.sends_otp


MOBILE_NUMBER = os.getenv("TEST_MOBILE_NUMBER", "9876543210")
COUNTRY_CODE = os.getenv("DEFAULT_COUNTRY_CODE", "+91")
VALID_OTP = os.getenv("TEST_VALID_OTP", "1234")
INVALID_OTP = os.getenv("TEST_INVALID_OTP", "0000")
RESEND_TIMEOUT = int(os.getenv("OTP_RESEND_TIMEOUT", "40"))


@pytest.fixture
def otp_page(driver):
    login_page = LoginPage(driver)
    login_page.wait_until_loaded()
    login_page.enter_mobile_number(MOBILE_NUMBER)
    login_page.tap_continue()

    page = OtpTypePage(driver)
    page.wait_until_loaded()
    return page


def test_otp_verification_page_is_displayed(otp_page):
    assert otp_page.is_visible(OtpTypePage.SCREEN)
    assert otp_page.is_visible(OtpTypePage.TITLE)
    assert otp_page.is_visible(OtpTypePage.INSTRUCTION)
    assert otp_page.is_visible(OtpTypePage.MOBILE_NUMBER)
    assert otp_page.is_visible(OtpTypePage.HELP_BUTTON)


def test_correct_mobile_number_is_displayed(otp_page):
    displayed_number = otp_page.displayed_mobile_number()
    assert COUNTRY_CODE in displayed_number
    assert MOBILE_NUMBER in displayed_number


def test_native_otp_input_is_displayed(otp_page):
    fields = otp_page.otp_fields()
    assert len(fields) == 1  # Flutter exposes the visual boxes as one input.
    assert all(field.is_displayed() for field in fields)


def test_otp_input_has_focus_and_numeric_keyboard(otp_page, driver):
    first_field = otp_page.otp_fields()[0]
    first_field.click()
    assert first_field.get_attribute("focused") == "true"
    assert driver.is_keyboard_shown(), "Numeric keyboard was not displayed"
    assert_numeric_keyboard(driver)


def test_entering_otp_populates_native_input(otp_page):
    # Input-only checks must not authenticate and consume the valid OTP.
    otp_page.enter_otp(INVALID_OTP)
    assert "".join(otp_page.otp_values()) == INVALID_OTP


def test_otp_input_retains_focus_while_typing(otp_page):
    field = otp_page.otp_fields()[0]
    field.click()
    field.send_keys("1")
    assert field.get_attribute("focused") == "true"
    field.send_keys("2")
    assert field.get_attribute("focused") == "true"
    assert otp_page.otp_values() == ["12"]


def test_otp_fields_reject_non_numeric_characters(otp_page):
    otp_page.enter_otp("ab@#")
    assert all(value.isdigit() or value == "" for value in otp_page.otp_values())


def test_otp_is_limited_to_four_digits(otp_page):
    otp_page.enter_otp("123456")
    assert len("".join(otp_page.otp_values())) <= 4


def test_incomplete_otp_does_not_verify_user(otp_page):
    otp_page.enter_otp("12")
    assert not otp_page.is_verified(timeout=2)


def test_invalid_otp_displays_error(otp_page):
    otp_page.enter_otp(INVALID_OTP)
    assert otp_page.error_message().strip()
    assert not otp_page.is_verified(timeout=2)


@pytest.mark.requires_valid_otp
def test_valid_otp_verifies_user(otp_page):
    otp_page.enter_otp(VALID_OTP)
    assert otp_page.is_verified()


def test_resend_countdown_is_displayed_initially(otp_page):
    text = otp_page.resend_text()
    assert "resend" in text.lower()
    assert re.search(r"\d{1,2}:\d{2}", text), f"Countdown missing from {text!r}"


def test_resend_otp_becomes_available_after_countdown(otp_page):
    resend = otp_page.wait_for_resend_to_be_enabled(RESEND_TIMEOUT)
    assert resend.is_enabled()
    resend.click()
    assert re.search(r"\d{1,2}:\d{2}", otp_page.resend_text())


def test_edit_mobile_number_returns_to_login_page(otp_page):
    otp_page.tap_edit_mobile_number()
    login_page = LoginPage(otp_page.driver)
    assert login_page.is_visible(LoginPage.MOBILE_NUMBER_INPUT, timeout=10)
    assert MOBILE_NUMBER in login_page.mobile_number_value()


def test_help_button_opens_whatsapp(otp_page, driver):
    otp_page.tap_help()
    WebDriverWait(driver, 10).until(
        lambda current_driver: "whatsapp" in current_driver.current_package.lower()
    )
    assert "whatsapp" in driver.current_package.lower()


def test_otp_page_elements_are_visible_and_on_screen(otp_page, driver):
    window_size = driver.get_window_size()
    locators = (
        OtpTypePage.TITLE,
        OtpTypePage.INSTRUCTION,
        OtpTypePage.MOBILE_NUMBER,
        OtpTypePage.EDIT_MOBILE_NUMBER,
        OtpTypePage.HELP_BUTTON,
        OtpTypePage.RESEND_TEXT,
        *OtpTypePage.OTP_FIELDS,
    )
    for locator in locators:
        element = otp_page.element(locator)
        assert element.is_displayed(), f"Element {locator} is not displayed"
        assert otp_page.is_element_within_screen(element, window_size), (
            f"Element {locator} is outside the visible screen"
        )
