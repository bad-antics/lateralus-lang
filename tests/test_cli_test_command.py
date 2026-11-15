"""`lateralus test` runs @test functions and reports failure through its exit code."""
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
AOC_2024 = sorted((REPO / "examples" / "advent_of_code" / "2024").glob("day*.ltl"))


def _strip(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _lateralus_test(path):
    return subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "test", str(path)],
        capture_output=True, text=True, encoding="utf-8", timeout=120, cwd=str(REPO),
    )


@pytest.mark.e2e
def test_passing_tests_exit_zero(tmp_path):
    p = tmp_path / "ok.ltl"
    p.write_text('@test\nfn test_add() {\n    assert_eq(1 + 1, 2)\n}\n', encoding="utf-8")
    r = _lateralus_test(p)
    out = _strip(r.stdout)
    assert r.returncode == 0, out + r.stderr
    assert "1 passed  0 failed" in out


@pytest.mark.e2e
def test_failing_tests_exit_nonzero(tmp_path):
    p = tmp_path / "bad.ltl"
    p.write_text('@test\nfn test_add() {\n    assert_eq(1 + 1, 3)\n}\n', encoding="utf-8")
    r = _lateralus_test(p)
    out = _strip(r.stdout)
    assert r.returncode == 1, out + r.stderr
    assert "0 passed  1 failed" in out


@pytest.mark.examples
@pytest.mark.parametrize("path", AOC_2024, ids=lambda p: p.stem)
def test_advent_of_code_2024_self_verifies(path):
    r = _lateralus_test(path)
    out = _strip(r.stdout)
    assert r.returncode == 0, out + r.stderr
    assert re.search(r"\b0 failed", out)
