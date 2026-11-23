"""Regression tests for the dictionary-encoding tutorial companion."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_dict_encoding_tutorial_execution() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(REPO_ROOT / "examples" / "dict_encoding_tutorial.ltl")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=_env(),
    )
    output = result.stdout
    assert "dictionary=['pending', 'paid', 'failed']" in output
    assert "indices=[0,1,0,2,1]" in output
    assert "cardinality=3" in output
    assert "index_bits=2" in output
    assert "roundtrip=True" in output
    assert "pending=['pending', 'pending']" in output
    assert "pending_count=2" in output
    assert "empty=[]" in output
    assert "single=['only']" in output
    assert "single_bits=1" in output
    assert "four_bits=2" in output
    assert "PINNED_VECTORS:" in output


def test_dict_encoding_tutorial_typecheck() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "check", str(REPO_ROOT / "examples" / "dict_encoding_tutorial.ltl")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=_env(),
    )
    assert "OK" in result.stdout
