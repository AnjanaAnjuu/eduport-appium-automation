"""My Course / Expired page based on the supplied screenshot.

Uses inspected selectors, not image coordinates. Inherits common My Course
navigation/text helpers; see the expired test module for the configuration.
"""
from pages.Profile.mycourse.mycourse_page import MyCoursePage


class MycourseSubscriptionExpiredPage(MyCoursePage):
    SCREENSHOT_SUBSCRIPTION = {
        'course': 'Class 10 CBSE (Tuition) 2026-27',
        'batch': 'Class 10 CBSE (Tuition) 2026-27_B11',
        'expiry': '17 Jul 2026',
        'status': 'Expired',
        'subject': '',
        'sticker': '',
    }
    FIELD_NAMES = ('course', 'batch', 'expiry', 'status', 'subject', 'sticker')
    REQUIRED_SELECTORS = (
        'title', 'back', 'help', 'active_tab', 'expired_tab', 'card',
        'course', 'batch', 'expiry_label', 'expiry', 'status',
        'subject', 'sticker', 'renew_now', 'previous_screen',
        'active_content', 'expired_content', 'active_empty', 'expired_empty',
        'list_region', 'loading',
    )

    def __init__(self, driver, selectors, selected_attribute='selected', timeout=15, max_scrolls=50):
        super().__init__(driver, selectors, selected_attribute, timeout)
        self.max_scrolls = max_scrolls

    def locator(self, name):
        locator = super().locator(name)
        if name == 'renew_now' and locator[0] == 'xpath' and not locator[1].startswith('.'):
            raise ValueError('renew_now XPath must be relative to its card')
        return locator

    def select_tab(self, tab):
        assert tab in ('active', 'expired')
        self.tap(f'{tab}_tab')
        self.wait.until(lambda _: self.tab_selected(f'{tab}_tab'))
        self.wait.until(lambda _: not self.tab_selected('expired_tab' if tab == 'active' else 'active_tab'))
        self.target(f'{tab}_content')
        self.wait.invisible(self.locator('loading'))
        self.wait.until(lambda _: self.is_visible(self.locator('card'), 0.2)
                        or self.is_visible(self.locator(f'{tab}_empty'), 0.2))

    def select_expired(self):
        self.select_tab('expired')

    def select_active(self):
        self.select_tab('active')

    def read_card(self, card):
        values = {}
        for name in self.FIELD_NAMES:
            elements = card.find_elements(*self.locator(name))
            if name in ('subject', 'sticker') and not elements:
                values[name] = ''
            else:
                assert len(elements) == 1 and elements[0].is_displayed(), f'{name} must be visible once per card'
                values[name] = ' '.join(self.text(name, card).split())
        return values

    def scroll(self, direction):
        region = self.target('list_region').rect
        can_scroll = self.driver.execute_script('mobile: scrollGesture', {
            'left': int(region['x']), 'top': int(region['y']),
            'width': int(region['width']), 'height': int(region['height']),
            'direction': direction, 'percent': 0.65,
        })
        if not isinstance(can_scroll, bool):
            raise ValueError('UiAutomator2 scrollGesture must return whether more scrolling is possible')
        self.wait.invisible(self.locator('loading'))
        return can_scroll

    def list_top(self):
        for _ in range(self.max_scrolls):
            if not self.scroll('up'):
                return
        raise AssertionError('Could not reach the start of the subscription list')

    @staticmethod
    def identity(row):
        return row['course'], row['batch'], row['subject']

    def subscriptions(self, tab='expired'):
        """Scan to the actual scroll boundary, merging overlapping viewports.

        Seed unique course/batch/subject combinations. This reader is intended
        for visibility tests, not duplicate-record detection. Cards and list
        region selectors must be scoped to the currently selected tab.
        """
        if self.is_visible(self.locator(f'{tab}_empty'), 0.2):
            assert not self.driver.find_elements(*self.locator('card'))
            return []
        self.list_top()
        rows = {}
        at_end = False
        for _ in range(self.max_scrolls):
            for card in self.driver.find_elements(*self.locator('card')):
                if card.is_displayed():
                    row = self.read_card(card)
                    key = self.identity(row)
                    if key in rows:
                        assert rows[key] == row, 'Card content changed while reading the list'
                    rows[key] = row
            if at_end:
                return list(rows.values())
            at_end = not self.scroll('down')
        raise AssertionError('List traversal exceeded max_scrolls; completeness not established')

    def assert_subscriptions(self, expected, tab='expired'):
        actual = self.subscriptions(tab)
        assert sorted(actual, key=self.identity) == sorted(expected, key=self.identity)
        return actual

    def find_subscription(self, expected):
        self.list_top()
        at_end = False
        for _ in range(self.max_scrolls):
            for card in self.driver.find_elements(*self.locator('card')):
                if card.is_displayed() and self.identity(self.read_card(card)) == self.identity(expected):
                    return card
            if at_end:
                break
            at_end = not self.scroll('down')
        raise AssertionError(f'Subscription not found: {self.identity(expected)}')

    def renew_button(self, expected):
        card = self.find_subscription(expected)
        button = self.target('renew_now', card)
        assert button.is_displayed() and button.is_enabled()
        assert self.text('renew_now', card) == 'Renew Now'
        return button

    def renew(self, expected):
        self.renew_button(expected).click()
        # Must identify the confirmed destination, not the source button.
        self.target('renewal_screen')


MyCourseSubscriptionExpiredPage = MycourseSubscriptionExpiredPage
