"""Analysis dashboard read-only UI checks. Configure selectors with EFFORT_UI_DATA."""
import pytest
from appium.webdriver.common.appiumby import AppiumBy
from pages.Analysis.effort_index import EffortIndexPage

pytestmark = [pytest.mark.sends_otp, pytest.mark.requires_valid_otp]


def test_effort_index_dashboard(analysis_driver, effort_data):
    page = EffortIndexPage(analysis_driver, effort_data.get('analysis_selectors'))
    page.open()
    assert page.index() >= 0
    assert 'Daily Effort Tracker' in page.read('effort_card')


def test_more_opens_effort_tracker(analysis_driver, effort_data):
    page = EffortIndexPage(analysis_driver, effort_data.get('analysis_selectors'))
    page.open()
    page.open_tracker()
    title = effort_data.get('tracker_selectors', {}).get(
        'title', [AppiumBy.ACCESSIBILITY_ID, 'Effort Tracker'])
    assert 'Effort Tracker' in (
        page.element(tuple(title)).get_attribute('content-desc') or ''
    )
