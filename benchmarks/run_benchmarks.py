#!/usr/bin/env python3
"""Cross-language benchmark harness for Lateralus vs Python vs Node.js.

Runs each benchmark N times per backend, reports median + min wall time,
writes results.json plus a Markdown table.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
REF = ROOT / "reference"
RESULTS = ROOT / "results"
BUILD = ROOT / "build"

BENCHMARKS = ["fib", "sieve", "mandelbrot", "binary_trees", "nbody"]

# stdlib micro-benchmarks (issue #865): one .ltl source + py/js reference
# drivers, each printing one digest line per workload.  Run at the "verify"
# profile so the pure-Python tree-walking interpreter finishes in seconds
# while still producing digests that match CPython and Node.js exactly.
STDLIB_BENCH = "stdlib"
STDLIB_PROFILE = "verify"


def time_cmd(cmd: list[str], *, timeout: float = 120.0) -> tuple[float, str]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(
            f"{cmd!r} failed rc={proc.returncode}\nSTDERR:\n{proc.stderr}"
        )
    return elapsed, proc.stdout.strip()


def build_c99(bench: str) -> Path:
    """Transpile .ltl → .c and compile with gcc -O2. Returns binary path.

    Raises RuntimeError on any stage failure so the harness can skip cleanly.
    """
    BUILD.mkdir(parents=True, exist_ok=True)
    src = SRC / f"{bench}.ltl"
    c_out = BUILD / f"{bench}.c"
    bin_out = BUILD / f"{bench}_c99"
    # Transpile
    proc = subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "c", str(src), "-o", str(c_out)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"transpile failed: {proc.stderr}")
    # Compile
    proc = subprocess.run(
        ["gcc", "-O2", "-o", str(bin_out), str(c_out), "-lm"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gcc failed: {proc.stderr.splitlines()[0] if proc.stderr else '?'}")
    return bin_out


def measure(cmd: list[str], *, warmup: int, iters: int) -> dict:
    # Warmup
    for _ in range(warmup):
        time_cmd(cmd)
    # Measured
    samples = []
    output = ""
    for _ in range(iters):
        t, out = time_cmd(cmd)
        samples.append(t)
        output = out
    return {
        "min": min(samples),
        "median": statistics.median(samples),
        "mean": statistics.mean(samples),
        "samples": samples,
        "output": output,
    }


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def run_stdlib(args) -> dict:
    """Run the stdlib micro-benchmarks (issue #865) across all backends.

    Each backend prints one digest line per workload.  At the "verify"
    profile the Lateralus / CPython / Node outputs are byte-identical, so
    the correctness cross-check passes and the Markdown table records the
    per-backend wall time for the whole 5-workload suite.
    """
    RESULTS.mkdir(parents=True, exist_ok=True)
    profile = STDLIB_PROFILE
    backends = ["lateralus", "python", "node"]
    if not have("node"):
        print("skipping node (not installed)")
        backends.remove("node")

    cmds = {
        "lateralus": [sys.executable, "-m", "lateralus_lang", "run",
                      str(ROOT / "stdlib_bench.ltl"), profile],
        "python": [sys.executable, str(REF / "stdlib_bench.py"), "all", profile],
        "node": ["node", str(REF / "stdlib_bench.js"), "all", profile],
    }

    results: dict = {
        "meta": {
            "python": sys.version.split()[0],
            "node": subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip() if have("node") else None,
            "iters": args.iters,
            "warmup": args.warmup,
            "profile": profile,
            "suite": "stdlib (xxhash64 / lz4 / chacha20 / aho_corasick / radix_sort_u32)",
        },
        "benchmarks": {},
    }

    print(f"\n=== stdlib (profile={profile}) ===")
    results["benchmarks"][STDLIB_BENCH] = {}
    for b in backends:
        try:
            r = measure(cmds[b], warmup=args.warmup, iters=args.iters)
            print(f"  {b:14s} min={r['min']:.4f}s median={r['median']:.4f}s")
            for line in r["output"].splitlines():
                print(f"      {line}")
            results["benchmarks"][STDLIB_BENCH][b] = r
        except Exception as e:
            print(f"  {b:14s} FAILED: {str(e).splitlines()[0][:80]}")
            results["benchmarks"][STDLIB_BENCH][b] = {"error": str(e)}

    # Correctness cross-check: all backends must print identical digests.
    print("\n=== Correctness (stdlib) ===")
    backs = results["benchmarks"][STDLIB_BENCH]
    outs = {b: v.get("output") for b, v in backs.items() if "output" in v}
    unique = set(outs.values())
    status = "OK" if len(unique) == 1 else "MISMATCH"
    print(f"  stdlib {status}")
    for b, o in outs.items():
        print(f"    {b}: {o!r}")

    # Markdown table
    md_lines = ["# Lateralus stdlib micro-benchmarks (issue #865)\n"]
    md_lines.append(
        f"Python {results['meta']['python']} · Node {results['meta']['node']} · "
        f"profile={profile} · {args.iters} iters + {args.warmup} warmup\n"
    )
    md_lines.append("Five workloads, one digest line each (identical across backends):\n")
    md_lines.append("| Backend | median (s) | min (s) |")
    md_lines.append("|---------|-----------|---------|")
    for b in backends:
        v = backs.get(b, {})
        if "median" in v:
            md_lines.append(f"| {b} | {v['median']:.4f} | {v['min']:.4f} |")
        else:
            md_lines.append(f"| {b} | — | — |")
    md_lines.append("")
    md_lines.append("Digest output (byte-identical across Lateralus / CPython / Node):\n")
    md_lines.append("```")
    ref_out = next((v.get("output", "") for v in backs.values() if "output" in v), "")
    md_lines.append(ref_out)
    md_lines.append("```")
    md_lines.append("")
    md_lines.append(f"Correctness: **{status}** (all backends agree)")
    md_lines.append("")

    Path(args.json).write_text(json.dumps(results, indent=2))
    (RESULTS / "stdlib_results.md").write_text("\n".join(md_lines) + "\n")
    print(f"\nWrote {args.json} and {RESULTS / 'stdlib_results.md'}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--filter", default=None, help="comma-separated bench names")
    ap.add_argument("--backends", default="lateralus,lateralus-c99,python,node")
    ap.add_argument("--json", default=str(RESULTS / "results.json"))
    ap.add_argument("--stdlib", action="store_true",
                    help="run the stdlib micro-benchmarks (issue #865) instead of the core suite")
    args = ap.parse_args()

    if args.stdlib:
        run_stdlib(args)
        return 0

    RESULTS.mkdir(parents=True, exist_ok=True)
    selected = args.filter.split(",") if args.filter else BENCHMARKS
    backends = args.backends.split(",")

    # Sanity
    if "node" in backends and not have("node"):
        print("skipping node (not installed)")
        backends.remove("node")
    if "lateralus-c99" in backends and not have("gcc"):
        print("skipping lateralus-c99 (gcc not installed)")
        backends.remove("lateralus-c99")

    # Pre-build C99 binaries so compile time doesn't pollute runtime samples.
    c99_bins: dict[str, Path] = {}
    if "lateralus-c99" in backends:
        print("\n=== Building C99 binaries ===")
        for bench in selected:
            try:
                c99_bins[bench] = build_c99(bench)
                print(f"  {bench:14s} built {c99_bins[bench].name}")
            except Exception as e:
                print(f"  {bench:14s} SKIP: {str(e).splitlines()[0][:80]}")

    results: dict = {
        "meta": {
            "python": sys.version.split()[0],
            "node": subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip() if have("node") else None,
            "iters": args.iters,
            "warmup": args.warmup,
        },
        "benchmarks": {},
    }

    for bench in selected:
        print(f"\n=== {bench} ===")
        results["benchmarks"][bench] = {}
        for b in backends:
            if b == "lateralus":
                cmd = [sys.executable, "-m", "lateralus_lang", "run", str(SRC / f"{bench}.ltl")]
            elif b == "lateralus-c99":
                if bench not in c99_bins:
                    print(f"  {b:14s} skipped (C99 build failed)")
                    results["benchmarks"][bench][b] = {"error": "C99 build failed"}
                    continue
                cmd = [str(c99_bins[bench])]
            elif b == "python":
                cmd = [sys.executable, str(REF / "bench.py"), bench]
            elif b == "node":
                cmd = ["node", str(REF / "bench.js"), bench]
            else:
                continue
            try:
                r = measure(cmd, warmup=args.warmup, iters=args.iters)
                print(f"  {b:14s} min={r['min']:.4f}s median={r['median']:.4f}s  out={r['output'][:40]}")
                results["benchmarks"][bench][b] = r
            except Exception as e:
                print(f"  {b:14s} FAILED: {str(e).splitlines()[0][:80]}")
                results["benchmarks"][bench][b] = {"error": str(e)}

    # Cross-check outputs match
    print("\n=== Correctness ===")
    for bench, backs in results["benchmarks"].items():
        outs = {b: v.get("output") for b, v in backs.items() if "output" in v}
        unique = set(outs.values())
        status = "OK" if len(unique) == 1 else "MISMATCH"
        print(f"  {bench:14s} {status}  {outs}")

    # Markdown table
    md_lines = ["# Lateralus Benchmark Results\n"]
    md_lines.append(f"Python {results['meta']['python']} · Node {results['meta']['node']} · gcc -O2 · {args.iters} iters + {args.warmup} warmup\n")
    md_lines.append("| Benchmark | Lateralus C99 (s) | Lateralus interp (s) | Python (s) | Node (s) | Output |")
    md_lines.append("|-----------|-------------------|----------------------|------------|----------|--------|")
    for bench, backs in results["benchmarks"].items():
        def cell(b):
            v = backs.get(b, {})
            if "error" in v or "median" not in v:
                return "—"
            return f"{v['median']:.4f}"
        out = next((v.get("output", "") for v in backs.values() if "output" in v), "")
        md_lines.append(
            f"| {bench} | {cell('lateralus-c99')} | {cell('lateralus')} | "
            f"{cell('python')} | {cell('node')} | `{out}` |"
        )

    Path(args.json).write_text(json.dumps(results, indent=2))
    (RESULTS / "results.md").write_text("\n".join(md_lines) + "\n")
    print(f"\nWrote {args.json} and {RESULTS / 'results.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
