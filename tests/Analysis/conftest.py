"""Shared authenticated Analysis setup; no session is opened without data."""
import json
import os
from pathlib import Path
import pytest
from appium.webdriver.common.appiumby import AppiumBy
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Analysis.effort_flow import EffortFlowPage


@pytest.fixture
def effort_data():
    path = os.getenv('EFFORT_UI_DATA')
    if not path or not Path(path).is_file():
        pytest.skip('Set EFFORT_UI_DATA to inspected Analysis/Effort Tracker selectors')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('ready'):
        if data.get('course_name'):
            flow = EffortFlowPage(None, data.get('flow_selectors', {}))
            flow.locator('selected_course')
            flow.validate(data.get('select_course_steps'))
    return data


@pytest.fixture
def analysis_driver(request, effort_data):
    if not effort_data.get('ready'):
        pytest.skip('Set ready=true after inspecting selectors on this app build')
    if effort_data.get('mobile_number') != os.getenv('TEST_MOBILE_NUMBER'):
        pytest.skip('EFFORT_UI_DATA mobile_number must match authorized TEST_MOBILE_NUMBER')
    driver = request.getfixturevalue('driver')
    login = LoginPage(driver)
    login.wait_until_loaded()
    login.enter_mobile_number(effort_data['mobile_number'])
    login.tap_continue()
    otp = OtpTypePage(driver)
    otp.wait_until_loaded()
    otp.enter_otp(os.environ['TEST_VALID_OTP'])
    # A newly signed-in account may enter onboarding and trigger Android's
    # notification permission prompt before Home is visible.
    def authenticated_or_onboarding(current):
        permission = current.find_elements(
            AppiumBy.ID, 'com.android.permissioncontroller:id/permission_allow_button'
        )
        if permission:
            permission[0].click()
        return (current.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Home')
                or current.find_elements(AppiumBy.ACCESSIBILITY_ID, 'ANALYSE')
                or current.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Skip'))

    otp.wait.until(authenticated_or_onboarding)
    skip = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Skip')
    if skip:
        skip[0].click()
    otp.element((AppiumBy.ACCESSIBILITY_ID, 'Home'))
    if effort_data.get('course_name'):
        flow = EffortFlowPage(driver, effort_data.get('flow_selectors', {}))
        flow.steps(effort_data.get('select_course_steps'))
        course = flow.element(flow.locator('selected_course'))
        label = course.get_attribute('content-desc') or course.get_attribute('text') or course.text or ''
        if effort_data['course_name'].casefold() not in label.casefold():
            raise AssertionError(f"Wrong course: expected {effort_data['course_name']!r}, found {label!r}")
    return driver
