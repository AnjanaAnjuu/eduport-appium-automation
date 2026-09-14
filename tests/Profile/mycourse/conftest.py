"""Shared fixtures for My Course header and active subscription tests."""
from datetime import datetime
import json
import os
from pathlib import Path
import re
import pytest
from pages.Login.login_page import LoginPage
from pages.Login.otp_page import OtpTypePage
from pages.Profile.mycourse.active_subscription_page import (
    ActiveSubscription, MycourseSubscriptionActivePage,
)


@pytest.fixture(scope='module')
def active_data():
    path = os.getenv('MYCOURSE_ACTIVE_DATA')
    if not path:
        pytest.skip('Set MYCOURSE_ACTIVE_DATA with inspected selectors and one active enrollment')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    validator = MycourseSubscriptionActivePage(None, data['selectors'])
    for route in ('open_route', 'cleanup_route'):
        assert isinstance(data.get(route), list) and data[route], f'Configure {route}'
        for name in data[route]:
            validator.locator(name)
    expected = ActiveSubscription(**data['expected'])
    assert expected.status == 'Active'
    assert all(isinstance(value, str) and value.strip() for value in vars(expected).values())
    datetime.strptime(expected.expiry, data['expiry_format'])
    assert re.fullmatch(data['expiry_pattern'], expected.expiry)
    return data



@pytest.fixture
def active_page(request, active_data):
    # Validate configuration before requesting the shared driver or sending OTP.
    driver = request.getfixturevalue('driver')
    page = MycourseSubscriptionActivePage(
        driver, active_data['selectors'], active_data.get('selected_attribute', 'selected'),
    )
    authenticated = False
    try:
        login = LoginPage(driver)
        login.wait_until_loaded()
        login.enter_mobile_number(os.environ['TEST_MOBILE_NUMBER'])
        login.tap_continue()
        otp = OtpTypePage(driver)
        otp.wait_until_loaded()
        otp.enter_otp(os.environ['TEST_VALID_OTP'])
        assert otp.is_verified(timeout=20), 'Login failed'
        authenticated = True
        page.navigate(active_data['open_route'])
        page.wait_loaded()
        yield page
    finally:
        # The shared driver's teardown then performs supported logout and quit.
        if authenticated:
            page.navigate(active_data['cleanup_route'])

