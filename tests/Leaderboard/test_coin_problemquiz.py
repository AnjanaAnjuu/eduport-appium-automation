"""Problem-based quiz navigation and overview acceptance tests."""

import os

import pytest
from appium.webdriver.common.appiumby import AppiumBy

from pages.Leaderboard.coin_problemquiz_page import CoinProblemQuizPage
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage


pytestmark = [pytest.mark.coin_quiz, pytest.mark.sends_otp,
              pytest.mark.requires_valid_otp]

QUIZ_DATA = {
    "course": "JEE Repeater 2027",
    "subject": "Chemistry",
    "chapter": "Some Basic Concepts of Chemistry",
    "subtopic": "Importance of Chemistry",
    "title": "Importance of Chemistry",
    "questions": 1,
}


@pytest.fixture
def problem_quiz_page(driver):
    mobile = os.environ["TEST_MOBILE_NUMBER"]
    otp_value = os.environ["TEST_VALID_OTP"]

    login = LoginPage(driver)
    login.wait_until_loaded()
    login.enter_mobile_number(mobile)
    login.tap_continue()

    otp = OtpTypePage(driver)
    otp.wait_until_loaded()
    otp.enter_otp(otp_value)
    assert otp.is_verified(timeout=25), "Login did not reach Home"

    skip = driver.find_elements(
        AppiumBy.XPATH,
        "//*[@content-desc='Skip' or @content-desc='SKIP' or @text='Skip']",
    )
    if skip:
        driver.execute_script("mobile: clickGesture", {"elementId": skip[0].id})

    page = CoinProblemQuizPage(driver, timeout=20)
    page.select_course(QUIZ_DATA["course"])
    page.open_problem_quiz(
        QUIZ_DATA["subject"], QUIZ_DATA["chapter"], QUIZ_DATA["subtopic"]
    )
    return page


def test_problem_based_quiz_opens(problem_quiz_page):
    assert problem_quiz_page.is_visible(CoinProblemQuizPage.QUIZ_KIND)


def test_problem_quiz_overview_matches_data(problem_quiz_page):
    problem_quiz_page.assert_overview(QUIZ_DATA)


def test_first_attempt_shows_start_button(problem_quiz_page):
    state, _ = problem_quiz_page.primary_action()
    if state != "start":
        pytest.skip(f"Requires a fresh first-attempt quiz; current state is {state!r}")
    problem_quiz_page.assert_attempt_action("first")


def test_completed_attempt_shows_review_button(problem_quiz_page):
    state, _ = problem_quiz_page.primary_action()
    if state != "review":
        pytest.skip(f"Requires a completed quiz attempt; current state is {state!r}")
    problem_quiz_page.assert_attempt_action("completed")


def test_start_or_resume_opens_question_ui(problem_quiz_page):
    state, _ = problem_quiz_page.primary_action()
    if state == "review":
        pytest.skip("Completed attempt correctly exposes Review instead of Start")
    assert problem_quiz_page.tap_primary_action() in {"start", "resume"}
