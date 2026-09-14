"""Load sample test data independently of the current working directory."""

import json
from pathlib import Path


def load_test_data(name: str) -> dict:
    """Load a named dataset: 'login' or 'otp'."""
    if name not in {"login", "otp"}:
        raise ValueError(f"Unknown test dataset: {name!r}")
    path = Path(__file__).parent / f"{name}_data.json"
    with path.open(encoding="utf-8") as data_file:
        return json.load(data_file)
