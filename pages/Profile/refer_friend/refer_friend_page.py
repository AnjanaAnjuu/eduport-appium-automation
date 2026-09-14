"""Profile → Refer a friend / Share the App → native device share sheet.

The screenshot shows a paginated Android share sheet, not a complete payload
or download URL. Use inspected locators and independent expected share data.
"""
import re
from urllib.parse import urlsplit

from selenium.webdriver.common.actions.action_builder import ActionBuilder

from pages.base_page import BasePage


def shared_urls(message):
    """Extract URLs without discarding query strings or referral tokens."""
    return re.findall(r'https?://[^\s<>"\u201c\u201d]+', message)


def validate_download_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Configure the actual HTTP(S) app download URL without embedded credentials')
    return url


class ReferFriendPage(BasePage):
    REQUIRED = ('profile_screen', 'refer_friend', 'share_sheet', 'cancel_share',
                'profile_back', 'previous_screen', 'copy_link')

    def __init__(self, driver, data):
        super().__init__(driver)
        self.data = data
        for key in self.REQUIRED:
            self.locator(key)

    def locator(self, key):
        spec = self.data['selectors'][key]
        locator = spec.get('locator') if isinstance(spec, dict) else spec
        if not isinstance(locator, (list, tuple)) or len(locator) != 2 or not all(locator):
            raise ValueError(f'Provide inspected selector {key}')
        return tuple(locator)

    def target(self, key):
        return self.element(self.locator(key))

    def text(self, key):
        element = self.target(key)
        spec = self.data['selectors'][key]
        attribute = spec.get('attribute') if isinstance(spec, dict) else None
        return ((element.get_attribute(attribute) if attribute else element.text) or '').strip()

    def tap(self, key):
        self.wait.clickable(self.locator(key)).click()

    def route(self, key):
        steps = self.data['routes'][key]
        if not steps:
            raise ValueError(f'Configure nonempty routes.{key}')
        for target in steps:
            self.tap(target)

    def open_profile(self):
        self.route('profile')
        self.target('profile_screen')

    def open_share(self):
        self.tap('refer_friend')
        self.target('share_sheet')

    def cancel(self):
        self.tap('cancel_share')
        self.wait.invisible(self.locator('share_sheet'))
        self.target('profile_screen')

    def choose_medium(self, medium):
        # Routes handle real share-sheet pagination and More/See all options.
        # Stop at the target composer; recipient selection/send belongs to the
        # controlled delivery provider, not a guessed coordinate in this page.
        self.route(f'share_{medium}')
        self.target(f'{medium}_composer')

    def assert_payload(self, payload):
        assert payload['mime_type'] == 'text/plain'
        message = payload['text']
        assert isinstance(message, str) and message
        assert self.data['download_url'] in shared_urls(message), 'Expected download URL is absent or altered'
        return message

    def assert_message(self, payload):
        message = self.assert_payload(payload)
        assert self.data['app_name'] in message
        assert message == self.data['expected_message'], 'Share message differs from approved locale/template'

    def clipboard(self):
        # Driver session must own restoration of the original clipboard.
        return self.driver.get_clipboard_text()

    def rapid_share(self, count=3):
        if not 2 <= count <= 5:
            raise ValueError('Use 2–5 rapid taps')
        rect = self.target('refer_friend').rect
        actions = ActionBuilder(self.driver)
        touch = actions.add_pointer_input('touch', 'referral-finger')
        touch.create_pointer_move(duration=0, x=int(rect['x'] + rect['width']/2),
                                  y=int(rect['y'] + rect['height']/2), origin='viewport')
        for _ in range(count):
            touch.create_pointer_down(button=0)
            touch.create_pause(0.04)
            touch.create_pointer_up(button=0)
            touch.create_pause(0.04)
        actions.perform()
        self.target('share_sheet')
