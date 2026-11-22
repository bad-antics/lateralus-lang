"""
Regression test for examples/statsd_tutorial.ltl (stdlib/statsd tutorial companion).
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


def test_statsd_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "statsd_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB STATSD TUTORIAL ===" in out
    assert "counter=http.requests:5|c|@0.5|#env:prod,region:us" in out
    assert "gauge=cpu.load:0.75|g" in out
    assert "gauge_delta=queue.depth:+3|g|#queue:jobs" in out
    assert "timer=db.query:12.5|ms" in out
    assert "histogram=resp.size:2048|h|@1.0|#ep:api" in out
    assert "distribution=latency:42|d" in out
    assert "set=users.online:user42|s|#dc:east" in out
    assert "name=http.requests" in out
    assert "rate=0.5" in out
    assert "tags=[['env', 'prod']]" in out
    assert "p2_tags=[['queue', 'jobs'], ['dc', 'east']]" in out
    assert "p3_rate=0.1 kind=c" in out
    assert "bare_tag=m:1|g|#solo" in out
    assert "bad_line=None" in out
    assert "one_field=None" in out
    assert "PINNED_VECTORS: counter_tags" in out


def test_statsd_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "statsd_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
