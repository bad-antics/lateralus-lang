"""
Regression test for examples/ini_tutorial.ltl and stdlib/ini.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned INI configuration outputs.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_ini_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "ini_tutorial.ltl"),
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

    assert "=== LATERALUS STDLIB INI TUTORIAL ===" in stdout
    assert "STEP 1: Parsed INI document sections:" in stdout
    assert "server.host = api.example.com" in stdout
    assert "server.port = 8080" in stdout
    assert "server.timeout = 30.5" in stdout
    assert "server.ssl = True" in stdout
    assert "database.name = production" in stdout
    assert "database.pool_size = 20" in stdout
    assert "STEP 3: Mutated and serialized INI:" in stdout
    assert "STEP 4: Merged server.port=9000 workers=8" in stdout
    assert "PINNED_VECTORS: host=api.example.com port=8080 ssl=True merged_port=9000" in stdout
    assert "ini tutorial: all checks passed" in stdout


def test_ini_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "ini_tutorial.ltl"),
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
    test_ini_tutorial_execution()
    test_ini_tutorial_typecheck()
    print("PASS")
