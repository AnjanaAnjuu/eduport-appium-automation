"""Screenshot-derived My Course / Active cases (Android, one enrollment).

Run: venv/bin/python -m pytest tests/Profile/mycourse/test_active_subscription.py

Live setup: set MYCOURSE_ACTIVE_DATA to a JSON file with:
  selectors: all MycourseSubscriptionActivePage.REQUIRED_SELECTORS plus route
    targets; values are [strategy, value] or {"locator": [...], "attribute":
    "content-desc"} for Flutter text. Card field selectors must be relative.
  open_route: nonempty list of selector names from Home to My Course.
  cleanup_route: nonempty list returning from any tested destination to Home.
  selected_attribute: actual inspected tab selection attribute (default selected).
  expected: {"course": "...", "batch": "...", "expiry": "...", "status": "Active"}.
  expiry_format: "%d %b %Y"; expiry_pattern: "\\d{2} [A-Z][a-z]{2} \\d{4}".

Use an existing, independently prepared account with exactly one active
subscription. Set TEST_MOBILE_NUMBER, ALLOW_OTP_SEND=true and TEST_VALID_OTP,
following the project's existing SMS controls. Each test authenticates afresh,
so the OTP must be valid for each login (e.g. a supported staging OTP).

The screenshot's 28 Aug 2026 expiry is historical; it is reference content,
not a claim that this enrollment is still active. Supply current seed values,
or use a controlled historical environment for exact screenshot reproduction.
These tests check semantic text and element geometry, not pixel-perfect colors.
"""
from datetime import datetime
import re

import pytest

from pages.Profile.mycourse.active_subscription_page import (
    ActiveSubscription,
)

pytestmark = [pytest.mark.sends_otp, pytest.mark.requires_valid_otp]


def test_tc_004_single_active_card(active_page, active_data):
    assert active_page.subscription() == ActiveSubscription(**active_data['expected'])


def test_tc_005_course_name(active_page, active_data):
    assert active_page.subscription().course == active_data['expected']['course']


def test_tc_006_batch_name(active_page, active_data):
    assert active_page.subscription().batch == active_data['expected']['batch']


def test_tc_007_active_status_badge(active_page):
    assert active_page.subscription().status == 'Active'


def test_tc_008_expiry_label(active_page):
    assert active_page.text('expiry_label', active_page.card()) == 'Expiry'


def test_tc_009_expiry_value(active_page, active_data):
    assert active_page.subscription().expiry == active_data['expected']['expiry']


def test_tc_010_expiry_date_format(active_page, active_data):
    value = active_page.subscription().expiry
    assert re.fullmatch(active_data['expiry_pattern'], value)
    datetime.strptime(value, active_data['expiry_format'])


def test_tc_011_expired_tab_navigation(active_page):
    active_page.select_expired()
    assert not active_page.tab_selected('active_tab')


def test_tc_012_return_to_active_tab(active_page, active_data):
    active_page.select_expired()
    active_page.select_active()
    assert not active_page.tab_selected('expired_tab')
    assert active_page.subscription() == ActiveSubscription(**active_data['expected'])


def test_tc_013_reselect_active_preserves_card(active_page, active_data):
    active_page.select_active()
    active_page.select_active()
    assert active_page.subscription() == ActiveSubscription(**active_data['expected'])


def test_tc_014_help_navigation(active_page):
    assert active_page.text('help') == 'Help'
    active_page.open_help()


def test_tc_015_back_navigation(active_page):
    active_page.go_back()


def test_tc_016_screen_elements_within_viewport(active_page):
    active_page.assert_in_bounds(('title', 'back', 'help', 'active_tab', 'expired_tab', 'card'))


def test_tc_017_course_details_within_card(active_page):
    active_page.assert_in_bounds(('course', 'batch', 'status', 'expiry_label', 'expiry'), active_page.card())


def test_tc_018_card_vertical_text_order(active_page):
    card = active_page.card()
    fields = [active_page.target(name, card).rect for name in ('course', 'batch', 'expiry_label', 'expiry')]
    for upper, lower in zip(fields, fields[1:]):
        assert upper['y'] + upper['height'] <= lower['y'], 'Card text rows overlap or are out of order'


def test_tc_019_header_controls_are_actionable(active_page):
    for name in ('back', 'help', 'active_tab', 'expired_tab'):
        element = active_page.wait.clickable(active_page.locator(name))
        assert element.is_displayed() and element.is_enabled()
