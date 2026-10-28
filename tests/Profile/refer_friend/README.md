# Refer a Friend / Share the App

## Focused suite: `test_refer.py`

`pages/Profile/refer_friend/refer_page.py` provides `ReferPage` for these cases:

| Case | Check | Expected result |
| --- | --- | --- |
| REF001 | Refer a Friend button | Visible, enabled, and within the screen |
| REF002 | Click Refer a Friend | The configured destination opens with the full expected URL |
| REF003 | Tap Refer a Friend three times rapidly | One native share sheet is visible, exactly one launch is recorded, and dismissing it returns to Profile without another sheet |

```sh
REFER_FRIEND_TEST_DATA=/absolute/path/referral.json \
  venv/bin/python -m pytest tests/Profile/refer_friend/test_refer.py -v -rs
```

With no `REFER_FRIEND_TEST_DATA`, the focused suite now uses the inspected
Android emulator flow: authenticates the supplied account, opens Profile,
scrolls to `Refer\na Friend`, and reads native Android activity events for
duplicate launches. Run it with:

```sh
TEST_MOBILE_NUMBER=<authorized-number> TEST_VALID_OTP=<otp> ALLOW_OTP_SEND=true \
  venv/bin/python -m pytest tests/Profile/refer_friend/test_refer.py -v -rs \
  --junitxml=reports/refer_latest.xml
```

Appium and the emulator must be running. `ANDROID_UDID` defaults to
`emulator-5554` for event collection; `ADB_PATH` can override adb discovery.
The inspected app opens a native share sheet, so REF002 currently fails the
requested direct-browser-navigation expectation. This is a behavior/requirement
mismatch, not missing test setup. The test does not treat a preview URL as a
browser destination.

When an explicit data path is supplied, the suite uses the `referral_session`
and `referral_share_probe` integration contracts documented below. Missing
custom providers produce explicit skips. Invalid configured selectors fail setup.
The session must restore navigation state even if an assertion fails.

All three cases need inspected `profile_screen` and `refer_friend` selectors
and a nonempty `routes.profile`. The route should finish with the referral
button visible; include the actual scroll navigation in the session/route
implementation when needed. REF002 also needs `download_url`,
`url_destination` (the loaded browser/webview destination), and `opened_url`
(the full browser address, using a selector attribute if appropriate).
REF003 needs `share_sheet` and `cancel_share` selectors, plus the share probe.
Optional `focused_cases.REF003.tap_count` accepts 2–5, default 3.

REF002 tests **direct URL navigation caused by the button click**. A URL merely
shown in the share preview does not satisfy it. If the actual product only
opens a share sheet, that expectation needs clarification before configuring
this case; the existing TC_003 and TC_013 cover shared content and recipient
URL navigation instead. REF003 neither chooses a recipient nor sends a message.

`pages/Profile/refer_friend/refer_friend_page.py` and `test_refer_friend.py`
implement TC_001–TC_025. The image is a UI reference: its preview is truncated,
so the actual URL, message, locale and recipient destination are not inferred.

```sh
venv/bin/python -m pytest tests/Profile/refer_friend --collect-only -q
REFER_FRIEND_TEST_DATA=/absolute/path/referral.json \
  venv/bin/python -m pytest tests/Profile/refer_friend
```

## Configuration

Supply independently verified JSON with:

```json
{
  "app_id": "actual.application.package.or.bundle",
  "store_app_id": "actual.store.listing.id",
  "download_url": "https://your.actual.referral.host/path",
  "app_name": "Eduport",
  "expected_message": "Actual approved localized message and URL",
  "selectors": {},
  "routes": {"profile": []},
  "cases": {"TC_001": {"ready": false}}
}
```

Replace example values; set each `cases.TC_###.ready` true only when its setup
is available. `download_url` must be the expected complete URL, including query
parameters/referral tokens. The tests do not use a guessed Play Store URL.

Selectors are `[strategy,value]` or `{"locator":[strategy,value],"attribute":
"content-desc"}`. Required names: `profile_screen`, `refer_friend`, `share_sheet`,
`cancel_share`, `profile_back`, `previous_screen`, `copy_link`. Add `offline_error`
for offline rejection and each `<medium>_composer` for sharing cases. These must
identify actual native system/target-app UI, not app-owned imitation dialogs.

Routes are nonempty lists of selector names to tap. `profile` navigates from the
session's authenticated initial state to Profile. `share_whatsapp`, `share_sms`,
`share_email`, `share_telegram`, `share_slack`, `share_bluetooth` and/or
`share_nearby_share` handle real pagination/More options and open the intended
composer. Extend the page's route method with inspected native gestures if the
sheet is swipe-only. Routes must stop before selecting a recipient or sending.

## Integration fixtures

Define project-owned fixtures in parent conftest.py or a pytest plugin:

- `referral_session`: callable `(data,case)` returning a context manager yielding
  an authenticated Appium driver. Own setup/login, restore clipboard, app/device
  state and quit in `finally`. Use actual platform/device capabilities and verify
  tablet form factor from device inventory. Honor existing OTP/SMS controls when
  authenticating. Do not seed from the personal name/number in the screenshot.
- `referral_share_probe`: reads native share intent/activity payloads rather than
  the truncated preview. Methods:
  - `payload(driver) -> {text,mime_type}` for the current share operation.
  - `sheet_info(driver) -> {native,owner,visible_sheet_count}` from native activity
    or accessibility evidence. Count sheet roots, not option rows or contacts.
  - `cursor(driver)`; `actions_since(driver,cursor)` lists actual share/copy/send
    actions, excluding opening/canceling the sheet.
  - `all_targets(driver)` traverses every sheet page/More area and returns stable
    share-target IDs. Do not confuse recipient suggestions with applications.
  - `sheet_launches_since(driver,cursor)` counts launches, waiting for queued
    launches after dismissal. This must not merely count currently visible roots.
- `referral_delivery`: `available(driver,medium) -> bool` verifies installation
  and setup. `send_and_wait(driver,medium,recipient,payload,case)` operates only
  on `authorized_test_recipient`, records a pre-send baseline and returns fresh
  correlated delivery evidence `{medium,recipient,delivered,message_id,text}`.
  Evidence must come from the controlled receiving account/device (or verified
  delivery service), not composer contents or old messages. Nearby/Bluetooth
  requires a paired, consenting receiver and confirmed received text/file.
- `referral_recipient`: `open_url(url,state,case)` runs on a **separate disposable
  recipient device**. Prepare and independently verify install/login state,
  open the actual shared URL through browser/OS link dispatch, observe redirects
  and return the fields asserted by TC_013–017. Do not directly activate the app
  or manually navigate to the expected page to manufacture a deep-link pass.
  Install tests use controlled devices and the correct store listing. Restore
  recipient state afterward. A post-install destination must follow the actual
  installation/referral flow; do not substitute manually entering the app page.
- `referral_network`: context-manager factory `(driver,'offline')`, yielding
  `active_transport()` and restoring exact prior connectivity on exit. Disable
  all usable transports, not just Wi-Fi.
- `referral_visual`: callable `(driver,case,scope) -> bool` comparing approved
  OS/device-specific Profile and native share-sheet baselines; capture relevant
  screens and persist diffs. System share-sheet appearance varies by OS/vendor.

Missing prerequisites skip before driver creation. Installed-provider failures
fail. No live sends, installations or account mutations were executed when
creating these files. To run delivery cases, explicitly configure a controlled
recipient; do not point tests at personal contacts or production channels.

## Case-specific data

- 002: `native_sheet_owner` independently verified for the target OS/vendor.
- 004–009: `authorized_test_recipient`; 009 additionally `medium` equal to
  `bluetooth` or `nearby_share`. Unavailable apps skip instead of falsely passing.
- 010: `expected_clipboard` (actual full message or URL according to the platform).
  Clipboard is first changed to a unique sentinel to rule out a stale-value pass;
  the session must restore the original clipboard even after failure.
- 012: `supported_targets`, at least two IDs from the independent installed-app
  inventory. Only eligible installed applications are expected, not every named
  service regardless of installation.
- 013: `allowed_destination_hosts` for the real app/store landing hosts. The
  recipient provider reports actual final HTTP status and navigation errors.
- 014/015/017: `expected_destination`; 015: approved `post_login_rule` and supported
  recipient authentication. Recipient results include verified initial states,
  foreground app ID and screen, plus the flags asserted in each test.
- 016: `expected_store` (Play Store on Android, App Store on iOS), verified listing
  ID from `store_app_id`. Do not treat merely opening a store as the right listing.
- 018: approved `offline_rule`, `offline_behavior` (`share_sheet` or `error`) and
  exact `offline_error` for the latter. Showing a share sheet offline does not
  claim that a network message was delivered.
- 021: `device_form_factor: "tablet"` plus verified visual baseline.
- 024: optional `tap_count` from 2 to 5 (default 3).
- 025: approved design baseline/locale/device information for the visual provider.

TC_023 checks the full message against the expected localized template, including
app name and exact URL. It does not copy the screenshot's truncated Malayalam
preview as an expected complete share message.
