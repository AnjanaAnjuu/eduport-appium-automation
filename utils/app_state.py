"""Restore the development app's logged-out UI without deleting app data."""

from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


def ensure_logged_out(driver) -> None:
    page = BasePage(driver, timeout=25)
    ready = (
        AppiumBy.XPATH,
        "//*[@content-desc='Send OTP' or @content-desc='OTP Verifications' "
        "or @content-desc='Home' or @content-desc='Profile' "
        "or @content-desc='ANALYSE' or @content-desc='Sign Out' "
        "or @content-desc='Skip' or @content-desc='Sign out' "
        "or @resource-id='com.google.android.gms:id/cancel' "
        "or @resource-id='com.android.permissioncontroller:id/permission_allow_button']",
    )
    page.element(ready)
    if driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Send OTP'):
        return
    if driver.find_elements(AppiumBy.ID, 'com.google.android.gms:id/cancel'):
        return  # LoginPage handles the phone hint dialog.
    permission = driver.find_elements(
        AppiumBy.ID, 'com.android.permissioncontroller:id/permission_allow_button'
    )
    if permission:
        permission[0].click()
        # Existing accounts can land on onboarding, Home, or Profile after the
        # Android notification prompt.  Do not assume onboarding is next.
        page.wait.until(
            lambda d: not d.find_elements(
                AppiumBy.ID,
                'com.android.permissioncontroller:id/permission_allow_button',
            )
        )
        page.element(ready)
        if (driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Send OTP')
                or driver.find_elements(AppiumBy.ID, 'com.google.android.gms:id/cancel')):
            return
    if driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'OTP Verifications'):
        return
    skip = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Skip')
    if skip:
        skip[0].click()
        page.element((AppiumBy.ACCESSIBILITY_ID, 'Home'))
    profile = driver.find_elements(
        AppiumBy.XPATH, "//android.widget.ImageView[@content-desc='Profile']"
    )
    if profile:
        profile[0].click()
        page.element((AppiumBy.ACCESSIBILITY_ID, 'Settings'))
    confirm = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Sign out')
    if not confirm:
        sign_out = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Sign Out')
        for _ in range(3):
            if sign_out:
                break
            size = driver.get_window_size()
            driver.execute_script('mobile: swipeGesture', {
                'left': 40, 'top': 300, 'width': size['width'] - 80,
                'height': size['height'] - 500, 'direction': 'up', 'percent': 0.8,
            })
            sign_out = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Sign Out')
        if not sign_out:
            raise RuntimeError('Cannot isolate test: no supported Sign Out control found')
        sign_out[0].click()
    page.click((AppiumBy.ACCESSIBILITY_ID, 'Sign out'))
    page.wait.until(lambda d: bool(d.find_elements(AppiumBy.ACCESSIBILITY_ID, 'Send OTP'))
                    or bool(d.find_elements(AppiumBy.ID, 'com.google.android.gms:id/cancel')))
