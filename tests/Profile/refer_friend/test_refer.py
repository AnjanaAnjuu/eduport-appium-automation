"""Three focused referral cases; configuration is documented in README.md."""
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from pages.Profile.refer_friend.refer_page import ReferPage
from pages.Profile.refer_friend.refer_friend_page import validate_download_url
from tests.Profile.refer_friend.live_support import live_data, live_session, AndroidShareProbe


def required_provider(request, name):
    try:
        return request.getfixturevalue(name)
    except pytest.FixtureLookupError as error:
        if error.argname != name:
            raise
        pytest.skip(f'Missing {name}; see tests/Profile/refer_friend/README.md')


@pytest.fixture
def refer(request):
    path = os.getenv('REFER_FRIEND_TEST_DATA')
    data = json.loads(Path(path).read_text(encoding='utf-8')) if path else live_data()
    validator = ReferPage(None, data)
    case_id = request.node.name.split('_')[1].upper()
    request.node.user_properties.append(('tc_id', case_id))
    case = dict(data.get('focused_cases', {}).get(case_id, {}), tc_id=case_id)
    if data.get('mode') == 'live_android':
        if not (os.getenv('TEST_MOBILE_NUMBER') and os.getenv('TEST_VALID_OTP')
                and os.getenv('ALLOW_OTP_SEND', '').lower() == 'true'):
            pytest.skip('Set TEST_MOBILE_NUMBER, TEST_VALID_OTP, and ALLOW_OTP_SEND=true for live login')
        with live_session(data, case) as driver:
            request.node._appium_driver = driver
            try:
                page = ReferPage(driver, data)
                page.open_profile()
                yield SimpleNamespace(page=page, probe=AndroidShareProbe(), case=case)
            finally:
                request.node._appium_driver = None
        return
    assert data['routes']['profile'], 'Configure a route from the authenticated screen to Profile'
    for key in data['routes']['profile']:
        validator.locator(key)
    probe = None
    if case_id == 'REF002':
        validate_download_url(data['download_url'])
        for key in ('url_destination', 'opened_url'):
            validator.locator(key)
    if case_id == 'REF003':
        for key in ('share_sheet', 'cancel_share'):
            validator.locator(key)
        probe = required_provider(request, 'referral_share_probe')
    session = required_provider(request, 'referral_session')
    with session(data, case) as driver:
        request.node._appium_driver = driver
        try:
            page = ReferPage(driver, data)
            page.open_profile()
            yield SimpleNamespace(page=page, probe=probe, case=case)
        finally:
            request.node._appium_driver = None


def test_ref001_refer_a_friend_button_is_visible_and_enabled(refer):
    refer.page.assert_button_available()


def test_ref002_click_refer_a_friend_opens_url(refer):
    refer.page.open_url()


def test_ref003_multiple_taps_open_only_one_share_sheet(refer):
    refer.page.assert_single_share_sheet(refer.probe, refer.case.get('tap_count', 3))
