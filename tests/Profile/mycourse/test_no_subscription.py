"""MC_NONE_001–015: screenshot-derived My Course no-subscription tests.

Run: venv/bin/python -m pytest tests/Profile/mycourse/test_no_subscription.py

Live configuration:
Set MYCOURSE_NO_SUBSCRIPTION_DATA to a JSON file containing:
- selectors: every MycourseNoSubscriptionPage.REQUIRED_SELECTORS name plus
  route targets. Use [strategy, value] or {"locator": [strategy, value],
  "attribute": "content-desc"} for Flutter labels. Inspect selectors on-device;
  the screenshot does not reveal IDs or destination screens. card must match
  real enrollment cards in the selected tab, not the empty-state illustration.
  active_content / expired_content must identify the respective selected panel.
  contact_screen / help_screen must identify the confirmed destination, not the
  originating button. Contact Us tests open support UI without sending messages.
- open_route: nonempty list of selector names from authenticated Home to My Course.
- cleanup_route: nonempty list of selector names returning from every tested
  destination (including Help, Contact Us and Back) to Home before shared logout.
- selected_attribute: inspected tab-selection attribute (default: selected).
- mobile_number: the prepared account, matching TEST_MOBILE_NUMBER.
- enrollments: [] from independent account preparation, not read from the UI.

Example shape (populate selectors and routes before running):
  {"selectors": {}, "open_route": [], "cleanup_route": [],
   "mobile_number": "STAGING_NUMBER", "enrollments": []}

Use an existing staging account without any active or expired enrollments.
Set ALLOW_OTP_SEND=true, TEST_MOBILE_NUMBER and TEST_VALID_OTP, following existing
project controls. Each case authenticates independently; use a supported staging
OTP valid for each login. Missing configuration skips before driver creation.
The image shows the Active empty state; no expired-tab wording, contact options
or external-app behavior is invented. Geometry checks do not verify pixel colors
or the exact illustration artwork.
"""
import json
import os
from pathlib import Path

import pytest

from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Profile.mycourse.no_subscription_page import MycourseNoSubscriptionPage

pytestmark = [pytest.mark.sends_otp, pytest.mark.requires_valid_otp]


@pytest.fixture(scope='module')
def no_subscription_data():
    path = os.getenv('MYCOURSE_NO_SUBSCRIPTION_DATA')
    if not path:
        pytest.skip('Set MYCOURSE_NO_SUBSCRIPTION_DATA with inspected selectors and a prepared empty account')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    assert data['enrollments'] == [], 'Prepare an account without active or expired enrollments'
    assert data['mobile_number'] == os.environ['TEST_MOBILE_NUMBER'], 'Configured account differs from login account'
    validator = MycourseNoSubscriptionPage(None, data['selectors'])
    for route in ('open_route', 'cleanup_route'):
        assert isinstance(data.get(route), list) and data[route], f'Configure nonempty {route}'
        for name in data[route]:
            validator.locator(name)
    return data


@pytest.fixture
def no_subscription_page(request, no_subscription_data):
    data = no_subscription_data
    driver = request.getfixturevalue('driver')
    page = MycourseNoSubscriptionPage(
        driver, data['selectors'], data.get('selected_attribute', 'selected'),
    )
    authenticated = False
    try:
        login = LoginPage(driver)
        login.wait_until_loaded()
        login.enter_mobile_number(data['mobile_number'])
        login.tap_continue()
        otp = OtpTypePage(driver)
        otp.wait_until_loaded()
        otp.enter_otp(os.environ['TEST_VALID_OTP'])
        assert otp.is_verified(timeout=20), 'Login failed'
        authenticated = True
        page.navigate(data['open_route'])
        page.wait_loaded()
        yield page
    finally:
        if authenticated:
            page.navigate(data['cleanup_route'])


def test_mc_none_001_my_course_header(no_subscription_page):
    """My Course title, Back and Help are displayed."""
    page = no_subscription_page
    assert page.normalized_text('title') == 'My Course'
    assert page.normalized_text('help') == 'Help'
    page.target('back')


def test_mc_none_002_active_selected_by_default(no_subscription_page):
    """Active is selected by default; Expired is not selected."""
    assert no_subscription_page.tab_selected('active_tab')
    assert not no_subscription_page.tab_selected('expired_tab')


def test_mc_none_003_tab_labels(no_subscription_page):
    assert no_subscription_page.normalized_text('active_tab') == 'Active'
    assert no_subscription_page.normalized_text('expired_tab') == 'Expired'


def test_mc_none_004_empty_illustration_visible(no_subscription_page):
    """The empty-state illustration is visible and within the viewport."""
    no_subscription_page.assert_in_bounds(('empty_illustration',))


def test_mc_none_005_active_empty_message(no_subscription_page):
    """Message matches screenshot wording, regardless of line wrapping."""
    assert no_subscription_page.normalized_text('empty_message') == 'Your active subscriptions will appear here.'


def test_mc_none_006_missing_subscription_prompt(no_subscription_page):
    assert no_subscription_page.normalized_text('missing_subscription') == 'Not seeing your subscription?'


def test_mc_none_007_contact_us_button(no_subscription_page):
    page = no_subscription_page
    assert page.normalized_text('contact_us') == 'Contact Us'
    page.wait.clickable(page.locator('contact_us'))


def test_mc_none_008_no_active_subscription_cards(no_subscription_page):
    no_subscription_page.assert_no_cards()


def test_mc_none_009_contact_us_navigation(no_subscription_page):
    """Contact Us opens the confirmed support destination."""
    no_subscription_page.open_contact_us()


def test_mc_none_010_help_navigation(no_subscription_page):
    no_subscription_page.open_help()


def test_mc_none_011_expired_tab_navigation(no_subscription_page):
    """Expired is selected and has no cards for this zero-enrollment account."""
    no_subscription_page.select_expired()
    no_subscription_page.assert_no_cards()


def test_mc_none_012_return_to_active_empty_state(no_subscription_page):
    no_subscription_page.select_expired()
    no_subscription_page.select_active()
    no_subscription_page.assert_active_empty()


def test_mc_none_013_reselect_active(no_subscription_page):
    """Reselecting Active preserves the complete empty state."""
    no_subscription_page.select_active()
    no_subscription_page.assert_active_empty()


def test_mc_none_014_back_navigation(no_subscription_page):
    no_subscription_page.go_back()


def test_mc_none_015_empty_state_layout(no_subscription_page):
    """Controls fit on-screen; illustration, text, prompt and CTA do not overlap."""
    page = no_subscription_page
    page.assert_in_bounds(('title', 'back', 'help', 'active_tab', 'expired_tab'))
    page.assert_empty_layout()
