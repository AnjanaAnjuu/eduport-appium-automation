"""Read README.md for session, seed, network and playback integration contracts."""
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
from contextlib import ExitStack

import pytest

from pages.Profile.preference.Video_quality_preference import VideoQualityPreferencePage
from pages.Profile.preference.audio_sticker_preference import AudioStickerPreferencePage
from pages.Profile.preference.Notification_preference import NotificationPreferencePage


def provider(request, name):
    try:
        return request.getfixturevalue(name)
    except pytest.FixtureLookupError as error:
        if error.argname != name:
            raise
        pytest.skip(f'Implement {name}; see tests/Profile/preference/README.md')


@pytest.fixture
def preference_case(request):
    path = os.getenv('PREFERENCE_TEST_DATA')
    if not path:
        path = Path(__file__).resolve().parents[3] / 'test_data/preference_live.json'
    data = json.loads(Path(path).read_text())
    tc = re.search(r'tc_\d{3}', request.node.name).group().upper()
    case = data.get('cases', {}).get(tc)
    if not case or not case.get('ready'):
        pytest.skip(f"{tc}: {(case or {}).get('skip_reason', 'configure independent case data and ready=true')}")
    request.node.user_properties.append(('tc_id', tc))
    return data, dict(case, tc_id=tc)


@pytest.fixture(scope='module')
def preference_live_session():
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    from tests.Profile.mycourse.live_support import CourseSession
    if not (os.getenv('TEST_MOBILE_NUMBER') and os.getenv('TEST_VALID_OTP')
            and os.getenv('ALLOW_OTP_SEND', '').lower() == 'true'):
        pytest.skip('Set authorized TEST_MOBILE_NUMBER, TEST_VALID_OTP, and ALLOW_OTP_SEND=true')
    session = CourseSession()
    try:
        session.driver.activate_app('com.dev.eduportlms')
        def ready(driver):
            deny = driver.find_elements(AppiumBy.XPATH,
                "//*[contains(@package,'permissioncontroller') and contains(@resource-id,':id/permission_deny')]")
            if deny:
                deny[0].click()
            if driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Confirm your Birthday'):
                driver.back()
            return driver.find_elements(AppiumBy.XPATH,
                "//*[@content-desc='Profile' or @content-desc='Home' or @content-desc='Preferences' "
                "or @content-desc='Send OTP' or @content-desc='OTP Verifications' or @content-desc='Enter Your Details']")
        WebDriverWait(session.driver, 30).until(ready)
        if session.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Enter Your Details'):
            pytest.skip(f"Account {os.environ['TEST_MOBILE_NUMBER']} is on Enter Your Details; complete its name/gender onboarding before Preferences tests can run")
        session.profile()
        session.authenticate()
        yield session
    finally:
        session.driver.quit()


@pytest.fixture
def pref(request, preference_case):
    data, case = preference_case
    if data.get('mode') == 'live_android':
        from tests.Profile.preference.live_support import LiveVideo, LiveAudio, LiveNotification, notification_policy_access
        session = request.getfixturevalue('preference_live_session')
        request.node._appium_driver = session.driver
        context = SimpleNamespace(data=data, case=case, hooks={}, driver=session.driver,
            video=LiveVideo(session.driver, data), audio=LiveAudio(session.driver, data),
            notification=LiveNotification(session.driver, data))
        original = {}
        original_quality = {}
        permissions = ExitStack()
        try:
            context.video.open()
            number = int(case['tc_id'][-3:])
            if number in range(31, 39):
                key = context.audio.TOGGLES[(number - 31) % 4]
                original = {key: context.audio.state(key)}
                context.video.open()
            if number == 40:
                permissions.enter_context(notification_policy_access(session.driver, data['app_id']))
                original = {key: context.notification.state(key) for key in data['notification_controls']}
                context.video.open()
            if number in {*range(15,25),52,58}:
                original_quality = {network: context.video.quality(network) for network in ('mobile','wifi')}
            yield context
        finally:
            try:
                if original:
                    context.audio.open()
                    for key, value in original.items():
                        context.audio.target(key)
                        context.audio.toggle(key, value)
                        assert context.audio.state(key) == value, f'Could not restore {key}'
                if original_quality:
                    context.video.open()
                    inverse = {label: quality for quality, label in data['quality_labels'].items()}
                    for network, label in original_quality.items():
                        context.video.select(network, inverse[label])
                session.profile()
            finally:
                try:
                    permissions.close()
                finally:
                    request.node._appium_driver = None
        return
    number = int(case['tc_id'][-3:])
    hooks = {}
    needed = {'network': {25,26,27,28,29,30,41,42}, 'playback': {25,26,27,28,29},
              'fault': {44}, 'visual': {45,49,50,51,54,60}, 'relogin': {57}}
    for key, cases in needed.items():
        if number in cases:
            hooks[key] = provider(request, f'preference_{key}')
    session = provider(request, 'preference_session')
    # Session owns platform-specific login, isolated preferences and restoration.
    with session(data, case) as driver:
        request.node._appium_driver = driver
        context = SimpleNamespace(data=data, case=case, hooks=hooks, driver=driver,
            video=VideoQualityPreferencePage(driver, data),
            audio=AudioStickerPreferencePage(driver, data),
            notification=NotificationPreferencePage(driver, data))
        try:
            context.video.open()
            yield context
        finally:
            request.node._appium_driver = None
