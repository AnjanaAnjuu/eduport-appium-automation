# Analysis tests

Run the Effort Index tests with `venv/bin/python -m pytest tests/Analysis/test_effortindex.py`.
Set `EFFORT_UI_DATA` to a JSON file containing `ready: true`, the authorized
`mobile_number`, and inspected `analysis_selectors`. The existing login controls
`TEST_MOBILE_NUMBER`, `TEST_VALID_OTP`, and `ALLOW_OTP_SEND=true` also apply.

The More navigation test can use `tracker_selectors.title` for an inspected
Effort Tracker title locator. If `course_name` is set, configure
`select_course_steps` and `flow_selectors.selected_course` to select and verify
that course before the tests run.

The 44 Study/Revision/Practice/Exam/Cross Effort Tracker cases are in
[effort_tracker/test_study_effort.py](effort_tracker/test_study_effort.py).
Their setup is described in [effort_tracker/README.md](effort_tracker/README.md).
