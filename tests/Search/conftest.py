"""Shared authenticated session for the Home Search test module."""

import json
import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from appium.webdriver.common.appiumby import AppiumBy

from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Search.home_search_page import HomeSearchPage
from utils.app_state import ensure_logged_out
from utils.driver import create_driver
from utils.waits import Waits


DATA_PATH = Path(os.getenv(
    "SEARCH_TEST_DATA",
    Path(__file__).resolve().parents[2] / "test_data/search_ui.json",
))
SKIP_TUTORIAL = (AppiumBy.XPATH, "//*[@content-desc='Skip' or @content-desc='SKIP']")
NOTIFICATION_PERMISSION = (
    AppiumBy.ID,
    "com.android.permissioncontroller:id/permission_allow_button",
)
COURSE_SWITCHER = (AppiumBy.ACCESSIBILITY_ID, "Tap here to switch your course.")
EXPIRED_DISMISS = (AppiumBy.ACCESSIBILITY_ID, "Dismiss")


def _dismiss_tutorial(driver):
    tutorial = driver.find_elements(*SKIP_TUTORIAL)
    if tutorial:
        driver.execute_script("mobile: clickGesture", {"elementId": tutorial[0].id})
        Waits(driver, 10).until(lambda current: not current.find_elements(*SKIP_TUTORIAL))


def _select_course(driver, course_name):
    """Select the requested course once before any Search case executes."""
    dismiss = driver.find_elements(*EXPIRED_DISMISS)
    if dismiss:
        dismiss[0].click()

    current = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, course_name)
    if current:
        return

    Waits(driver, 15).clickable(COURSE_SWITCHER).click()
    target = (AppiumBy.ACCESSIBILITY_ID, course_name)
    Waits(driver, 15).clickable(target).click()
    Waits(driver, 25).until(
        lambda active: active.find_elements(AppiumBy.ACCESSIBILITY_ID, course_name)
        and active.find_elements(*HomeSearchPage.DEFAULTS["home_search"])
    )


@pytest.fixture(scope="session")
def search_data():
    if not DATA_PATH.is_file():
        pytest.skip(f"Provide SEARCH_TEST_DATA with inspected Search UI data: {DATA_PATH}")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    required = {"mobile_number", "placeholder", "valid_keyword", "partial_keyword",
                "invalid_keyword", "case_keyword", "subjects", "resources", "results"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"SEARCH_TEST_DATA is missing: {missing}")
    if data["mobile_number"] != os.getenv("TEST_MOBILE_NUMBER"):
        pytest.skip("TEST_MOBILE_NUMBER must match SEARCH_TEST_DATA mobile_number")
    return data


def _login_once(driver, data):
    """Authenticate once; every Search case inherits this session."""
    login = LoginPage(driver)
    login.wait_until_loaded()
    login.enter_mobile_number(data["mobile_number"])
    login.tap_continue()

    otp = OtpTypePage(driver)
    otp.wait_until_loaded()
    otp.enter_otp(os.environ["TEST_VALID_OTP"])

    home_search = HomeSearchPage.DEFAULTS["home_search"]
    Waits(driver, 25).until(lambda current: current.find_elements(*NOTIFICATION_PERMISSION)
                           or current.find_elements(*home_search)
                           or current.find_elements(*SKIP_TUTORIAL))

    permission = driver.find_elements(*NOTIFICATION_PERMISSION)
    if permission:
        permission[0].click()
        Waits(driver, 25).until(lambda current: current.find_elements(*home_search)
                               or current.find_elements(*SKIP_TUTORIAL))

    _dismiss_tutorial(driver)

    Waits(driver, 25).visible(home_search)
    _select_course(driver, data["course"])


@pytest.fixture(scope="module")
def authenticated_search(request, search_data):
    """Own the single driver/login used by all tests in this module."""
    driver = create_driver()
    request.node._appium_driver = driver
    try:
        # A new Appium session has already launched the configured activity.
        # Restarting it here is redundant and can fail while Flutter is still
        # completing startup, preventing the single-login setup from running.
        ensure_logged_out(driver)
        _login_once(driver, search_data)
        yield HomeSearchPage(driver, search_data.get("selectors"))
    finally:
        try:
            ensure_logged_out(driver)
        except Exception:
            pass
        finally:
            driver.quit()
            request.node._appium_driver = None


@pytest.fixture
def search_page(authenticated_search):
    """Give each case the inherited login, reset to the Home screen."""
    _dismiss_tutorial(authenticated_search.driver)
    authenticated_search.go_home()
    _dismiss_tutorial(authenticated_search.driver)
    return authenticated_search


@pytest.fixture
def search_network_controller(authenticated_search):
    """Temporarily disable networking and always restore its prior state."""
    class NetworkController:
        @contextmanager
        def offline(self):
            driver = authenticated_search.driver
            original = driver.network_connection
            try:
                driver.set_network_connection(0)
                yield
            finally:
                driver.set_network_connection(original)

    return NetworkController()
