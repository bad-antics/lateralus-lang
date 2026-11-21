"""
Regression test for examples/opentelemetry_tutorial.ltl (stdlib/opentelemetry tutorial companion).
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


def test_opentelemetry_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "opentelemetry_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB OPENTELEMETRY TUTORIAL ===" in out
    assert "resource attrs=3 first=service.name" in out
    assert "spans=2 root=POST /pay child_parent=00f067aa0ba902b7" in out
    assert "request keys=checkout-api" in out
    assert "status.code=2 msg=card declined" in out
    assert "gauge=request_latency_seconds points=2 asDouble=12.5" in out
    assert "sum=requests_total monotonic=True" in out
    assert "sev=9/INFO body=payment captured" in out
    assert "trace=4bf92f3577b34da6a3ce929d0e0e4736" in out
    assert "PINNED_VECTORS: res=3attrs" in out


def test_opentelemetry_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "opentelemetry_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
