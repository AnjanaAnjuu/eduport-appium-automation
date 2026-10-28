"""Splash-flow tests for Eduport Appium automation."""
from __future__ import annotations
import os
import pytest
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Login.splash_page import SplashPage


def perform_login(driver, number: str, otp: str) -> None:
    """Log in through the app's existing page objects; OTP auto-submits."""
    login = LoginPage(driver)
    login.wait_until_loaded()
    login.enter_mobile_number(number)
    login.tap_continue()

    otp_page = OtpTypePage(driver)
    otp_page.wait_until_loaded()
    otp_page.enter_otp(otp)


@pytest.mark.splash
def test_existing_user_sees_splash_before_onboarding(driver):
    """TC_SPLASH_001: Login -> splash appears -> splash disappears -> onboarding."""
    number = os.getenv("LOGIN_NUMBER")
    otp = os.getenv("LOGIN_OTP")
    if not number or not otp:
        pytest.skip("Set LOGIN_NUMBER and LOGIN_OTP before running this test.")

    perform_login(driver, number, otp)
    SplashPage(driver).verify_splash_flow()


@pytest.mark.splash
def test_app_does_not_get_stuck_on_splash(driver):
    """TC_SPLASH_002: Verify splash disappears within the allowed time."""
    number = os.getenv("LOGIN_NUMBER")
    otp = os.getenv("LOGIN_OTP")
    if not number or not otp:
        pytest.skip("Set LOGIN_NUMBER and LOGIN_OTP before running this test.")

    perform_login(driver, number, otp)
    page = SplashPage(driver)
    page.wait_until_splash_appears(timeout=3.0)
    page.wait_until_splash_disappears(timeout=8.0)
    page.wait_for_onboarding(timeout=12.0)
