# Test data

These files contain sample, non-secret values. Use TEST_MOBILE_NUMBER for an
authorized test account and TEST_VALID_OTP for a valid OTP. Do not commit real
credentials, OTPs, or personal information.

```python
from test_data import load_test_data

data = load_test_data("login")
number = data["invalid_mobile_number"]
```

Existing tests keep their current environment-based settings; these datasets
are available for new tests or future parameterization.
