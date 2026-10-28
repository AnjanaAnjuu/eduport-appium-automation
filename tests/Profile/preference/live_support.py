"""Inspected Android Preferences navigation; restore switches after each case."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import shutil
import subprocess
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException

from pages.Profile.preference.Video_quality_preference import VideoQualityPreferencePage
from pages.Profile.preference.audio_sticker_preference import AudioStickerPreferencePage
from pages.Profile.preference.Notification_preference import NotificationPreferencePage
from tests.Profile.mycourse.live_support import scroll_profile


@contextmanager
def notification_policy_access(driver, app_id):
    """Temporarily prepare the OS permission required by the DND switch."""
    adb = os.getenv('ADB_PATH') or shutil.which('adb') or str(Path.home() / 'Library/Android/sdk/platform-tools/adb')
    serial = driver.capabilities['deviceUDID']
    def shell(*args):
        return subprocess.run([adb, '-s', serial, 'shell', *args],
            check=True, capture_output=True, text=True, timeout=20).stdout.strip()
    user = shell('am', 'get-current-user')
    def allowed():
        dump = shell('dumpsys', 'notification')
        assert 'Allowed condition providers:' in dump, 'Cannot read the original DND access list'
        section = dump.split('Allowed condition providers:', 1)[1].split('Has user set:', 1)[0]
        entries = re.findall(r'^\s*(\S+) \(user: ' + re.escape(user) + r' isPrimary:', section, re.M)
        return {package for entry in entries for package in entry.split(':')}
    original_access = app_id in allowed()
    original_zen = shell('settings', 'get', 'global', 'zen_mode')
    assert original_zen in ('0','1','2','3'), 'Cannot snapshot the original DND mode'
    try:
        if not original_access:
            shell('cmd', 'notification', 'allow_dnd', app_id, user)
        assert app_id in allowed(), 'DND access preparation failed'
        yield
    finally:
        if shell('settings', 'get', 'global', 'zen_mode') != original_zen:
            shell('cmd', 'notification', 'set_dnd', {'0':'off','1':'priority','2':'none','3':'alarms'}[original_zen])
        if not original_access:
            shell('cmd', 'notification', 'disallow_dnd', app_id, user)
        assert (app_id in allowed()) == original_access, 'DND access restoration failed'


class LivePreferencesMixin:
    def state(self, key):
        # Flutter replaces switch nodes after updates; read a fresh node.
        return WebDriverWait(self.driver, 15, ignored_exceptions=(StaleElementReferenceException,)).until(
            lambda _: (super(LivePreferencesMixin, self).state(key),)
        )[0]

    def dismiss_notification_prompt(self):
        buttons = self.driver.find_elements(AppiumBy.XPATH,
            "//*[contains(@package,'permissioncontroller') and "
            "contains(@resource-id,':id/permission_deny')]")
        if buttons:
            buttons[0].click()
        if self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Confirm your Birthday'):
            self.driver.back()

    def scroll_to(self, key):
        elements = self.driver.find_elements(*self.locator(key))
        if elements and self.is_element_within_screen(elements[0], self.driver.get_window_size()):
            return elements[0]
        # Start at the top when a section has already scrolled out of view.
        for _ in range(10):
            before = self.driver.page_source
            scroll_profile(self.driver, 'down')
            elements = self.driver.find_elements(*self.locator(key))
            if elements and self.is_element_within_screen(elements[0], self.driver.get_window_size()):
                return elements[0]
            if self.driver.page_source == before:
                break
        for _ in range(16):
            elements = self.driver.find_elements(*self.locator(key))
            if elements and self.is_element_within_screen(elements[0], self.driver.get_window_size()):
                return elements[0]
            scroll_profile(self.driver, 'up')
        raise AssertionError(f'Preferences control {key} was not visible after scrolling')

    def open(self):
        from tests.Profile.mycourse.live_support import CourseSession
        session = CourseSession.__new__(CourseSession)
        session.driver = self.driver
        self.dismiss_notification_prompt()
        assert session.profile(), 'Login is required to open Preferences'
        self.scroll_to('preferences_entry').click()
        self.wait_loaded()

    def wait_loaded(self):
        assert self.text('title') == 'Preferences'
        self.section('video')

    def section(self, key):
        self.scroll_to(f'{key}_section')

    def target(self, key):
        if key in (*AudioStickerPreferencePage.TOGGLES, *self.data.get('notification_controls', [])):
            self.scroll_to(key)
        return super().target(key)

    def restart(self):
        self.driver.terminate_app(self.data['app_id'])
        self.driver.activate_app(self.data['app_id'])
        def ready(driver):
            self.dismiss_notification_prompt()
            return driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Profile')
        WebDriverWait(self.driver, 25).until(ready)
        self.open()


class LiveVideo(LivePreferencesMixin, VideoQualityPreferencePage):
    def quality(self, network):
        self.section('video')
        return self.text(f'{network}_quality').splitlines()[-1]

    def select(self, network, quality):
        assert quality in self.QUALITIES
        self.open_quality(network)
        if quality.endswith('p'):
            self.tap('advanced')
            self.target('advanced_sheet')
        self.tap(self.option(quality))
        # This build saves the choice while leaving its sheet open.
        for _ in range(2):
            if self.is_visible(self.locator('quality_sheet'), .3) or self.is_visible(self.locator('advanced_sheet'), .3):
                self.driver.back()
        self.wait.until(lambda _: self.quality(network) == self.data['quality_labels'][quality],
                        f'{network} did not save quality {quality}')


class LiveAudio(LivePreferencesMixin, AudioStickerPreferencePage):
    pass


class LiveNotification(LivePreferencesMixin, NotificationPreferencePage):
    pass
