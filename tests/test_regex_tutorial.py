"""Regression tests for stdlib.regex tutorial companion (issue #888)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_regex_tutorial_execution() -> None:
    example_path = REPO_ROOT / "examples" / "regex_log_extraction.ltl"
    result = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(example_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=_env(),
    )
    output = result.stdout
    assert "First Job ID: sync-104" in output
    assert "All Job IDs:  [sync-104, build-7]" in output
    assert "Has Jobs:     True" in output
    assert "All Job IDs:  []" in output
    assert "Has Jobs:     False" in output
    assert "PINNED_VECTORS:" in output
    assert "✓ examples/regex_log_extraction.ltl: OK" in output


def test_regex_tutorial_typecheck() -> None:
    example_path = REPO_ROOT / "examples" / "regex_log_extraction.ltl"
    result = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "check", str(example_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=_env(),
    )
    assert "OK" in result.stdout
