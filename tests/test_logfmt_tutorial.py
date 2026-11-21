"""
Regression test for examples/logfmt_tutorial.ltl and stdlib/logfmt.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned logfmt output.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_logfmt_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "logfmt_tutorial.ltl"),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    stdout = res.stdout

    assert "=== LATERALUS STDLIB LOGFMT TUTORIAL ===" in stdout
    assert "STEP 1: Encoded logfmt line:" in stdout
    assert 'level=info msg="hello world" job=42 empty=""' in stdout
    assert "STEP 2: Round-trip parsed key-value pairs (count=4):" in stdout
    assert "level -> info" in stdout
    assert "msg -> hello world" in stdout
    assert "job -> 42" in stdout
    assert "PINNED_VECTORS: line='level=info msg=\"hello world\" job=42 empty=\"\"' pairs_count=4" in stdout


def test_logfmt_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "logfmt_tutorial.ltl"),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert "OK" in res.stdout


if __name__ == "__main__":
    test_logfmt_tutorial_execution()
    test_logfmt_tutorial_typecheck()
    print("PASS")
