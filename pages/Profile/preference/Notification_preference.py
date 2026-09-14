"""Notification preferences; exact controls were not shown in the screenshot."""
from pages.Profile.preference.preferences_page import PreferencesPage


class NotificationPreferencePage(PreferencesPage):
    def controls(self):
        controls = self.data['notification_controls']
        assert controls, 'Configure actual notification toggle selector names'
        self.section('notification')
        for key in controls:
            self.target(key)
        return controls

    def update_and_verify(self):
        before = {key: self.state(key) for key in self.controls()}
        for key, value in before.items():
            self.toggle(key, not value)
        self.reopen()
        self.controls()
        assert {key: self.state(key) for key in before} == {key: not value for key, value in before.items()}
