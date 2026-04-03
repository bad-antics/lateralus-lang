"""
LATERALUS Benchmark Suite
Comprehensive performance benchmarking for all engine subsystems.

Usage:
    python -m lateralus_lang.bench [--suite SUITE] [--iterations N] [--json]
"""
from __future__ import annotations

import time
import statistics
import json as json_mod
import sys
from dataclasses import dataclass, field
from typing import Callable, Any, Optional


# ─── Benchmark Infrastructure ─────────────────────────────────────────

@dataclass
class BenchmarkResult:
    """Result of a single benchmark."""
    name: str
    iterations: int
    total_time: float  # seconds
    mean_time: float
    median_time: float
    std_dev: float
    min_time: float
    max_time: float
    ops_per_sec: float
    times: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_ms": round(self.total_time * 1000, 3),
            "mean_ms": round(self.mean_time * 1000, 6),
            "median_ms": round(self.median_time * 1000, 6),
            "std_dev_ms": round(self.std_dev * 1000, 6),
            "min_ms": round(self.min_time * 1000, 6),
            "max_ms": round(self.max_time * 1000, 6),
            "ops_per_sec": round(self.ops_per_sec, 1),
        }

    def __str__(self) -> str:
        return (
            f"  {self.name:<40} "
            f"{self.mean_time*1000:>10.3f}ms "
            f"(+/- {self.std_dev*1000:.3f}ms) "
            f"[{self.ops_per_sec:,.0f} ops/s]"
        )


def run_benchmark(name: str, fn: Callable, iterations: int = 1000,
                  warmup: int = 10, setup: Optional[Callable] = None) -> BenchmarkResult:
    """Run a benchmark and return results."""
    # Warmup
    for _ in range(warmup):
        if setup:
            setup()
        fn()

    # Actual benchmark
    times = []
    for _ in range(iterations):
        if setup:
            setup()
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    total = sum(times)
    mean = statistics.mean(times)
    median = statistics.median(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0.0
    min_t = min(times)
    max_t = max(times)
    ops = iterations / total if total > 0 else float("inf")

    return BenchmarkResult(
        name=name,
        iterations=iterations,
        total_time=total,
        mean_time=mean,
        median_time=median,
        std_dev=stdev,
        min_time=min_t,
        max_time=max_t,
        ops_per_sec=ops,
        times=times,
    )


@dataclass
class BenchmarkSuite:
    """A collection of benchmarks."""
    name: str
    results: list[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult):
        self.results.append(result)

    def summary(self) -> str:
        lines = [
            f"\n  Benchmark Suite: {self.name}",
            f"  {'='*70}",
        ]
        for r in self.results:
            lines.append(str(r))
        lines.append(f"  {'='*70}")
        lines.append(f"  Total benchmarks: {len(self.results)}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "suite": self.name,
            "benchmarks": [r.to_dict() for r in self.results],
        }


# ─── Math Engine Benchmarks ───────────────────────────────────────────

def bench_math_engine(iterations: int = 1000) -> BenchmarkSuite:
    """Benchmark the math engine."""
    from lateralus_lang.math_engine import (
        LTLNumber, Matrix, Vector, Interval, Dual,
        mean, median, variance, std_dev,
        newton_raphson, trapezoidal_integrate, simpson_integrate,
    )

    suite = BenchmarkSuite("Math Engine")

    # LTLNumber arithmetic
    a, b = LTLNumber(42), LTLNumber(17)
    suite.add(run_benchmark("LTLNumber add", lambda: a + b, iterations))
    suite.add(run_benchmark("LTLNumber mul", lambda: a * b, iterations))
    suite.add(run_benchmark("LTLNumber div", lambda: a / b, iterations))
    suite.add(run_benchmark("LTLNumber pow", lambda: a ** LTLNumber(3), iterations))

    # Matrix operations
    m = Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 10]])
    suite.add(run_benchmark("Matrix 3x3 transpose", lambda: m.transpose(), iterations))
    suite.add(run_benchmark("Matrix 3x3 determinant", lambda: m.determinant(), iterations))
    suite.add(run_benchmark("Matrix 3x3 inverse", lambda: m.inverse(), iterations))

    m4 = Matrix([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 12, 11], [13, 14, 15, 17]])
    suite.add(run_benchmark("Matrix 4x4 determinant", lambda: m4.determinant(), iterations // 2))

    m_a = Matrix([[1, 2], [3, 4]])
    m_b = Matrix([[5, 6], [7, 8]])
    suite.add(run_benchmark("Matrix 2x2 matmul", lambda: m_a.matmul(m_b), iterations))

    # Vector operations
    v1 = Vector([1.0, 2.0, 3.0])
    v2 = Vector([4.0, 5.0, 6.0])
    suite.add(run_benchmark("Vector dot product", lambda: v1.dot(v2), iterations))
    suite.add(run_benchmark("Vector cross product", lambda: v1.cross(v2), iterations))
    suite.add(run_benchmark("Vector normalize", lambda: v1.normalize(), iterations))

    # Interval arithmetic
    i1, i2 = Interval(1, 3), Interval(2, 5)
    suite.add(run_benchmark("Interval add", lambda: i1 + i2, iterations))
    suite.add(run_benchmark("Interval mul", lambda: i1 * i2, iterations))

    # Automatic differentiation
    d = Dual(2.0, 1.0)
    suite.add(run_benchmark("Dual number arithmetic", lambda: d * d + Dual(3.0) * d, iterations))

    # Statistics
    data = list(range(1000))
    suite.add(run_benchmark("mean(1000 items)", lambda: mean(data), iterations // 10))
    suite.add(run_benchmark("median(1000 items)", lambda: median(data), iterations // 10))
    suite.add(run_benchmark("variance(1000 items)", lambda: variance(data), iterations // 10))
    suite.add(run_benchmark("std_dev(1000 items)", lambda: std_dev(data), iterations // 10))

    # Numerical methods
    suite.add(run_benchmark(
        "newton_raphson (sqrt 2)",
        lambda: newton_raphson(lambda x: x*x - 2, lambda x: 2*x, 1.0),
        iterations // 10,
    ))
    suite.add(run_benchmark(
        "trapezoidal (sin 0..pi)",
        lambda: trapezoidal_integrate(lambda x: x*x, 0, 1, 100),
        iterations // 10,
    ))
    suite.add(run_benchmark(
        "simpson (x^2 0..1)",
        lambda: simpson_integrate(lambda x: x*x, 0, 1, 100),
        iterations // 10,
    ))

    return suite


# ─── Crypto Engine Benchmarks ─────────────────────────────────────────

def bench_crypto_engine(iterations: int = 1000) -> BenchmarkSuite:
    """Benchmark the crypto engine."""
    from lateralus_lang.crypto_engine import (
        Hashing, HMAC, Password, RandomTokens, Encoding, LBEEncoder, LBEDecoder,
    )

    suite = BenchmarkSuite("Crypto Engine")

    data = "The quick brown fox jumps over the lazy dog"
    big_data = data * 100

    # Hashing
    suite.add(run_benchmark("SHA-256 (short)", lambda: Hashing.sha256(data), iterations))
    suite.add(run_benchmark("SHA-256 (long)", lambda: Hashing.sha256(big_data), iterations))
    suite.add(run_benchmark("SHA-512 (short)", lambda: Hashing.sha512(data), iterations))
    suite.add(run_benchmark("BLAKE2b (short)", lambda: Hashing.blake2b(data), iterations))
    suite.add(run_benchmark("MD5 (short)", lambda: Hashing.md5(data), iterations))

    # HMAC
    suite.add(run_benchmark("HMAC-SHA256", lambda: HMAC.sign(data, "secret"), iterations))
    sig = HMAC.sign(data, "secret")
    suite.add(run_benchmark("HMAC-verify", lambda: HMAC.verify(data, "secret", sig), iterations))

    # Random tokens
    suite.add(run_benchmark("random_token(32)", lambda: RandomTokens.hex_token(32), iterations))
    suite.add(run_benchmark("random_token(64)", lambda: RandomTokens.hex_token(64), iterations))

    # Encoding
    suite.add(run_benchmark("Base64 encode", lambda: Encoding.base64_encode(data), iterations))
    b64 = Encoding.base64_encode(data)
    suite.add(run_benchmark("Base64 decode", lambda: Encoding.base64_decode(b64), iterations))
    suite.add(run_benchmark("Hex encode", lambda: Encoding.hex_encode(data), iterations))

    # LBE (LATERALUS Binary Encoding)
    test_data = {"name": "test", "values": [1, 2, 3], "nested": {"a": True}}
    suite.add(run_benchmark("LBE encode", lambda: LBEEncoder.encode(test_data), iterations))
    encoded = LBEEncoder.encode(test_data)
    suite.add(run_benchmark("LBE decode", lambda: LBEDecoder.decode(encoded), iterations))

    # Password hashing (very few iterations — it's intentionally slow)
    suite.add(run_benchmark(
        "PBKDF2 hash",
        lambda: Password.hash_password("password123", iterations=1000),
        3,
    ))

    return suite


# ─── Markup Engine Benchmarks ─────────────────────────────────────────

def bench_markup_engine(iterations: int = 500) -> BenchmarkSuite:
    """Benchmark the LTLML markup engine."""
    from lateralus_lang.markup import parse_ltlml, render_ltlml, compile_ltlml_file

    suite = BenchmarkSuite("Markup Engine (LTLML)")

    small_doc = """---
title: Test
---
# Hello World
This is a paragraph.
"""

    medium_doc = """---
title: Medium Document
author: Test
---
# Chapter 1

This is a **bold** and *italic* text with `code`.

## Section 1.1

A list of items and some math: $E = mc^2$

```lateralus
fn hello() {
    println("world")
}
```

> This is a blockquote.

## Section 1.2

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |

!!! note "Important Note"
    This is an admonition.

""" * 3  # Repeat for larger document

    suite.add(run_benchmark("Parse small doc", lambda: parse_ltlml(small_doc), iterations))
    suite.add(run_benchmark("Parse medium doc", lambda: parse_ltlml(medium_doc), iterations // 5))
    suite.add(run_benchmark("Render small doc", lambda: render_ltlml(small_doc), iterations))
    suite.add(run_benchmark("Render medium doc", lambda: render_ltlml(medium_doc), iterations // 5))

    return suite


# ─── Bytecode Engine Benchmarks ───────────────────────────────────────

def bench_bytecode_engine(iterations: int = 500) -> BenchmarkSuite:
    """Benchmark the bytecode compilation engine."""
    from lateralus_lang.bytecode_format import LTLCCompiler, LTLCDecompiler, LTLCInspector

    suite = BenchmarkSuite("Bytecode Engine (.ltlc)")

    source = """fn factorial(n) {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}
let result = factorial(10)
println(result)
"""

    suite.add(run_benchmark("Compile to .ltlc", lambda: LTLCCompiler().compile_source(source), iterations))

    compiled = LTLCCompiler().compile_source(source)
    suite.add(run_benchmark("Decompile .ltlc", lambda: LTLCDecompiler().decompile(compiled), iterations))

    suite.add(run_benchmark(
        "Compile compressed",
        lambda: LTLCCompiler(compress=True).compile_source(source),
        iterations,
    ))

    suite.add(run_benchmark("Inspect .ltlc", lambda: LTLCInspector().inspect(compiled), iterations))

    return suite


# ─── Optimizer Benchmarks ──────────────────────────────────────────────

def bench_optimizer(iterations: int = 1000) -> BenchmarkSuite:
    """Benchmark the optimizer."""
    from lateralus_lang.optimizer import Optimizer, OptLevel

    suite = BenchmarkSuite("Optimizer")

    source = """
let x = 2 + 3 * 4
let y = x * 1
let z = y + 0
let unused = 42
let result = x + y + z
println(result)
"""

    for level in [OptLevel.O1, OptLevel.O2, OptLevel.O3]:
        opt = Optimizer(level)
        suite.add(run_benchmark(
            f"Optimize {level.name}",
            lambda: opt.optimize(source),
            iterations,
        ))

    return suite


# ─── Type System Benchmarks ───────────────────────────────────────────

def bench_type_system(iterations: int = 1000) -> BenchmarkSuite:
    """Benchmark the type system."""
    from lateralus_lang.type_system import (
        TypeChecker, TypeEnvironment, TypeInferencer,
        parse_type_annotation, INT, FLOAT, STR, BOOL,
        FunctionType, ListType, UnionType, OptionalType,
    )

    suite = BenchmarkSuite("Type System")

    # Type parsing
    suite.add(run_benchmark("parse 'int'", lambda: parse_type_annotation("int"), iterations))
    suite.add(run_benchmark("parse 'list<int>'", lambda: parse_type_annotation("list<int>"), iterations))
    suite.add(run_benchmark("parse 'int | str'", lambda: parse_type_annotation("int | str"), iterations))
    suite.add(run_benchmark("parse 'int?'", lambda: parse_type_annotation("int?"), iterations))

    # Subtype checking
    suite.add(run_benchmark("int <: float", lambda: INT.is_subtype_of(FLOAT), iterations))
    union = UnionType(frozenset([INT, STR]))
    suite.add(run_benchmark("int <: int|str", lambda: INT.is_subtype_of(union), iterations))

    # Type inference
    inferencer = TypeInferencer()
    suite.add(run_benchmark("infer int literal", lambda: inferencer.infer_literal(42), iterations))
    suite.add(run_benchmark("infer string literal", lambda: inferencer.infer_literal("hello"), iterations))
    suite.add(run_benchmark("infer binary (int+int)", lambda: inferencer.infer_binary("+", INT, INT), iterations))

    # Environment operations
    env = TypeEnvironment()
    for i in range(100):
        env.bind(f"var_{i}", INT)
    suite.add(run_benchmark("env lookup (100 vars)", lambda: env.lookup("var_50"), iterations))

    return suite


# ─── Compiler Pipeline Benchmarks ─────────────────────────────────────

def bench_compiler_pipeline(iterations: int = 100) -> BenchmarkSuite:
    """Benchmark the full compiler pipeline."""
    suite = BenchmarkSuite("Compiler Pipeline")

    try:
        from lateralus_lang.compiler import Compiler, Target

        small_program = 'let x = 42\nprintln(x)\n'
        medium_program = """
fn fibonacci(n) {
    if n <= 1 { return n }
    return fibonacci(n - 1) + fibonacci(n - 2)
}

fn factorial(n) {
    let result = 1
    for i in range(1, n + 1) {
        result = result * i
    }
    return result
}

let data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
let squared = data |> map((x) => x ** 2)
let evens = squared |> filter((x) => x % 2 == 0)
let total = evens |> reduce((a, b) => a + b, 0)

println("Fibonacci(10) = " + str(fibonacci(10)))
println("Factorial(10) = " + str(factorial(10)))
println("Pipeline result = " + str(total))
"""

        # Lexing
        from lateralus_lang.lexer import Lexer
        suite.add(run_benchmark(
            "Lex small program",
            lambda: list(Lexer(small_program).tokenize()),
            iterations * 10,
        ))
        suite.add(run_benchmark(
            "Lex medium program",
            lambda: list(Lexer(medium_program).tokenize()),
            iterations,
        ))

        # Full compilation
        suite.add(run_benchmark(
            "Compile small (Python target)",
            lambda: Compiler().compile(small_program, Target.PYTHON),
            iterations,
        ))
        suite.add(run_benchmark(
            "Compile medium (Python target)",
            lambda: Compiler().compile(medium_program, Target.PYTHON),
            iterations // 5,
        ))

    except ImportError as e:
        suite.add(run_benchmark(f"SKIPPED (import error: {e})", lambda: None, 1))

    return suite


# ─── All Suites ────────────────────────────────────────────────────────

SUITES = {
    "math": bench_math_engine,
    "crypto": bench_crypto_engine,
    "markup": bench_markup_engine,
    "bytecode": bench_bytecode_engine,
    "optimizer": bench_optimizer,
    "types": bench_type_system,
    "pipeline": bench_compiler_pipeline,
}


def run_all_benchmarks(iterations: int = 500, suites: Optional[list[str]] = None,
                       output_json: bool = False) -> dict:
    """Run all benchmark suites."""
    results = {}
    selected = suites or list(SUITES.keys())

    if not output_json:
        print("\n  LATERALUS Benchmark Suite")
        print("  Spiraling Performance Measurements")
        print(f"  {'='*60}")

    for suite_name in selected:
        if suite_name not in SUITES:
            if not output_json:
                print(f"\n  Unknown suite: {suite_name}")
            continue

        try:
            suite = SUITES[suite_name](iterations)
            results[suite_name] = suite

            if not output_json:
                print(suite.summary())
        except Exception as e:
            if not output_json:
                print(f"\n  Suite '{suite_name}' failed: {e}")
            results[suite_name] = BenchmarkSuite(f"{suite_name} (FAILED)")

    if output_json:
        combined = {
            name: suite.to_dict() for name, suite in results.items()
        }
        print(json_mod.dumps(combined, indent=2))
    else:
        # Summary
        total_benchmarks = sum(len(s.results) for s in results.values())
        print(f"\n  Total: {total_benchmarks} benchmarks across {len(results)} suites")

    return results


# ─── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="lateralus-bench",
        description="LATERALUS Benchmark Suite",
    )
    parser.add_argument(
        "--suite", "-s",
        action="append",
        choices=list(SUITES.keys()),
        help="Run specific suite(s)",
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=500,
        help="Number of iterations per benchmark",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available suites",
    )

    args = parser.parse_args()

    if args.list:
        print("Available benchmark suites:")
        for name in SUITES:
            print(f"  {name}")
        return

    run_all_benchmarks(
        iterations=args.iterations,
        suites=args.suite,
        output_json=args.json,
    )


if __name__ == "__main__":
    main()
