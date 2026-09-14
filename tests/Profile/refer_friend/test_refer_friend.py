"""TC_001–TC_025 from the supplied Refer a Friend table and share-sheet image.

Run: venv/bin/python -m pytest tests/Profile/refer_friend/test_refer_friend.py
See README.md in this directory for selectors, session and evidence providers.
No messages are sent without an explicitly configured controlled recipient.
"""
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest

from pages.Profile.refer_friend.refer_friend_page import ReferFriendPage, validate_download_url


@pytest.fixture
def referral_case(request):
    path = os.getenv('REFER_FRIEND_TEST_DATA')
    if not path:
        pytest.skip('Set REFER_FRIEND_TEST_DATA; see Profile/refer_friend/README.md')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    tc_id = re.search(r'tc_\d{3}', request.node.name).group().upper()
    case = data.get('cases', {}).get(tc_id)
    if not case or not case.get('ready'):
        pytest.skip(f'{tc_id}: configure independent prerequisites and ready=true')
    validate_download_url(data['download_url'])
    assert data['app_name'] and data['expected_message']
    validator = ReferFriendPage(None, data)
    for key in data['selectors']:
        validator.locator(key)
    assert data['routes']['profile']
    for route in data['routes'].values():
        for key in route:
            validator.locator(key)
    request.node.user_properties.append(('tc_id', tc_id))
    return data, dict(case, tc_id=tc_id)


def provider(request, name):
    try:
        return request.getfixturevalue(name)
    except pytest.FixtureLookupError as error:
        if error.argname != name:
            raise
        pytest.skip(f'Implement fixture {name}; see refer_friend/README.md')


@pytest.fixture
def referral(request, referral_case):
    data, case = referral_case
    number = int(case['tc_id'][-3:])
    hooks = {'share': provider(request, 'referral_share_probe')}
    needed = {'delivery': set(range(4, 10)), 'recipient': set(range(13, 18)),
              'network': {18}, 'visual': {21, 25}}
    for key, cases in needed.items():
        if number in cases:
            hooks[key] = provider(request, f'referral_{key}')
    if number in range(4, 10):
        if not case.get('authorized_test_recipient'):
            pytest.skip('Configure authorized_test_recipient for a controlled delivery test')
    session = provider(request, 'referral_session')
    with session(data, case) as driver:
        request.node._appium_driver = driver
        try:
            page = ReferFriendPage(driver, data)
            page.open_profile()
            yield SimpleNamespace(page=page, driver=driver, data=data, case=case, hooks=hooks)
        finally:
            request.node._appium_driver = None


def opened(referral):
    referral.page.open_share()
    return referral.page


def payload(referral):
    opened(referral)
    result = referral.hooks['share'].payload(referral.driver)
    referral.page.assert_payload(result)
    return result


def deliver(referral, medium):
    if not referral.hooks['delivery'].available(referral.driver, medium):
        pytest.skip(f'{medium} is not installed/configured on this test device')
    shared = payload(referral)
    referral.page.choose_medium(medium)
    # The provider captures a delivery baseline before sending and correlates
    # actual recipient evidence; opening a composer alone cannot pass this case.
    receipt = referral.hooks['delivery'].send_and_wait(
        referral.driver, medium, referral.case['authorized_test_recipient'], shared, referral.case)
    assert receipt['medium'] == medium
    assert receipt['recipient'] == referral.case['authorized_test_recipient']
    assert receipt['delivered'] is True and receipt['message_id']
    assert receipt['text'] == shared['text']


def recipient_flow(referral, state):
    actual = payload(referral)
    url = referral.data['download_url']
    referral.page.assert_payload(actual)
    # Provider uses a separate disposable recipient device, not the sender.
    result = referral.hooks['recipient'].open_url(url, state, referral.case)
    assert result['opened_url'] == url
    return result


def test_tc_001_navigation_from_profile(referral):
    opened(referral)


def test_tc_002_native_share_sheet(referral):
    opened(referral)
    info = referral.hooks['share'].sheet_info(referral.driver)
    assert info['native'] is True and info['owner'] == referral.case['native_sheet_owner']


def test_tc_003_download_url_in_shared_content(referral):
    payload(referral)


def test_tc_004_share_whatsapp(referral):
    deliver(referral, 'whatsapp')


def test_tc_005_share_sms(referral):
    deliver(referral, 'sms')


def test_tc_006_share_email(referral):
    deliver(referral, 'email')


def test_tc_007_share_telegram(referral):
    deliver(referral, 'telegram')


def test_tc_008_share_slack(referral):
    deliver(referral, 'slack')


def test_tc_009_bluetooth_nearby_share(referral):
    medium = referral.case['medium']
    assert medium in ('bluetooth', 'nearby_share')
    deliver(referral, medium)


def test_tc_010_copy_link(referral):
    # Overwrite with a unique sentinel to exclude stale clipboard false passes.
    sentinel = f'referral-test-{uuid4()}'
    referral.driver.set_clipboard_text(sentinel)
    opened(referral)
    referral.page.tap('copy_link')
    referral.page.wait.until(lambda _: referral.page.clipboard() != sentinel)
    copied = referral.page.clipboard()
    expected = referral.case['expected_clipboard']
    assert copied == expected
    referral.page.assert_payload({'text': copied, 'mime_type': 'text/plain'})


def test_tc_011_cancel_share_sheet(referral):
    probe = referral.hooks['share']
    cursor = probe.cursor(referral.driver)
    opened(referral).cancel()
    assert probe.actions_since(referral.driver, cursor) == [], 'Cancel triggered a share/copy action'


def test_tc_012_multiple_share_options(referral):
    opened(referral)
    # Probe traverses every native share page; direct-share contacts are not apps.
    options = referral.hooks['share'].all_targets(referral.driver)
    expected = set(referral.case['supported_targets'])
    assert len(expected) >= 2
    assert expected <= set(options), 'Supported installed share targets are missing'


def test_tc_013_shared_url_valid(referral):
    result = recipient_flow(referral, 'browser')
    assert result['opened_url'] == referral.data['download_url']
    assert result['navigation_error'] is None
    assert 200 <= result['final_http_status'] < 400
    assert result['final_host'] in referral.case['allowed_destination_hosts']


def test_tc_014_installed_logged_in_deep_link(referral):
    result = recipient_flow(referral, 'installed_logged_in')
    assert result['initial_installed'] is True and result['initial_logged_in'] is True
    assert result['foreground_app'] == referral.data['app_id']
    assert result['screen'] == referral.case['expected_destination']
    assert result['login_presented'] is False and result['store_presented'] is False


def test_tc_015_installed_logged_out_deep_link(referral):
    assert referral.case['post_login_rule']
    result = recipient_flow(referral, 'installed_logged_out_then_login')
    assert result['initial_installed'] is True and result['initial_logged_in'] is False
    assert result['login_presented'] is True and result['login_completed'] is True
    assert result['foreground_app'] == referral.data['app_id']
    assert result['screen'] == referral.case['expected_destination']


def test_tc_016_app_not_installed_store_redirect(referral):
    result = recipient_flow(referral, 'not_installed')
    assert result['initial_installed'] is False
    assert result['store_presented'] is True
    assert result['store_app_id'] == referral.data['store_app_id']
    assert result['store'] == referral.case['expected_store']


def test_tc_017_link_destination_after_install(referral):
    result = recipient_flow(referral, 'install_after_link')
    assert result['initial_installed'] is False and result['installed_during_flow'] is True
    assert result['store_presented'] is True
    assert result['store_app_id'] == referral.data['store_app_id']
    assert result['foreground_app'] == referral.data['app_id']
    assert result['screen'] == referral.case['expected_destination']
    assert result['launched_from_install_flow'] is True


def test_tc_018_share_offline(referral):
    assert referral.case['offline_rule']
    with referral.hooks['network'](referral.driver, 'offline') as network:
        assert network.active_transport() == 'offline'
        behavior = referral.case['offline_behavior']
        if behavior == 'share_sheet':
            payload(referral)
        else:
            assert behavior == 'error'
            referral.page.tap('refer_friend')
            assert referral.page.text('offline_error') == referral.case['offline_error']


def platform_case(referral, platform):
    if referral.driver.capabilities['platformName'].lower() != platform.lower():
        pytest.skip(f'Requires {platform}')
    payload(referral)
    referral.page.cancel()


def test_tc_019_android(referral):
    platform_case(referral, 'Android')


def test_tc_020_ios(referral):
    platform_case(referral, 'iOS')


def test_tc_021_tablet(referral):
    assert referral.case['device_form_factor'] == 'tablet'
    payload(referral)
    assert referral.hooks['visual'](referral.driver, referral.case, 'tablet_share_sheet') is True


def test_tc_022_back_after_share_sheet(referral):
    opened(referral).cancel()
    referral.page.tap('profile_back')
    referral.page.target('previous_screen')


def test_tc_023_shared_message_format(referral):
    referral.page.assert_message(payload(referral))


def test_tc_024_no_duplicate_share_sheets(referral):
    probe = referral.hooks['share']
    cursor = probe.cursor(referral.driver)
    referral.page.rapid_share(referral.case.get('tap_count', 3))
    info = probe.sheet_info(referral.driver)
    assert info['visible_sheet_count'] == 1
    referral.page.cancel()
    assert probe.sheet_launches_since(referral.driver, cursor) == 1
    assert not referral.page.is_visible(referral.page.locator('share_sheet'), 1)


def test_tc_025_approved_design(referral):
    payload(referral)
    assert referral.hooks['visual'](referral.driver, referral.case, 'profile_and_native_share') is True
    referral.page.cancel()
