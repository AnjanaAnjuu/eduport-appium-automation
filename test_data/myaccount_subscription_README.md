# My Account → Subscription tests

The suite contains all 60 supplied acceptance cases. UI locators, seeded accounts,
Mixpanel access, business rules and design baselines were not supplied. These are
integration prerequisites, not verified features. Tests skip when data or a
required fixture is absent; malformed ready cases fail.

Run collection or the suite:

```sh
venv/bin/python -m pytest tests/test_myaccount_subscription.py --collect-only -q
SUBSCRIPTION_TEST_DATA=/absolute/path/subscription.json \
  venv/bin/python -m pytest tests/test_myaccount_subscription.py
```

## Data format

Use a separate JSON configuration for each platform. Minimal structure (replace
example selectors with inspected values; this example is deliberately not ready):

```json
{
  "app_id": "your.application.id",
  "row_key_attribute": "your-stable-rendered-row-attribute",
  "max_scrolls": 50,
  "update_timeout": 30,
  "selectors": {
    "profile_screen": ["accessibility id", "INSPECT_ME"],
    "course": {
      "locator": ["xpath", ".//*[@resource-id='INSPECT_ME']"],
      "attribute": "text"
    }
  },
  "routes": {
    "profile": ["profile_tab"],
    "list_top": ["list_top_control"],
    "list_next": ["list_next_control"],
    "reload": ["reload_control"],
    "return_to_subscription": ["return_control"]
  },
  "cases": {
    "TC_006": {
      "ready": false,
      "account_kind": "active",
      "expected": [{
        "enrollment_id": "seed-enrollment-1",
        "course": "Seeded course",
        "batch": "Seeded batch",
        "expiry": "31 Dec 2026",
        "status": "Active"
      }]
    }
  }
}
```

Each test needs its own `TC_001`…`TC_060` case, with `ready: true` only after
independent account preparation is implemented. Expected values must come from
seed data, never from the UI being tested. Expected rows always require
`enrollment_id`, `course`, `batch`, `expiry`, `status`. Subject and Continuous
cases also need `subject` / `continuous` in expected rows and selectors.

Page selector names, as needed by the cases:

- Navigation: `profile_screen`, `subscription_entry`, `subscription_screen`,
  `back`, plus any route targets.
- Content: `loading`, `cards`, `list_end`, `empty`, `missing_subscription`.
- Card-relative fields: `enrollment_id`, `course`, `batch`, `expiry`, `status`,
  optional `subject`, `continuous`. XPath field selectors must start with `.`
  to stay scoped to their card. Optional field selectors should expose empty
  text when not applicable, or adapt the reader to the app's semantics.
- Contact: `contact_us`, `contact_options`, `whatsapp`, `call_contact`,
  `renew_message`, `renew_contact`.
- Connectivity: `offline_screen`, `offline_message`, `try_again`,
  `go_to_downloads`, `downloads_screen`, `api_error`.

Selectors may be `[strategy, value]` or an object containing `locator` and an
optional `attribute` (for Flutter semantics use `content-desc` on Android or
`label` on iOS). No subscription selectors have been verified against a device.

Routes are lists of selector names to tap. `profile` must work from each relevant
app state. Adapt `route()` for swipe-only lists: `list_top` must reliably reset
the scroll position; `list_next` must move forward with overlap after content
settles. `list_end` must prove the entire list was traversed, including empty
lists. `row_key_attribute` must be stable per rendered list row across scrolls
and different for duplicate enrollment occurrences. Do not use enrollment ID
as this key: doing so would hide duplicate enrollment bugs. If the app exposes
neither row identities nor a list-end sentinel, add test semantics or implement
an app-specific complete-list traversal before marking these cases ready.

## Fixture integration

Implement these fixtures in `tests/conftest.py` or a local pytest plugin. Existing
login/OTP and coin tests are unaffected.

- `subscription_authenticated_driver(subscription_case)`: create an isolated
  Appium driver, seed the requested account, authenticate and yield the driver
  at Home/Profile. Restore seed state and quit in `finally`. This deliberately
  does not request the shared `driver` fixture, which always logs out. Android
  can reuse `utils.driver.create_driver`; iOS needs an XCUITest factory. Use
  existing OTP authorization controls if the implementation sends SMS. Never
  use real subscription purchases to prepare a case.
- `subscription_network`: callable `(driver, online=False)` returning a context
  manager. Capture and restore the exact initial network state even on failure;
  disable all usable transports, not just Wi-Fi. Required for 031–036 and 049.
- `subscription_analytics`: object with `cursor(case)` and
  `wait_event(case, cursor, event_name) -> bool`. Poll captured Mixpanel events
  after the cursor, scoped to the test user/session. Required for 005 and 018.
- `subscription_backend`: object with context managers `hold_response(case)`
  and `fail_response(case)`, and `change(case, action)` for update, renew,
  expire, add. Use controlled staging service/proxy support. Hold the actual
  subscription response until context exit for 037. Restore fault injection
  and enrollment mutations in fixture teardown. Required for 036–038, 057–059.
- `subscription_visual`: callable `(driver, case, scope) -> bool` comparing
  screenshots against approved platform/device baselines. Check truncation,
  alignment, badge colors and full-page design according to scope. Do not
  substitute element existence for a visual comparison. Required for 028–029,
  039–040, 043–046, 060. Fixtures own diff artifact storage.
- `subscription_relogin`: callable `(driver, case)` performing actual logout,
  verifying the login screen and logging back into the same account. Required
  for 051. Merely restarting the app does not satisfy this contract.

Fixtures receive `(data, case)` through `subscription_case`. Prerequisite
providers are resolved before the driver. Provider setup must not itself create
a driver; the call receives it where needed. Exceptions from installed providers
are failures, not silently converted to skips.

## Case-specific data

- 003/004: `account_kind: "trial"`; 027: `expected: []`.
- 016/017: `external_destination`, the selector name for the external app or OS
  contact screen. Opening support options alone does not satisfy these tests.
  Do not configure a control that sends a message or places a call.
- 018: nonempty `events` mapping actual Renew contact option selector names to
  confirmed Mixpanel event names.
- 022: `expected` in approved sort order, with at least two enrollments.
- 023/024: `excluded_ids.archived` / `excluded_ids.unavailable` with seeded IDs.
- 025: `expired_batch_rule`, `expired_batch_ids`, and expected visible rows
  matching the approved rule; no visibility rule was specified in the request.
- 028/029: independently seed names long enough to wrap/truncate at the target
  viewport and provide corresponding visual baselines.
- Visual cases: nonempty `targets` listing visible labels/buttons to check for
  bounds and a baseline identifier understood by the visual provider.
- 036, 057–059: `expected_after`, distinct from `expected`.
- 038: exact `error_message`.
- 040: boolean `landscape_supported`; unsupported orientation is skipped.
- 041/042: run on Android/iOS respectively; the other platform skips.
- 043: `device_form_factor: "tablet"`, verified by the driver fixture against
  the device inventory, plus tablet baseline.
- 047: `expiry_pattern` for exact format and `expiry_format` for strptime.
- 052: product-approved `minimum_enrollments` and `max_load_seconds`. Timing
  includes Profile navigation through the first loaded Subscription state;
  completeness is checked afterward across the entire list.
- 057/058: `changed_id`; renewed Expired → Active with a new expiry date,
  or Active → Expired, respectively.

Live UI, backend, analytics and visual behavior require the integrations above;
collection and an unconfigured skipped run do not establish acceptance coverage.
