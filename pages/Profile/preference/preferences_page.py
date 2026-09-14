"""Shared inspected-locator interactions for Preferences."""
from pages.base_page import BasePage


class PreferencesPage(BasePage):
    def __init__(self, driver, data):
        super().__init__(driver)
        self.data = data

    def locator(self, key):
        spec = self.data['selectors'][key]
        locator = spec.get('locator') if isinstance(spec, dict) else spec
        if not isinstance(locator, (list, tuple)) or len(locator) != 2 or not all(locator):
            raise ValueError(f'Configure inspected selector {key}')
        return tuple(locator)

    def target(self, key):
        return self.element(self.locator(key))

    def text(self, key):
        spec = self.data['selectors'][key]
        element = self.target(key)
        attribute = spec.get('attribute') if isinstance(spec, dict) else None
        return ((element.get_attribute(attribute) if attribute else element.text) or '').strip()

    def tap(self, key):
        self.wait.clickable(self.locator(key)).click()

    def route(self, key):
        steps = self.data['routes'][key]
        if not steps:
            raise ValueError(f'Configure nonempty route {key}')
        for target in steps:
            self.tap(target)

    def open(self):
        self.route('preferences')
        self.wait_loaded()

    def wait_loaded(self):
        assert self.text('title') == 'Preferences'
        self.target('video_section')
        self.wait.invisible(self.locator('loading'))

    def section(self, key):
        # Authored route scrolls to the section via an inspected UiScrollable
        # target, or taps an app-specific navigation control.
        self.route(f'show_{key}')
        self.target(f'{key}_section')

    def restart(self):
        self.driver.terminate_app(self.data['app_id'])
        self.driver.activate_app(self.data['app_id'])
        self.open()

    def reopen(self):
        self.tap('back')
        self.target('previous_screen')
        self.open()

    def state(self, key):
        value = self.target(key).get_attribute(self.data.get('toggle_attribute', 'checked'))
        if str(value).lower() not in ('true', 'false', '1', '0'):
            raise ValueError(f'{key} does not expose a boolean toggle state')
        return str(value).lower() in ('true', '1')

    def toggle(self, key, enabled):
        if self.state(key) != enabled:
            self.tap(key)
        self.wait.until(lambda _: self.state(key) == enabled)

    def accessible(self, key):
        element = self.wait.clickable(self.locator(key))
        attribute = self.data.get('accessibility_attribute', 'content-desc')
        assert element.get_attribute(attribute), f'{key} has no accessible label'
        assert self.is_element_within_screen(element, self.driver.get_window_size())
