"""Read-only emulator support for the supplied existing accounts.

Empty-state observations must not be turned into invented enrollment records.
Populated-card checks continue to require the original independent data setup.
"""
import os
import re
import json
from pathlib import Path
from contextlib import contextmanager

from appium.webdriver.common.appiumby import AppiumBy
import pytest
from selenium.webdriver.support.ui import WebDriverWait

from config.config import settings
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Profile.mycourse.mycourse_page import MyCoursePage
from pages.Profile.mycourse.active_subscription_page import MycourseSubscriptionActivePage
from pages.Profile.mycourse.expired_subscription_page import MycourseSubscriptionExpiredPage
from pages.Profile.mycourse.no_subscription_page import MycourseNoSubscriptionPage
from utils.app_state import ensure_logged_out
from utils.driver import create_driver


def live_data():
    return json.loads((Path(__file__).resolve().parents[3] / 'test_data' / 'mycourse_live.json').read_text())


def scroll_profile(driver, direction):
    size = driver.get_window_size()
    driver.execute_script('mobile: swipeGesture', {
        'left': 40, 'top': 400, 'width': size['width'] - 80,
        'height': int(size['height'] * .6), 'direction': direction,
        'percent': .2, 'speed': 300,
    })


class CourseSession:
    def __init__(self):
        self.driver = create_driver(no_reset=True)
        self.phone = os.environ['TEST_MOBILE_NUMBER']

    def profile(self):
        d = self.driver
        for _ in range(8):
            if d.find_elements(AppiumBy.XPATH, "//android.view.View[@content-desc='Profile']"):
                return True
            if d.find_elements(*LoginPage.CONTINUE_BUTTON) or d.find_elements(*OtpTypePage.SCREEN) or d.find_elements(AppiumBy.ID, 'com.google.android.gms:id/cancel'):
                return False
            tabs = d.find_elements(AppiumBy.XPATH, "//android.widget.ImageView[@content-desc='Profile']")
            if tabs:
                tabs[0].click()
            else:
                d.back()
        raise AssertionError('Could not return to Profile from the current app screen')

    def owner(self):
        d = self.driver
        for _ in range(15):
            for label in d.find_elements(AppiumBy.XPATH, '//*[@content-desc]'):
                text = label.get_attribute('content-desc') or ''
                if re.fullmatch(r'(?:\+?91\s*)?\d{10}', text.strip()):
                    return re.sub(r'\D', '', text)[-10:]
            scroll_profile(d, 'down')
        raise AssertionError('Cannot verify the signed-in phone number on Profile')

    def authenticate(self):
        d = self.driver
        d.activate_app(settings.app_package)
        WebDriverWait(d, 25).until(lambda driver: driver.find_elements(AppiumBy.XPATH,
            "//*[@content-desc='Profile' or @content-desc='Home' or @content-desc='My Course' "
            "or @content-desc='Reach Us' or @content-desc='Send OTP' or @content-desc='OTP Verifications' "
            "or @content-desc='Enter Your Details' "
            "or @resource-id='com.google.android.gms:id/cancel']"))
        self.require_completed_profile()
        if self.profile():
            if self.owner() == self.phone:
                return
            ensure_logged_out(d)
        if d.find_elements(*OtpTypePage.SCREEN):
            d.back()
        login = LoginPage(d, timeout=25)
        login.wait_until_loaded()
        login.enter_mobile_number(self.phone)
        login.tap_continue()
        otp = OtpTypePage(d, timeout=25)
        otp.wait_until_loaded()
        otp.enter_otp(os.environ['TEST_VALID_OTP'])
        def authenticated(driver):
            self.require_completed_profile()
            deny = driver.find_elements(AppiumBy.ID, 'com.android.permissioncontroller:id/permission_deny_button')
            if deny:
                deny[0].click()
            return driver.find_elements(*OtpTypePage.VERIFIED_SCREEN)
        otp.wait.until(authenticated, 'OTP did not reach Home')
        assert self.profile()
        assert self.owner() == self.phone, 'Authenticated account differs from the requested account'

    def require_completed_profile(self):
        if self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Enter Your Details'):
            pytest.skip(
                'Account onboarding is incomplete: the app shows Enter Your Details and requires a full name '
                'and gender before Home/Profile can be opened. Complete this profile or supply an already '
                'onboarded no-course account. No My Course test assertions executed.'
            )

    def open(self):
        assert self.profile(), 'The test session is no longer authenticated'
        d = self.driver
        for _ in range(15):
            entries = d.find_elements(AppiumBy.ACCESSIBILITY_ID, 'My Courses')
            if entries and entries[0].is_displayed():
                d.execute_script('mobile: clickGesture', {'elementId': entries[0].id})
                WebDriverWait(d, 20).until(lambda x: x.find_elements(AppiumBy.ACCESSIBILITY_ID, 'My Course'))
                return
            scroll_profile(d, 'up')
        raise AssertionError('My Courses was not found by scrolling Profile')

    @contextmanager
    def page(self, request, page_class, data, tab='active'):
        request.node._appium_driver = self.driver
        try:
            self.open()
            page = page_class(self.driver, data['selectors'])
            page.wait_loaded()
            if tab == 'expired':
                page.select_expired()
            yield page
        finally:
            try:
                self.profile()
            finally:
                request.node._appium_driver = None


class LiveCourseMixin:
    def require_card(self, tab):
        if self.is_visible(self.locator(f'{tab}_empty'), 1):
            raise AssertionError(
                f"Account {os.environ['TEST_MOBILE_NUMBER']} shows '{self.text(f'{tab}_empty')}' "
                f"on the {tab.title()} tab; this case requires a {tab} subscription. "
                'Verify the account enrollment/backend data.'
            )
        pytest.skip('A populated card needs inspected card selectors and independent expected enrollment records; configure the original staging data file')

    def select_tab(self, tab):
        self.tap(f'{tab}_tab')
        self.wait.until(lambda _: self.tab_selected(f'{tab}_tab'))
        self.target(f'{tab}_content')


class LiveActivePage(LiveCourseMixin, MycourseSubscriptionActivePage):
    REQUIRED_SELECTORS = MyCoursePage.REQUIRED_SELECTORS + ('active_empty', 'expired_empty', 'active_content', 'expired_content', 'previous_screen', 'help_screen')

    def card(self):
        return self.require_card('active')

    def target(self, name, root=None):
        if name == 'card':
            return self.card()
        return super().target(name, root)

    def select_active(self):
        self.select_tab('active')
        self.card()

    def select_expired(self):
        self.select_tab('expired')


class LiveExpiredPage(LiveCourseMixin, MycourseSubscriptionExpiredPage):
    REQUIRED_SELECTORS = LiveActivePage.REQUIRED_SELECTORS


class LiveEmptyPage(MycourseNoSubscriptionPage):
    REQUIRED_SELECTORS = MyCoursePage.REQUIRED_SELECTORS + (
        'active_content', 'expired_content', 'active_empty', 'expired_empty',
        'empty_illustration', 'empty_message', 'missing_subscription', 'contact_us',
        'contact_screen', 'help_screen', 'previous_screen',
    )

    def wait_active_empty(self):
        self.target('active_content')
        for name in self.EMPTY_TARGETS:
            self.target(name)

    def assert_no_cards(self):
        tab = 'active' if self.tab_selected('active_tab') else 'expired'
        panel = self.target(f'{tab}_content')
        # Inspect the entire tab panel, not just the empty-message wrapper.
        expected = {f'Your {tab} subscriptions will appear here.', self.MISSING_MESSAGE, self.CONTACT_LABEL}
        actual = {e.get_attribute('content-desc') for e in panel.find_elements(AppiumBy.XPATH, './/*[@content-desc]')}
        assert actual == expected, f'Expected only the empty-state controls; found {sorted(actual)}'
        assert len(panel.find_elements(AppiumBy.CLASS_NAME, 'android.widget.ImageView')) == 1, 'Unexpected content alongside the empty-state illustration'

    def select_expired(self):
        self.tap('expired_tab')
        self.wait.until(lambda _: self.tab_selected('expired_tab') and not self.tab_selected('active_tab'))
        self.target('expired_content')
        self.target('expired_empty')
