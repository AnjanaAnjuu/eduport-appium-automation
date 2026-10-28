"""Focused Refer a Friend interactions using inspected, configurable locators."""
from pages.Profile.refer_friend.refer_friend_page import (
    ReferFriendPage,
    validate_download_url,
)


class ReferPage(ReferFriendPage):
    # Each test validates its additional selectors before starting a session.
    REQUIRED = ('profile_screen', 'refer_friend')

    def assert_button_available(self):
        button = self.wait.clickable(self.locator('refer_friend'))
        assert button.is_displayed(), 'Refer a Friend button is not visible'
        assert button.is_enabled(), 'Refer a Friend button is disabled'
        assert self.is_element_within_screen(button, self.driver.get_window_size()), (
            'Refer a Friend button is outside the screen'
        )

    def open_url(self):
        """Verify that tapping the button itself reaches the configured URL.

        url_destination identifies the loaded browser/webview destination;
        opened_url reads its full address, not a link in a share-sheet preview.
        """
        if self.data.get('mode') == 'live_android':
            self.tap('refer_friend')
            self.wait.until(lambda _: self.driver.current_package != self.data['app_id'])
            assert not self.is_visible(self.locator('share_sheet'), 2), (
                'Refer a Friend opens the Android share sheet containing a referral URL, '
                'not a browser URL destination. The direct-URL requirement differs from '
                'the observed app behavior.'
            )
            raise AssertionError('Unexpected external destination; configure its inspected URL locator')
        expected = validate_download_url(self.data['download_url'])
        self.tap('refer_friend')
        self.target('url_destination')
        self.wait.until(
            lambda _: self.text('opened_url') == expected,
            f'Refer a Friend did not open the expected URL: {expected}',
        )

    def assert_single_share_sheet(self, probe, tap_count=3):
        assert not self.is_visible(self.locator('share_sheet'), 1), (
            'A share sheet was already open before the repeated taps'
        )
        cursor = probe.cursor(self.driver)
        self.rapid_share(tap_count)
        info = probe.sheet_info(self.driver)
        assert info['native'] is True, 'Expected a native share sheet'
        assert info['visible_sheet_count'] == 1, 'Multiple share sheets are visible'
        self.cancel()
        # The probe must wait for queued launches after dismissal. Counting
        # visible UI roots alone cannot detect a second sheet behind the first.
        launches = probe.sheet_launches_since(self.driver, cursor)
        assert launches == 1, (
            f'Expected exactly one share-sheet launch after {tap_count} taps; recorded {launches}'
        )
        assert not self.is_visible(self.locator('share_sheet'), 1), (
            'Another share sheet appeared after dismissing the first'
        )
        self.target('profile_screen')

    def open_profile(self):
        if self.data.get('mode') == 'live_android':
            self.target('profile_screen')  # Live session owns navigation and scrolling.
        else:
            super().open_profile()

    def cancel(self):
        if self.data.get('mode') == 'live_android':
            self.driver.back()
            self.wait.invisible(self.locator('share_sheet'))
            self.target('profile_screen')
        else:
            super().cancel()
