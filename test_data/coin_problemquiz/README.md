# Coin & problem-based quiz tests

`pages/Leaderboard/coin_problemquiz_page.py` is the page object. `tests/Leaderboard/test_coin_problemquiz.py`
contains all 34 scenarios (one independent pytest function per TC ID).

Default identity: **9995759936**, course **JEE Repeater 2027**. The OTP is supplied
through `TEST_VALID_OTP`, not stored in test data. The previously supplied default
test OTP is 4305; use it only where this staging account actually accepts it.

## Current readiness

The test logic is implemented, but coin/quiz selectors, answer keys, scoring rules,
and staging fixtures could not be verified during generation: the account's login
check did not authenticate, and an Inspector session was active. No quiz was
answered or coin collected. `Home` is the previously observed accessibility label;
all unobserved selectors are deliberately `null`, not fabricated IDs.

The default dataset has `ready=false` on all 34 cases. This is a configuration
template, not a claim of 34 device-verified passes. Collection and safety checks
work without configuring or sending SMS. Each ready case still needs its own
pristine/known attempt state and ledger. A fresh Appium session does not reset
backend attempts, account age, prior collections, or course question changes.

## Configure the app and data

1. Confirm the product/server timezone and put its IANA name in `server_timezone`.
   Do not assume the emulator timezone defines server midnight.
2. Inspect the selected course, coin panels, quiz/results, and history. Set each
   needed selector to `[strategy, exact_identifier]`; prefer stable resource IDs
   or accessibility IDs. Do not use a bare numeric text locator for balances.
3. Configure nonempty global `paths` with the actual navigation steps. `course`
   must select this course from any starting screen; `course_title` verifies it.
   `home` and optional per-case `phases.cleanup` must handle quiz exits/confirmation
   and reach Home before the shared fixture signs out.
4. Provide an independently known answer key, full question count and configured
   reward for each case. Do not copy the app's observed result into the expected
   data simply to make the test pass.
5. Provide a project-owned `coin_prepare_case` pytest fixture returning a callable
   `(tc_id, scenario, data)`. It should prepare only authorized staging state for
   this account/course. No reset/delete endpoint is invented by this project.
   If a case already has a dedicated independently prepared quiz/ledger, set
   `requires_seed_provider=false` explicitly. Do not reuse a consumed first
   attempt across scenarios or make one test depend on another.
6. Set only the prepared cases to `ready=true`. Keep the rest false, with explicit
   skip reasons. `TC001` also requires `is_new_user=true`: an existing account must
   not be relabelled/reset as a new account to manufacture zero coins.

Selector with a label containing multiple numbers:

```json
{"locator": ["accessibility id", "INSPECTED_IDENTIFIER"], "pattern": "Coins: ([+-]?[0-9,]+)"}
```

`INSPECTED_IDENTIFIER` above is illustrative, not an app ID. The count parser
requires exactly one integer or a regex with exactly one captured integer.

Supported UI steps:

```json
{"action": "tap", "target": "configured_selector_name"}
```

Also supported: `enter_text` (with `text`), `wait_visible`, `wait_absent`, `back`,
`hide_keyboard`, and `scroll` (with an inspected scroll-container `target`, optional
`direction` and `percent`). Inline `[strategy, value]` targets are accepted.
There are no arbitrary Python/shell/HTTP execution steps.

## Reward/result scenario schema

Add fields to a case in `cases.json`. For completed quizzes, required fields are:

```json
{
  "ready": false,
  "requires_seed_provider": true,
  "quiz_kind": "topic_concept",
  "expected_total": 1,
  "expected_coins": null,
  "answers": [
    {
      "question_id": "AUTHOR_THE_REAL_QUESTION_ID",
      "outcome": "correct",
      "steps": []
    }
  ],
  "phases": {"open": [], "submit": [], "collect": [], "cleanup": []}
}
```

This is deliberately not runnable sample data: author real navigation/selection
steps and the real configured reward before enabling it. `outcome` is independently
known `correct`, `wrong`, or `unknown` (I don't know). Each answer has nonempty UI
steps, including navigation as necessary. Repeated question IDs use the final
selection for expected counts. Include every final question outcome, including
unknowns. Coin scoring is not guessed: supply the configured `expected_coins`.
TC005/TC006 enforce 10. TC018/TC020 require positive reward; TC019 requires negative;
TC032 requires zero. Positive rewards are credited through an actual Collect Coins
phase, not by page-object arithmetic or backend bypass.

`immediate_update_timeout_seconds` is a bounded UI consistency wait (default 20),
not a next-day retry. Deltas must occur within one product calendar day. Snapshots
read Home and each leaderboard period through explicit paths.

## Per-scenario additions

| Cases | Additional data / phases |
|---|---|
| TC002–TC006 | `quiz_kind`: topic_concept, subtopic, practice, exam, daily_task respectively |
| TC011 | `expected_before` and `expected_after` balance objects; nonzero Today, expected Today zero; `refresh_after_boundary` phase |
| TC012 | `expected_before`, `expected_after`, nonzero prior Weekly; `expected_weekly_history`; `refresh_after_boundary` |
| TC013–TC015 | Nonempty `expected_history`; All Time must contain multiple dates |
| TC017 | First two answers share an ID and change correct→wrong; `expected_indicator_text` follows the product's defined behavior |
| TC019/TC032 | `close` phase and actual Close locator; zero-result collection may also be tested if enabled |
| TC021 | `review`, `leave_review`, and `recollect` if collection remains actionable |
| TC022 | `review`; inspected Coins Collected marker |
| TC023 | `refresh_after_change`, `review`; stable `collected_value` selector |
| TC024 | `after_change_answers` (new correct answers), `expected_total_after`, `expected_correct_after`, `expected_balance_delta_after_change`, `after_change_submit`, `refresh_after_change` |
| TC025 | `expected_total_after`, `open_after_change`, `review`, `refresh_after_change`; total increases by one |
| TC026 | `variants.positive` and `.negative`, each a complete independent quiz scenario; negative has `expected_coins_after_pending`; both have `refresh_after_change` and `review` |
| TC027 | `partial_answers`, `expected_total`, `open`, `exit_incomplete` |
| TC028 | `partial_answers`, complete `answers`, `expected_total`, `expected_coins`, `open`, `exit_incomplete`, `reopen`, `resume`, `submit`, `collect` |
| TC030 | At least one correct, wrong, and unknown authored outcome |
| TC031 | `leaderboard_navigation_available` boolean, `navigate_to_leaderboard`, actual leaderboard-screen marker |
| TC033 | `partial_answers`, final complete `answers` including the new question, `expected_total_before`, `expected_total`, nonzero configured `expected_coins`, `open`, `exit_incomplete`, `refresh_after_change`, `reopen`, `resume`, `submit`, `collect` or `close` |
| TC034 | Complete nonempty all-time transaction ledger; no hidden opening balance or omitted old transactions |

Balance objects use `home`, `today`, `weekly`, `all_time` integer keys. The current
suite interprets the Home total as the all-time earned total, and Weekly as
Tuesday–Monday, following these requirements. Confirm those product definitions
before enabling the suite; adjust the oracle if the product defines them differently.

Admin cases TC023–TC026 and TC033 additionally need
`ALLOW_COIN_ADMIN_MUTATIONS=true` and a pytest fixture `coin_admin_change` returning
a callable `(tc_id, change_kind, scenario_or_variant, data)`. Implement the approved
staging change and restoration there, not by changing production questions. Kinds:
`delete_adaptive`, `add_adaptive`, `add_new_question`, `mark_pending`, and
`add_question_during_resume`. These providers are not implemented because the
project has no verified administration interface. A missing provider yields a
specific prerequisite skip before sending OTP.

## Calendar tests

TC011/TC012 require `ALLOW_COIN_BOUNDARY_TESTS=true` and controlled seeded history.
Run near actual product midnight/the Tuesday refresh, within the configured 60-second
boundary budget. Configure `weekly_refresh_time` as the confirmed Tuesday HH:MM in
`server_timezone`; the Tuesday refresh time was not specified and is not guessed.
The suite does not change emulator or server clocks. TC011 uses explicit expected
Weekly values, including a coincident weekly refresh if the product schedules one.
Other coin-earning activity on the same account
must be paused while the boundary observation runs.

## Complete coin history

Set `log_rows`, `log_scroll_container`, an inspected `log_end` sentinel and a
`history.row_pattern` matching the full row text with named groups `id`, `coins`,
`recorded_at`. Rows need unique transaction IDs and ISO timestamps with timezone
offsets. If the UI does not expose these fields, add an approved read-only ledger
adapter/accessibility support; do not claim complete history based on visible rows.

`expected_history` entries have this shape:

```json
{"id": "REAL_TRANSACTION_ID", "coins": 10, "recorded_at": "2026-09-13T12:00:00+05:30"}
```

The date/ID above are illustrative. Use the actual prepared ledger. History
pagination is bounded by `max_pages` and must reach the end sentinel to pass.

## Collect, run, report

From `/Users/anjana/eduport_appium`:

```bash
venv/bin/python -m pytest tests/Leaderboard/test_coin_problemquiz.py --collect-only -q
```

Run only after configuring approved staging data; close Inspector's active session
first. Existing sessions are not automatically deleted by these tests.

```bash
NO_RESET=true ANDROID_UDID=emulator-5554 \
TEST_MOBILE_NUMBER=9995759936 TEST_VALID_OTP=4305 \
ALLOW_OTP_SEND=true ALLOW_COIN_TESTS=true \
venv/bin/python -m pytest tests/Leaderboard/test_coin_problemquiz.py \
  --junitxml=reports/coin_problemquiz_results.xml
```

No `-x`: every selected case is attempted independently. Enable admin/boundary
flags only for the appropriate controlled subset, for example
`-k 'tc011 or tc012'`. A full reward suite can send many OTP requests and mutate
quiz attempts/coins; a reused account can encounter throttling. Do not parallelize
these live tests on one emulator/account. Shared fixture sign-out preserves data,
but provider teardown must restore changed staging questions and prepared state.

Generate standalone HTML using the project's existing report utility:

```bash
venv/bin/python utils/html_report.py reports/coin_problemquiz_results.xml \
  reports/coin_problemquiz_report.html --expected-count 34
```

Skips mean prerequisites are unmet, not passes. Setup errors and test failures
capture screenshots through the shared fixture hook. Do not publish phone numbers
or account screenshots without review.
