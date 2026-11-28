import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent


def test_http_status_family_example_is_offline_and_executable():
    result = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run",
         "examples/http_status_families.ltl"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "HTTP status family boundaries pass" in result.stdout
