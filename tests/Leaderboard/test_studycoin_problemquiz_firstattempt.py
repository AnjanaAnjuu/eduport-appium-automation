"""Acceptance cases for the first problem-quiz attempt."""

import os

import pytest
from appium.webdriver.common.appiumby import AppiumBy

from pages.Leaderboard.studycoin_problemquiz_firstattempt_page import (
    StudyCoinProblemQuizFirstAttemptPage,
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
def first_attempt_page(driver):
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

    page = StudyCoinProblemQuizFirstAttemptPage(driver, timeout=20)
    page.select_course(DATA["course"])
    page.open_problem_quiz(DATA["subject"], DATA["chapter"], DATA["subtopic"])
    return page


def test_first_attempt_overview_ui(first_attempt_page):
    first_attempt_page.assert_overview(DATA)


def test_first_attempt_displays_start(first_attempt_page):
    state, _ = first_attempt_page.primary_action()
    if state != "start":
        pytest.skip(f"Requires fresh quiz state; current state is {state!r}")
    assert first_attempt_page.assert_first_attempt().is_displayed()


def test_first_attempt_start_opens_question(first_attempt_page):
    state, _ = first_attempt_page.primary_action()
    if state != "start":
        pytest.skip(f"Requires fresh quiz state; current state is {state!r}")
    first_attempt_page.start_test()

