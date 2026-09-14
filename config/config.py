import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    appium_server_url: str = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
    device_name: str = os.getenv("DEVICE_NAME", "Android Emulator")
    platform_version: str = os.getenv("PLATFORM_VERSION", "")
    app_path: str = os.getenv("APP_PATH", "")
    app_package: str = os.getenv("APP_PACKAGE", "com.dev.eduportlms")
    app_activity: str = os.getenv("APP_ACTIVITY", "com.irah.eduportlms.MainActivity")
    udid: str = os.getenv("ANDROID_UDID", "")
    no_reset: bool = _as_bool(os.getenv("NO_RESET", "false"))
    test_username: str = os.getenv("TEST_USERNAME", "test@example.com")
    test_password: str = os.getenv("TEST_PASSWORD", "password")


settings = Settings()
