from appium import webdriver
from appium.options.android import UiAutomator2Options

from config.config import settings


def create_driver(no_reset=None):
    """Create an Android Appium driver from environment-backed settings."""
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = settings.device_name
    if settings.app_path:
        options.app = settings.app_path
    else:
        options.app_package = settings.app_package
        options.app_activity = settings.app_activity
    options.no_reset = settings.no_reset if no_reset is None else no_reset

    if settings.udid:
        options.udid = settings.udid

    if settings.platform_version:
        options.platform_version = settings.platform_version

    driver = webdriver.Remote(settings.appium_server_url, options=options)
    # UiAutomator2's XPath2 engine crashes on Flutter hierarchies containing
    # following/preceding axes. Search selectors intentionally use those axes.
    driver.update_settings({"enforceXPath1": True})
    return driver
