"""ONB-01–ONB-04: onboarding after new and existing-user authentication.

The ``authenticated_onboarding`` fixture is intentionally supplied by the
staging environment.  It must reset onboarding state, authenticate the
requested account type, and return a driver positioned on onboarding page 1.
This avoids creating accounts or consuming OTPs without an approved reset.
"""

import os

import pytest

from pages.Login.login_page import LoginPage
from pages.Login.onboarding_page import OnboardingPage
from pages.Login.otp_page import OtpTypePage
from pages.Login.signup_page import SignupPage


pytestmark = [pytest.mark.onboarding, pytest.mark.sends_otp, pytest.mark.requires_valid_otp]


@pytest.fixture
def authenticated_onboarding(driver):
    """Authenticate the requested staging account and stop on onboarding."""
    def authenticate(user_type):
        env_key = "ONBOARDING_NEW_NUMBER" if user_type == "new" else "ONBOARDING_EXISTING_NUMBER"
        number = os.getenv(env_key)
        otp = os.getenv("TEST_VALID_OTP")
        if not number or not otp:
            pytest.skip(f"Set {env_key} and TEST_VALID_OTP")

        login = LoginPage(driver)
        login.wait_until_loaded()
        login.enter_mobile_number(number)
        login.tap_continue()
        otp_page = OtpTypePage(driver)
        otp_page.wait_until_loaded()
        otp_page.enter_otp(otp)

        if user_type == "new":
            signup = SignupPage(driver)
            if signup.is_displayed():
                signup.wait_until_loaded()
                signup.enter_name(os.getenv("ONBOARDING_NEW_NAME", "Appium Test User"))
                signup.select_gender(os.getenv("ONBOARDING_NEW_GENDER", "Female"))
                signup.wait_gender_selected(os.getenv("ONBOARDING_NEW_GENDER", "Female"))
                signup.save()
        return driver

    return authenticate


def _onboarding_page(request, user_type):
    try:
        factory = request.getfixturevalue("authenticated_onboarding")
    except pytest.FixtureLookupError:
        pytest.skip(
            "Provide authenticated_onboarding(user_type), backed by an approved "
            "staging reset, to run onboarding tests"
        )
    if not callable(factory):
        raise TypeError("authenticated_onboarding must return a callable")
    page = OnboardingPage(factory(user_type))
    page.wait_until_loaded()
    assert page.current_page() == 1
    return page


@pytest.mark.parametrize("user_type", ["new", "existing"])
def test_onb01_skip_on_first_page_opens_home(request, user_type):
    page = _onboarding_page(request, user_type)
    page.tap_skip()
    assert page.is_home_displayed()


@pytest.mark.parametrize("user_type", ["new", "existing"])
def test_onb02_four_pages_load_in_order_then_open_home(request, user_type):
    page = _onboarding_page(request, user_type)
    assert page.complete_all_pages() == [1, 2, 3, 4]
    assert page.is_home_displayed()


@pytest.mark.parametrize("user_type", ["new", "existing"])
def test_onb03_skip_is_available_on_first_page(request, user_type):
    page = _onboarding_page(request, user_type)
    skip = page.element(OnboardingPage.SKIP_BUTTON)
    assert skip.is_displayed()
    assert skip.get_attribute("clickable") == "true"


@pytest.mark.parametrize("user_type", ["new", "existing"])
def test_onb04_each_page_is_visible_before_advancing(request, user_type):
    page = _onboarding_page(request, user_type)
    for expected in range(1, 5):
        page.wait_for_page(expected)
        assert page.is_page_displayed(expected)
        assert page.current_page() == expected
