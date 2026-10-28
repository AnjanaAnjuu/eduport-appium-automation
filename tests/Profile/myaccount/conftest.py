"""UI-only isolation for cases which never submit account changes."""
from contextlib import contextmanager
import os
import re

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
import pytest
from selenium.webdriver.support.ui import WebDriverWait

from config.config import settings
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Profile.myaccount.myaccount_page import MyAccountPage


class LiveAccount:
    def __init__(self, driver):
        self.driver = driver
        self.baseline = None

    def close_sheets(self):
        d = self.driver
        if d.is_keyboard_shown():
            d.hide_keyboard()
        for _ in range(4):
            picker_locator = (AppiumBy.XPATH, "//*[starts-with(@content-desc, 'Select ')]")
            if d.find_elements(*picker_locator):
                d.back()
                WebDriverWait(d, 10).until(lambda driver: not driver.find_elements(*picker_locator))
                continue
            discard = d.find_elements(AppiumBy.ACCESSIBILITY_ID, "DON'T SAVE & EXIT")
            if discard:
                d.execute_script('mobile: clickGesture', {'elementId': discard[0].id})
                return
            return
        raise AssertionError('Could not close account picker/sheet')

    @contextmanager
    def prepare(self, request, data, case):
        d = self.driver
        page = MyAccountPage(d, data)
        self.close_sheets()
        page.route('profile')
        # Verify the signed-in owner before any test edits.
        for _ in range(15):
            labels = d.find_elements(AppiumBy.XPATH, '//*[@content-desc]')
            if any(re.sub(r'\D', '', e.get_attribute('content-desc') or '').endswith(data['mobile_number'])
                   for e in labels):
                break
            page.scroll_profile('down')
        else:
            raise AssertionError('Profile does not show the authorized mobile number')
        page.open()
        current = page.details()
        if self.baseline is None:
            self.baseline = current
        assert current == self.baseline, 'Account baseline changed between cases'
        case['baseline'] = dict(self.baseline)
        case['_page'] = page
        request.node._appium_driver = d
        try:
            yield
        finally:
            try:
                self.close_sheets()
                page.route('profile')
                page.open()
                assert page.details() == self.baseline, 'Discard did not restore original account values'
                self.close_sheets()
            finally:
                request.node._appium_driver = None


@pytest.fixture(scope='module')
def myaccount_live(request):
    credentials = request.module.TEST_CREDENTIALS
    phone = os.getenv('TEST_MOBILE_NUMBER', credentials.get('TEST_MOBILE_NUMBER', ''))
    otp_value = os.getenv('TEST_VALID_OTP', credentials.get('TEST_VALID_OTP', ''))
    options = UiAutomator2Options()
    options.platform_name = 'Android'
    options.automation_name = 'UiAutomator2'
    options.device_name = settings.device_name
    options.app_package = settings.app_package
    options.app_activity = settings.app_activity
    options.no_reset = True
    if settings.udid:
        options.udid = settings.udid
    if settings.platform_version:
        options.platform_version = settings.platform_version
    d = webdriver.Remote(settings.appium_server_url, options=options)
    live = LiveAccount(d)
    try:
        d.activate_app(settings.app_package)
        login = LoginPage(d, timeout=25)
        login.wait.until(lambda x: x.find_elements(AppiumBy.XPATH,
            "//*[@content-desc='Profile' or @content-desc='Home' or @content-desc='My Account' "
            "or @content-desc='Send OTP' or @content-desc='OTP Verifications' "
            "or starts-with(@content-desc,'Select ') or @resource-id='com.google.android.gms:id/cancel']"))
        if d.find_elements(*LoginPage.CONTINUE_BUTTON) or d.find_elements(AppiumBy.ID, 'com.google.android.gms:id/cancel'):
            login.wait_until_loaded()
            login.enter_mobile_number(phone)
            login.tap_continue()
        if d.find_elements(*OtpTypePage.SCREEN) or not d.find_elements(AppiumBy.XPATH,
                "//*[@content-desc='Profile' or @content-desc='Home' or @content-desc='My Account' or starts-with(@content-desc,'Select ')]"):
            otp = OtpTypePage(d, timeout=25)
            otp.wait_until_loaded()
            otp.enter_otp(otp_value)
            def authenticated(driver):
                deny = driver.find_elements(AppiumBy.ID, 'com.android.permissioncontroller:id/permission_deny_button')
                if deny:
                    deny[0].click()
                return driver.find_elements(*OtpTypePage.VERIFIED_SCREEN)
            otp.wait.until(authenticated, 'OTP did not reach Home')
        yield live
    finally:
        try:
            live.close_sheets()
        finally:
            d.quit()
