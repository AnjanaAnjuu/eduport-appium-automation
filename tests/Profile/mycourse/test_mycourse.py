"""Shared My Course header and default-tab coverage using an active account.

Setup: see test_active_subscription.py for MYCOURSE_ACTIVE_DATA configuration.
"""
import pytest

pytestmark = [pytest.mark.sends_otp, pytest.mark.requires_valid_otp]


def test_tc_001_navigation_to_my_course(active_page):
    """My Course opens with its title and navigation controls."""
    active_page.wait_loaded()



def test_tc_002_active_tab_selected_by_default(active_page):
    assert active_page.tab_selected('active_tab')
    assert not active_page.tab_selected('expired_tab')



def test_tc_003_tab_labels(active_page):
    assert active_page.text('active_tab') == 'Active'
    assert active_page.text('expired_tab') == 'Expired'

