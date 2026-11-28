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

# Repo root (two levels up from benchmarks/) — where stdlib/ lives.
REPO_ROOT = ROOT.parent
STDLIB = REPO_ROOT / "stdlib"

BENCHMARKS = ["fib", "sieve", "mandelbrot", "binary_trees", "nbody"]

# stdlib micro-benchmarks (bounty: benchmark-ingest, issue #156).
# Each entry maps a bench name to the stdlib module that must be inlined
# above the driver to form a single combined source file. The interpreter's
# `import` resolves to a Python module (not a .ltl file), so modules are
# concatenated with their driver instead of imported.
STDLIB_BENCHMARKS = {
    "xxhash": "xxhash",
    "lz4": "lz4",
    "chacha20": "chacha20",
    "aho_corasick": "aho_corasick",
    "radix_sort": "radix_sort",
}


def build_stdlib_source(bench: str) -> Path:
    """Inline stdlib/<module>.ltl above benchmarks/src/stdlib/<bench>_driver.ltl
    to produce a single combined .ltl source file. Returns the path.
    """
    module = STDLIB_BENCHMARKS[bench]
    module_path = STDLIB / f"{module}.ltl"
    driver_path = SRC / "stdlib" / f"{bench}_driver.ltl"
    if not module_path.exists():
        raise RuntimeError(f"stdlib module not found: {module_path}")
    if not driver_path.exists():
        raise RuntimeError(f"driver not found: {driver_path}")
    BUILD.mkdir(parents=True, exist_ok=True)
    combined = BUILD / f"stdlib_{bench}.ltl"
    parts = [
        f"// AUTO-GENERATED combined source for stdlib benchmark '{bench}'.\n",
        f"// Inlines stdlib/{module}.ltl + benchmarks/src/stdlib/{bench}_driver.ltl\n",
        module_path.read_text(),
        "\n// ---- driver ----\n",
        driver_path.read_text(),
    ]
    combined.write_text("\n".join(parts))
    return combined


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--filter", default=None, help="comma-separated bench names")
    ap.add_argument("--backends", default="lateralus,lateralus-c99,python,node")
    ap.add_argument("--json", default=str(RESULTS / "results.json"))
    ap.add_argument("--stdlib", action="store_true",
                    help="run the 5 stdlib micro-benchmarks (issue #156) instead of the core suite")
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    if args.stdlib:
        selected = args.filter.split(",") if args.filter else list(STDLIB_BENCHMARKS)
    else:
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
            "stdlib": args.stdlib,
        },
        "benchmarks": {},
    }

    for bench in selected:
        print(f"\n=== {bench} ===")
        results["benchmarks"][bench] = {}
        # For stdlib benchmarks, build the combined source (stdlib module + driver).
        lat_src = None
        if args.stdlib:
            try:
                lat_src = build_stdlib_source(bench)
                print(f"  combined source: {lat_src.relative_to(REPO_ROOT)}")
            except Exception as e:
                print(f"  lateralus    SKIP: {e}")
                results["benchmarks"][bench]["lateralus"] = {"error": str(e)}
        for b in backends:
            if b == "lateralus":
                src_path = lat_src if lat_src is not None else (SRC / f"{bench}.ltl")
                cmd = [sys.executable, "-m", "lateralus_lang", "run", str(src_path)]
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

    # Cross-check outputs match (normalize whitespace: Lateralus println emits
    # one value per line, Python/Node emit space-separated — compare tokens).
    print("\n=== Correctness ===")
    for bench, backs in results["benchmarks"].items():
        outs = {b: v.get("output") for b, v in backs.items() if "output" in v}
        norm = {b: " ".join(o.split()) for b, o in outs.items()}
        unique = set(norm.values())
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
    out_md = RESULTS / ("stdlib_results.md" if args.stdlib else "results.md")
    (RESULTS / "results.md").write_text("\n".join(md_lines) + "\n")
    if args.stdlib:
        out_md.write_text("\n".join(md_lines) + "\n")
    print(f"\nWrote {args.json} and {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
