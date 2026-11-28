"""Keep the published tutorial's command and pinned vectors executable."""
import subprocess
import sys
from pathlib import Path


def test_aho_corasick_tutorial() -> None:
    """Run all assertions in the real .ltl example from outside the repo root."""
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "run_aho_corasick_tutorial.py")],
        cwd=root.parent,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        "error [0,5): error: timeout",
        "timeout [7,14): error: timeout",
        "out [11,14): error: timeout",
        "timeout [0,7): timeout then error",
        "out [4,7): timeout then error",
        "error [13,18): timeout then error",
        "PASS: 53 assertions across 7 vectors and matcher reuse",
    ]
