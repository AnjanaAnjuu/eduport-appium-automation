# My Account tests

Run `venv/bin/python -m pytest tests/Profile/myaccount/test_myaccount.py -v -rs`.

The default configuration is `test_data/myaccount_ui.json`, inspected on Android
Eduport 9.1.0 (100). Credentials come from the git-ignored
`test_data/myaccount_credentials.local.json`; explicit environment variables
`TEST_MOBILE_NUMBER`, `TEST_VALID_OTP`, and `ALLOW_OTP_SEND` override them.

## Default UI mode

The module opens its own Appium session with existing app data preserved. It
logs in if needed, verifies the supplied phone number on Profile, and captures
the original account values. Each test starts from those values, discards its
unsaved edits, reopens My Account, and verifies the original values again.
Account mismatches fail rather than silently switching or modifying users.

Save availability is read from `clickable`: this build exposes `enabled=true`
even for disabled Save. Gender selection is checked from the white border at
the top of the selected card because neither `selected` nor `checked` exposes
it. This visual check is specific to the inspected build/theme and uses Pillow.

The baseline account must have missing required data for ACC_009. That test
fails if run against an account whose fields are all populated.

## Cases requiring more configuration

- ACC_011 and ACC_012: the current account has unset gender and DOB. The UI has
  no inspected controls to restore those empty values after saving. Supply
  independent staging snapshot/prepare/restore through `myaccount_prepare`.
- ACC_016: supply the confirmed invalid-name policy and expected validation.
- ACC_020: additionally supply `myaccount_save_probe` backed by real network
  requests or server counters. Counting taps does not prove one submission.

These cases remain explicitly skipped in default UI mode. To enable staging
mode, set `MYACCOUNT_TEST_DATA` to a JSON following the schema in
`test_myaccount.py` without `mode: live_unsaved`, and provide the required
fixtures in a pytest plugin or conftest. Default UI mode never enables saving
cases even if their `ready` flags are changed.

## Device setup

Appium must be reachable at `APPIUM_SERVER_URL` (default localhost:4723), and
the emulator must have working DNS. On the current network, cold-starting the
existing AVD with `-no-snapshot-load -dns-server 192.168.1.1` restored DNS; that
address is network-specific and is not assumed by the tests.
