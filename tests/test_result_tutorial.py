"""
Regression test for examples/result_tutorial.ltl (stdlib/result tutorial companion).
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


def test_result_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "result_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "is_ok(good)=True" in out
    assert "is_err(bad)=True" in out
    assert "unwrap(good)*2=42" in out
    assert "unwrap_or(bad, -1)=-1" in out
    assert "unwrap_err(bad)=div by zero" in out
    assert "is_result(good)=True" in out
    assert "is_result(plain_map)=False" in out
    assert "map_result=42" in out
    assert "or_else=div by zero!" in out
    assert "and_then_chain=60" in out
    assert "flatten=7" in out
    assert "is_some(s)=True" in out
    assert "is_none(n)=True" in out
    assert "unwrap_option_or(n,0)=0" in out
    assert "map_option=100" in out
    assert "option_and_then_none=True" in out
    assert "option_or=99" in out
    assert "is_option(s)=True" in out
    assert "option_to_result=missing" in out
    assert "result_to_option=21" in out
    assert "collect_results=[1, 2, 3]" in out
    assert "partition_oks=[1, 3]" in out
    assert "partition_errs=['e1']" in out
    assert "PINNED_VECTORS" in out
    assert "RESULT_DEMO_OK" in out


def test_result_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "result_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
