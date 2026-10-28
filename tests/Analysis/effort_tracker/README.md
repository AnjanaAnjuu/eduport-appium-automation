# Study Effort test cases

`test_study_effort.py` contains all 44 IDs from the supplied case sheet:
ET-STUDY-001–032, ET-REV-001–003, ET-PRACT-001–002,
ET-EXAM-001–002 and ET-CROSS-001–005. The source titles, steps and expected
results are preserved in
[study_effort_cases.example.json](../../../test_data/study_effort_cases.example.json).

Copy the example JSON to a local test-data file and set `STUDY_EFFORT_DATA`
to its path. Inspect the installed app to configure:

- `selectors`: Appium `[strategy, value]` pairs for tracker fields and
  every action target. The tracker fields need readable time labels such as
  `04m:33s`. The default fields are Study, Practice, Exam and Total.
- `select_course_steps`, `flow_selectors.selected_course`, and
  `tracker_entry_steps`: select **JEE Repeater 2027**, verify it, and open
  Analytics → Effort Tracker → More.
- `reset_to_home_steps`: return from any prior test destination to Home.
  This runs before every active case, followed by `tracker_entry_steps`.
- Per-case `phases`: authored UI steps from the tracker, through the
  activity, and back to the tracker. Supported actions are tap, visible,
  absent, back, wait_seconds, screen_off, scroll, swipe_element and
  restart_app. Quiz answer targets must refer to prepared questions.
- `expected_delta_seconds`: independent [minimum, maximum] seconds by
  category, e.g. `{"study":[55,65]}`. Other configured categories must not
  change. The observed Total delta must equal the component deltas.
- `ready: true` on the suite and each prepared case. Missing content and
  expected values leave a case skipped before OTP or Appium startup.

For quiz cases, `attempt` ends before submission, `check_pending` returns
to the tracker to verify no credit, `resume` returns to the quiz, and
`submit` ends at the tracker. Review cases run a submitted
`qualifying_activity` followed by a `review` route; only the latter is
expected to add zero. PDF reopen has separate `first_open` and
`second_open` phases, each with its own expected delta.

The 10-minute video cases check 600 seconds divided by their specified speed.
The two five-minute cap cases require one prepared question to remain open
for more than 300 seconds. History cases require seven dated, independent
observations; day/week consistency requires two corresponding observations.

## Day and Week navigation

Three additional tests check the screen shown in the supplied Effort Tracker
screenshot. Configure `navigation.ready=true`, `today_iso`, eight `days`
entries in order from Today through seven days ago, and the current `week`.
Each day needs its ISO date, displayed label, Effort Index range and expected
Total Time Spent range from independent account data. The week needs its
seven-day start/end dates, Effort Index and weekly time ranges. Configure
`selectors.day`, `week`, `date`, `previous_day`, `next_day`, and
`effort_index` from the live UI. The tests verify:

- Day opens Today, with a left arrow and no visible right arrow.
- Each left tap changes to the expected date and its expected values.
- The eighth left tap cannot move earlier than seven days ago.
- Right taps return through each dated value to Today.
- Week shows the configured current week's Effort Index and time values.

Rows whose expected rule says “verify whether” or depends on approval are
`unresolved` in the example. Set an approved rule and select a concrete
policy only after the product expectation is known. Do not infer tracking
from a screenshot.

The suite opens one Appium session and logs in once for all active cases in
this test module. It signs out and quits once at module teardown. Keep case
content independent: submitted quizzes, watched videos and tracked time
remain on the account between tests even though the screen returns to Home.
Run this module without parallel workers on the same account.

Run with the repository's authorized OTP controls:

```sh
STUDY_EFFORT_DATA=/path/to/study_effort.json \
TEST_MOBILE_NUMBER=9995759936 ALLOW_OTP_SEND=true TEST_VALID_OTP=... \
venv/bin/python -m pytest tests/Analysis/effort_tracker/test_study_effort.py -ra
```
