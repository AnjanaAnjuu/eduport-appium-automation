import os

import pytest
from selenium.webdriver.support.ui import WebDriverWait

from pages.Login.login_page import LoginPage
from utils.keyboard import assert_numeric_keyboard


VALID_MOBILE_NUMBER = os.getenv("TEST_MOBILE_NUMBER", "9876543210")
INVALID_MOBILE_NUMBER = os.getenv("INVALID_MOBILE_NUMBER", "123")
DEFAULT_COUNTRY_CODE = os.getenv("DEFAULT_COUNTRY_CODE", "+91")
ALTERNATE_COUNTRY_CODE = os.getenv("ALTERNATE_COUNTRY_CODE", "+1")
MAX_MOBILE_LENGTH = int(os.getenv("MAX_MOBILE_LENGTH", "10"))


@pytest.fixture
def login_page(driver):
    page = LoginPage(driver)
    page.wait_until_loaded()
    return page


def test_login_page_is_displayed_for_logged_out_user(login_page):
    assert login_page.is_visible(LoginPage.MOBILE_NUMBER_INPUT)
    assert login_page.is_visible(LoginPage.COUNTRY_CODE_BUTTON)
    assert login_page.is_visible(LoginPage.CONTINUE_BUTTON)
    assert login_page.is_visible(LoginPage.HELP_BUTTON)


def test_mobile_number_field_displays_prompt(login_page):
    prompt = login_page.mobile_number_prompt().lower()
    assert "mobile" in prompt or "phone" in prompt, (
        f"Expected a mobile-number prompt, but found {prompt!r}"
    )


def test_user_can_select_country_code(login_page):
    login_page.select_country_code(ALTERNATE_COUNTRY_CODE)
    assert ALTERNATE_COUNTRY_CODE in login_page.country_code()


def test_default_country_code(login_page):
    assert DEFAULT_COUNTRY_CODE in login_page.country_code()


def test_user_can_enter_valid_mobile_number(login_page):
    login_page.enter_mobile_number(VALID_MOBILE_NUMBER)
    assert login_page.mobile_number_value() == VALID_MOBILE_NUMBER


def test_invalid_mobile_number_disables_send_otp(login_page):
    login_page.enter_mobile_number(INVALID_MOBILE_NUMBER)
    assert not login_page.can_send_otp()


def test_empty_mobile_number_disables_send_otp(login_page):
    login_page.enter_mobile_number("")
    assert not login_page.can_send_otp()
    assert not login_page.is_otp_page_displayed(timeout=2)


@pytest.mark.parametrize("invalid_characters", ["abc", "98@76-54"])
def test_mobile_number_rejects_invalid_characters(login_page, invalid_characters):
    login_page.enter_mobile_number(invalid_characters)
    accepted_value = login_page.mobile_number_value()
    assert accepted_value.isdigit() or accepted_value == ""


def test_mobile_number_rejects_excess_length(login_page):
    login_page.enter_mobile_number("9" * (MAX_MOBILE_LENGTH + 3))
    accepted_value = login_page.mobile_number_value()
    assert len(accepted_value) <= MAX_MOBILE_LENGTH


@pytest.mark.sends_otp
def test_continue_with_valid_mobile_number_opens_otp_page(login_page):
    login_page.enter_mobile_number(VALID_MOBILE_NUMBER)
    login_page.tap_continue()
    assert login_page.is_otp_page_displayed()


def test_continue_with_invalid_mobile_number_stays_on_login_page(login_page):
    login_page.enter_mobile_number(INVALID_MOBILE_NUMBER)
    assert login_page.is_visible(LoginPage.MOBILE_NUMBER_INPUT)
    assert not login_page.can_send_otp()
    assert not login_page.is_otp_page_displayed(timeout=2)


def test_help_button_opens_whatsapp(login_page, driver):
    login_page.open_whatsapp()
    WebDriverWait(driver, 10).until(
        lambda current_driver: "whatsapp" in current_driver.current_package.lower()
    )
    assert "whatsapp" in driver.current_package.lower()


def test_login_page_ui_elements_are_visible_and_on_screen(login_page, driver):
    window_size = driver.get_window_size()
    required_elements = (
        LoginPage.LOGIN_LOGO,
        LoginPage.MOBILE_NUMBER_INPUT,
        LoginPage.COUNTRY_CODE_BUTTON,
        LoginPage.CONTINUE_BUTTON,
        LoginPage.HELP_BUTTON,
    )
    for locator in required_elements:
        element = login_page.element(locator)
        assert element.is_displayed(), f"Element {locator} is not visible"
        assert login_page.is_element_within_screen(element, window_size), (
            f"Element {locator} is outside the visible screen"
        )


def test_mobile_number_field_opens_numeric_keyboard(login_page, driver):
    field = login_page.element(LoginPage.MOBILE_NUMBER_INPUT)
    field.click()
    assert driver.is_keyboard_shown(), "Keyboard was not displayed"
    assert_numeric_keyboard(driver)


@pytest.mark.sends_otp
def test_country_code_and_mobile_number_are_passed_to_otp_page(login_page):
    login_page.enter_mobile_number(VALID_MOBILE_NUMBER)
    login_page.tap_continue()
    assert login_page.is_otp_page_displayed()
    displayed_number = login_page.otp_mobile_number().replace(" ", "")
    assert DEFAULT_COUNTRY_CODE in displayed_number
    assert VALID_MOBILE_NUMBER in displayed_number
