"""Screenshot capture helpers. Images can contain sensitive application data."""

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DEFAULT_SCREENSHOT_DIR = Path(__file__).resolve().parents[1] / "screenshots"


def take_screenshot(driver, name: str = "screenshot", directory=None) -> Path:
    """Save the current screen and return its path.

    Sanitizes the name and adds a UTC timestamp and random suffix to avoid
    filename collisions. Capture errors propagate to the caller.
    """
    output_dir = (
        Path(directory).expanduser().resolve()
        if directory is not None
        else DEFAULT_SCREENSHOT_DIR
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:80]
    safe_name = safe_name or "screenshot"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    path = output_dir / f"{safe_name}_{timestamp}_{uuid4().hex}.png"
    if not driver.save_screenshot(str(path)):
        raise RuntimeError(f"Appium failed to save screenshot: {path}")
    return path
