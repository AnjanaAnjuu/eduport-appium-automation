"""Verify the active keyboard's input class using Android editor metadata."""

import os
from pathlib import Path
import re
import shutil
import subprocess

from utils.waits import Waits


def assert_numeric_keyboard(driver, timeout: int = 5) -> None:
    Waits(driver, timeout).until(lambda d: d.is_keyboard_shown(),
                                message='Keyboard was not displayed')
    adb = os.getenv('ANDROID_ADB') or shutil.which('adb')
    if not adb:
        sdk = Path(os.getenv('ANDROID_HOME', str(Path.home() / 'Library/Android/sdk')))
        adb = str(sdk / 'platform-tools/adb')
    udid = os.getenv('ANDROID_UDID') or driver.capabilities.get('udid') or driver.capabilities.get('deviceUDID')
    if not udid:
        raise RuntimeError('ANDROID_UDID is required for numeric keyboard verification')
    result = subprocess.run([adb, '-s', udid, 'shell', 'dumpsys', 'input_method'],
                            capture_output=True, text=True, timeout=15, check=True)
    # Select the latest StartInput record, not any historical numeric record.
    records = re.findall(r'StartInput #(\d+):.*?targetWin=.*?\[([^\]]+)\].*?inputType=(0x[0-9a-fA-F]+)',
                         result.stdout, flags=re.DOTALL)
    if not records:
        raise AssertionError('Android did not report active editor input metadata')
    _, package, input_type = max(records, key=lambda record: int(record[0]))
    assert package == driver.current_package, 'Keyboard targets another application'
    assert int(input_type, 16) & 0xF in {2, 3}, f'Expected number/phone input class, got {input_type}'
