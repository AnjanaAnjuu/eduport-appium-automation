"""Splash screen Page Object for Eduport Appium tests."""
from __future__ import annotations
import time
from typing import Tuple
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException

Locator = Tuple[str, str]


class SplashPage:
    """Verifies that splash appears briefly and the app reaches onboarding."""

    SPLASH_LOCATORS: tuple[Locator, ...] = (
        (AppiumBy.ID, "com.dev.eduportlms:id/splash"),
        (AppiumBy.ACCESSIBILITY_ID, "Splash"),
        (AppiumBy.XPATH, "//*[contains(@resource-id, 'splash')]"),
    )

    ONBOARDING_LOCATORS: tuple[Locator, ...] = (
        (AppiumBy.ACCESSIBILITY_ID, "Skip"),
        (AppiumBy.ACCESSIBILITY_ID, "LEARN"),
        (AppiumBy.ACCESSIBILITY_ID, "Get Started"),
        (AppiumBy.ACCESSIBILITY_ID, "Continue"),
        (AppiumBy.XPATH, "//*[contains(@text, 'Get Started') or contains(@text, 'Continue')]") ,
        (AppiumBy.XPATH, "//*[contains(@text, 'Onboarding')]") ,
    )

    PERMISSION_ALLOW_LOCATORS: tuple[Locator, ...] = (
        (AppiumBy.ID, "com.android.permissioncontroller:id/permission_allow_button"),
        (AppiumBy.XPATH, "//*[@text='Allow']"),
    )

    def __init__(self, driver, splash_timeout=8.0, onboarding_timeout=12.0, poll_interval=0.25):
        self.driver = driver
        self.splash_timeout = splash_timeout
        self.onboarding_timeout = onboarding_timeout
        self.poll_interval = poll_interval

    def _visible(self, locator: Locator) -> bool:
        try:
            return self.driver.find_element(*locator).is_displayed()
        except WebDriverException:
            return False

    def is_splash_visible(self) -> bool:
        return any(self._visible(locator) for locator in self.SPLASH_LOCATORS)

    def is_onboarding_visible(self) -> bool:
        return any(self._visible(locator) for locator in self.ONBOARDING_LOCATORS)

    def allow_notifications_if_requested(self) -> None:
        """Dismiss Android's runtime notification prompt when it covers onboarding."""
        for locator in self.PERMISSION_ALLOW_LOCATORS:
            elements = self.driver.find_elements(*locator)
            if elements and elements[0].is_displayed():
                elements[0].click()
                return

    def wait_until_splash_appears(self, timeout=None) -> bool:
        timeout = self.splash_timeout if timeout is None else timeout
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.is_splash_visible():
                return True
            time.sleep(self.poll_interval)
        return False

    def wait_until_splash_disappears(self, timeout=None) -> None:
        timeout = self.splash_timeout if timeout is None else timeout
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if not self.is_splash_visible():
                return
            time.sleep(self.poll_interval)
        raise AssertionError(
            f"Splash is still visible after {timeout:.1f}s; app may be stuck on splash."
        )

    def wait_for_onboarding(self, timeout=None) -> None:
        timeout = self.onboarding_timeout if timeout is None else timeout
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.allow_notifications_if_requested()
            if self.is_onboarding_visible():
                return
            time.sleep(self.poll_interval)
        raise AssertionError(
            f"Onboarding was not detected within {timeout:.1f}s. Update ONBOARDING_LOCATORS."
        )

    def verify_splash_flow(self) -> None:
        splash_seen = self.wait_until_splash_appears(timeout=3.0)
        self.wait_until_splash_disappears()
        self.wait_for_onboarding()
        if not splash_seen:
            print("WARNING: Splash was not detected; update SPLASH_LOCATORS if it is too fast or custom.")
