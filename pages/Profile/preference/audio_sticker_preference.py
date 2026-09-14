"""Audio, sticker and special-day app-icon preference switches."""
from pages.Profile.preference.preferences_page import PreferencesPage


class AudioStickerPreferencePage(PreferencesPage):
    TOGGLES = ('sound_effects', 'app_launch_sound', 'stickers', 'app_icon_change')

    def set_preference(self, key, enabled):
        assert key in self.TOGGLES
        self.section('audio')
        self.toggle(key, enabled)

    def verify_roundtrip(self, key):
        for enabled in (False, True):
            self.set_preference(key, enabled)
            self.reopen()
            self.section('audio')
            assert self.state(key) == enabled

    def verify_restart(self, key):
        self.section('audio')
        changed = not self.state(key)
        self.set_preference(key, changed)
        self.restart()
        self.section('audio')
        assert self.state(key) == changed
