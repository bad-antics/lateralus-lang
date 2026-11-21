"""
Regression test for examples/ranking_tutorial.ltl (stdlib/ranking tutorial companion).
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


def test_ranking_tutorial_execution():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "run",
        str(REPO_ROOT / "examples" / "ranking_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    out = res.stdout
    assert "=== LATERALUS STDLIB RANKING TUTORIAL ===" in out
    assert "ntoks=11" in out
    assert "tf_the=3" in out
    assert "tf_fox=2" in out
    assert "tf_cat=0" in out
    assert "n_docs=3" in out
    assert "avgdl=7.666666666666667" in out
    assert "df_fox=2" in out
    assert "df_the=1" in out
    assert "df_lorem=1" in out
    assert "idf_fox=0.47000362924573574" in out
    assert "ranked=[[1, 0.9219687396718058], [0, 0.8717809252138647], [2, 0.0]]" in out
    assert "cos01=0.17318840522143186" in out
    assert "cos02=0.0" in out
    assert "cos_self=0.9999999999999999" in out
    assert "PINNED_VECTORS: ntoks11" in out


def test_ranking_tutorial_typecheck():
    cmd = [
        sys.executable, "-m", "lateralus_lang", "check",
        str(REPO_ROOT / "examples" / "ranking_tutorial.ltl"),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                         check=True, env=_env())
    assert "OK" in res.stdout
