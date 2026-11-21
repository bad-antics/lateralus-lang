"""Exercise the public `lateralus test` command in a real subprocess."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_test_command(tmp_path, source):
    source_path = tmp_path / "suite.ltl"
    source_path.write_text(source, encoding="utf-8")
    temp_root = tmp_path / "runner-temp"
    temp_root.mkdir()
    env = os.environ.copy()
    # The generated script runs from a temp directory, outside the checkout.
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [
        str(REPO_ROOT), env.get("PYTHONPATH"),
    ]))
    env.update({
        "TMP": str(temp_root),
        "TEMP": str(temp_root),
        "TMPDIR": str(temp_root),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "0",
    })
    result = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "test", str(source_path)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert list(temp_root.iterdir()) == [], "Test runner left temporary files behind"
    return result


def test_passing_test_runs_and_exits_zero(tmp_path):
    result = run_test_command(tmp_path, '''
@test
fn test_addition() {
    print("addition executed")
    assert_eq(1 + 1, 2)
}
''')
    assert result.returncode == 0, result.stderr
    assert "addition executed" in result.stdout
    assert "test_addition" in result.stdout
    assert "1 passed  0 failed" in result.stdout


def test_failed_assertion_exits_nonzero_and_runs_remaining_tests(tmp_path):
    result = run_test_command(tmp_path, '''
@test
fn test_wrong_answer() { assert_eq(1, 2) }
@test
fn test_after_failure() { print("remaining test executed") }
''')
    assert result.returncode == 1
    assert "remaining test executed" in result.stdout
    assert "test_wrong_answer" in result.stdout
    assert "1 passed  1 failed" in result.stdout
    assert "Traceback" not in result.stderr


def test_runtime_exception_counts_as_failure(tmp_path):
    result = run_test_command(tmp_path, '''
@test
fn test_runtime_error() { let value = 1 / 0 }
''')
    assert result.returncode == 1
    assert "division by zero" in result.stdout
    assert "0 passed  1 failed" in result.stdout
    assert "Traceback" not in result.stderr


def test_unicode_source_survives_temporary_script(tmp_path):
    result = run_test_command(tmp_path, '''
@test
fn test_unicode() {
    print("café 雪 🧪")
    assert_eq("雪 🧪", "雪 🧪")
}
''')
    assert result.returncode == 0, result.stderr
    assert "café 雪 🧪" in result.stdout
    assert "1 passed  0 failed" in result.stdout


def test_no_registered_tests_reports_empty_suite(tmp_path):
    result = run_test_command(tmp_path, "let value = 1\n")
    assert result.returncode == 0, result.stderr
    assert "0 passed  0 failed" in result.stdout


def test_invalid_source_reports_compiler_error(tmp_path):
    result = run_test_command(tmp_path, "fn broken( {\n")
    assert result.returncode == 1
    assert "ParseError" in result.stderr
    assert "Traceback" not in result.stderr


def test_runner_directory_is_removed_when_process_cannot_start(tmp_path, monkeypatch):
    from lateralus_lang.__main__ import main

    source_path = tmp_path / "suite.ltl"
    source_path.write_text("@test\nfn test_ok() { assert_eq(1, 1) }\n", encoding="utf-8")
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))

    def fail_to_start(*args, **kwargs):
        raise OSError("Cannot start Python")

    monkeypatch.setattr(subprocess, "run", fail_to_start)
    with pytest.raises(OSError, match="Cannot start Python"):
        main(["test", str(source_path)])
    assert set(tmp_path.iterdir()) == {source_path}
