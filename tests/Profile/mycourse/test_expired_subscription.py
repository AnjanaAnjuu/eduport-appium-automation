"""MC_EXP_001–018; the repeated subject-wise row is covered once, by 013.

Reference image: WhatsApp Image 2026-08-27 at 17.05.18 (2).jpeg.
Expected reference text is in the page object's SCREENSHOT_SUBSCRIPTION.
No image-derived Appium selectors or purchase destination are assumed.

Run: venv/bin/python -m pytest tests/Profile/mycourse/test_expired_subscription.py

Set MYCOURSE_EXPIRED_DATA to a JSON file containing:
- selectors: page REQUIRED_SELECTORS and navigation targets, as [strategy, value]
  or {"locator": [strategy, value], "attribute": "content-desc"} for Flutter.
  Field and renew_now XPath locators must start with '.' and be card-relative.
  card/list_region must select only the current tab's list. Content markers
  must identify the actual tab panel; empty markers must be its actual empty UI.
  renewal_screen is additionally required for 008, at the confirmed destination.
- open_route / cleanup_route: nonempty lists of selector names to tap, from
  authenticated Home to My Course, and from any tested destination back to Home.
- selected_attribute: inspected tab-selection attribute; default 'selected'.
- cases: keyed MC_EXP_001 ... MC_EXP_018, each with ready:true, enrollments:[...].
  Each enrollment has course, batch, expiry, status ('Active'/'Expired'),
  subject and sticker (empty strings when absent), course_state
  ('available'/'archived'/'unavailable'), and sticker_visible (boolean).
  These describe independent seed data. Example reference enrollment:
    {"course":"Class 10 CBSE (Tuition) 2026-27",
     "batch":"Class 10 CBSE (Tuition) 2026-27_B11", "expiry":"17 Jul 2026",
     "status":"Expired", "subject":"", "sticker":"",
     "course_state":"available", "sticker_visible":false}
  Use unique course/batch/subject tuples; overlapping scroll results are merged
  by that key. Configure max_scrolls if lists exceed the default 50 gestures.
  014 additionally needs sticker_rule documenting the approved visibility rule.
- prepared_case_id: for a manually prepared single scenario, its MC_EXP ID.
  For running all scenarios, implement mycourse_expired_prepare as a pytest
  fixture returning a context manager factory (case_id, case, data). It must
  snapshot, independently seed and restore an authorized staging account, even
  after test failures. Absent setup skips before requesting an Appium driver.

Android login reuses project fixtures. Set TEST_MOBILE_NUMBER,
ALLOW_OTP_SEND=true and TEST_VALID_OTP. The preparation must target this account;
use a supported staging OTP valid for each independent login. No test completes
checkout. Screenshot text is reference seed data, not a live account assumption.
Visual colors are not asserted from native text/geometry alone.
"""
from contextlib import nullcontext
import json
import os
from pathlib import Path
import re

import pytest

from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Profile.mycourse.expired_subscription_page import MycourseSubscriptionExpiredPage
from tests.Profile.mycourse.live_support import live_data, LiveExpiredPage

pytestmark = [pytest.mark.sends_otp, pytest.mark.requires_valid_otp]
CRITICAL = {2, 7, 8, 9, 10, 11, 12, 15, 16}


@pytest.fixture
def expired_case(request):
    path = os.getenv('MYCOURSE_EXPIRED_DATA')
    if not path:
        data = live_data()
        case_id = re.search(r'mc_exp_\d{3}', request.node.name).group().upper()
        number = int(case_id[-3:])
        request.node.user_properties.append(('tc_id', case_id))
        reasons = {
            9: 'Needs an independently prepared archived expired enrollment to verify exclusion.',
            10: 'Needs an independently prepared unavailable expired enrollment to verify exclusion.',
            11: 'Needs at least two known expired enrollments and independent expected records.',
            12: 'Needs known active, expired, archived, and unavailable enrollments in one prepared scenario.',
            13: 'Needs a known subject-wise expired enrollment and its expected subject.',
            14: 'Needs a Continuous-sticker enrollment and the confirmed sticker visibility rule.',
            15: 'Needs known archived/unavailable-only records; an empty screen alone does not prove exclusion.',
            16: 'Needs an independently verified active-only enrollment scenario.',
            17: 'Needs independent expected records for both populated Active and Expired lists.',
        }
        if number in reasons:
            pytest.skip(reasons[number])
        yield data, {'mode': 'live_existing_account'}
        return
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    case_id = re.search(r'mc_exp_\d{3}', request.node.name).group().upper()
    case = data.get('cases', {}).get(case_id)
    if not case or not case.get('ready'):
        pytest.skip(f'{case_id}: prepare the scenario and set ready=true')
    number = int(case_id[-3:])
    request.node.user_properties.extend([
        ('tc_id', case_id),
        ('priority', 'Critical' if number in CRITICAL else 'Medium' if number in {14, 18} else 'High'),
    ])
    validator = MycourseSubscriptionExpiredPage(None, data['selectors'])
    for route in ('open_route', 'cleanup_route'):
        assert isinstance(data.get(route), list) and data[route], f'Configure {route}'
        for name in data[route]:
            validator.locator(name)
    if number == 8:
        validator.locator('renewal_screen')
    seeds = case['enrollments']
    assert seeds, 'Every supplied scenario requires seeded enrollments, including excluded records'
    for row in seeds:
        assert all(isinstance(row[field], str) for field in validator.FIELD_NAMES)
        assert all(row[field].strip() for field in ('course', 'batch', 'expiry'))
        assert row['status'] in {'Active', 'Expired'}
        assert row['course_state'] in {'available', 'archived', 'unavailable'}
        assert isinstance(row['sticker_visible'], bool)
    assert len({validator.identity(row) for row in seeds}) == len(seeds), 'Seed unique course/batch/subject combinations'
    if data.get('prepared_case_id') == case_id:
        preparation = nullcontext()
    else:
        try:
            prepare = request.getfixturevalue('mycourse_expired_prepare')
        except pytest.FixtureLookupError as error:
            if error.argname != 'mycourse_expired_prepare':
                raise
            pytest.skip('Implement mycourse_expired_prepare or set prepared_case_id for one preseeded case')
        preparation = prepare(case_id, case, data)
    with preparation:
        yield data, case


@pytest.fixture
def expired_page(request, expired_case):
    data, _ = expired_case
    if data.get('mode') == 'live_existing_account':
        session = request.getfixturevalue('course_session')
        with session.page(request, LiveExpiredPage, data, 'expired') as page:
            expired_case[1]['_page'] = page
            yield page
        return
    driver = request.getfixturevalue('driver')
    page = MycourseSubscriptionExpiredPage(
        driver, data['selectors'], data.get('selected_attribute', 'selected'),
        max_scrolls=data.get('max_scrolls', 50),
    )
    authenticated = False
    try:
        login = LoginPage(driver)
        login.wait_until_loaded()
        login.enter_mobile_number(os.environ['TEST_MOBILE_NUMBER'])
        login.tap_continue()
        otp = OtpTypePage(driver)
        otp.wait_until_loaded()
        otp.enter_otp(os.environ['TEST_VALID_OTP'])
        assert otp.is_verified(timeout=20), 'Login failed'
        authenticated = True
        page.navigate(data['open_route'])
        page.wait_loaded()
        page.select_expired()
        yield page
    finally:
        if authenticated:
            page.navigate(data['cleanup_route'])


def expected_rows(case, status='Expired'):
    rows = []
    for seed in case['enrollments']:
        if seed['status'] == status and seed['course_state'] == 'available':
            row = {field: seed[field] for field in MycourseSubscriptionExpiredPage.FIELD_NAMES}
            if not seed['sticker_visible']:
                row['sticker'] = ''
            rows.append(row)
    return rows


def eligible(expired_case):
    if expired_case[1].get('mode') == 'live_existing_account':
        expired_case[1]['_page'].require_card('expired')
    rows = expected_rows(expired_case[1])
    assert rows, 'Seed at least one eligible expired enrollment'
    return rows


def verify_list(page, case, tab='expired'):
    expected = expected_rows(case, tab.title())
    actual = page.assert_subscriptions(expected, tab)
    if not expected:
        assert page.is_visible(page.locator(f'{tab}_empty'))
    return actual


def test_mc_exp_001_open_expired_tab(expired_page):
    """High: Expired is selected and Active is deselected."""
    assert expired_page.text('expired_tab') == 'Expired'
    assert expired_page.tab_selected('expired_tab')
    assert not expired_page.tab_selected('active_tab')


def test_mc_exp_002_expired_subscription_card(expired_page, expired_case):
    """Critical: An eligible expired card displays all expected details."""
    expired_page.assert_subscriptions(eligible(expired_case))


def test_mc_exp_003_course_name(expired_page, expired_case):
    """High: Correct course name, allowing visual line wrapping."""
    for row in eligible(expired_case):
        card = expired_page.find_subscription(row)
        assert expired_page.read_card(card)['course'] == row['course']


def test_mc_exp_004_batch_name(expired_page, expired_case):
    """High: Correct enrolled batch is displayed on the matching card."""
    for row in eligible(expired_case):
        card = expired_page.find_subscription(row)
        assert expired_page.read_card(card)['batch'] == row['batch']


def test_mc_exp_005_expired_status(expired_page, expired_case):
    """High: Each eligible card has its own Expired badge."""
    expired_page.assert_subscriptions(eligible(expired_case))
    assert all(row['status'] == 'Expired' for row in expired_page.subscriptions())


def test_mc_exp_006_expiry_date(expired_page, expired_case):
    """High: Expiry label and date match the independently seeded record."""
    for row in eligible(expired_case):
        card = expired_page.find_subscription(row)
        assert expired_page.text('expiry_label', card) == 'Expiry'
        assert expired_page.read_card(card)['expiry'] == row['expiry']


def test_mc_exp_007_renew_now_button(expired_page, expired_case):
    """Critical: Each expired card exposes an enabled Renew Now button."""
    for row in eligible(expired_case):
        expired_page.renew_button(row)


def test_mc_exp_008_renew_now_navigation(expired_page, expired_case):
    """Critical: Renew Now opens the configured renewal/purchase destination."""
    expired_page.renew(eligible(expired_case)[0])


def exclusion(page, case, state):
    assert any(row['status'] == 'Expired' and row['course_state'] == state
               for row in case['enrollments']), f'Seed an expired {state} enrollment'
    verify_list(page, case)


def test_mc_exp_009_archived_course_exclusion(expired_page, expired_case):
    """Critical: Archived expired enrollments are excluded from the full list."""
    exclusion(expired_page, expired_case[1], 'archived')


def test_mc_exp_010_unavailable_course_exclusion(expired_page, expired_case):
    """Critical: Unavailable expired enrollments are excluded."""
    exclusion(expired_page, expired_case[1], 'unavailable')


def test_mc_exp_011_multiple_expired_enrollments(expired_page, expired_case):
    """Critical: All eligible expired enrollments appear, including after scrolling."""
    expected = eligible(expired_case)
    assert len(expected) >= 2
    expired_page.assert_subscriptions(expected)


def mixed_case(expired_case):
    case = expired_case[1]
    seeds = case['enrollments']
    assert expected_rows(case, 'Active') and expected_rows(case, 'Expired')
    assert {'archived', 'unavailable'} <= {row['course_state'] for row in seeds}
    return case


def test_mc_exp_012_mixed_enrollment_visibility(expired_page, expired_case):
    """Critical: Eligible records appear only in their correct tab."""
    case = mixed_case(expired_case)
    verify_list(expired_page, case)
    expired_page.select_active()
    verify_list(expired_page, case, 'active')


def test_mc_exp_013_subject_wise_enrollment(expired_page, expired_case):
    """High: Subject name appears with course details; duplicate input row merged here."""
    expected = eligible(expired_case)
    assert any(row['subject'] for row in expected), 'Seed a subject-wise enrollment'
    expired_page.assert_subscriptions(expected)


def test_mc_exp_014_continuous_sticker(expired_page, expired_case):
    """Medium: Sticker visibility and text follow the confirmed business rule."""
    case = expired_case[1]
    assert case['sticker_rule'], 'Document whether expired cards may display the sticker'
    assert any(row['status'] == 'Expired' and row['course_state'] == 'available'
               and row['sticker'] == 'Continuous' for row in case['enrollments'])
    expired_page.assert_subscriptions(eligible(expired_case))


def test_mc_exp_015_no_eligible_expired_subscription(expired_page, expired_case):
    """Critical: Archived/unavailable-only expired records produce an empty state."""
    case = expired_case[1]
    assert all(row['status'] == 'Expired' and row['course_state'] in {'archived', 'unavailable'}
               for row in case['enrollments'])
    assert verify_list(expired_page, case) == []


def test_mc_exp_016_active_only_absent_from_expired(expired_page, expired_case):
    """Critical: An active-only account has an empty Expired tab."""
    case = expired_case[1]
    assert all(row['status'] == 'Active' and row['course_state'] == 'available'
               for row in case['enrollments'])
    assert verify_list(expired_page, case) == []


def test_mc_exp_017_tab_switching(expired_page, expired_case):
    """High: Active → Expired → Active preserves each independent list."""
    case = expired_case[1]
    assert expected_rows(case, 'Active') and expected_rows(case, 'Expired')
    for tab in ('active', 'expired', 'active'):
        expired_page.select_tab(tab)
        verify_list(expired_page, case, tab)


def test_mc_exp_018_back_navigation(expired_page):
    """Medium: Back returns to the configured previous page."""
    expired_page.go_back()
