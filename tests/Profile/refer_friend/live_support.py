"""Android emulator setup and observed native share activity evidence."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import time

from appium.webdriver.common.appiumby import AppiumBy

from config.config import settings
from tests.Profile.mycourse.live_support import CourseSession, scroll_profile


def live_data():
    return {
        'mode': 'live_android', 'app_id': settings.app_package,
        'selectors': {
            'profile_screen': [AppiumBy.XPATH, "//android.view.View[@content-desc='Profile']"],
            'refer_friend': [AppiumBy.ACCESSIBILITY_ID, 'Refer\na Friend'],
            'share_sheet': [AppiumBy.ID, 'android:id/chooser_header'],
        },
    }


@contextmanager
def live_session(data, case):
    session = CourseSession()
    driver = session.driver
    try:
        driver.activate_app(settings.app_package)
        # Return from a previous child page/share sheet before login detection.
        session.profile()
        session.authenticate()
        assert session.profile()
        for _ in range(20):
            buttons = driver.find_elements(*data['selectors']['refer_friend'])
            if buttons:
                rect = buttons[0].rect
                # Keep repeated taps above the native sheet's share targets.
                if 250 < rect['y'] and rect['y'] + rect['height'] < 1000:
                    break
            scroll_profile(driver, 'up')
        else:
            raise AssertionError('Could not scroll Refer a Friend into the upper Profile area')
        yield driver
    finally:
        try:
            if driver.current_package == 'com.android.intentresolver':
                driver.back()
            driver.activate_app(settings.app_package)
            session.profile()
        finally:
            driver.quit()


class AndroidShareProbe:
    def __init__(self):
        self.adb = os.getenv('ADB_PATH') or shutil.which('adb') or str(
            Path.home() / 'Library/Android/sdk/platform-tools/adb')
        self.udid = settings.udid or 'emulator-5554'

    def events(self):
        result = subprocess.run(
            [self.adb, '-s', self.udid, 'logcat', '-d', '-b', 'events', '-v', 'epoch'],
            capture_output=True, text=True, check=True, timeout=15,
        )
        return result.stdout.splitlines()

    def cursor(self, driver):
        lines = self.events()
        assert lines, 'Android activity event log is unavailable'
        return lines[-1]

    def sheet_info(self, driver):
        return {
            'native': driver.current_package == 'com.android.intentresolver',
            'visible_sheet_count': len(driver.find_elements(AppiumBy.ID, 'android:id/chooser_header')),
        }

    def sheet_launches_since(self, driver, cursor):
        # Allow queued launches to arrive after dismissal; never clear device logs.
        time.sleep(2)
        lines = self.events()
        assert cursor in lines, 'Activity log rotated; duplicate launch evidence is incomplete'
        recent = lines[lines.index(cursor) + 1:]
        evidence = Path(__file__).resolve().parents[3] / 'reports' / 'refer_share_events.txt'
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text('\n'.join(recent), encoding='utf-8')
        return sum(
            'com.android.intentresolver/.ChooserActivity' in line
            and ('wm_create_activity:' in line or 'wm_new_intent:' in line)
            for line in recent
        )
