"""TC001–TC034: independent coin and problem-based quiz tests.

Every live test requires explicit SMS/coin authorization and authored test data.
See test_data/coin_problemquiz/README.md. No test calls another test.
"""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import urllib.request

import pytest
from appium.webdriver.common.appiumby import AppiumBy

from pages.Login.login_page import LoginPage
from config.config import settings
from pages.Login.otp_page import OtpTypePage
from pages.Leaderboard.coin_problemquiz_page import (
    CoinBalances, CoinConfigurationError, CoinProblemQuizPage, answer_counts,
)


pytestmark = [pytest.mark.coin_quiz, pytest.mark.sends_otp, pytest.mark.requires_valid_otp]
DATA_PATH = Path(os.getenv('COIN_TEST_DATA', str(
    Path(__file__).resolve().parents[2] / 'test_data/coin_problemquiz/cases.json')))
ADMIN_CASES = {'TC023', 'TC024', 'TC025', 'TC026', 'TC033'}
BOUNDARY_CASES = {'TC011', 'TC012'}
COMPLETE_CASES = {'TC002', 'TC003', 'TC004', 'TC005', 'TC006', 'TC007', 'TC008',
                  'TC009', 'TC010', 'TC016', 'TC018', 'TC019', 'TC020', 'TC021',
                  'TC022', 'TC023', 'TC024', 'TC025', 'TC029', 'TC030', 'TC031', 'TC032'}
REQUIRED = {
    'TC001': ('is_new_user',), 'TC011': ('expected_before', 'expected_after'),
    'TC012': ('expected_before', 'expected_after', 'expected_weekly_history'),
    'TC013': ('expected_history',), 'TC014': ('expected_history',), 'TC015': ('expected_history',),
    'TC017': ('answers', 'expected_indicator_text', 'expected_total', 'expected_coins'),
    'TC024': ('after_change_answers', 'expected_total_after', 'expected_correct_after', 'expected_balance_delta_after_change'),
    'TC025': ('expected_total_after',), 'TC026': ('variants',),
    'TC027': ('partial_answers', 'expected_total'),
    'TC028': ('partial_answers', 'answers', 'expected_total', 'expected_coins'),
    'TC031': ('leaderboard_navigation_available',),
    'TC033': ('partial_answers', 'answers', 'expected_total', 'expected_total_before', 'expected_coins'),
}


@pytest.fixture(scope='session')
def coin_data():
    if not DATA_PATH.is_file():
        pytest.skip(f'Provide COIN_TEST_DATA: {DATA_PATH}')
    data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    if data.get('login_number') != os.getenv('TEST_MOBILE_NUMBER'):
        pytest.skip('TEST_MOBILE_NUMBER must match the authorized login_number in COIN_TEST_DATA (default 9995759936)')
    return data


def optional_provider(request, name):
    try:
        provider = request.getfixturevalue(name)
    except pytest.FixtureLookupError:
        pytest.skip(f'Controlled staging prerequisite: implement fixture {name} in tests/conftest.py')
    if not callable(provider):
        raise CoinConfigurationError(f'{name} must return a callable staging provider')
    return provider


@pytest.fixture
def coin_case(request, coin_data):
    tc_id = re.search(r'tc\d{3}', request.node.name).group().upper()
    scenario = dict(coin_data.get('cases', {}).get(tc_id, {}))
    if not scenario.get('ready'):
        pytest.skip(scenario.get('skip_reason') or f'{tc_id}: configure inspected locators, paths, independent seed/answer key and set ready=true')
    if not coin_data.get('server_timezone'):
        pytest.skip('Confirm and configure the product server_timezone before coin/date assertions')
    missing = [key for key in REQUIRED.get(tc_id, ()) if scenario.get(key) is None]
    if tc_id in COMPLETE_CASES:
        missing += [key for key in ('answers', 'expected_total', 'expected_coins') if scenario.get(key) is None]
    if missing:
        raise CoinConfigurationError(f'{tc_id}: missing fields {sorted(set(missing))}')
    for key in ('answers', 'partial_answers', 'after_change_answers'):
        if key in scenario and scenario[key] is not None:
            if not scenario[key]:
                raise CoinConfigurationError(f'{tc_id}: {key} must be nonempty')
            answer_counts(scenario[key])
            if any(not answer.get('steps') for answer in scenario[key]):
                raise CoinConfigurationError(f'{tc_id}: every authored answer needs UI steps')
    # Validate provided locators before an OTP request, without accessing a driver.
    validator = CoinProblemQuizPage(None, coin_data)
    for path in ('home', 'course'):
        if not coin_data.get('paths', {}).get(path):
            raise CoinConfigurationError(f'Configure nonempty paths.{path}')
    validator.locator('course_title')
    for actions in list(coin_data.get('paths', {}).values()) + list(scenario.get('phases', {}).values()):
        validator.validate_steps(actions)
    for key in ('answers', 'partial_answers', 'after_change_answers'):
        for answer in scenario.get(key) or []:
            validator.validate_steps(answer['steps'])
    if tc_id in COMPLETE_CASES or tc_id in {'TC017', 'TC028', 'TC033'}:
        if type(scenario['expected_total']) is not int or scenario['expected_total'] <= 0 or type(scenario['expected_coins']) is not int:
            raise CoinConfigurationError('expected_total must be a positive integer and expected_coins an integer')
    if tc_id == 'TC012' and not coin_data.get('weekly_refresh_time'):
        raise CoinConfigurationError('Confirm and configure Tuesday weekly_refresh_time before this case')
    if tc_id == 'TC001' and not scenario['is_new_user']:
        pytest.skip('TC001 requires a genuinely new account with no coin history; do not reset the existing user to manufacture zero')
    if tc_id == 'TC031' and not scenario['leaderboard_navigation_available']:
        pytest.skip('Optional post-collection Leaderboard navigation is not provided in this build')
    if tc_id in ADMIN_CASES:
        if os.getenv('ALLOW_COIN_ADMIN_MUTATIONS', 'false').lower() != 'true':
            pytest.skip('Admin question changes require controlled staging data and ALLOW_COIN_ADMIN_MUTATIONS=true')
        scenario['_admin_change'] = optional_provider(request, 'coin_admin_change')
    if tc_id in BOUNDARY_CASES:
        if os.getenv('ALLOW_COIN_BOUNDARY_TESTS', 'false').lower() != 'true':
            pytest.skip('Run near a real server calendar boundary with ALLOW_COIN_BOUNDARY_TESTS=true; emulator clock is not changed')
    if scenario.get('requires_seed_provider', True):
        prepare = optional_provider(request, 'coin_prepare_case')
        prepare(tc_id, scenario, coin_data)
    scenario['_tc_id'] = tc_id
    request.node.user_properties.extend((('tc_id', tc_id), ('course', coin_data['course_name']),
                                         ('test_mobile', coin_data['login_number'])))
    return scenario


@pytest.fixture
def coin_page(request, coin_case, coin_data):
    # Prerequisites above run before creating a driver or sending any OTP.
    with urllib.request.urlopen(settings.appium_server_url.rstrip('/') + '/sessions', timeout=10) as response:
        sessions = json.load(response).get('value', [])
    if sessions:
        pytest.skip('Close existing Inspector/test sessions before independent coin tests; no session is deleted automatically')
    driver = request.getfixturevalue('driver')
    login = LoginPage(driver)
    login.wait_until_loaded()
    login.enter_mobile_number(coin_data['login_number'])
    login.tap_continue()
    otp = OtpTypePage(driver)
    otp.wait_until_loaded()
    otp.enter_otp(os.environ['TEST_VALID_OTP'])
    assert otp.is_verified(timeout=20), 'Authorized login did not reach Home/onboarding'
    if driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Skip'):
        otp.click((AppiumBy.ACCESSIBILITY_ID, 'Skip'))
    otp.element((AppiumBy.ACCESSIBILITY_ID, 'Home'))
    page = CoinProblemQuizPage(driver, coin_data)
    page.select_course()
    try:
        yield page
    finally:
        # Return to Home before the shared driver fixture uses supported sign-out.
        # Configure this route to handle your quiz exit/confirmation UI as well.
        if coin_case.get('phases', {}).get('cleanup'):
            page.phase(coin_case, 'cleanup')
        else:
            page.path('home')


def expected_balances(before, amount):
    return CoinBalances(*(getattr(before, key) + amount for key in ('home', 'today', 'weekly', 'all_time')))


def week_start(day):
    return day - timedelta(days=(day.weekday() - 1) % 7)  # Tuesday


def answer_counts_as_ids(answers):
    return {answer['question_id'] for answer in answers}


def same_period(page, start):
    assert page.now().date() == start.date(), 'Calendar boundary crossed during delta check; run boundary cases separately'


def earn(page, scenario, expected_kind=None, fixed_reward=None):
    if expected_kind:
        assert scenario.get('quiz_kind') == expected_kind, f'Scenario must target {expected_kind}, not another quiz type'
    if fixed_reward is not None:
        assert scenario['expected_coins'] == fixed_reward, 'Authored reward must match the configured requirement'
    started = page.now()
    before = page.balances()
    result = page.complete(scenario)
    assert result.coins > 0, 'This case requires a positive configured reward'
    page.collect(scenario)
    after = page.wait_balances(expected_balances(before, result.coins), timeout=page.data['immediate_update_timeout_seconds'])
    same_period(page, started)
    return before, result, after


def assert_history(page, period, expected):
    actual = page.history(period)
    actual_map = {row.transaction_id: (row.coins, row.recorded_at) for row in actual}
    expected_map = {row['id']: (row['coins'], datetime.fromisoformat(row['recorded_at'])) for row in expected}
    assert len(expected_map) == len(expected), 'Expected ledger contains duplicate IDs'
    assert all(time.tzinfo is not None for _, time in expected_map.values()), 'Expected timestamps need timezone offsets'
    assert actual_map == expected_map, 'Complete coin history differs from the independent seeded transaction ledger'
    return actual


def change_questions(page, scenario, kind, variant=None):
    # Implemented by a project-owned, explicitly authorized staging fixture.
    # The page object never invents admin endpoints or runs arbitrary commands.
    scenario['_admin_change'](scenario['_tc_id'], kind, variant or scenario, page.data)
    page.phase(variant or scenario, 'refresh_after_change')


def test_tc001_initial_coin_count(coin_page, coin_case):
    assert coin_page.balances() == CoinBalances(0, 0, 0, 0)


def test_tc002_topic_concept_quiz_coins(coin_page, coin_case):
    earn(coin_page, coin_case, expected_kind='topic_concept')


def test_tc003_subtopic_quiz_coins(coin_page, coin_case):
    earn(coin_page, coin_case, expected_kind='subtopic')


def test_tc004_practice_quiz_coins(coin_page, coin_case):
    earn(coin_page, coin_case, expected_kind='practice')


def test_tc005_exam_awards_ten_coins(coin_page, coin_case):
    earn(coin_page, coin_case, expected_kind='exam', fixed_reward=10)


def test_tc006_daily_task_awards_ten_coins(coin_page, coin_case):
    earn(coin_page, coin_case, expected_kind='daily_task', fixed_reward=10)


def test_tc007_home_coin_update(coin_page, coin_case):
    before, result, after = earn(coin_page, coin_case)
    assert after.home - before.home == result.coins


def test_tc008_today_coins_update_immediately(coin_page, coin_case):
    before, result, after = earn(coin_page, coin_case)
    assert after.today - before.today == result.coins


def test_tc009_all_time_coins_update_immediately(coin_page, coin_case):
    before, result, after = earn(coin_page, coin_case)
    assert after.all_time - before.all_time == result.coins


def test_tc010_weekly_coins_update_immediately(coin_page, coin_case):
    before, result, after = earn(coin_page, coin_case)
    assert after.weekly - before.weekly == result.coins


def test_tc011_today_coins_reset_at_midnight(coin_page, coin_case):
    observed_at = coin_page.now()
    before = coin_page.balances()
    assert before == CoinBalances(**coin_case['expected_before'])
    assert before.today > 0, 'Seed nonzero Today coins to prove a reset actually happened'
    assert coin_page.now().date() == observed_at.date(), 'Midnight passed before the baseline was captured'
    boundary = coin_page.wait_calendar_boundary('daily')
    assert boundary.hour == 0 and boundary.minute == 0
    coin_page.phase(coin_case, 'refresh_after_boundary')
    expected = CoinBalances(**coin_case['expected_after'])
    assert expected.today == 0 and expected.home == before.home and expected.all_time == before.all_time
    coin_page.wait_balances(expected)


def test_tc012_weekly_leaderboard_refreshes_tuesday(coin_page, coin_case):
    before = coin_page.balances()
    assert before == CoinBalances(**coin_case['expected_before'])
    assert before.weekly > 0, 'Seed nonzero weekly coins before the Tuesday refresh'
    boundary = coin_page.wait_calendar_boundary('weekly')
    assert boundary.weekday() == 1
    coin_page.phase(coin_case, 'refresh_after_boundary')
    after = coin_page.wait_balances(CoinBalances(**coin_case['expected_after']))
    assert after.home == before.home and after.all_time == before.all_time
    assert after.weekly != before.weekly, 'Weekly values did not refresh across Tuesday'
    assert_history(coin_page, 'weekly', coin_case['expected_weekly_history'])


def test_tc013_coin_log_today(coin_page, coin_case):
    rows = assert_history(coin_page, 'today', coin_case['expected_history'])
    assert rows, 'Use a nonempty seeded Today ledger to test the filter'
    assert all(row.recorded_at.astimezone(coin_page.zone).date() == coin_page.now().date() for row in rows)


def test_tc014_coin_log_this_week(coin_page, coin_case):
    rows = assert_history(coin_page, 'weekly', coin_case['expected_history'])
    assert rows, 'Use a nonempty seeded weekly ledger to test completeness'
    start = week_start(coin_page.now().date())
    assert all(start <= row.recorded_at.astimezone(coin_page.zone).date() < start + timedelta(days=7) for row in rows)


def test_tc015_coin_log_all_time(coin_page, coin_case):
    rows = assert_history(coin_page, 'all_time', coin_case['expected_history'])
    assert rows, 'Use transactions from multiple dates, not an empty ledger'
    assert len({row.recorded_at.astimezone(coin_page.zone).date() for row in rows}) > 1


def test_tc016_quiz_result_matches_answers(coin_page, coin_case):
    result = coin_page.complete(coin_case)
    counts = answer_counts(coin_case['answers'])
    assert (result.correct, result.wrong) == (counts['correct'], counts['wrong'])


def test_tc017_change_correct_answer_to_wrong(coin_page, coin_case):
    answers = coin_case['answers']
    assert len(answers) >= 2 and answers[0]['outcome'] == 'correct' and answers[1]['outcome'] == 'wrong'
    assert answers[0]['question_id'] == answers[1]['question_id']
    coin_page.phase(coin_case, 'open')
    coin_page.answer(answers)
    assert coin_page.text('status_indicator') == coin_case['expected_indicator_text']
    coin_page.phase(coin_case, 'submit')
    result = coin_page.result()
    counts = answer_counts(answers)
    assert (result.correct, result.wrong, result.unknown) == (counts['correct'], counts['wrong'], counts['unknown'])
    assert result.total == coin_case['expected_total'] and result.coins == coin_case['expected_coins']


def test_tc018_positive_result_shows_collect_coins(coin_page, coin_case):
    assert coin_page.complete(coin_case).coins > 0
    assert coin_page.actionable('collect_coins')


def test_tc019_negative_result_hides_or_disables_collect(coin_page, coin_case):
    before = coin_page.balances()
    assert coin_page.complete(coin_case).coins < 0
    assert not coin_page.actionable('collect_coins')
    assert coin_page.actionable('close_result')
    coin_page.close_result(coin_case)
    assert coin_page.balances() == before


def test_tc020_collect_adds_displayed_coins_to_leaderboard(coin_page, coin_case):
    before, result, after = earn(coin_page, coin_case)
    assert after.delta(before) == CoinBalances(result.coins, result.coins, result.coins, result.coins)


def test_tc021_prevent_duplicate_collection(coin_page, coin_case):
    _, _, collected = earn(coin_page, coin_case)
    coin_page.phase(coin_case, 'review')
    if coin_page.actionable('collect_coins'):
        coin_page.phase(coin_case, 'recollect')
    else:
        assert not coin_page.actionable('collect_coins')
    coin_page.phase(coin_case, 'leave_review')
    assert coin_page.balances() == collected


def test_tc022_subsequent_review_hides_coins_collected(coin_page, coin_case):
    earn(coin_page, coin_case)
    coin_page.phase(coin_case, 'review')
    assert not coin_page.visible('coins_collected')
    assert not coin_page.actionable('collect_coins')


def test_tc023_delete_adaptive_question_preserves_collected_coins(coin_page, coin_case):
    _, result, collected = earn(coin_page, coin_case)
    change_questions(coin_page, coin_case, 'delete_adaptive')
    coin_page.phase(coin_case, 'review')
    assert coin_page.number('collected_value') == result.coins
    assert coin_page.balances() == collected


def test_tc024_add_adaptive_question_preserves_old_coins_updates_correct_count(coin_page, coin_case):
    _, result, collected = earn(coin_page, coin_case)
    change_questions(coin_page, coin_case, 'add_adaptive')
    coin_page.answer(coin_case['after_change_answers'])
    assert all(a['outcome'] == 'correct' for a in coin_case['after_change_answers'])
    coin_page.phase(coin_case, 'after_change_submit')
    after = coin_page.result()
    assert after.correct == coin_case['expected_correct_after']
    assert after.correct > result.correct and after.total == coin_case['expected_total_after']
    assert coin_page.number('collected_value') == result.coins
    coin_page.wait_balances(expected_balances(collected, coin_case['expected_balance_delta_after_change']))


def test_tc025_new_question_increases_start_total_preserves_old_coins(coin_page, coin_case):
    _, result, collected = earn(coin_page, coin_case)
    change_questions(coin_page, coin_case, 'add_new_question')
    coin_page.phase(coin_case, 'open_after_change')
    assert coin_page.number('start_total') == coin_case['expected_total_after'] == result.total + 1
    coin_page.phase(coin_case, 'review')
    assert coin_page.number('collected_value') == result.coins
    assert coin_page.balances() == collected


def test_tc026_pending_question_coin_rules(coin_page, coin_case):
    assert set(coin_case['variants']) == {'positive', 'negative'}, 'TC026 requires both coin-result branches'
    for kind, variant in coin_case['variants'].items():
        before = coin_page.balances()
        result = coin_page.complete(variant)
        assert (result.coins > 0) if kind == 'positive' else (result.coins < 0)
        if kind == 'positive':
            coin_page.collect(variant)
            baseline = coin_page.wait_balances(expected_balances(before, result.coins))
        else:
            coin_page.close_result(variant)
            baseline = before
        change_questions(coin_page, coin_case, 'mark_pending', variant)
        coin_page.phase(variant, 'review')
        if kind == 'positive':
            assert coin_page.number('collected_value') == result.coins
        else:
            assert coin_page.number('result_coins') == variant['expected_coins_after_pending']
        assert coin_page.balances() == baseline


def test_tc027_exit_incomplete_quiz_awards_no_coins(coin_page, coin_case):
    before = coin_page.balances()
    coin_page.select_course()
    coin_page.phase(coin_case, 'open')
    assert coin_page.number('start_total') == coin_case['expected_total']
    assert 0 < len(answer_counts_as_ids(coin_case['partial_answers'])) < coin_case['expected_total']
    coin_page.answer(coin_case['partial_answers'])
    coin_page.phase(coin_case, 'exit_incomplete')
    assert coin_page.balances() == before


def test_tc028_resume_test_awards_only_after_completion(coin_page, coin_case):
    started = coin_page.now()
    before = coin_page.balances()
    coin_page.select_course()
    coin_page.phase(coin_case, 'open')
    assert coin_page.number('start_total') == coin_case['expected_total']
    assert 0 < len(answer_counts_as_ids(coin_case['partial_answers'])) < coin_case['expected_total']
    coin_page.answer(coin_case['partial_answers'])
    coin_page.phase(coin_case, 'exit_incomplete')
    assert coin_page.balances() == before
    coin_page.select_course()
    coin_page.phase(coin_case, 'reopen')
    assert coin_page.actionable('resume_test')
    coin_page.phase(coin_case, 'resume')
    coin_page.answer(coin_case['answers'])
    coin_page.phase(coin_case, 'submit')
    result = coin_page.result()
    counts = answer_counts(coin_case['answers'])
    assert (result.correct, result.wrong, result.unknown) == (counts['correct'], counts['wrong'], counts['unknown'])
    assert result.coins == coin_case['expected_coins'] > 0
    assert result.total == coin_case['expected_total']
    coin_page.collect(coin_case)
    coin_page.wait_balances(expected_balances(before, result.coins))
    same_period(coin_page, started)


def test_tc029_summary_total_question_count(coin_page, coin_case):
    assert coin_page.complete(coin_case).total == coin_case['expected_total']


def test_tc030_summary_correct_unknown_wrong_counts(coin_page, coin_case):
    counts = answer_counts(coin_case['answers'])
    assert all(counts.values()), 'Seed at least one correct, wrong, and I-do-not-know answer'
    result = coin_page.complete(coin_case)
    assert (result.correct, result.unknown, result.wrong) == (counts['correct'], counts['unknown'], counts['wrong'])


def test_tc031_collect_coins_leaderboard_navigation(coin_page, coin_case):
    before = coin_page.balances()
    result = coin_page.complete(coin_case)
    assert result.coins > 0
    coin_page.collect(coin_case)
    coin_page.phase(coin_case, 'navigate_to_leaderboard')
    # Check the app's navigation before the balance helper navigates itself.
    assert coin_page.visible('leaderboard_screen')
    coin_page.wait_balances(expected_balances(before, result.coins))


def test_tc032_zero_result_does_not_add_coins(coin_page, coin_case):
    before = coin_page.balances()
    assert coin_page.complete(coin_case).coins == 0
    if coin_page.actionable('collect_coins'):
        coin_page.collect(coin_case)
    else:
        coin_page.close_result(coin_case)
    assert coin_page.balances() == before


def test_tc033_new_question_during_resume_recalculates_counts_and_coins(coin_page, coin_case):
    started = coin_page.now()
    before = coin_page.balances()
    coin_page.select_course()
    coin_page.phase(coin_case, 'open')
    assert coin_page.number('start_total') == coin_case['expected_total_before']
    assert 0 < len(answer_counts_as_ids(coin_case['partial_answers'])) < coin_case['expected_total_before']
    coin_page.answer(coin_case['partial_answers'])
    coin_page.phase(coin_case, 'exit_incomplete')
    assert coin_page.balances() == before
    change_questions(coin_page, coin_case, 'add_question_during_resume')
    coin_page.select_course()
    coin_page.phase(coin_case, 'reopen')
    assert coin_page.number('start_total') == coin_case['expected_total'] == coin_case['expected_total_before'] + 1
    assert coin_page.actionable('resume_test')
    coin_page.phase(coin_case, 'resume')
    coin_page.answer(coin_case['answers'])
    coin_page.phase(coin_case, 'submit')
    result = coin_page.result()
    counts = answer_counts(coin_case['answers'])
    assert (result.correct, result.wrong, result.unknown) == (counts['correct'], counts['wrong'], counts['unknown'])
    assert result.total == coin_case['expected_total']
    assert result.coins == coin_case['expected_coins'] != 0
    if result.coins > 0:
        coin_page.collect(coin_case)
        coin_page.wait_balances(expected_balances(before, result.coins))
    else:
        assert not coin_page.actionable('collect_coins')
        coin_page.close_result(coin_case)
        assert coin_page.balances() == before
    same_period(coin_page, started)


def test_tc034_coin_totals_match_actual_transactions(coin_page, coin_case):
    started = coin_page.now()
    ledger = coin_page.history('all_time')
    assert ledger, 'Seed nonempty historical earnings so consistency is not a vacuous zero check'
    today = started.date()
    start_week = week_start(today)
    all_time = sum(row.coins for row in ledger)
    today_total = sum(row.coins for row in ledger if row.recorded_at.astimezone(coin_page.zone).date() == today)
    weekly_total = sum(row.coins for row in ledger if start_week <= row.recorded_at.astimezone(coin_page.zone).date() < start_week + timedelta(days=7))
    assert coin_page.balances() == CoinBalances(all_time, today_total, weekly_total, all_time)
    same_period(coin_page, started)
