"""
Regression test for examples/influx_line_tutorial.ltl and stdlib/influx_line.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned InfluxDB line protocol outputs.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_influx_line_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "influx_line_tutorial.ltl"),
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

    assert "=== LATERALUS STDLIB INFLUX_LINE TUTORIAL ===" in stdout
    assert "STEP 1: Serialized full sensor metric with nanosecond timestamp:" in stdout
    assert "weather\\ sensor,region=north\\ bay,sensor_id=temp_01 temperature=23.5,error_count=3i,status=\"ok\",active=true 1700000000000000000" in stdout
    assert "STEP 2: Serialized metric omitting timestamp (server arrival):" in stdout
    assert "sensor,region=north\\ bay count=3i" in stdout
    assert "STEP 3: Deserialized measurement: weather sensor" in stdout
    assert "STEP 3: Deserialized timestamp: 1700000000000000000" in stdout
    assert "PINNED_VECTORS: measurement=weather sensor ts=1700000000000000000" in stdout


def test_influx_line_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "influx_line_tutorial.ltl"),
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
    test_influx_line_tutorial_execution()
    test_influx_line_tutorial_typecheck()
    print("PASS")
