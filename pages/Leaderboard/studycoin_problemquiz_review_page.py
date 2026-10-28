"""Completed-attempt review behavior for a problem-based quiz."""

from pages.Leaderboard.coin_problemquiz_page import CoinProblemQuizPage


class StudyCoinProblemQuizReviewPage(CoinProblemQuizPage):
    """Problem Practice overview for an account with a completed attempt."""

    def assert_review_attempt(self):
        self.assert_attempt_action("completed")
        return self.element(self.REVIEW)

    def open_review(self):
        self.assert_review_attempt()
        self.click(self.REVIEW)

