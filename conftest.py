"""Root pytest conftest: ensure headless Qt platform for CI environments."""

import os


def pytest_configure(config: object) -> None:
    """Set Qt to use the offscreen platform when no display is available.

    This allows all Qt-backed tests (pytestqt) to run in headless CI
    environments (Docker, GitHub Actions, sandboxes) without X11 or Wayland.
    If a real display is already configured (DISPLAY / WAYLAND_DISPLAY),
    QT_QPA_PLATFORM is left untouched so interactive tests still work.
    """
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolate_qsettings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate QSettings to a per-test temporary directory so tests don't pollute each other."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

