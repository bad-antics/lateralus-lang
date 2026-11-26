"""Run the documented example and check its pinned vectors and sharding demo."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_hash_tutorial(tmp_path):
    # Running outside the checkout also verifies the runner's path handling.
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_hash_tutorial.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        "21 pinned checks passed",
        "Sharding 3 keys across 8 buckets:",
        "alpha -> bucket 3",
        "beta -> bucket 7",
        "gamma -> bucket 2",
    ]
