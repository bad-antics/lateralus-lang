"""
Regression test for examples/roaring_tutorial.ltl (stdlib/roaring tutorial companion).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_roaring_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "roaring_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB ROARING TUTORIAL ===" in out
    assert "card=4" in out
    assert "has3=False" in out
    assert "has100000=True" in out
    assert "sorted=[1, 2, 70000, 100000, 100001, 131072]" in out
    assert "card_after_dups=6" in out
    assert "union_card=5" in out
    assert "union_list=[1, 2, 5, 70000, 80000]" in out
    assert "card=5000" in out
    assert "has9999=False" in out
    assert "list_head=[0, 2, 4, 6, 8]" in out
    assert "PINNED_VECTORS: card5" in out


def test_roaring_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "roaring_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
