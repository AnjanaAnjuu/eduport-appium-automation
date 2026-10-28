import os
import warnings

import pytest

from config.config import settings
from utils.app_state import ensure_logged_out
from utils.driver import create_driver
from utils.screenshots import take_screenshot
from utils.signup_support import SignupPrerequisiteMissing, SignupStagingClient


def pytest_collection_modifyitems(items):
    """Gate real SMS requests before any Appium session is created."""
    for item in items:
        credentials = getattr(item.module, 'TEST_CREDENTIALS', {})
        item_allow_send = os.getenv('ALLOW_OTP_SEND', str(credentials.get('ALLOW_OTP_SEND', 'false'))).lower() == 'true'
        item_mobile = os.getenv('TEST_MOBILE_NUMBER', credentials.get('TEST_MOBILE_NUMBER', '')).strip()
        item_otp = os.getenv('TEST_VALID_OTP', credentials.get('TEST_VALID_OTP', ''))
        if item.get_closest_marker("signup") and os.getenv("ALLOW_SIGNUP_TESTS", "false").lower() != "true":
            item.add_marker(pytest.mark.skip(
                reason="Signup changes onboarding state; configure staging prerequisites and set ALLOW_SIGNUP_TESTS=true"
            ))
        if item.get_closest_marker("coin_quiz") and os.getenv("ALLOW_COIN_TESTS", "false").lower() != "true":
            item.add_marker(pytest.mark.skip(
                reason="Coin/quiz actions change account state; configure staging data and set ALLOW_COIN_TESTS=true"
            ))
        if item.get_closest_marker("sends_otp") and not (item_allow_send and item_mobile):
            item.add_marker(pytest.mark.skip(
                reason="Requires authorized TEST_MOBILE_NUMBER and ALLOW_OTP_SEND=true"
            ))
        if item.get_closest_marker("requires_valid_otp") and not item_otp:
            item.add_marker(pytest.mark.skip(reason="Requires TEST_VALID_OTP"))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed and report.when in {"setup", "call"}:
        appium_driver = (item.funcargs.get("driver") or item.funcargs.get("study_driver")
                         or getattr(item, "_appium_driver", None))
        if appium_driver is not None:
            try:
                path = take_screenshot(appium_driver, item.nodeid)
                item.user_properties.append(("screenshot", str(path)))
            except Exception as error:
                warnings.warn(f"Screenshot capture failed: {error}", RuntimeWarning)


@pytest.fixture(scope="function")
def driver(request):
    """Restart the app for each case; never reuse another test's UI state."""
    appium_driver = create_driver()
    request.node._appium_driver = appium_driver
    try:
        appium_driver.terminate_app(settings.app_package, timeout=5000)
        appium_driver.activate_app(settings.app_package)
        ensure_logged_out(appium_driver)
        yield appium_driver
    finally:
        try:
            if request.node.get_closest_marker("requires_valid_otp"):
                ensure_logged_out(appium_driver)
        finally:
            try:
                appium_driver.quit()
            finally:
                request.node._appium_driver = None


@pytest.fixture
def signup_prepare_account(request):
    """Snapshot, prepare and restore only an explicitly approved staging phone."""
    data = request.getfixturevalue('signup_data')
    try:
        client = SignupStagingClient(data, ('snapshot', 'prepare', 'restore'))
    except SignupPrerequisiteMissing as error:
        pytest.skip(str(error))
    restore_tokens = []

    def prepare(mobile_number, sup_id):
        if mobile_number != data['mobile_number']:
            raise ValueError('Refusing to prepare another signup phone')
        token = client.snapshot()
        restore_tokens.append(token)  # Restore even if the following preparation fails.
        client.prepare(sup_id)

    try:
        yield prepare
    finally:
        for token in reversed(restore_tokens):
            client.restore(token)


@pytest.fixture
def signup_submission_probe(request):
    """Read actual staging counters; no tap-count or navigation guesses."""
    data = request.getfixturevalue('signup_data')
    try:
        client = SignupStagingClient(data, ('probe',))
    except SignupPrerequisiteMissing as error:
        pytest.skip(str(error))

    def probe(mobile_number):
        if mobile_number != data['mobile_number']:
            raise ValueError('Refusing to probe another signup phone')
        result = client.probe()
        return {key: result[key] for key in ('successful_submissions', 'course_navigations', 'profiles_created')}

    return probe
