"""My Course empty Active tab from the supplied screenshot.

Locators require Appium Inspector verification. Shared My Course header,
text, navigation and bounds helpers come from the shared My Course page object.
"""
from pages.Profile.mycourse.mycourse_page import MyCoursePage


class MycourseNoSubscriptionPage(MyCoursePage):
    EMPTY_MESSAGE = 'Your active subscriptions will appear here.'
    MISSING_MESSAGE = 'Not seeing your subscription?'
    CONTACT_LABEL = 'Contact Us'
    REQUIRED_SELECTORS = (
        'title', 'back', 'help', 'active_tab', 'expired_tab',
        'active_content', 'expired_content', 'loading', 'card',
        'empty_illustration', 'empty_message', 'missing_subscription',
        'contact_us', 'contact_screen', 'help_screen', 'previous_screen',
    )
    EMPTY_TARGETS = (
        'empty_illustration', 'empty_message', 'missing_subscription', 'contact_us',
    )

    def normalized_text(self, name):
        # Text wrapping differs with device width; preserve words/punctuation.
        return ' '.join(self.text(name).split())

    def wait_active_empty(self):
        self.target('active_content')
        self.wait.invisible(self.locator('loading'))
        for name in self.EMPTY_TARGETS:
            self.target(name)

    def wait_loaded(self):
        super().wait_loaded()
        # Do not select Active here: default-tab tests must observe app behavior.
        self.wait_active_empty()

    def assert_no_cards(self):
        assert not any(card.is_displayed() for card in self.driver.find_elements(*self.locator('card'))), (
            'Subscription card displayed for an account without enrollments'
        )

    def assert_active_empty(self):
        self.wait_active_empty()
        assert self.tab_selected('active_tab')
        assert not self.tab_selected('expired_tab')
        assert self.normalized_text('empty_message') == self.EMPTY_MESSAGE
        assert self.normalized_text('missing_subscription') == self.MISSING_MESSAGE
        assert self.normalized_text('contact_us') == self.CONTACT_LABEL
        self.assert_no_cards()

    def select_active(self):
        self.tap('active_tab')
        self.wait.until(lambda _: self.tab_selected('active_tab') and not self.tab_selected('expired_tab'))
        self.wait_active_empty()

    def select_expired(self):
        self.tap('expired_tab')
        self.wait.until(lambda _: self.tab_selected('expired_tab') and not self.tab_selected('active_tab'))
        self.target('expired_content')
        self.wait.invisible(self.locator('loading'))
        # The expired empty-state wording is not present in this screenshot.

    def open_contact_us(self):
        self.tap('contact_us')
        self.target('contact_screen')

    def assert_empty_layout(self):
        self.assert_in_bounds(self.EMPTY_TARGETS)
        rects = [self.target(name).rect for name in self.EMPTY_TARGETS]
        for upper, lower in zip(rects, rects[1:]):
            assert upper['y'] + upper['height'] <= lower['y'], 'Empty-state elements overlap or are out of order'


MyCourseNoSubscriptionPage = MycourseNoSubscriptionPage
