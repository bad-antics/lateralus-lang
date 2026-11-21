"""
Regression test for examples/template_tutorial.ltl (stdlib/template tutorial companion).
Asserts the executable tutorial runs cleanly and produces exact pinned vectors.
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


def test_template_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "template_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB TEMPLATE TUTORIAL ===" in out
    assert "STEP 1: Hello world!" in out
    assert "STEP 2: n=42, missing=<<missing>>" in out
    assert "STEP 3: Hello world / earth!" in out
    assert "STEP 4: vars in '<<a>> and <<b>> and <<a>>' = [a, b]" in out
    assert "STEP 5: unclosed '<<oops' -> unclosed <<oops" in out
    assert "STEP 6 join: - a, - b, - c" in out
    assert "1. apples" in out and "2. pears" in out
    assert "STEP 8 raw: Title: Mr. <b>Bold</b> & Co" in out
    assert "STEP 9 safe: Title: Mr. &lt;b&gt;Bold&lt;/b&gt; &amp; Co" in out
    assert "PINNED_VECTORS: hello=Hello world! default=Hello world / earth! vars=a,b join=- a, - b, - c safe=Title: Mr. &lt;b&gt;Bold&lt;/b&gt; &amp; Co" in out


def test_template_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "template_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
