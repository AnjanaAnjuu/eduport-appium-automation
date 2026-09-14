"""Audio/sticker cases from the supplied acceptance table."""


def test_tc_004_audio_section(pref):
    pref.audio.section('audio')


def test_tc_031_sound_effects_toggle(pref):
    pref.audio.verify_roundtrip('sound_effects')


def test_tc_032_launch_sound_toggle(pref):
    pref.audio.verify_roundtrip('app_launch_sound')


def test_tc_033_stickers_toggle(pref):
    pref.audio.verify_roundtrip('stickers')


def test_tc_034_app_icon_toggle(pref):
    pref.audio.verify_roundtrip('app_icon_change')


def test_tc_035_sound_effects_restart(pref):
    pref.audio.verify_restart('sound_effects')


def test_tc_036_launch_sound_restart(pref):
    pref.audio.verify_restart('app_launch_sound')


def test_tc_037_stickers_restart(pref):
    pref.audio.verify_restart('stickers')


def test_tc_038_app_icon_restart(pref):
    pref.audio.verify_restart('app_icon_change')


def test_tc_055_toggle_accessibility(pref):
    pref.audio.section('audio')
    for key in pref.audio.TOGGLES:
        pref.audio.accessible(key)
    for key in pref.notification.controls():
        pref.notification.accessible(key)
