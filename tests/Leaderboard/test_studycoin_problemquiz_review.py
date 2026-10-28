"""Acceptance cases for reviewing a completed problem quiz."""

import os

import pytest
from appium.webdriver.common.appiumby import AppiumBy

from pages.Leaderboard.studycoin_problemquiz_review_page import (
    StudyCoinProblemQuizReviewPage,
)
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage


pytestmark = [pytest.mark.coin_quiz, pytest.mark.sends_otp,
              pytest.mark.requires_valid_otp]

DATA = {
    "course": "JEE Repeater 2027",
    "subject": "Chemistry",
    "chapter": "Some Basic Concepts of Chemistry",
    "subtopic": "Importance of Chemistry",
    "title": "Importance of Chemistry",
    "questions": 1,
}


@pytest.fixture
def review_page(driver):
    login = LoginPage(driver)
    login.wait_until_loaded()
    login.enter_mobile_number(os.environ["TEST_MOBILE_NUMBER"])
    login.tap_continue()

    otp = OtpTypePage(driver)
    otp.wait_until_loaded()
    otp.enter_otp(os.environ["TEST_VALID_OTP"])
    assert otp.is_verified(timeout=25), "Login did not reach Home"

    skip = driver.find_elements(
        AppiumBy.XPATH,
        "//*[@content-desc='Skip' or @content-desc='SKIP' or @text='Skip']",
    )
    if skip:
        driver.execute_script("mobile: clickGesture", {"elementId": skip[0].id})

    page = StudyCoinProblemQuizReviewPage(driver, timeout=20)
    page.select_course(DATA["course"])
    page.open_problem_quiz(DATA["subject"], DATA["chapter"], DATA["subtopic"])
    return page


def test_review_attempt_overview_ui(review_page):
    review_page.assert_overview(DATA)


def test_completed_attempt_displays_review(review_page):
    state, _ = review_page.primary_action()
    if state != "review":
        pytest.skip(f"Requires completed quiz state; current state is {state!r}")
    assert review_page.assert_review_attempt().is_displayed()


def test_review_button_is_actionable(review_page):
    state, _ = review_page.primary_action()
    if state != "review":
        pytest.skip(f"Requires completed quiz state; current state is {state!r}")
    review_page.open_review()
