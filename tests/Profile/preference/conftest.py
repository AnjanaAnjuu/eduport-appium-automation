"""Read README.md for session, seed, network and playback integration contracts."""
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

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
        pytest.skip('Set PREFERENCE_TEST_DATA with inspected selectors and case prerequisites')
    data = json.loads(Path(path).read_text())
    tc = re.search(r'tc_\d{3}', request.node.name).group().upper()
    case = data.get('cases', {}).get(tc)
    if not case or not case.get('ready'):
        pytest.skip(f'{tc}: configure independent case data and ready=true')
    request.node.user_properties.append(('tc_id', tc))
    return data, dict(case, tc_id=tc)


@pytest.fixture
def pref(request, preference_case):
    data, case = preference_case
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
