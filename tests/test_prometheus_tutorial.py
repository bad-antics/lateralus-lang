"""
Regression test for examples/prometheus_tutorial.ltl (stdlib/prometheus tutorial companion).
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


def test_prometheus_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "prometheus_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB PROMETHEUS TUTORIAL ===" in out
    assert '{path="/a/b",code="200"}' in out
    assert '{msg="say \\"hi\\"\\nnow"}' in out
    assert "empty: ''" in out
    assert '# HELP http_requests_total Total requests\\n# TYPE http_requests_total counter\\n' in out
    assert 'http_requests_total{method="GET",code="200"} 1027\\n' in out
    assert 'request_duration_seconds_bucket{le="+Inf"} 30\\n' in out
    assert "request_duration_seconds_sum 12.5\\n" in out
    assert "parsed 2 samples" in out
    assert "h labels=[['method', 'GET']] value=42" in out
    assert "h labels=[['method', 'POST']] value=7" in out
    assert "metric=cpu_seconds value=123.45 labels=2" in out
    assert "PINNED_VECTORS: lbl=path-code-200 esc=quoted-newline blk=HELP-TYPE-2samples hist=buckets-sum-count parsed=2 rt=cpu_seconds-123.45" in out


def test_prometheus_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "prometheus_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
