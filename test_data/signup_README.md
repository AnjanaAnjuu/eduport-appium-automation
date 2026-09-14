# Signup suite: SUP-01–SUP-20

Page object: `pages/Login/signup_page.py`. Tests: `tests/Login/test_signup.py`.
Authorized configured phone: **6224572310**. `test_data/signup_data.json` contains
names, conditional policy settings and optional inspected locator overrides.
Set `SIGNUP_TEST_DATA` to load a different approved data file.

## Readiness and independence

These are generated assertions, not live-verified signup results. No OTP request
or profile creation was performed to generate these files. The default locators
follow your supplied labels (Enter Your Details, Enter full name, Female, Male,
Save & Continue, Course Selection) and need verification in Appium Inspector.
Override them in `selectors` with `[strategy, value]` if the actual UI differs.
Supported strategies: accessibility id, id, xpath, class name, -android uiautomator.

Each test gets its own Appium session, app restart, OTP login, and verified blank
onboarding draft. Form-only checks no longer require a backend reset provider:
they may use normal login, but still fail setup if the form is not fresh/blank.
An enabled invalid submission is skipped without approved isolation because it
could unexpectedly create a real account. The number alone does not guarantee a new account. Successful SUP-07 and
SUP-20 consume onboarding state: restarting the app does NOT unregister a user.
To make successful submissions independent on one phone, configure the implemented
**staging-only** `signup_prepare_account` fixture in `tests/conftest.py`. It returns
a callable `prepare(mobile_number, sup_id)`. Its contract is to prepare the authorized number
as an unregistered/unfinished account with a blank name, no gender and clean,
logged-out app state. Its fixture teardown must restore authorized staging state.
No account deletion/reset endpoint is guessed by this project. An unconfigured
API produces a prerequisite skip BEFORE creating an Appium session or sending
OTP. Do not use a destructive reset on production accounts.

The signup suite uses its own driver fixture because the existing Home-only logout
helper cannot handle half-created accounts. Existing login/OTP tests are unchanged.
Shared screenshot hooks still capture signup setup/call failures via the driver stash.
Close active Inspector/test sessions before live execution; sessions are not deleted
automatically by this suite.

## Selection and validation evidence

Gender assertions read actual `checked` / `selected` attributes. If Flutter only
exposes selection through a separate accessibility node, configure exact
`female_selected` / `male_selected` locators. The page object never treats the last
tap or a Python variable as proof of UI selection.

If validation is inline and the button stays enabled, configure actual `name_error`
and `gender_error` locators. Negative cases accept disabled Continue OR a real
configured validation element after submission, and reject Course Selection.
Cases explicitly requiring disabled Continue assert that stricter behavior.

SUP-13/SUP-14 are conditional in your requirements: confirm and set
`allow_numeric_only_names` / `allow_special_only_names` to false before testing
rejection. Null means policy is unconfirmed; true means the rejection scenario is
not applicable. Those cases then have explicit prerequisite/not-applicable skips.

## Duplicate submission: SUP-20

Seeing Course Selection once cannot prove that the server processed only one
submission. Configure the implemented read-only authoritative fixture
`signup_submission_probe`, returning a callable `probe(mobile_number)` with this mapping:

```python
{
    "successful_submissions": 0,
    "course_navigations": 0,
    "profiles_created": 0,
}
```

The values above illustrate the schema, not a fake probe to paste into a passing
test. Supply real scoped backend/test-instrumentation counters (including actual
navigation events) for this account and test window. The test measures the before/
after delta and checks it for the full bounded observation period. It never derives
these counters from how many times its own tap method ran. Missing instrumentation
skips SUP-20 before any signup action.

Confirm `expected_profile_create_delta` as 0 or 1. Some apps create the account at
OTP verification and Save only updates details; others create a profile on Save.
The suite does not guess which behavior applies. Both successful submission and
Course Selection navigation must occur exactly once. Taps target only the original
Save element; no stale coordinate taps are sent onto the next page. If navigation
removes Save immediately, further taps stop, rather than clicking course controls.

## Configure the real staging adapters

The fixtures are implemented in `tests/conftest.py` with the HTTP adapter in
`utils/signup_support.py`. They do not fabricate accounts or counters. Fill
`staging_api` in signup_data.json using your actual verified server contract:

- `base_url`: approved staging origin (HTTPS except loopback). No credentials in URL.
- `snapshot`: method GET, phone-scoped path/query using `{mobile_number}`. Response
  must echo that phone and provide a nonempty restoration token BEFORE preparation.
- `prepare`: method POST, verified path, JSON `payload` containing the exact
  `{mobile_number}` as a field value; optional `{sup_id}` for scoped case setup.
- `restore`: method POST, verified path, JSON `payload` containing the exact
  `{mobile_number}` and captured `{restore_token}` as field values.
- `probe`: method GET, phone-scoped path/query using `{mobile_number}`; response
  echoes the phone and includes real successful_submissions, course_navigations,
  profiles_created counters. Navigation events need actual test instrumentation.

Response phone/token keys are configurable through `mobile_response_key` and
`restore_token_response_key`. Tokens/phone payloads are not forwarded on redirects.
Set `SIGNUP_STAGING_API_APPROVED=true` only after confirming these are approved
staging endpoints. Optional bearer authentication uses `SIGNUP_STAGING_TOKEN` in
the process environment, never JSON. The adapter snapshots before writing and
restores during fixture teardown even if preparation or the test fails.

No API endpoint is prefilled: this repository does not contain the server contract.
Do not invent a reset endpoint, enable writes against production, or use a no-op
fixture. SUP-07/SUP-20 stay prerequisite skips until real staging configuration is
available. Form checks can run without that API only when normal login reaches a
fresh blank form. A reused account with completed details is not a fresh signup.

## Collect and run

From `/Users/anjana/eduport_appium`:

```bash
venv/bin/python -m pytest tests/Login/test_signup.py --collect-only -q
```

After Inspector verification, a staging reset provider, confirmed policies/probe
as applicable, and an actually valid OTP for this number:

```bash
NO_RESET=true ANDROID_UDID=emulator-5554 \
TEST_MOBILE_NUMBER=6224572310 TEST_VALID_OTP=4305 \
ALLOW_OTP_SEND=true ALLOW_SIGNUP_TESTS=true \
venv/bin/python -m pytest tests/Login/test_signup.py \
  --junitxml=reports/signup_results.xml
```

4305 was the previously supplied default test OTP, not verified for this new number.
Replace it if the backend requires another valid OTP. The OTP is not stored in JSON.
All tests run independently, without `-x`. The dedicated signup gate is disabled by
default. Running the suite can send many OTP requests and create/save profiles;
use controlled staging data and do not parallelize on one emulator/account.

Generate HTML with the existing project utility:

```bash
venv/bin/python utils/html_report.py reports/signup_results.xml \
  reports/signup_report.html --expected-count 20
```

Skipped cases are not passes. Keep phone numbers and account screenshots private.
