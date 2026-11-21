"""
Regression test for examples/lru_tutorial.ltl and stdlib/lru.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned outputs.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_lru_tutorial_execution():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "run",
        str(REPO_ROOT / "examples" / "lru_tutorial.ltl"),
    ]
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = res.stdout

    assert "=== LATERALUS STDLIB LRU TUTORIAL ===" in stdout
    assert "STEP 1: Initialized LRU cache capacity=3, size=0" in stdout
    assert "STEP 2: Inserted 3 items. Cache size=3" in stdout
    assert "STEP 3: Accessed user:1 -> value=Alice (hits=1, misses=0)" in stdout
    assert "STEP 4: Inserted user:4 -> user:2 evicted: has_user2=False, has_user1=True" in stdout
    assert "STEP 5: Querying evicted key -> val=None (hits=1, misses=1)" in stdout
    assert "STEP 6: Resized cache to capacity=2 -> current_size=2" in stdout
    assert "PINNED_VECTORS: hits=1 misses=1 final_size=2" in stdout


def test_lru_tutorial_typecheck():
    cmd = [
        sys.executable,
        "-m",
        "lateralus_lang",
        "check",
        str(REPO_ROOT / "examples" / "lru_tutorial.ltl"),
    ]
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "OK" in res.stdout


if __name__ == "__main__":
    test_lru_tutorial_execution()
    test_lru_tutorial_typecheck()
    print("PASS")
