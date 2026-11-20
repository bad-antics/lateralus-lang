"""Run the documented example and check its pinned vectors and suggestions."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_levenshtein_tutorial(tmp_path):
    # Running outside the checkout also verifies the runner's path handling.
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_levenshtein_tutorial.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        "18 pinned checks passed",
        "Suggestions for aple (at most 2 edits):",
        "apple: 1",
        "maple: 1",
        "apply: 2",
    ]
