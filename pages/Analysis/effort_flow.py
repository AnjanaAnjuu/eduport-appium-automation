"""Inspected, declarative UI steps for Effort Tracker activity scenarios."""
import time

from appium.webdriver.common.appiumby import AppiumBy
from pages.base_page import BasePage


class EffortFlowPage(BasePage):
    STRATEGIES = {
        'accessibility id': AppiumBy.ACCESSIBILITY_ID,
        'id': AppiumBy.ID,
        'xpath': AppiumBy.XPATH,
        'class name': AppiumBy.CLASS_NAME,
        '-android uiautomator': AppiumBy.ANDROID_UIAUTOMATOR,
    }

    def __init__(self, driver, selectors, timeout=15):
        super().__init__(driver, timeout)
        self.selectors = selectors

    def locator(self, name):
        spec = self.selectors.get(name)
        if (not isinstance(spec, (list, tuple)) or len(spec) != 2
                or spec[0] not in self.STRATEGIES or not spec[1]):
            raise ValueError(f'Provide inspected selector for {name!r}')
        return self.STRATEGIES[spec[0]], spec[1]

    def validate(self, steps):
        if not isinstance(steps, list) or not steps:
            raise ValueError('Each activity phase needs nonempty UI steps')
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError(f'Invalid UI step: {step!r}')
            action = step.get('action')
            if action in ('tap', 'visible', 'absent'):
                self.locator(step.get('target'))
            elif action in ('wait_seconds', 'screen_off'):
                seconds = step.get('seconds')
                if not isinstance(seconds, (int, float)) or not 0 < seconds <= 360:
                    raise ValueError(f'{action} requires seconds in (0, 360]')
            elif action == 'scroll':
                self.locator(step.get('target'))
                if step.get('direction') not in ('up', 'down', 'left', 'right'):
                    raise ValueError('scroll needs up/down/left/right direction')
                if not isinstance(step.get('percent', .8), (int, float)) or not 0 < step.get('percent', .8) <= 1:
                    raise ValueError('scroll percent must be in (0, 1]')
            elif action == 'swipe_element':
                self.locator(step.get('target'))
                fractions = (step.get('from_fraction'), step.get('to_fraction'))
                if any(not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in fractions):
                    raise ValueError('swipe_element fractions must be in [0, 1]')
                if not isinstance(step.get('speed', 300), (int, float)) or step.get('speed', 300) <= 0:
                    raise ValueError('swipe_element speed must be positive')
            elif action == 'restart_app':
                if not isinstance(step.get('app_package'), str) or not step['app_package']:
                    raise ValueError('restart_app needs an app_package')
            elif action != 'back':
                raise ValueError(f'Unsupported UI action: {action!r}')

    def steps(self, steps):
        self.validate(steps)
        for step in steps:
            action = step['action']
            if action == 'tap':
                self.click(self.locator(step['target']))
            elif action == 'visible':
                self.element(self.locator(step['target']))
            elif action == 'absent':
                self.wait.invisible(self.locator(step['target']))
            elif action == 'wait_seconds':
                time.sleep(step['seconds'])
            elif action == 'screen_off':
                self.driver.lock()
                try:
                    time.sleep(step['seconds'])
                finally:
                    self.driver.unlock()
            elif action == 'back':
                self.driver.back()
            elif action == 'scroll':
                item = self.element(self.locator(step['target']))
                self.driver.execute_script('mobile: scrollGesture', {
                    'elementId': item.id, 'direction': step['direction'],
                    'percent': step.get('percent', .8),
                })
            elif action == 'swipe_element':
                rect = self.element(self.locator(step['target'])).rect
                y = int(rect['y'] + rect['height'] / 2)
                self.driver.execute_script('mobile: dragGesture', {
                    'startX': int(rect['x'] + rect['width'] * step['from_fraction']),
                    'startY': y,
                    'endX': int(rect['x'] + rect['width'] * step['to_fraction']),
                    'endY': y,
                    'speed': step.get('speed', 300),
                })
            elif action == 'restart_app':
                self.driver.terminate_app(step['app_package'])
                self.driver.activate_app(step['app_package'])
