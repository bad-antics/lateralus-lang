"""
Regression test for examples/metrics_tutorial.ltl (stdlib/metrics tutorial companion).
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


def test_metrics_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "metrics_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB METRICS TUTORIAL ===" in out
    assert "STEP 1 families: http_requests_total,queue_depth,request_latency_seconds" in out
    assert "STEP 2 counter series:" in out and "method=GET,route=/api" in out
    assert "STEP 5 prometheus output:" in out
    assert '# TYPE http_requests_total counter' in out
    assert 'http_requests_total{route="/api",method="GET"} 1.0' in out
    assert 'http_requests_total 2.0' in out
    assert 'queue_depth 3.0' in out
    assert 'request_latency_seconds_bucket{le="0.1"} 1' in out
    assert 'request_latency_seconds_bucket{le="0.5"} 2' in out
    assert 'request_latency_seconds_bucket{le="1.0"} 2' in out
    assert 'request_latency_seconds_bucket{le="+Inf"} 3' in out
    assert "request_latency_seconds_sum 2.35" in out
    assert "request_latency_seconds_count 3" in out
    assert "PINNED_VECTORS: families=http_requests_total,queue_depth,request_latency_seconds fp=method=GET,route=/api gauge=3.0 buckets=1,2,2,+Inf:3 sum=2.35 count=3 lbl=route=/api+method=GET" in out


def test_metrics_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "metrics_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
