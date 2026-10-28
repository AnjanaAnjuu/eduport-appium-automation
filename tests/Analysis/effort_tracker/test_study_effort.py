"""ET-STUDY, ET-REV, ET-PRACT, ET-EXAM and ET-CROSS cases from the supplied sheet.

Every live case needs inspected UI steps, prepared content and an independent
expected time. The example catalog keeps cases inactive until those exist.
"""
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException

from pages.Analysis.effort_flow import EffortFlowPage
from pages.Analysis.effort_tracker.study_effort_page import StudyEffortPage
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from utils.app_state import ensure_logged_out
from utils.driver import create_driver
from utils.waits import Waits

pytestmark = [pytest.mark.sends_otp, pytest.mark.requires_valid_otp]

CATALOG = Path(__file__).resolve().parents[3] / 'test_data/study_effort_cases.example.json'
CASE_IDS = tuple(json.loads(CATALOG.read_text(encoding='utf-8'))['cases'])
POLICIES = {'credit', 'no_credit', 'pending_credit', 'review_no_credit',
            'repeat_credit', 'aggregate', 'observations'}
APPROVAL_REQUIRED = {
    'ET-STUDY-009', 'ET-STUDY-011', 'ET-STUDY-028', 'ET-STUDY-029',
    'ET-STUDY-030', 'ET-STUDY-031', 'ET-REV-002', 'ET-REV-003',
    'ET-CROSS-004',
}


@pytest.fixture(scope='module')
def study_data():
    path = Path(os.getenv('STUDY_EFFORT_DATA', str(CATALOG)))
    if not path.is_file():
        pytest.skip(f'Provide STUDY_EFFORT_DATA: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def study_driver(study_data):
    """Authenticate once, then reuse the session for every active case."""
    cases_ready = any(case.get('ready') for case in study_data.get('cases', {}).values())
    if not study_data.get('ready') or not (cases_ready or study_data.get('navigation', {}).get('ready')):
        pytest.skip('Study Effort suite has no prepared, active cases')
    if study_data.get('mobile_number') != os.getenv('TEST_MOBILE_NUMBER'):
        pytest.skip('STUDY_EFFORT_DATA mobile_number must match authorized TEST_MOBILE_NUMBER')
    validator = StudyEffortPage(None, study_data)
    validator.validate(study_data.get('reset_to_home_steps'))
    validator.validate(study_data.get('tracker_entry_steps'))
    course_flow = EffortFlowPage(None, study_data.get('flow_selectors', {}))
    course_flow.validate(study_data.get('select_course_steps'))
    course_flow.locator('selected_course')

    driver = create_driver(no_reset=True)
    try:
        ensure_logged_out(driver)
        login = LoginPage(driver)
        login.wait_until_loaded()
        login.enter_mobile_number(study_data['mobile_number'])
        login.tap_continue()
        otp = OtpTypePage(driver)
        otp.wait_until_loaded()
        otp.enter_otp(os.environ['TEST_VALID_OTP'])

        def home_or_onboarding(current):
            permission = current.find_elements(
                AppiumBy.ID, 'com.android.permissioncontroller:id/permission_allow_button'
            )
            if permission:
                permission[0].click()
            return (current.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Home')
                    or current.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Skip'))

        otp.wait.until(home_or_onboarding)
        skip = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Skip')
        if skip:
            skip[0].click()
        otp.element((AppiumBy.ACCESSIBILITY_ID, 'Home'))
        flow = EffortFlowPage(driver, study_data['flow_selectors'])
        flow.steps(study_data['select_course_steps'])
        course = flow.element(flow.locator('selected_course'))
        label = course.get_attribute('content-desc') or course.get_attribute('text') or course.text or ''
        if study_data['course_name'].casefold() not in label.casefold():
            raise AssertionError(f"Wrong course: expected {study_data['course_name']!r}, found {label!r}")
        yield driver
    finally:
        try:
            ensure_logged_out(driver)
        finally:
            driver.quit()


@pytest.fixture
def study_case(request, study_data):
    case_id = request.param
    case = study_data.get('cases', {}).get(case_id)
    if not case or not case.get('ready'):
        pytest.skip(f'{case_id}: configure inspected steps, content and independent expected time')
    if case_id in APPROVAL_REQUIRED and not case.get('approved_rule'):
        pytest.skip(f'{case_id}: configure the approved product tracking rule')
    if case.get('policy') == 'unresolved':
        pytest.skip(f'{case_id}: approved product tracking rule is not specified')
    if case.get('policy') not in POLICIES:
        raise ValueError(f'{case_id}: unsupported policy {case.get("policy")!r}')
    if not study_data.get('ready'):
        pytest.skip('Set study suite ready=true after inspecting course and tracker selectors')
    page = StudyEffortPage(None, study_data)
    page.validate(study_data.get('tracker_entry_steps'))
    for field in study_data.get('tracker_fields', []):
        page.locator(field)
    phases = case.get('phases', {})
    required = {
        'credit': ('activity',),
        'no_credit': ('activity',),
        'pending_credit': ('attempt', 'check_pending', 'resume', 'submit'),
        'review_no_credit': ('qualifying_activity', 'review'),
        'repeat_credit': ('first_open', 'second_open'),
        'aggregate': ('activity',),
        'observations': (),
    }[case['policy']]
    for name in required:
        page.validate(phases.get(name))
    if case['policy'] == 'observations':
        observations = case.get('observations', [])
        if len(observations) != (7 if case_id == 'ET-CROSS-002' else 2):
            raise ValueError(f'{case_id}: configure dated observations for each required view')
        for observation in observations:
            page.validate(observation.get('steps'))
            if not observation.get('expected_snapshot_seconds'):
                raise ValueError(f'{case_id}: observation needs independent expected times')
        if case_id == 'ET-CROSS-002':
            dates = [item.get('date') for item in observations]
            if any(not value for value in dates) or len(set(dates)) != 7:
                raise ValueError('Seven-day history needs seven distinct known dates')
    else:
        expected = case.get('expected_delta_seconds')
        if not isinstance(expected, dict) or not expected:
            raise ValueError(f'{case_id}: configure expected_delta_seconds')
        if case['policy'] == 'repeat_credit' and not case.get('expected_second_delta_seconds'):
            raise ValueError(f'{case_id}: configure expected_second_delta_seconds')
    if case_id in {'ET-STUDY-001', 'ET-STUDY-002', 'ET-STUDY-003',
                   'ET-STUDY-004', 'ET-STUDY-005'}:
        if case.get('content_duration_seconds') != 600:
            raise ValueError(f'{case_id}: use an inspected 600-second video')
        seconds = round(600 / case['playback_speed'])
        low, high = case['expected_delta_seconds']['study']
        if not low <= seconds <= high:
            raise ValueError(f'{case_id}: expected range must include {seconds}s')
    if case_id in {'ET-STUDY-017', 'ET-STUDY-020'}:
        if case.get('question_count') != 1 or not any(
            step['action'] == 'wait_seconds' and step['seconds'] > 300
            for step in phases['attempt']
        ):
            raise ValueError(f'{case_id}: one question must remain open >300s')
        if case['expected_delta_seconds']['study'][1] > 300:
            raise ValueError(f'{case_id}: one question cannot credit >300s')
    if case_id in {'ET-STUDY-007', 'ET-STUDY-008'} and not any(
        step['action'] == 'swipe_element' for step in phases['activity']
    ):
        raise ValueError(f'{case_id}: configure an inspected seek gesture')
    if case_id == 'ET-STUDY-027' and not any(
        step['action'] == 'scroll' for step in phases['activity']
    ):
        raise ValueError('PDF scroll case must actually scroll')
    return case_id, case


@pytest.fixture
def study_page(study_case, study_driver, study_data):
    page = StudyEffortPage(study_driver, study_data)
    page.steps(study_data['reset_to_home_steps'])
    page.steps(study_data['tracker_entry_steps'])
    page.snapshot()
    return page


@pytest.fixture
def navigation_case(study_data):
    navigation = study_data.get('navigation', {})
    if not study_data.get('ready') or not navigation.get('ready'):
        pytest.skip('Configure inspected Day/Week selectors and dated expected values; set navigation.ready=true')
    page = StudyEffortPage(None, study_data)
    page.validate(study_data.get('tracker_entry_steps'))
    for name in ('day', 'week', 'date', 'previous_day', 'next_day', 'effort_index'):
        page.locator(name)
    for name in study_data.get('tracker_fields', []):
        page.locator(name)
    days = navigation.get('days', [])
    if len(days) != 8:
        raise ValueError('Configure Today and exactly seven previous days')
    today = date.fromisoformat(navigation['today_iso'])
    for offset, entry in enumerate(days):
        if entry.get('date_iso') != (today - timedelta(days=offset)).isoformat():
            raise ValueError(f'Day {offset} must be today minus {offset} calendar days')
        if not entry.get('expected_label') or not entry.get('expected_snapshot_seconds'):
            raise ValueError(f'Day {offset} needs its displayed label and independent time values')
        if 'total' not in entry['expected_snapshot_seconds']:
            raise ValueError(f'Day {offset} needs expected Total Time Spent')
        if not isinstance(entry.get('expected_index'), list) or len(entry['expected_index']) != 2:
            raise ValueError(f'Day {offset} needs [minimum, maximum] Effort Index')
    week = navigation.get('week', {})
    if not week.get('expected_snapshot_seconds') or not isinstance(week.get('expected_index'), list):
        raise ValueError('Configure weekly Effort Index and time values')
    if len(week['expected_index']) != 2:
        raise ValueError('Weekly Effort Index needs [minimum, maximum]')
    if 'total' not in week['expected_snapshot_seconds']:
        raise ValueError('Week needs expected Total Time Spent')
    start = date.fromisoformat(week['week_start_iso'])
    end = date.fromisoformat(week['week_end_iso'])
    if not start <= today <= end or (end - start).days != 6:
        raise ValueError('Configured current week must be seven days and contain today')
    return navigation


@pytest.fixture
def navigation_page(navigation_case, study_driver, study_data):
    page = StudyEffortPage(study_driver, study_data)
    page.steps(study_data['reset_to_home_steps'])
    page.steps(study_data['tracker_entry_steps'])
    return page


def assert_dated_values(page, observation, expected):
    assert expected['expected_label'] in observation['date_label'], (
        f"Expected date label {expected['expected_label']!r}, found {observation['date_label']!r}"
    )
    low, high = expected['expected_index']
    assert low <= observation['effort_index'] <= high, (
        f"Effort Index {observation['effort_index']} outside {low}–{high}"
    )
    page.verify_observation(observation, expected['expected_snapshot_seconds'])


def test_day_opens_today_with_only_previous_arrow(navigation_case, navigation_page):
    page = navigation_page
    page.tap('day')
    today = page.dated_snapshot()
    assert 'Today' in today['date_label']
    assert_dated_values(page, today, navigation_case['days'][0])
    assert page.control_available('previous_day'), 'Today must have a left arrow'
    assert not any(item.is_displayed() for item in page.driver.find_elements(*page.locator('next_day'))), (
        'Today must show only the left date arrow'
    )


def test_previous_day_data_stops_after_seven_days(navigation_case, navigation_page):
    page = navigation_page
    page.tap('day')
    assert_dated_values(page, page.dated_snapshot(), navigation_case['days'][0])
    for offset in range(1, 8):
        assert page.control_available('previous_day'), f'Left arrow missing before day {offset}'
        page.tap('previous_day')
        assert_dated_values(page, page.dated_snapshot(), navigation_case['days'][offset])
    boundary = page.dated_snapshot()
    if page.control_available('previous_day'):
        page.tap('previous_day')
        assert page.dated_snapshot() == boundary, 'Date moved earlier than seven days'
    for offset in range(6, -1, -1):
        assert page.control_available('next_day'), f'Right arrow missing when returning to day {offset}'
        page.tap('next_day')
        assert_dated_values(page, page.dated_snapshot(), navigation_case['days'][offset])
    assert not page.control_available('next_day'), 'Date moved forward beyond Today'


def test_week_displays_current_week_data(navigation_case, navigation_page):
    page = navigation_page
    page.tap('week')
    observed = page.dated_snapshot()
    expected = navigation_case['week']
    if expected.get('expected_label'):
        assert expected['expected_label'] in observed['date_label']
    low, high = expected['expected_index']
    assert low <= observed['effort_index'] <= high
    page.verify_observation(observed, expected['expected_snapshot_seconds'])


def observed_after(page, before, case):
    """Allow the tracker a bounded time to publish a positive effort delta."""
    expected = case['expected_delta_seconds']
    minimum = max((bounds[0] for bounds in expected.values()), default=0)
    if minimum == 0:
        time.sleep(case.get('settle_seconds', 3))
        return page.snapshot()
    last = None

    def updated(_):
        nonlocal last
        last = page.snapshot()
        return last if all(last[name] - before[name] >= bounds[0]
                           for name, bounds in expected.items() if bounds[0] > 0) else False

    try:
        return Waits(page.driver, case.get('update_timeout_seconds', 30)).until(updated)
    except TimeoutException as error:
        raise AssertionError(f'Effort did not update; last snapshot: {last}') from error


@pytest.mark.parametrize('study_case', CASE_IDS, indirect=True, ids=CASE_IDS)
def test_study_effort_case(study_case, study_page):
    case_id, case = study_case
    page = study_page
    phases = case.get('phases', {})
    policy = case['policy']
    before = page.snapshot()

    if policy in ('credit', 'no_credit', 'aggregate'):
        page.steps(phases['activity'])
        after = observed_after(page, before, case)
        page.verify_change(before, after, case['expected_delta_seconds'])
    elif policy == 'pending_credit':
        page.steps(phases['attempt'])
        page.steps(phases['check_pending'])
        time.sleep(case.get('settle_seconds', 3))
        page.verify_change(before, page.snapshot(), {case['category']: [0, 0]})
        page.steps(phases['resume'])
        page.steps(phases['submit'])
        page.verify_change(before, observed_after(page, before, case),
                           case['expected_delta_seconds'])
    elif policy == 'review_no_credit':
        page.steps(phases['qualifying_activity'])
        after_submit = page.snapshot()
        page.steps(phases['review'])
        time.sleep(case.get('settle_seconds', 3))
        page.verify_change(after_submit, page.snapshot(), case['expected_delta_seconds'])
    elif policy == 'repeat_credit':
        page.steps(phases['first_open'])
        first = observed_after(page, before, case)
        page.verify_change(before, first, case['expected_delta_seconds'])
        page.steps(phases['second_open'])
        second_case = {**case, 'expected_delta_seconds': case['expected_second_delta_seconds']}
        second = observed_after(page, first, second_case)
        page.verify_change(first, second, case['expected_second_delta_seconds'])
    elif policy == 'observations':
        observed = []
        for item in case['observations']:
            page.steps(item['steps'])
            snapshot = page.snapshot()
            page.verify_observation(snapshot, item['expected_snapshot_seconds'])
            if item.get('date'):
                label = page.read('date')
                assert item['date'] in label, f'{case_id}: expected date {item["date"]}, found {label!r}'
            observed.append(snapshot)
        if case_id == 'ET-CROSS-003':
            for field in case.get('compare_fields', ('study', 'practice', 'exam', 'total')):
                assert observed[0][field] == observed[1][field], (
                    f'{case_id}: {field} differs between corresponding day/week views'
                )
