"""Shared My Course navigation, inspected selectors and layout helpers."""
from pages.base_page import BasePage


class MyCoursePage(BasePage):
    FIELD_NAMES = ()
    REQUIRED_SELECTORS = ('title', 'back', 'help', 'active_tab', 'expired_tab')

    def __init__(self, driver, selectors, selected_attribute='selected', timeout=15):
        super().__init__(driver, timeout)
        self.selectors = selectors
        self.selected_attribute = selected_attribute
        for name in self.REQUIRED_SELECTORS:
            self.locator(name)

    def locator(self, name):
        spec = self.selectors.get(name)
        locator = spec.get('locator') if isinstance(spec, dict) else spec
        if not isinstance(locator, (list, tuple)) or len(locator) != 2 or not all(locator):
            raise ValueError(f'Provide an inspected locator for {name}')
        if name in (*self.FIELD_NAMES, 'expiry_label') and locator[0] == 'xpath':
            if not locator[1].startswith('.'):
                raise ValueError(f'{name} XPath must be relative to the course card')
        return tuple(locator)

    def target(self, name, root=None):
        if root is not None:
            return root.find_element(*self.locator(name))
        return self.element(self.locator(name))

    def text(self, name, root=None):
        element = self.target(name, root)
        spec = self.selectors[name]
        attribute = spec.get('attribute') if isinstance(spec, dict) else None
        value = element.get_attribute(attribute) if attribute else element.text
        return (value or '').strip()

    def tap(self, name):
        self.wait.clickable(self.locator(name)).click()

    def navigate(self, route):
        for name in route:
            self.tap(name)

    def wait_loaded(self):
        for name in ('title', 'back', 'help', 'active_tab', 'expired_tab'):
            self.target(name)
        assert self.text('title') == 'My Course'

    def tab_selected(self, name):
        return str(self.target(name).get_attribute(self.selected_attribute)).lower() == 'true'

    def open_help(self):
        self.tap('help')
        self.target('help_screen')

    def go_back(self):
        self.tap('back')
        self.target('previous_screen')

    def assert_in_bounds(self, names, root=None):
        bounds = root.rect if root is not None else dict(x=0, y=0, **self.driver.get_window_size())
        for name in names:
            element = self.target(name, root)
            rect = element.rect
            assert element.is_displayed(), f'{name} is hidden'
            assert rect['width'] > 0 and rect['height'] > 0
            assert bounds['x'] <= rect['x'] and bounds['y'] <= rect['y']
            assert rect['x'] + rect['width'] <= bounds['x'] + bounds['width'], f'{name} overflows horizontally'
            assert rect['y'] + rect['height'] <= bounds['y'] + bounds['height'], f'{name} overflows vertically'

