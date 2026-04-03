#!/usr/bin/env python3
"""
LATERALUS Master Test Suite
Runs all test suites and generates a comprehensive report.

Usage:
    python scripts/run_all_tests.py [--verbose] [--json] [--suite SUITE]

Suites:
    core        — Original compiler tests (167 tests)
    engines     — New engine module tests
    integration — Integration and pipeline tests
    tools       — Formatter, linter, package manager, LSP tests
    science     — Scientific computing tests
    all         — Everything (default)
"""
import subprocess
import sys
import time
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent

# Test suite definitions
SUITES = {
    "core": {
        "name": "Core Compiler",
        "description": "Original 167 compiler tests",
        "paths": ["tests/test_compiler.py", "tests/test_lexer.py",
                  "tests/test_parser.py", "tests/test_codegen.py"],
        "fallback": ["tests/"],  # If specific files don't exist
    },
    "math": {
        "name": "Math Engine",
        "paths": ["tests/test_math_engine.py"],
    },
    "crypto": {
        "name": "Crypto Engine",
        "paths": ["tests/test_crypto_engine.py"],
    },
    "markup": {
        "name": "Markup Engine",
        "paths": ["tests/test_markup.py"],
    },
    "bytecode": {
        "name": "Bytecode Format",
        "paths": ["tests/test_bytecode_format.py"],
    },
    "errors": {
        "name": "Error Engine",
        "paths": ["tests/test_error_engine.py"],
    },
    "engines": {
        "name": "Engine Integration",
        "paths": ["tests/test_engines.py", "tests/test_cli_extensions.py"],
    },
    "optimizer": {
        "name": "Optimizer",
        "paths": ["tests/test_optimizer.py"],
    },
    "types": {
        "name": "Type System",
        "paths": ["tests/test_type_system.py"],
    },
    "async": {
        "name": "Async Runtime",
        "paths": ["tests/test_async_runtime.py"],
    },
    "pipeline": {
        "name": "Full Pipeline",
        "paths": ["tests/test_full_pipeline.py"],
    },
    "tools": {
        "name": "Developer Tools",
        "paths": ["tests/test_formatter_linter.py",
                  "tests/test_package_manager.py",
                  "tests/test_lsp_server.py"],
    },
    "science": {
        "name": "Scientific Computing",
        "paths": ["tests/test_science.py"],
    },
}

# Composite suites
COMPOSITE_SUITES = {
    "all_engines": ["math", "crypto", "markup", "bytecode", "errors"],
    "all_new": ["math", "crypto", "markup", "bytecode", "errors", "engines",
                "optimizer", "types", "async", "pipeline", "tools", "science"],
    "all": ["core"] + list(SUITES.keys()),
}


def run_pytest(paths: list[str], verbose: bool = False) -> dict:
    """Run pytest on given paths and return results."""
    existing = [p for p in paths if (PROJECT_ROOT / p).exists()]

    if not existing:
        return {
            "status": "skipped",
            "reason": "No test files found",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "duration": 0,
        }

    cmd = [sys.executable, "-m", "pytest"]
    if verbose:
        cmd.append("-v")
    cmd.extend(["--tb=short", "-q"])
    cmd.extend([str(PROJECT_ROOT / p) for p in existing])

    start = time.perf_counter()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    duration = time.perf_counter() - start

    # Parse output
    output = result.stdout + result.stderr
    passed = failed = errors = 0

    for line in output.split("\n"):
        if "passed" in line:
            import re
            m = re.search(r"(\d+)\s+passed", line)
            if m:
                passed = int(m.group(1))
            m = re.search(r"(\d+)\s+failed", line)
            if m:
                failed = int(m.group(1))
            m = re.search(r"(\d+)\s+error", line)
            if m:
                errors = int(m.group(1))

    return {
        "status": "passed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "duration": round(duration, 2),
        "output": output if verbose else "",
    }


def run_suite(suite_name: str, verbose: bool = False) -> dict:
    """Run a single test suite."""
    if suite_name in COMPOSITE_SUITES:
        results = {}
        for sub in COMPOSITE_SUITES[suite_name]:
            results[sub] = run_suite(sub, verbose)
        return results

    if suite_name not in SUITES:
        return {"status": "unknown", "reason": f"Unknown suite: {suite_name}"}

    suite = SUITES[suite_name]
    paths = suite["paths"]

    # Try fallback paths if primary don't exist
    if not any((PROJECT_ROOT / p).exists() for p in paths):
        paths = suite.get("fallback", paths)

    return run_pytest(paths, verbose)


def print_report(results: dict, suite_name: str):
    """Print a formatted test report."""
    print(f"\n  LATERALUS Test Report — {suite_name}")
    print(f"  {'='*60}")

    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_duration = 0

    for name, result in results.items():
        if isinstance(result, dict) and "status" in result:
            status = result["status"]
            passed = result.get("passed", 0)
            failed = result.get("failed", 0)
            errors = result.get("errors", 0)
            duration = result.get("duration", 0)

            total_passed += passed
            total_failed += failed
            total_errors += errors
            total_duration += duration

            display_name = SUITES.get(name, {}).get("name", name)
            if status == "passed":
                icon = "PASS"
            elif status == "skipped":
                icon = "SKIP"
            else:
                icon = "FAIL"

            print(f"  {icon:4} {display_name:<30} "
                  f"{passed:3d} passed, {failed:2d} failed "
                  f"({duration:.1f}s)")

    print(f"  {'='*60}")
    print(f"  Total: {total_passed} passed, {total_failed} failed, "
          f"{total_errors} errors in {total_duration:.1f}s")

    if total_failed == 0 and total_errors == 0:
        print(f"\n  All tests passed!")
    else:
        print(f"\n  {total_failed + total_errors} issue(s) found.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LATERALUS Master Test Runner")
    parser.add_argument("--suite", "-s", default="all_new",
                       choices=list(SUITES.keys()) + list(COMPOSITE_SUITES.keys()),
                       help="Test suite to run")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list", action="store_true", help="List available suites")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable test suites:")
        for name, suite in SUITES.items():
            desc = suite.get("name", name)
            paths = ", ".join(suite["paths"])
            print(f"  {name:<15} {desc:<30} [{paths}]")
        print("\nComposite suites:")
        for name, subs in COMPOSITE_SUITES.items():
            print(f"  {name:<15} [{', '.join(subs)}]")
        return

    results = run_suite(args.suite, args.verbose)

    if isinstance(results, dict) and "status" in results:
        # Single suite result
        results = {args.suite: results}

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results, args.suite)

    # Exit with error if any failures
    has_failures = any(
        r.get("failed", 0) > 0 or r.get("errors", 0) > 0
        for r in results.values()
        if isinstance(r, dict) and "status" in r
    )
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
