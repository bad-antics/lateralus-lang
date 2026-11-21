"""
Regression test for examples/color_tutorial.ltl (stdlib/color tutorial companion).
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


def test_color_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "color_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB COLOR TUTORIAL ===" in out
    assert "STEP 1: rgb(255,127,80) = #ff7f50" in out
    assert "STEP 2: rgba(200,30,30,128) = #c81e1e" in out
    assert "STEP 2: alpha(rgba) = 128" in out
    assert "STEP 3: to_hex round-trip #FF7F50 -> #ff7f50" in out
    assert "STEP 4: lighten(coral, 0.25) = #ff9f7b" in out
    assert "STEP 5: darken(coral, 0.25) = #bf5f3c" in out
    assert "STEP 6: mix(coral, teal, 0.5) = #7f7f68" in out
    assert "STEP 7: invert(teal) = #ff7f7f" in out
    assert "STEP 8: grayscale(coral) = #9f9f9f" in out
    assert "STEP 9: clamp test rgb(300,-5,128) = #ff0080" in out
    assert "PINNED_VECTORS: coral=#ff7f50 lighten25=#ff9f7b darken25=#bf5f3c mix=#7f7f68 invert_teal=#ff7f7f gray_coral=#9f9f9f" in out


def test_color_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "color_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "error" not in res.stdout.lower() or "0 error" in res.stdout
