# My Course emulator runs

The default fixtures open Profile, scroll to **My Courses**, and test the live
Android screen using inspected selectors from `test_data/mycourse_live.json`.
Supply `TEST_MOBILE_NUMBER`, `TEST_VALID_OTP`, and `ALLOW_OTP_SEND=true` when
running a suite. The session verifies the phone number on Profile and signs
out/re-authenticates if the existing session belongs to a different account.
Each case reopens My Courses from Profile. Help and Contact Us only open the
Reach Us sheet; they do not send messages, place calls, renew, or purchase.

Run the suites separately so accounts and reports stay distinct:

- `tests/Profile/mycourse/test_active_subscription.py`
- `tests/Profile/mycourse/test_expired_subscription.py`
- `tests/Profile/mycourse/test_no_subscription.py`

## What the default live mode can verify

- Header, tab selection, Help, Back, and empty-state content/layout.
- Whether the requested account actually displays an enrollment in a required
  tab. An explicit empty message fails card-dependent cases with an account
  precondition explanation; it is not evidence that all those features are bugs.
- For the no-course account, the entire selected tab panel must contain only
  the expected empty-state text and a single illustration. This does not rely
  on an invented selector for subscription cards that were not present during
  inspection.

The initial inspected account 9995759936 showed empty Active and Expired tabs
in development/UAT build 9.1.0 (100). Live mode does not invent records to compare
against that UI. If populated cards become available, card-dependent checks
skip until populated-card selectors and independent expected records are
configured. The old full-data workflows remain available via
`MYCOURSE_ACTIVE_DATA`, `MYCOURSE_EXPIRED_DATA`, and
`MYCOURSE_NO_SUBSCRIPTION_DATA`.

Expired scenarios 009–017 require independent enrollment records/preparation
(archived, unavailable, multiple, mixed, subject-wise, sticker, or active-only
scenarios). One fixed account cannot establish those test preconditions. Set
up the original expired-data workflow and preparation fixture to run them.

The supplied no-course account 8222211111 reached `Enter Your Details` after
OTP verification. Its profile is not complete in this environment. The
fixture reports this prerequisite as skipped until a test name/gender is
provided and onboarding completed, or another onboarded account is supplied.
It does not invent identity details or complete signup implicitly.
