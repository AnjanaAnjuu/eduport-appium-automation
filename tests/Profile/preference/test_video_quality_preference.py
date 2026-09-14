"""Video and shared Preferences cases. See README.md for live setup."""
from time import monotonic

import pytest

from pages.Profile.preference.Video_quality_preference import VideoQualityPreferencePage


def selection(pref, quality):
    for network in ('mobile', 'wifi'):
        pref.video.select(network, quality)


def configured(pref):
    for network, quality in pref.case['qualities'].items():
        pref.video.select(network, quality)


def assert_qualities(pref, expected):
    assert set(expected) == {'mobile', 'wifi'}
    for network, quality in expected.items():
        assert pref.video.quality(network) == pref.data['quality_labels'][quality]


def play(pref, network, quality, kind='subtopic'):
    # Different other-network setting exposes accidental selection of that value.
    pref.video.select('wifi' if network == 'mobile' else 'mobile', '240p' if quality != '240p' else '720p')
    pref.video.select(network, quality)
    with pref.hooks['network'](pref.driver, network) as connection:
        assert connection.active_transport() == network
        video = pref.video.open_video(network, kind)
        pref.video.verify_playback(pref.hooks['playback'], network, video, quality, pref.case)
        assert connection.active_transport() == network


def visual(pref, scope):
    assert pref.hooks['visual'](pref.driver, pref.case, scope) is True


def orientation(pref, value):
    original = pref.driver.orientation
    try:
        pref.driver.orientation = value
        assert pref.driver.orientation.upper() == value
        visual(pref, value.lower())
    finally:
        pref.driver.orientation = original


def test_tc_001_navigation(pref):
    pref.video.wait_loaded()


def test_tc_002_back(pref):
    pref.video.tap('back')
    pref.video.target('previous_screen')


def test_tc_003_video_section(pref):
    pref.video.section('video')


def network_row(pref, network):
    assert pref.video.quality(network) == pref.data['quality_labels'][pref.case['baseline'][network]]
    label = pref.video.target(f'{network}_network').rect
    value = pref.video.target(f'{network}_quality').rect
    assert value['x'] > label['x'], 'Selected quality should be on the right'


def test_tc_006_mobile_network(pref):
    network_row(pref, 'mobile')


def test_tc_007_wifi_network(pref):
    network_row(pref, 'wifi')


def test_tc_008_mobile_quality_sheet(pref):
    pref.video.open_quality('mobile')


def test_tc_009_wifi_quality_sheet(pref):
    pref.video.open_quality('wifi')


def option_visible(pref, key):
    pref.video.open_quality('mobile')
    pref.video.target(key)


def test_tc_010_auto_option(pref):
    option_visible(pref, 'auto')


def test_tc_011_high_quality_option(pref):
    option_visible(pref, 'high_quality')


def test_tc_012_data_saver_option(pref):
    option_visible(pref, 'data_saver')


def test_tc_013_advanced_option(pref):
    option_visible(pref, 'advanced')


def test_tc_014_advanced_resolutions(pref):
    pref.video.open_quality('mobile')
    pref.video.tap('advanced')
    for quality in ('720p', '480p', '360p', '240p'):
        assert pref.video.text(quality) == quality


def test_tc_015_select_auto(pref):
    selection(pref, 'Auto')


def test_tc_016_select_high_quality(pref):
    selection(pref, 'High Quality')


def test_tc_017_select_data_saver(pref):
    selection(pref, 'Data Saver')


def test_tc_018_select_720p(pref):
    selection(pref, '720p')


def test_tc_019_select_480p(pref):
    selection(pref, '480p')


def test_tc_020_select_360p(pref):
    selection(pref, '360p')


def test_tc_021_select_240p(pref):
    selection(pref, '240p')


def test_tc_022_independent_network_preferences(pref):
    pref.video.select('mobile', '240p')
    pref.video.select('wifi', '720p')
    pref.video.reopen()
    assert_qualities(pref, {'mobile': '240p', 'wifi': '720p'})


def test_tc_023_persist_on_reopen(pref):
    configured(pref)
    pref.video.reopen()
    assert_qualities(pref, pref.case['qualities'])


def test_tc_024_persist_after_restart(pref):
    configured(pref)
    pref.video.restart()
    assert_qualities(pref, pref.case['qualities'])


@pytest.mark.parametrize('quality', VideoQualityPreferencePage.QUALITIES)
def test_tc_025_mobile_importance_of_chemistry(pref, quality):
    play(pref, 'mobile', quality)


@pytest.mark.parametrize('quality', VideoQualityPreferencePage.QUALITIES)
def test_tc_026_wifi_laws_of_chemical_combinations(pref, quality):
    play(pref, 'wifi', quality)


def test_tc_027_resource_videos(pref):
    for network in ('mobile', 'wifi'):
        play(pref, network, pref.case['quality'], 'resource')
        pref.video.open()


def test_tc_028_subtopic_videos(pref):
    for network in ('mobile', 'wifi'):
        play(pref, network, pref.case['quality'], 'subtopic')
        pref.video.open()


def test_tc_029_single_video_override(pref):
    network = pref.case['network']
    global_quality, override = pref.case['quality'], pref.case['override_quality']
    assert global_quality != override
    selection(pref, global_quality)
    with pref.hooks['network'](pref.driver, network) as connection:
        assert connection.active_transport() == network
        video = pref.video.open_video(network)
        pref.video.verify_playback(pref.hooks['playback'], network, video, global_quality, pref.case)
        pref.video.route('player_override')
        pref.video.verify_playback(pref.hooks['playback'], network, video, override, pref.case)
        pref.video.open()
        assert_qualities(pref, {'mobile': global_quality, 'wifi': global_quality})
        # Play the other named Chemistry video on the SAME network to prove scope.
        other = pref.video.open_video('wifi' if network == 'mobile' else 'mobile')
        assert other['id'] != video['id']
        pref.video.verify_playback(pref.hooks['playback'], network, other, global_quality, pref.case)


def test_tc_030_global_change_from_player(pref):
    network = pref.case['network']
    with pref.hooks['network'](pref.driver, network) as connection:
        assert connection.active_transport() == network
        pref.video.open_video(network)
        pref.video.route('player_global_change')
        assert pref.video.text('global_quality_prompt') == pref.case['prompt_text']
        pref.video.route('prompt_to_preferences')
        pref.video.wait_loaded()


def test_tc_041_saved_preferences_offline(pref):
    configured(pref)
    with pref.hooks['network'](pref.driver, 'offline') as connection:
        assert connection.active_transport() == 'offline'
        pref.video.reopen()
        assert_qualities(pref, pref.case['qualities'])
        for section in ('audio', 'notification'):
            getattr(pref, section).section(section)
            expected = pref.case[f'{section}_baseline']
            assert expected
            for key, value in expected.items():
                assert getattr(pref, section).state(key) == value


def test_tc_042_change_preferences_offline(pref):
    assert pref.case['offline_rule'] and pref.case['offline_expected_text']
    with pref.hooks['network'](pref.driver, 'offline') as connection:
        assert connection.active_transport() == 'offline'
        pref.video.route('offline_change')
        for key, value in pref.case['offline_expected_text'].items():
            assert pref.video.text(key) == value
    pref.video.reopen()
    assert_qualities(pref, pref.case['reconnected_qualities'])


def test_tc_043_loading(pref):
    assert pref.case['max_load_seconds'] > 0
    start = monotonic()
    pref.video.reopen()
    assert monotonic() - start <= pref.case['max_load_seconds']
    assert not pref.video.is_visible(pref.video.locator('error'), 0.2)


def test_tc_044_api_failure(pref):
    with pref.hooks['fault'](pref.driver, pref.case):
        pref.video.route('reload')
        assert pref.video.text('error') == pref.case['error_text']


def test_tc_045_text_alignment(pref):
    visual(pref, 'long_labels')


def test_tc_046_dismiss_outside(pref):
    before = pref.video.quality('mobile')
    pref.video.open_quality('mobile')
    pref.video.tap('sheet_backdrop')
    pref.video.wait.invisible(pref.video.locator('quality_sheet'))
    assert pref.video.quality('mobile') == before


def test_tc_047_dismiss_back(pref):
    pref.video.open_quality('mobile')
    pref.driver.back()
    pref.video.wait.invisible(pref.video.locator('quality_sheet'))
    pref.video.wait_loaded()


def test_tc_048_single_selection(pref):
    pref.video.select('mobile', 'Auto')
    pref.video.select('mobile', 'Data Saver')
    pref.video.assert_selection('mobile', 'Data Saver')


def test_tc_049_selection_indicator(pref):
    pref.video.select('mobile', '720p')
    pref.video.assert_selection('mobile', '720p')
    visual(pref, 'selection_tick')


def test_tc_050_portrait(pref):
    orientation(pref, 'PORTRAIT')


def test_tc_051_landscape(pref):
    if not pref.case['landscape_supported']:
        pytest.skip('Landscape is not supported by this build')
    orientation(pref, 'LANDSCAPE')


def platform_check(pref, name):
    if pref.driver.capabilities['platformName'].lower() != name.lower():
        pytest.skip(f'Requires {name}')
    pref.video.select('mobile', '480p')
    pref.video.reopen()
    assert pref.video.quality('mobile') == pref.data['quality_labels']['480p']


def test_tc_052_android(pref):
    platform_check(pref, 'Android')


def test_tc_053_ios(pref):
    platform_check(pref, 'iOS')


def test_tc_054_tablet(pref):
    assert pref.case['device_form_factor'] == 'tablet'
    visual(pref, 'tablet')


def test_tc_056_quality_accessibility(pref):
    pref.video.open_quality('mobile')
    for key in pref.video.OPTIONS:
        pref.video.accessible(key)
    pref.video.tap('advanced')
    for key in pref.video.QUALITIES[3:]:
        pref.video.accessible(key)


def test_tc_057_logout_login_preferences(pref):
    assert pref.case['relogin_rule']
    configured(pref)
    pref.hooks['relogin'](pref.driver, pref.case)
    pref.video.open()
    assert_qualities(pref, pref.case['after_login'])
    for section in ('audio', 'notification'):
        getattr(pref, section).section(section)
        expected = pref.case[f'{section}_after_login']
        assert expected
        for key, value in expected.items():
            assert getattr(pref, section).state(key) == value


def test_tc_058_consecutive_changes(pref):
    for quality in ('720p', '240p', 'Auto', '480p'):
        pref.video.select('mobile', quality)
    pref.video.reopen()
    assert pref.video.quality('mobile') == pref.data['quality_labels']['480p']


def test_tc_059_performance(pref):
    assert pref.case['max_save_seconds'] > 0
    assert pref.case['max_load_seconds'] > 0
    start = monotonic()
    pref.video.reopen()
    assert monotonic() - start <= pref.case['max_load_seconds']
    start = monotonic()
    pref.video.select('mobile', '360p')
    assert monotonic() - start <= pref.case['max_save_seconds']
    pref.video.reopen()
    assert pref.video.quality('mobile') == pref.data['quality_labels']['360p']


def test_tc_060_approved_design(pref):
    visual(pref, 'full_preferences')
