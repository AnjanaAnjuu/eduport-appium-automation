"""SUP-01–SUP-20 for authorized new-user onboarding; phone configured in test data."""
import json
import os
from pathlib import Path
import time
import urllib.request

import pytest

from config.config import settings
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Login.signup_page import SignupPage, SignupSubmissionEvidence
from utils.driver import create_driver
from utils.signup_support import state_api_configured


pytestmark = [pytest.mark.signup, pytest.mark.sends_otp, pytest.mark.requires_valid_otp]
DATA_PATH = Path(os.getenv('SIGNUP_TEST_DATA', str(Path(__file__).resolve().parents[2] / 'test_data/signup_data.json')))


def provider(request, name):
    try:
        value = request.getfixturevalue(name)
    except pytest.FixtureLookupError:
        pytest.skip(f'Independent signup prerequisite: implement approved staging fixture {name}')
    if not callable(value):
        raise ValueError(f'{name} must return a callable')
    return value


@pytest.fixture(scope='session')
def signup_data():
    data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    if os.getenv('TEST_MOBILE_NUMBER') != data['mobile_number']:
        pytest.skip('TEST_MOBILE_NUMBER must match mobile_number in signup test data')
    if not isinstance(data.get('valid_names'), list) or not data['valid_names'] or any(
            not isinstance(name, str) or len(name.strip()) < 3 for name in data['valid_names']):
        raise ValueError('valid_names must contain real names of at least three characters')
    for key, value in data.get('selectors', {}).items():
        if value is not None:
            SignupPage(None, data['selectors']).locator(key)
    return data


@pytest.fixture
def signup_context(request, signup_data):
    sup_id = request.node.name.split('_')[1].upper().replace('SUP', 'SUP-')
    policy = {'SUP-13': 'allow_numeric_only_names', 'SUP-14': 'allow_special_only_names'}.get(sup_id)
    if policy:
        allowed = signup_data['name_policy'].get(policy)
        if allowed is None:
            pytest.skip(f'{sup_id}: confirm {policy}; rejection is conditional in the requirement')
        if allowed is True:
            pytest.skip(f'{sup_id}: not applicable because the confirmed policy permits this name type')
        if allowed is not False:
            raise ValueError(f'{policy} must be true, false, or null')
    if sup_id == 'SUP-20':
        if type(signup_data.get('expected_profile_create_delta')) is not int or signup_data['expected_profile_create_delta'] not in (0, 1):
            pytest.skip('SUP-20: confirm expected_profile_create_delta as 0 or 1 before live submission')
        if type(signup_data.get('rapid_tap_count')) is not int or not 2 <= signup_data['rapid_tap_count'] <= 10:
            raise ValueError('rapid_tap_count must be an integer from 2 to 10')
        duration = signup_data.get('duplicate_observation_seconds')
        if type(duration) not in (int, float) or not 0 < duration <= 5:
            raise ValueError('duplicate_observation_seconds must be in (0, 5]')
    with urllib.request.urlopen(settings.appium_server_url.rstrip('/') + '/sessions', timeout=10) as response:
        if json.load(response).get('value', []):
            pytest.skip('Close existing Inspector/test sessions before preparing independent signup state')
    probe = provider(request, 'signup_submission_probe') if sup_id == 'SUP-20' else None
    # Form-only cases do not create an account and can verify a fresh blank UI
    # through ordinary login. Successful submissions still require real reset/restore.
    prepare = None
    if sup_id in ('SUP-07', 'SUP-20') or (state_api_configured(signup_data) and
            os.getenv('SIGNUP_STAGING_API_APPROVED', 'false').lower() == 'true'):
        prepare = provider(request, 'signup_prepare_account')
    # Provider contract includes approved restoration in its fixture teardown.
    if prepare:
        prepare(signup_data['mobile_number'], sup_id)
    request.node.user_properties.extend((('sup_id', sup_id), ('test_mobile', signup_data['mobile_number'])))
    return {'data': signup_data, 'probe': probe, 'isolated_account': prepare is not None}


@pytest.fixture
def signup_page(request, signup_context):
    data = signup_context['data']
    with urllib.request.urlopen(settings.appium_server_url.rstrip('/') + '/sessions', timeout=10) as response:
        sessions = json.load(response).get('value', [])
    if sessions:
        pytest.skip('Close existing Inspector/test sessions before independent signup tests; none are deleted automatically')
    # Signup has its own fixture: the old driver's Home-only logout cannot handle
    # a half-created account on Enter Your Details. Existing login/OTP tests stay unchanged.
    driver = create_driver()
    request.node._appium_driver = driver
    try:
        driver.terminate_app(settings.app_package, timeout=5000)
        driver.activate_app(settings.app_package)
        login = LoginPage(driver)
        login.wait_until_loaded()
        login.enter_mobile_number(data['mobile_number'])
        login.tap_continue()
        otp = OtpTypePage(driver)
        otp.wait_until_loaded()
        otp.enter_otp(os.environ['TEST_VALID_OTP'])
        page = SignupPage(driver, data.get('selectors'))
        page.allow_validation_submission = signup_context['isolated_account']
        # New-account OTP targets signup, not OtpTypePage.is_verified()'s Home.
        page.wait_until_loaded()
        assert page.name_value().strip() == '', 'Prepared signup draft must have an empty name'
        assert not page.gender_selected('Female') and not page.gender_selected('Male'), 'Prepared signup draft must have no selected gender'
        yield page
    finally:
        try:
            driver.quit()
        finally:
            request.node._appium_driver = None


def valid_details(page, data, gender='Female'):
    page.enter_name(data['valid_names'][-1])
    page.select_gender(gender)
    page.wait_gender_selected(gender)
    page.wait_continue(True)


def choose_gender(page, gender):
    page.select_gender(gender)
    page.wait_gender_selected(gender)


def test_sup01_signup_page_displayed(signup_page):
    assert signup_page.is_displayed()
    for key in ('name_field', 'female', 'male', 'save_continue'):
        assert signup_page.element(signup_page.locator(key)).is_displayed()


def test_sup02_full_name_field_displayed(signup_page):
    assert signup_page.name_prompt().strip().casefold() == 'enter full name'


def test_sup03_accept_valid_names_of_three_or_more_characters(signup_page, signup_data):
    names = signup_data['valid_names']
    assert any(len(name.strip()) == 3 for name in names), 'Include a three-character boundary example'
    choose_gender(signup_page, 'Female')
    for name in names:
        assert len(name.strip()) >= 3
        signup_page.enter_name(name)
        assert signup_page.name_value() == name
        signup_page.wait_continue(True)
        assert not signup_page.validation_visible('name')


def test_sup04_select_female(signup_page):
    signup_page.select_gender('Female')
    signup_page.wait_gender_selected('Female')
    assert not signup_page.gender_selected('Male')


def test_sup05_select_male(signup_page):
    signup_page.select_gender('Male')
    signup_page.wait_gender_selected('Male')
    assert not signup_page.gender_selected('Female')


def test_sup06_valid_name_and_gender_enable_continue(signup_page, signup_data):
    valid_details(signup_page, signup_data)
    assert signup_page.can_continue()


def test_sup07_save_valid_details_opens_course_selection(signup_page, signup_data):
    valid_details(signup_page, signup_data)
    signup_page.save()
    signup_page.wait_course_selection()
    assert signup_page.is_course_selection_displayed()


def test_sup08_submit_without_name_is_blocked(signup_page):
    choose_gender(signup_page, 'Female')
    signup_page.assert_submission_blocked('name')


def test_sup09_submit_without_gender_is_blocked(signup_page, signup_data):
    signup_page.enter_name(signup_data['valid_names'][-1])
    assert signup_page.name_value() == signup_data['valid_names'][-1]
    assert not signup_page.gender_selected('Female') and not signup_page.gender_selected('Male')
    signup_page.assert_submission_blocked('gender')


def test_sup10_empty_name_and_gender_disable_continue(signup_page):
    assert signup_page.name_value().strip() == ''
    assert not signup_page.gender_selected('Female') and not signup_page.gender_selected('Male')
    signup_page.wait_continue(False)


def test_sup11_name_under_three_characters_is_blocked(signup_page, signup_data):
    name = signup_data['invalid_short_name']
    assert 0 < len(name.strip()) < 3
    signup_page.enter_name(name)
    choose_gender(signup_page, 'Male')
    signup_page.assert_submission_blocked('name')


def test_sup12_spaces_only_name_is_blocked(signup_page):
    signup_page.enter_name('   ')
    choose_gender(signup_page, 'Female')
    signup_page.assert_submission_blocked('name')


def test_sup13_numeric_only_name_rejected_when_unsupported(signup_page):
    signup_page.enter_name('12345')
    choose_gender(signup_page, 'Male')
    signup_page.assert_submission_blocked('name')


def test_sup14_special_only_name_rejected_when_unsupported(signup_page):
    signup_page.enter_name('@#$%')
    choose_gender(signup_page, 'Female')
    signup_page.assert_submission_blocked('name')


def test_sup15_invalid_name_plus_gender_is_blocked(signup_page, signup_data):
    signup_page.enter_name(signup_data['invalid_short_name'])
    choose_gender(signup_page, 'Female')
    signup_page.assert_submission_blocked('name')


def test_sup16_gender_without_name_keeps_continue_disabled(signup_page):
    signup_page.select_gender('Male')
    signup_page.wait_gender_selected('Male')
    signup_page.wait_continue(False)


def test_sup17_name_without_gender_keeps_continue_disabled(signup_page, signup_data):
    signup_page.enter_name(signup_data['valid_names'][-1])
    assert signup_page.name_value() == signup_data['valid_names'][-1]
    assert not signup_page.gender_selected('Female') and not signup_page.gender_selected('Male')
    signup_page.wait_continue(False)


def test_sup18_removing_valid_name_disables_continue_again(signup_page, signup_data):
    valid_details(signup_page, signup_data)
    signup_page.enter_name('')
    assert signup_page.name_value() == ''
    signup_page.wait_continue(False)


def test_sup19_changing_gender_deselects_previous_option(signup_page):
    signup_page.select_gender('Female')
    signup_page.wait_gender_selected('Female')
    assert not signup_page.gender_selected('Male')
    signup_page.select_gender('Male')
    signup_page.wait_gender_selected('Male')
    assert not signup_page.gender_selected('Female')


def test_sup20_multiple_save_taps_submit_and_navigate_only_once(signup_page, signup_context):
    data, probe = signup_context['data'], signup_context['probe']
    valid_details(signup_page, data)
    before = SignupSubmissionEvidence.from_mapping(probe(data['mobile_number']))
    signup_page.rapid_save_taps(data['rapid_tap_count'])
    signup_page.wait_course_selection()
    expected = SignupSubmissionEvidence(1, 1, data['expected_profile_create_delta'])

    def first_submission(_):
        delta = SignupSubmissionEvidence.from_mapping(probe(data['mobile_number'])).delta(before)
        for key in ('successful_submissions', 'course_navigations', 'profiles_created'):
            assert getattr(delta, key) <= getattr(expected, key), 'Duplicate signup detected'
        return delta == expected

    signup_page.wait.until(first_submission)
    # Observe a real staging/backend + navigation probe through the full window;
    # seeing Course Selection once alone cannot prove no duplicate submissions.
    deadline = time.monotonic() + data['duplicate_observation_seconds']

    def observe(_):
        after = SignupSubmissionEvidence.from_mapping(probe(data['mobile_number']))
        assert after.delta(before) == expected, 'Duplicate/missing signup, navigation, or profile creation'
        return time.monotonic() >= deadline

    signup_page.wait.until(observe)
