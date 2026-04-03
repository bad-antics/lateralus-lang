#!/usr/bin/env python3
"""
LATERALUS Profiler — Performance analysis for LATERALUS programs.

Wraps Python's cProfile to profile LATERALUS program execution.
Reports hot functions, call counts, and cumulative time.

Usage:
    python -m lateralus_lang.profiler program.ltl [--top N] [--sort cumtime|tottime|calls]
"""
from __future__ import annotations

import cProfile
import pstats
import io
import sys
import time
import tracemalloc
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ProfileResult:
    """Results from profiling a LATERALUS program."""
    file: str
    total_time: float
    function_stats: list[dict]
    peak_memory_mb: float
    call_count: int

    def summary(self) -> str:
        lines = [
            f"  Profile Report: {self.file}",
            f"  {'='*60}",
            f"  Total time:  {self.total_time:.4f}s",
            f"  Peak memory: {self.peak_memory_mb:.2f} MB",
            f"  Total calls: {self.call_count}",
            "",
            f"  {'Function':<40} {'Calls':>8} {'Tot(s)':>10} {'Cum(s)':>10}",
            f"  {'-'*40} {'-'*8} {'-'*10} {'-'*10}",
        ]

        for stat in self.function_stats[:20]:
            name = stat['name'][:40]
            lines.append(
                f"  {name:<40} {stat['calls']:>8} "
                f"{stat['tottime']:>10.4f} {stat['cumtime']:>10.4f}"
            )

        return "\n".join(lines)


@dataclass
class TimingBlock:
    """A named timing block for manual instrumentation."""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    children: list[TimingBlock] = field(default_factory=list)

    @property
    def elapsed(self) -> float:
        return self.end_time - self.start_time

    @property
    def self_time(self) -> float:
        child_time = sum(c.elapsed for c in self.children)
        return max(0.0, self.elapsed - child_time)


class LateralusProfiler:
    """Profiler for LATERALUS programs."""

    def __init__(self):
        self.profiler = cProfile.Profile()
        self.timing_stack: list[TimingBlock] = []
        self.timing_root: list[TimingBlock] = []
        self.snapshots: list[dict] = []

    def profile_file(self, filepath: str, top: int = 20,
                     sort_by: str = "cumtime") -> ProfileResult:
        """Profile a LATERALUS program file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        source = path.read_text()

        # Try to import the compiler
        try:
            from lateralus_lang.compiler import Compiler, Target
        except ImportError:
            raise RuntimeError("lateralus_lang not installed")

        compiler = Compiler()

        # Track memory
        tracemalloc.start()

        # Profile compilation and execution
        start = time.perf_counter()

        self.profiler.enable()
        try:
            result = compiler.run(source, target=Target.PYTHON)
        finally:
            self.profiler.disable()

        total_time = time.perf_counter() - start

        # Memory snapshot
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Extract stats
        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.sort_stats(sort_by)

        function_stats = []
        total_calls = 0

        for key, value in stats.stats.items():
            filename, line, func_name = key
            cc, nc, tt, ct, callers = value
            total_calls += nc

            # Filter to show relevant functions
            if "lateralus" in filename.lower() or func_name in (
                "<module>", "run", "compile", "tokenize", "parse",
            ):
                function_stats.append({
                    "name": f"{func_name} ({Path(filename).name}:{line})",
                    "calls": nc,
                    "tottime": tt,
                    "cumtime": ct,
                })

        # Sort by chosen metric
        sort_key = {"cumtime": "cumtime", "tottime": "tottime",
                    "calls": "calls"}.get(sort_by, "cumtime")
        function_stats.sort(key=lambda x: x[sort_key], reverse=True)

        return ProfileResult(
            file=filepath,
            total_time=total_time,
            function_stats=function_stats[:top],
            peak_memory_mb=peak / (1024 * 1024),
            call_count=total_calls,
        )

    def begin_timing(self, name: str):
        """Start a named timing block."""
        block = TimingBlock(name=name, start_time=time.perf_counter())
        if self.timing_stack:
            self.timing_stack[-1].children.append(block)
        else:
            self.timing_root.append(block)
        self.timing_stack.append(block)

    def end_timing(self) -> float:
        """End the current timing block and return elapsed time."""
        if not self.timing_stack:
            return 0.0
        block = self.timing_stack.pop()
        block.end_time = time.perf_counter()
        return block.elapsed

    def snapshot(self, label: str = ""):
        """Take a memory snapshot."""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            self.snapshots.append({
                "label": label,
                "current_mb": current / (1024 * 1024),
                "peak_mb": peak / (1024 * 1024),
                "timestamp": time.perf_counter(),
            })

    def timing_report(self) -> str:
        """Generate a report from timing blocks."""
        lines = [
            "  Timing Report",
            "  " + "=" * 50,
        ]

        def format_block(block: TimingBlock, depth: int = 0):
            indent = "    " * depth
            lines.append(
                f"  {indent}{block.name}: "
                f"{block.elapsed*1000:.2f}ms "
                f"(self: {block.self_time*1000:.2f}ms)"
            )
            for child in block.children:
                format_block(child, depth + 1)

        for block in self.timing_root:
            format_block(block)

        return "\n".join(lines)

    def memory_report(self) -> str:
        """Generate a memory snapshot report."""
        if not self.snapshots:
            return "  No memory snapshots taken."

        lines = [
            "  Memory Report",
            "  " + "=" * 50,
        ]

        for snap in self.snapshots:
            lines.append(
                f"  [{snap['label']}] "
                f"Current: {snap['current_mb']:.2f} MB, "
                f"Peak: {snap['peak_mb']:.2f} MB"
            )

        return "\n".join(lines)


class CompilationProfiler:
    """Profile individual compilation phases."""

    def __init__(self):
        self.phases: dict[str, list[float]] = {}

    def time_phase(self, name: str):
        """Context manager for timing a phase."""
        import contextlib

        @contextlib.contextmanager
        def _timer():
            start = time.perf_counter()
            yield
            elapsed = time.perf_counter() - start
            if name not in self.phases:
                self.phases[name] = []
            self.phases[name].append(elapsed)

        return _timer()

    def report(self) -> str:
        """Generate phase timing report."""
        lines = [
            "  Compilation Phase Report",
            "  " + "=" * 50,
            f"  {'Phase':<25} {'Count':>6} {'Mean(ms)':>10} {'Total(ms)':>10}",
            f"  {'-'*25} {'-'*6} {'-'*10} {'-'*10}",
        ]

        total = 0.0
        for name, times in sorted(self.phases.items()):
            count = len(times)
            mean = sum(times) / count * 1000
            total_ms = sum(times) * 1000
            total += sum(times)
            lines.append(
                f"  {name:<25} {count:>6} {mean:>10.2f} {total_ms:>10.2f}"
            )

        lines.append(f"  {'-'*25} {'-'*6} {'-'*10} {'-'*10}")
        lines.append(f"  {'TOTAL':<25} {'':>6} {'':>10} {total*1000:>10.2f}")

        return "\n".join(lines)


def main():
    """CLI entry point for the profiler."""
    import argparse

    parser = argparse.ArgumentParser(
        description="LATERALUS Profiler — Performance analysis"
    )
    parser.add_argument("file", help="LATERALUS source file to profile")
    parser.add_argument("--top", type=int, default=20,
                       help="Number of top functions to show")
    parser.add_argument("--sort", choices=["cumtime", "tottime", "calls"],
                       default="cumtime", help="Sort criterion")

    args = parser.parse_args()

    profiler = LateralusProfiler()

    try:
        result = profiler.profile_file(args.file, top=args.top, sort_by=args.sort)
        print(result.summary())
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Profiling error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
