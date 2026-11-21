"""
Regression test for examples/nats_tutorial.ltl and stdlib/nats.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned NATS wire frames.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_nats_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "nats_tutorial.ltl"),
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

    assert "=== LATERALUS STDLIB NATS TUTORIAL ===" in stdout
    assert "STEP 1: Multiline PUB with reply inbox (6 payload bytes):" in stdout
    assert "PUB press.status _INBOX.press 6" in stdout
    assert "STEP 2: Multiline PUB without reply (17 payload bytes):" in stdout
    assert "PUB telemetry.sensor 17" in stdout
    assert "STEP 3: Empty PUB heartbeat (0 payload bytes):" in stdout
    assert "PUB heartbeat 0" in stdout
    assert "STEP 4: PUB with trailing CRLF in payload (10 payload bytes):" in stdout
    assert "PUB logs.app 10" in stdout
    assert "STEP 5: Parsed incoming server message:" in stdout
    assert "op=MSG" in stdout
    assert "subject=press.status" in stdout
    assert "PINNED_VECTORS: len1=41 len2=44 len3=19 len4=29 op=MSG" in stdout


def test_nats_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "nats_tutorial.ltl"),
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
    test_nats_tutorial_execution()
    test_nats_tutorial_typecheck()
    print("PASS")
