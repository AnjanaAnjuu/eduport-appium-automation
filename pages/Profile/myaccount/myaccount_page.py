"""Profile → My Account bottom sheet interactions.

The screenshot defines labels, not selectors. Supply inspected selectors and
picker steps through MYACCOUNT_TEST_DATA; see test_myaccount.py for setup.
"""
from datetime import datetime

from selenium.webdriver.common.actions.action_builder import ActionBuilder

from pages.base_page import BasePage


class MyAccountPage(BasePage):
    REQUIRED = ('profile_screen', 'account_entry', 'sheet', 'title', 'name',
                'female', 'male', 'day', 'month', 'year', 'save', 'discard')

    def __init__(self, driver, data, timeout=15):
        super().__init__(driver, timeout)
        self.data = data
        for name in self.REQUIRED:
            self.locator(name)

    def locator(self, name):
        spec = self.data['selectors'].get(name)
        locator = spec.get('locator') if isinstance(spec, dict) else spec
        if not isinstance(locator, (list, tuple)) or len(locator) != 2 or not all(locator):
            raise ValueError(f'Configure inspected selector {name}')
        return tuple(locator)

    def target(self, name):
        return self.element(self.locator(name))

    def text(self, name):
        element = self.target(name)
        spec = self.data['selectors'][name]
        attribute = spec.get('attribute') if isinstance(spec, dict) else None
        return (element.get_attribute(attribute) if attribute else element.text) or ''

    def tap(self, name):
        self.wait.clickable(self.locator(name)).click()

    def route(self, name):
        if self.data.get('mode') == 'live_unsaved':
            if name == 'cleanup':
                if self.driver.find_elements(*self.locator('sheet')):
                    self.discard()
                self.driver.back()
                self.wait.until(lambda d: d.find_elements('accessibility id', 'Home'))
            elif name == 'profile':
                # Profile's title is a View; its Home tab is an ImageView.
                tabs = self.driver.find_elements('xpath', "//android.widget.ImageView[@content-desc='Profile']")
                if tabs:
                    self.driver.execute_script('mobile: clickGesture', {'elementId': tabs[0].id})
                self.target('profile_screen')
            else:
                raise ValueError(f'Unknown live route: {name}')
            return
        steps = self.data['routes'][name]
        if not steps:
            raise ValueError(f'Configure routes.{name}')
        for target in steps:
            self.tap(target)

    def open(self):
        self.target('profile_screen')
        # My Account sits below the initially visible Profile options.
        for _ in range(12):
            entries = self.driver.find_elements(*self.locator('account_entry'))
            if any(entry.is_displayed() for entry in entries):
                break
            self.scroll_profile('up')
        self.tap('account_entry')
        self.wait_loaded()

    def scroll_profile(self, direction):
        size = self.driver.get_window_size()
        self.driver.execute_script('mobile: swipeGesture', {
            'left': int(size['width'] * .05), 'top': int(size['height'] * .2),
            'width': int(size['width'] * .9), 'height': int(size['height'] * .6),
            'direction': direction, 'percent': .2, 'speed': 300,
        })

    def wait_loaded(self):
        self.target('sheet')
        for name in self.REQUIRED[3:]:
            self.target(name)
        assert self.text('title').strip() == 'My Account'

    def enter_name(self, value):
        self.enter_text(self.locator('name'), value)

    def dismiss_keyboard(self):
        if self.driver.is_keyboard_shown():
            self.driver.hide_keyboard()
            self.wait.until(lambda driver: not driver.is_keyboard_shown())

    def gender_selected(self, gender):
        if self.data.get('gender_visual_border'):
            # This Flutter build exposes neither selected nor checked state.
            # Its selected card has a continuous white top border. Sample only
            # the top middle section, away from the white icon and label.
            from io import BytesIO
            from PIL import Image
            rect = self.target(gender.lower()).rect
            screenshot = Image.open(BytesIO(self.driver.get_screenshot_as_png())).convert('RGB')
            scale = screenshot.width / self.driver.get_window_size()['width']
            left = int((rect['x'] + rect['width'] * .25) * scale)
            right = int((rect['x'] + rect['width'] * .75) * scale)
            top = int(rect['y'] * scale)
            bottom = int((rect['y'] + rect['height'] * .08) * scale)
            return any(sum(min(screenshot.getpixel((x, y))) > 220 for x in range(left, right))
                       / max(1, right - left) > .8 for y in range(top, bottom))
        value = self.target(gender.lower()).get_attribute(self.data.get('selected_attribute', 'selected'))
        return str(value).lower() == 'true'

    def select_gender(self, gender):
        if gender not in ('Female', 'Male'):
            raise ValueError('Gender must be Female or Male')
        self.dismiss_keyboard()
        self.tap(gender.lower())
        other = 'Male' if gender == 'Female' else 'Female'
        self.wait.until(lambda _: self.gender_selected(gender) and not self.gender_selected(other))

    def dob_values(self):
        return tuple(self.text(name).strip() for name in ('day', 'month', 'year'))

    def details(self):
        genders = [gender for gender in ('Female', 'Male') if self.gender_selected(gender)]
        assert len(genders) <= 1, 'Both genders are selected'
        values = self.dob_values()
        if values == ('DD', 'MM', 'YY'):
            dob = None
        else:
            dob = datetime.strptime(' '.join(values), self.data.get('dob_read_format', '%d %m %Y')).date().isoformat()
        return {'name': self.text('name'), 'gender': genders[0] if genders else None, 'dob': dob}

    def steps(self, steps):
        """Authored native picker interactions; no scripts or invented selectors."""
        if not steps:
            raise ValueError('Provide nonempty picker/navigation steps')
        self.dismiss_keyboard()
        for step in steps:
            action, target = step['action'], step['target']
            if action == 'tap':
                self.tap(target)
            elif action == 'visible':
                self.target(target)
            elif action == 'disabled':
                assert not self.target(target).is_enabled(), f'{target} is enabled'
            elif action == 'absent':
                self.wait.invisible(self.locator(target))
            elif action == 'back':
                self.driver.back()
                self.wait.invisible(self.locator(target))
            elif action == 'scroll_to':
                direction = step['direction']
                if direction not in ('up', 'down'):
                    raise ValueError('Picker scroll direction must be up or down')
                size = self.driver.get_window_size()
                for _ in range(12):
                    if any(e.is_displayed() for e in self.driver.find_elements(*self.locator(target))):
                        break
                    self.driver.execute_script('mobile: swipeGesture', {
                        'left': int(size['width'] * .1), 'top': int(size['height'] * .55),
                        'width': int(size['width'] * .8), 'height': int(size['height'] * .3),
                        'direction': direction, 'percent': .5, 'speed': 300,
                    })
                self.target(target)
            else:
                raise ValueError(f'Unsupported picker action: {action}')

    def fill(self, details, dob_steps):
        self.enter_name(details['name'])
        self.select_gender(details['gender'])
        self.steps(dob_steps)
        assert self.details() == details

    def save_enabled(self):
        element = self.target('save')
        attribute = self.data.get('save_enabled_attribute', 'enabled')
        return str(element.get_attribute(attribute)).lower() == 'true'

    def wait_save_enabled(self):
        self.dismiss_keyboard()
        self.wait.until(lambda _: self.save_enabled())

    def wait_profile(self):
        self.wait.invisible(self.locator('sheet'))
        self.target('profile_screen')

    def save(self):
        self.wait_save_enabled()
        self.tap('save')
        self.wait_profile()

    def discard(self):
        self.dismiss_keyboard()
        assert self.text('discard').strip() == "DON'T SAVE & EXIT"
        self.tap('discard')
        self.wait_profile()

    def assert_profile_details(self, expected):
        """Assert independently configured text for fields exposed on Profile."""
        assert expected, 'Configure the updated text visible on Profile'
        for name, value in expected.items():
            assert self.text(name).strip() == value

    def assert_blocked(self, error_target=None, error_text=None):
        self.dismiss_keyboard()
        self.target('sheet')
        if error_target:
            assert self.text(error_target).strip() == error_text
        else:
            self.wait.until(lambda _: not self.save_enabled(),
                            message='Save remains clickable for invalid/incomplete account details')

    def rapid_save(self, count=3):
        if not 2 <= count <= 5:
            raise ValueError('Use 2–5 rapid taps')
        self.wait_save_enabled()
        rect = self.target('save').rect
        actions = ActionBuilder(self.driver)
        touch = actions.add_pointer_input('touch', 'account-save-finger')
        touch.create_pointer_move(duration=0, x=int(rect['x'] + rect['width']/2),
                                  y=int(rect['y'] + rect['height']/2), origin='viewport')
        for _ in range(count):
            touch.create_pointer_down(button=0)
            touch.create_pause(0.04)
            touch.create_pointer_up(button=0)
            touch.create_pause(0.04)
        actions.perform()
        self.wait_profile()
