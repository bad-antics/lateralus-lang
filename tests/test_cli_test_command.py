"""Tests for `lateralus test` — the @test runner CLI command."""
import subprocess
import sys
import textwrap
import pathlib
import tempfile
import pytest


def _run_test(src: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(suffix=".ltl", delete=False, mode="w", encoding="utf-8") as f:
        f.write(textwrap.dedent(src))
        path = f.name
    try:
        return subprocess.run(
            [sys.executable, "-m", "lateralus_lang", "test", path],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    finally:
        pathlib.Path(path).unlink(missing_ok=True)


def test_passing_test_exits_zero():
    r = _run_test("""\
        @test
        fn test_ok() {
            assert_eq(1 + 1, 2)
        }
        fn main() {}
        main()
    """)
    assert r.returncode == 0


def test_failing_test_exits_one():
    r = _run_test("""\
        @test
        fn test_bad() {
            assert_eq(1, 2)
        }
        fn main() {}
        main()
    """)
    assert r.returncode == 1


def test_no_tests_exits_zero():
    r = _run_test("""\
        fn main() {
            let x = 1
        }
        main()
    """)
    assert r.returncode == 0


def test_multiple_tests_all_pass():
    r = _run_test("""\
        @test
        fn test_a() { assert_eq(2 * 3, 6) }
        @test
        fn test_b() { assert_eq(10 - 4, 6) }
        fn main() {}
        main()
    """)
    assert r.returncode == 0
    assert "2 passed" in r.stdout


def test_mixed_pass_fail_exits_one():
    r = _run_test("""\
        @test
        fn test_good() { assert_eq(1, 1) }
        @test
        fn test_bad()  { assert_eq(1, 99) }
        fn main() {}
        main()
    """)
    assert r.returncode == 1
    assert "1 passed" in r.stdout
    assert "1 failed" in r.stdout


# Verify each AoC 2024 day passes its own embedded @test suite
AOC_DIR = pathlib.Path(__file__).parent.parent / "examples" / "advent_of_code" / "2024"
AOC_DAYS = sorted(AOC_DIR.glob("day*.ltl"))


@pytest.mark.parametrize("ltl_file", AOC_DAYS, ids=lambda p: p.stem)
def test_aoc_2024_day(ltl_file):
    r = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "test", str(ltl_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, (
        f"{ltl_file.name} tests failed:\n{r.stdout}\n{r.stderr}"
    )
