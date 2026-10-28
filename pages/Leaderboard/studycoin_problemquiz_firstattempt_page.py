"""First-attempt behavior for a problem-based quiz."""

from pages.Leaderboard.coin_problemquiz_page import CoinProblemQuizPage


class StudyCoinProblemQuizFirstAttemptPage(CoinProblemQuizPage):
    """Problem Practice overview for an account with no previous attempt."""

    def assert_first_attempt(self):
        self.assert_attempt_action("first")
        return self.element(self.START)

    def start_test(self):
        self.assert_first_attempt()
        state = self.tap_primary_action()
        assert state == "start"

