"""
Regression test for examples/bloom_tutorial.ltl and stdlib/bloom.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned Bloom filter vectors.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_bloom_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "bloom_tutorial.ltl"),
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

    assert "=== LATERALUS STDLIB BLOOM FILTER TUTORIAL ===" in stdout
    assert "STEP 1: Created filter m=64, k=3, initial count=0" in stdout
    assert "STEP 2: Inserted 3 elements. Count=3, set bits=9" in stdout
    assert "STEP 3: True positives: apple=True, banana=True, cherry=True" in stdout
    assert "STEP 4: Negative tests: durian=False, elderberry=False" in stdout
    assert "STEP 5: Filter fill ratio: 140 ppt" in stdout
    assert "STEP 6: Union filter contains apple=True, durian=True" in stdout
    assert "PINNED_VECTORS: count=3 bits_set=9 apple=True durian=False union_apple=True" in stdout


def test_bloom_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "bloom_tutorial.ltl"),
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
    test_bloom_tutorial_execution()
    test_bloom_tutorial_typecheck()
    print("PASS")
