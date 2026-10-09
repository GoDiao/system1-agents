# coding: utf-8
"""Every test process writes under a fresh S1A_HOME, with the harness logs routed there as the console entry routes them."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# before the first s1a import: config.HOME is read once, resolved, so the tests compare paths to it directly
os.environ["S1A_HOME"] = str(Path(tempfile.mkdtemp(prefix="s1a-tests-")).resolve())
import s1a.entry  # noqa: E402, F401  the harness loggers write files under S1A_HOME and nothing to sys.stdout
from openjiuwen.core.common.logging.manager import LogManager  # noqa: E402


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    LogManager.reset()  # Close the harness's file handlers before removing their directory on Windows.
    shutil.rmtree(os.environ["S1A_HOME"])
