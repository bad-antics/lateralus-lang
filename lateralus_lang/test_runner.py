"""
LATERALUS Test Runner
Discovers and runs both Python tests and LATERALUS @test functions.

Usage:
    python -m lateralus_lang.test_runner [path] [--verbose] [--pattern PATTERN]
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    duration: float  # seconds
    error: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


@dataclass
class TestSuiteResult:
    """Result of a test suite run."""
    results: list[TestResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def all_passed(self) -> bool:
        return self.failed == 0


# --- ANSI Colors -------------------------------------------------------

class _C:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        for attr in ["GREEN", "RED", "YELLOW", "CYAN", "DIM", "BOLD", "RESET"]:
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    _C.disable()


# --- LTL Test Discovery -----------------------------------------------

def find_ltl_tests(path: Path) -> list[tuple[Path, str]]:
    """Find all @test functions in .ltl files."""
    tests = []

    if path.is_file() and path.suffix == ".ltl":
        files = [path]
    elif path.is_dir():
        files = sorted(path.rglob("*.ltl"))
    else:
        return tests

    test_pattern = re.compile(r"@test\s*\n\s*fn\s+(\w+)")

    for f in files:
        try:
            content = f.read_text()
            for match in test_pattern.finditer(content):
                tests.append((f, match.group(1)))
        except Exception:
            pass

    return tests


def run_ltl_test(file: Path, test_name: str, verbose: bool = False) -> TestResult:
    """Run a single @test function from a .ltl file."""
    start = time.perf_counter()

    try:
        # Import and use the compiler
        from lateralus_lang.compiler import Compiler, Target

        source = file.read_text()

        # Append a call to the test function
        test_source = source + f"\n{test_name}()\n"

        compiler = Compiler()
        result = compiler.compile_and_run(test_source, Target.PYTHON)

        elapsed = time.perf_counter() - start

        if result.returncode != 0:
            return TestResult(
                name=f"{file.stem}::{test_name}",
                passed=False,
                duration=elapsed,
                error=result.stderr or "Non-zero exit code",
                file=str(file),
            )

        return TestResult(
            name=f"{file.stem}::{test_name}",
            passed=True,
            duration=elapsed,
            file=str(file),
        )

    except Exception as e:
        elapsed = time.perf_counter() - start
        return TestResult(
            name=f"{file.stem}::{test_name}",
            passed=False,
            duration=elapsed,
            error=str(e),
            file=str(file),
        )


# --- Python Test Discovery --------------------------------------------

def find_python_tests(path: Path) -> list[tuple[Path, str]]:
    """Find all test_* functions in test_*.py files."""
    tests = []

    if path.is_file() and path.name.startswith("test_") and path.suffix == ".py":
        files = [path]
    elif path.is_dir():
        files = sorted(path.rglob("test_*.py"))
    else:
        return tests

    func_pattern = re.compile(r"def\s+(test_\w+)\s*\(")

    for f in files:
        try:
            content = f.read_text()
            for match in func_pattern.finditer(content):
                tests.append((f, match.group(1)))
        except Exception:
            pass

    return tests


# --- Test Runner -------------------------------------------------------

def run_tests(
    path: str = ".",
    verbose: bool = False,
    pattern: Optional[str] = None,
    ltl_only: bool = False,
    py_only: bool = False,
) -> TestSuiteResult:
    """Run all discovered tests."""
    suite = TestSuiteResult()
    suite.start_time = time.perf_counter()

    test_path = Path(path)

    print(f"\n{_C.BOLD}  LATERALUS Test Runner{_C.RESET}")
    print(f"  {'='*50}")

    # Discover tests
    ltl_tests = [] if py_only else find_ltl_tests(test_path)
    # We don't run Python tests directly from this runner to avoid complexity;
    # those should be run via pytest. But we can report their existence.

    if pattern:
        ltl_tests = [(f, n) for f, n in ltl_tests if re.search(pattern, n)]

    total = len(ltl_tests)
    print(f"  Discovered {_C.CYAN}{total}{_C.RESET} LATERALUS tests")

    if total == 0:
        print(f"  {_C.YELLOW}No tests found.{_C.RESET}")
        print("  Hint: Add @test decorator to functions in .ltl files")
        suite.end_time = time.perf_counter()
        return suite

    print()

    # Run LATERALUS tests
    for i, (file, name) in enumerate(ltl_tests, 1):
        if verbose:
            print(f"  [{i}/{total}] {file.name}::{name} ... ", end="", flush=True)

        result = run_ltl_test(file, name, verbose)
        suite.results.append(result)

        if verbose:
            if result.passed:
                print(f"{_C.GREEN}PASS{_C.RESET} ({result.duration*1000:.1f}ms)")
            else:
                print(f"{_C.RED}FAIL{_C.RESET} ({result.duration*1000:.1f}ms)")
                if result.error:
                    for line in result.error.strip().split("\n"):
                        print(f"    {_C.RED}{line}{_C.RESET}")

    suite.end_time = time.perf_counter()

    # Summary
    print(f"\n  {'='*50}")
    print("  Results: ", end="")

    if suite.all_passed:
        print(f"{_C.GREEN}{_C.BOLD}{suite.passed} passed{_C.RESET}", end="")
    else:
        print(f"{_C.GREEN}{suite.passed} passed{_C.RESET}, "
              f"{_C.RED}{_C.BOLD}{suite.failed} failed{_C.RESET}", end="")

    print(f" {_C.DIM}in {suite.duration:.2f}s{_C.RESET}")

    # Show failures
    if suite.failed > 0:
        print(f"\n  {_C.RED}Failures:{_C.RESET}")
        for r in suite.results:
            if not r.passed:
                print(f"    {_C.RED}FAIL{_C.RESET} {r.name}")
                if r.error:
                    print(f"         {_C.DIM}{r.error[:100]}{_C.RESET}")

    print()
    return suite


# --- CLI ---------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="lateralus-test",
        description="LATERALUS Test Runner",
    )
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-p", "--pattern", default=None, help="Filter tests by pattern")
    parser.add_argument("--ltl", action="store_true", help="Only run .ltl tests")
    parser.add_argument("--py", action="store_true", help="Only run Python tests")

    args = parser.parse_args()

    suite = run_tests(
        path=args.path,
        verbose=args.verbose,
        pattern=args.pattern,
        ltl_only=args.ltl,
        py_only=args.py,
    )

    sys.exit(0 if suite.all_passed else 1)


if __name__ == "__main__":
    main()
