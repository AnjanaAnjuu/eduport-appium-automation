"""Page object for the supplied My Course / Active subscription screenshot.

The image does not expose Appium selectors. Supply inspected selectors as
{key: [strategy, value]} to the constructor. Card field XPath selectors must
be relative (./...) to the card, so the Active tab cannot match its status badge.
"""
from dataclasses import dataclass

from pages.Profile.mycourse.mycourse_page import MyCoursePage


@dataclass(frozen=True)
class ActiveSubscription:
    course: str
    batch: str
    expiry: str
    status: str = 'Active'


class MycourseSubscriptionActivePage(MyCoursePage):
    SCREENSHOT_SUBSCRIPTION = ActiveSubscription(
        course='NEET Repeater 2026',
        batch='NEET Repeater 2026-Offline-Escola- B2',
        expiry='28 Aug 2026',
    )
    FIELD_NAMES = ('course', 'batch', 'expiry', 'status')
    REQUIRED_SELECTORS = (
        'title', 'back', 'help', 'active_tab', 'expired_tab', 'card',
        'course', 'batch', 'expiry_label', 'expiry', 'status',
        'previous_screen', 'help_screen', 'expired_content',
    )


    def select_active(self):
        self.tap('active_tab')
        self.wait.until(lambda _: self.tab_selected('active_tab'))
        self.target('card')

    def select_expired(self):
        self.tap('expired_tab')
        self.wait.until(lambda _: self.tab_selected('expired_tab'))
        self.target('expired_content')

    def card(self):
        """This screenshot scenario requires exactly one active enrollment."""
        self.target('card')
        cards = [card for card in self.driver.find_elements(*self.locator('card')) if card.is_displayed()]
        assert len(cards) == 1, f'Expected one visible active card, found {len(cards)}'
        return cards[0]

    def subscription(self):
        card = self.card()
        return ActiveSubscription(**{key: self.text(key, card) for key in self.FIELD_NAMES})


MyCourseSubscriptionActivePage = MycourseSubscriptionActivePage
