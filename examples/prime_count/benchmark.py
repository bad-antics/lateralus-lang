#!/usr/bin/env python3
"""Benchmark the prime-count port: Python original vs Lateralus C binary.

Builds the Lateralus program with `lateralus c` + gcc -O2, then times
both programs at the default limit (primes below 1,000,000) and reports
median / min wall time plus the speedup. Mirrors the method in
benchmarks/run_benchmarks.py (perf_counter around subprocess).

Usage:
    python3 benchmark.py            # 5 runs each (default)
    python3 benchmark.py --runs 3
"""

from __future__ import annotations

import argparse
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # repo root
LATERALUS = ROOT / ".venv" / "bin" / "lateralus"


def lateralus_cmd() -> list[str]:
    if LATERALUS.exists():
        return [str(LATERALUS)]
    if shutil.which("lateralus"):
        return ["lateralus"]
    raise SystemExit("lateralus not found: pip install -e . first (see CONTRIBUTING.md)")


def time_cmd(cmd: list[str]) -> tuple[float, str]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd!r} failed rc={proc.returncode}\n{proc.stderr}")
    return elapsed, proc.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark prime_count port.")
    parser.add_argument("--runs", type=int, default=5, help="runs per program")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="prime_count_bench_") as tmp:
        c_src = Path(tmp) / "prime_count.c"
        binary = Path(tmp) / "prime_count"
        subprocess.run(
            lateralus_cmd() + ["c", str(HERE / "prime_count.ltl"),
                               "-o", str(c_src)],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["gcc", "-O2", "-o", str(binary), str(c_src), "-lm"],
            check=True, capture_output=True, text=True,
        )

        py_times, py_out = [], ""
        for _ in range(args.runs):
            t, py_out = time_cmd([sys.executable, str(HERE / "prime_count.py")])
            py_times.append(t)
        c_times, c_out = [], ""
        for _ in range(args.runs):
            t, c_out = time_cmd([str(binary)])
            c_times.append(t)

    assert py_out.endswith("78498"), f"unexpected Python output: {py_out!r}"
    assert c_out == "78498", f"unexpected Lateralus output: {c_out!r}"

    py_med, c_med = statistics.median(py_times), statistics.median(c_times)
    print(f"Python   : median {py_med:.2f}s  min {min(py_times):.2f}s  ({args.runs} runs)")
    print(f"Lateralus: median {c_med:.3f}s  min {min(c_times):.3f}s  ({args.runs} runs)")
    print(f"Speedup  : {py_med / c_med:.1f}x faster (median wall time)")
    print(f"Output   : both print 78498 primes below 1000000")


if __name__ == "__main__":
    main()
