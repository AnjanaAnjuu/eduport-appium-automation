"""ACC_001–ACC_020: supplied My Account workflow and screenshot.

Run: venv/bin/python -m pytest tests/Profile/myaccount/test_myaccount.py

Set MYACCOUNT_TEST_DATA to JSON with:
  selectors: inspected [strategy,value] pairs, or {"locator":[strategy,value],
    "attribute":"text"}. Use content-desc for Flutter labels where appropriate;
    name must read the input value, not its label. Include MyAccountPage.REQUIRED,
    all picker targets, validation labels and Profile display fields used below.
  routes: profile (Home → Profile), cleanup (any test destination → Home), each
    a nonempty list of selector names to tap. Handle open pickers/sheets during
    cleanup. Do not put actions that submit changes in cleanup.
  selected_attribute: actual gender selected attribute; default selected.
  save_enabled_attribute: actual enabled attribute; default enabled.
  dob_read_format: strptime format for joined day/month/year; default %d %m %Y.
  mobile_number: authorized staging account matching TEST_MOBILE_NUMBER.
  cases: ACC_001 ... ACC_020, each with ready:true and baseline details:
    {"name":"Previously Saved", "gender":"Female", "dob":"2000-02-15"}.
    Missing gender/DOB use null. Missing DOB must show DD/MM/YY placeholders.
    ACC_009 baseline must have missing required data.
    Cases which edit all fields additionally use updated details and dob_steps.
    Example updated: {"name":"Anjana Test", "gender":"Male", "dob":"2001-03-16"}.
    dob_steps: ordered {"action":"tap", "target":"picker_or_option"} entries.
    Steps may also assert visible/disabled/absent targets. Populate inspected
    day/month/year options and picker confirmations in the correct app order.

Required staging fixture myaccount_prepare returns a context-manager factory
(case_id, case, data). Snapshot the account, seed baseline before each test and
restore on exit, including failed saves. It must target data.mobile_number only.
The tests reuse Android login and the shared driver. Set ALLOW_OTP_SEND=true,
TEST_MOBILE_NUMBER and TEST_VALID_OTP using the existing project controls.
Each independent login needs a valid OTP (e.g. supported staging OTP).

Extra case data:
- 011,012,020: profile_expected mapping inspected Profile selector names to
  updated visible text. Reopening the sheet additionally verifies all fields.
- 015: valid updated + dob_steps; name is then cleared.
- 016: invalid_name and name_rule describing the confirmed invalid-character
  policy, validation_steps (may tap Save if validation occurs on submit),
  optional error_target/error_text, or disabled Save. Do not assume real names
  with punctuation or non-Latin letters are invalid.
- 017/018: valid updated + dob_steps, attempted_dob in ISO-shaped YYYY-MM-DD,
  attempt_steps which open the real picker and attempt that date. 017 also
  requires today from the controlled device/server date. rejection is 'picker'
  (last attempt step must assert disabled/absent date option), or 'form'
  (Save disabled or exact error_target/error_text). Back out/confirm pickers
  via rejection_cleanup_steps (optional) before asserting the form state.
- 019: back_behavior 'discard' or 'confirm_discard'; back_steps for the latter
  must verify and dismiss the actual unsaved-changes confirmation.
- 020: save_taps (2–5) and fixture myaccount_save_probe. Its capture(case)
  context manager yields evidence whose processed_requests is populated at
  exit from actual account-update traffic/server counters scoped to this user
  and observation window. It must wait for late/duplicate requests to settle,
  not return at the first save. UI tap counts are not submission evidence.

Unknown prerequisites skip before creating a driver. Configured failures fail.
Exact native selectors, name policy, date-picker behavior and Back confirmation
cannot be inferred from this screenshot; configure them from the actual build.
"""
from datetime import date
import json
import os
from pathlib import Path
import re

import pytest

from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Profile.myaccount.myaccount_page import MyAccountPage

pytestmark = [pytest.mark.sends_otp, pytest.mark.requires_valid_otp]


def integration(request, name):
    try:
        return request.getfixturevalue(name)
    except pytest.FixtureLookupError as error:
        if error.argname != name:
            raise
        pytest.skip(f'Implement {name}; see setup instructions in test_myaccount.py')


@pytest.fixture
def account_case(request):
    path = os.getenv('MYACCOUNT_TEST_DATA')
    if not path:
        pytest.skip('Set MYACCOUNT_TEST_DATA with inspected selectors and independent staging cases')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    case_id = re.search(r'acc_\d{3}', request.node.name).group().upper()
    case = data.get('cases', {}).get(case_id)
    if not case or not case.get('ready'):
        pytest.skip(f'{case_id}: configure baseline and ready=true')
    assert data['mobile_number'] == os.environ['TEST_MOBILE_NUMBER']
    page = MyAccountPage(None, data)
    for route in ('profile', 'cleanup'):
        assert data['routes'][route]
        for target in data['routes'][route]:
            page.locator(target)
    for key in ('baseline', 'updated'):
        if key in case:
            details = case[key]
            assert set(details) == {'name', 'gender', 'dob'}
            assert isinstance(details['name'], str)
            assert details['gender'] in ('Female', 'Male', None)
            if details['dob'] is not None:
                date.fromisoformat(details['dob'])
    for key in ('dob_steps', 'attempt_steps', 'rejection_cleanup_steps', 'validation_steps', 'back_steps'):
        for step in case.get(key, []):
            assert step['action'] in {'tap', 'visible', 'disabled', 'absent'}
            page.locator(step['target'])
    probe = integration(request, 'myaccount_save_probe') if case_id == 'ACC_020' else None
    prepare = integration(request, 'myaccount_prepare')
    request.node.user_properties.append(('tc_id', case_id))
    with prepare(case_id, case, data):
        yield data, case, probe


@pytest.fixture
def account(request, account_case):
    data, case, _ = account_case
    driver = request.getfixturevalue('driver')
    page = MyAccountPage(driver, data)
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
        page.route('profile')
        page.open()
        assert page.details() == case['baseline'], 'UI differs from independently prepared baseline'
        yield page
    finally:
        if authenticated:
            page.route('cleanup')


def fill_updated(page, account_case):
    case = account_case[1]
    assert case['updated'] != case['baseline'], 'Use changed data to exercise an update'
    assert case['updated']['name'].strip() and case['updated']['gender'] and case['updated']['dob']
    page.fill(case['updated'], case['dob_steps'])
    return case


def save_and_check(page, account_case):
    case = fill_updated(page, account_case)
    page.save()
    page.assert_profile_details(case['profile_expected'])
    return case


def test_acc_001_open_my_account(account):
    """Profile account entry opens the My Account bottom sheet."""
    account.target('sheet')


def test_acc_002_my_account_title(account):
    assert account.text('title').strip() == 'My Account'


def test_acc_003_full_name_field(account):
    assert account.target('name').is_displayed()


def test_acc_004_enter_valid_name(account):
    account.enter_name('Anjana Test')
    assert account.text('name') == 'Anjana Test'


def test_acc_005_select_female(account):
    account.select_gender('Female')
    assert account.gender_selected('Female')


def test_acc_006_select_male(account):
    account.select_gender('Male')
    assert account.gender_selected('Male')


def test_acc_007_change_gender(account):
    account.select_gender('Female')
    account.select_gender('Male')
    assert account.gender_selected('Male') and not account.gender_selected('Female')


def test_acc_008_select_dob(account, account_case):
    case = account_case[1]
    account.steps(case['dob_steps'])
    assert account.details()['dob'] == case['updated']['dob']


def test_acc_009_save_disabled_missing_required_data(account, account_case):
    baseline = account_case[1]['baseline']
    assert not baseline['name'].strip() or baseline['gender'] is None or baseline['dob'] is None
    assert not account.save_enabled()


def test_acc_010_save_enabled_valid_details(account, account_case):
    fill_updated(account, account_case)
    account.wait_save_enabled()


def test_acc_011_save_details_to_profile(account, account_case):
    save_and_check(account, account_case)


def test_acc_012_saved_details_persist_on_reopen(account, account_case):
    case = save_and_check(account, account_case)
    account.open()
    assert account.details() == case['updated']


def test_acc_013_dont_save_and_exit(account, account_case):
    case = fill_updated(account, account_case)
    account.discard()
    account.open()
    assert account.details() == case['baseline']


def test_acc_014_discarded_changes_stay_discarded(account, account_case):
    case = fill_updated(account, account_case)
    account.discard()
    # Leave Profile and navigate back before reopening to catch cached edits.
    account.route('cleanup')
    account.route('profile')
    account.open()
    assert account.details() == case['baseline']


def test_acc_015_empty_name_validation(account, account_case):
    fill_updated(account, account_case)
    account.enter_name('')
    assert account.text('name') == ''
    account.assert_blocked()


def test_acc_016_invalid_name_validation(account, account_case):
    case = fill_updated(account, account_case)
    assert case['name_rule'] and case['invalid_name'], 'Supply confirmed invalid input policy'
    account.enter_name(case['invalid_name'])
    if case.get('validation_steps'):
        account.steps(case['validation_steps'])
    account.assert_blocked(case.get('error_target'), case.get('error_text'))


def attempt_rejected_dob(page, case):
    assert case['attempt_steps']
    if case['rejection'] == 'picker':
        assert case['attempt_steps'][-1]['action'] in {'disabled', 'absent'}
    else:
        assert case['rejection'] == 'form'
    page.steps(case['attempt_steps'])
    if case.get('rejection_cleanup_steps'):
        page.steps(case['rejection_cleanup_steps'])
    if case['rejection'] == 'form':
        page.assert_blocked(case.get('error_target'), case.get('error_text'))
    else:
        assert page.details()['dob'] == case['updated']['dob'], 'Blocked picker selection changed DOB'


def test_acc_017_future_dob_rejected(account, account_case):
    case = fill_updated(account, account_case)
    assert date.fromisoformat(case['attempted_dob']) > date.fromisoformat(case['today'])
    attempt_rejected_dob(account, case)


def test_acc_018_invalid_dob_rejected(account, account_case):
    case = fill_updated(account, account_case)
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', case['attempted_dob'])
    with pytest.raises(ValueError):
        date.fromisoformat(case['attempted_dob'])
    attempt_rejected_dob(account, case)


def test_acc_019_android_back_navigation(account, account_case):
    case = fill_updated(account, account_case)
    account.dismiss_keyboard()
    account.driver.back()
    if case['back_behavior'] == 'confirm_discard':
        account.steps(case['back_steps'])
    else:
        assert case['back_behavior'] == 'discard', 'Configure confirmed Android Back behavior'
    account.wait_profile()
    account.open()
    assert account.details() == case['baseline']


def test_acc_020_multiple_save_taps_one_request(account, account_case):
    case = fill_updated(account, account_case)
    probe = account_case[2]
    with probe.capture(case) as evidence:
        account.rapid_save(case.get('save_taps', 3))
    assert type(evidence.processed_requests) is int and evidence.processed_requests == 1
    account.assert_profile_details(case['profile_expected'])
    account.open()
    assert account.details() == case['updated']
