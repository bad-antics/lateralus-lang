#!/usr/bin/env python3
"""
Tests for the LATERALUS profiler module.
"""
import pytest
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lateralus_lang.profiler import (
    ProfileResult, TimingBlock, LateralusProfiler,
    CompilationProfiler
)


# ─── ProfileResult Tests ───────────────────────────────────────────────

class TestProfileResult:
    def test_basic_result(self):
        result = ProfileResult(
            file="test.ltl",
            total_time=1.234,
            function_stats=[],
            peak_memory_mb=10.5,
            call_count=100
        )
        assert result.file == "test.ltl"
        assert result.total_time == 1.234
        assert result.peak_memory_mb == 10.5
        assert result.call_count == 100

    def test_summary(self):
        result = ProfileResult(
            file="test.ltl",
            total_time=0.5,
            function_stats=[
                {"name": "compile", "calls": 1, "tottime": 0.3, "cumtime": 0.5},
                {"name": "tokenize", "calls": 1, "tottime": 0.1, "cumtime": 0.1},
            ],
            peak_memory_mb=5.0,
            call_count=50
        )
        summary = result.summary()
        assert "test.ltl" in summary
        assert "compile" in summary
        assert "tokenize" in summary
        assert "0.5000" in summary  # total time

    def test_empty_stats_summary(self):
        result = ProfileResult(
            file="test.ltl",
            total_time=0.0,
            function_stats=[],
            peak_memory_mb=0.0,
            call_count=0
        )
        summary = result.summary()
        assert "test.ltl" in summary


# ─── TimingBlock Tests ──────────────────────────────────────────────────

class TestTimingBlock:
    def test_basic_timing(self):
        block = TimingBlock(name="test")
        block.start_time = 1.0
        block.end_time = 2.0
        assert block.elapsed == 1.0

    def test_self_time(self):
        parent = TimingBlock(name="parent", start_time=0.0, end_time=10.0)
        child1 = TimingBlock(name="child1", start_time=1.0, end_time=4.0)
        child2 = TimingBlock(name="child2", start_time=5.0, end_time=8.0)
        parent.children = [child1, child2]

        assert parent.elapsed == 10.0
        assert child1.elapsed == 3.0
        assert child2.elapsed == 3.0
        assert parent.self_time == 4.0  # 10 - 3 - 3

    def test_no_children_self_time(self):
        block = TimingBlock(name="leaf", start_time=0.0, end_time=5.0)
        assert block.self_time == 5.0


# ─── LateralusProfiler Tests ───────────────────────────────────────────

class TestLateralusProfiler:
    def test_timing_blocks(self):
        profiler = LateralusProfiler()

        profiler.begin_timing("phase1")
        time.sleep(0.01)
        elapsed = profiler.end_timing()

        assert elapsed > 0
        assert len(profiler.timing_root) == 1
        assert profiler.timing_root[0].name == "phase1"

    def test_nested_timing(self):
        profiler = LateralusProfiler()

        profiler.begin_timing("outer")
        profiler.begin_timing("inner")
        profiler.end_timing()
        profiler.end_timing()

        assert len(profiler.timing_root) == 1
        assert profiler.timing_root[0].name == "outer"
        assert len(profiler.timing_root[0].children) == 1
        assert profiler.timing_root[0].children[0].name == "inner"

    def test_timing_report(self):
        profiler = LateralusProfiler()

        profiler.begin_timing("compile")
        profiler.begin_timing("tokenize")
        time.sleep(0.01)
        profiler.end_timing()
        profiler.begin_timing("parse")
        time.sleep(0.01)
        profiler.end_timing()
        profiler.end_timing()

        report = profiler.timing_report()
        assert "compile" in report
        assert "tokenize" in report
        assert "parse" in report

    def test_empty_timing_report(self):
        profiler = LateralusProfiler()
        report = profiler.timing_report()
        assert "Timing Report" in report

    def test_memory_report_no_snapshots(self):
        profiler = LateralusProfiler()
        report = profiler.memory_report()
        assert "No memory snapshots" in report

    def test_profile_nonexistent_file(self):
        profiler = LateralusProfiler()
        with pytest.raises(FileNotFoundError):
            profiler.profile_file("nonexistent.ltl")

    def test_end_timing_empty_stack(self):
        profiler = LateralusProfiler()
        elapsed = profiler.end_timing()
        assert elapsed == 0.0


# ─── CompilationProfiler Tests ──────────────────────────────────────────

class TestCompilationProfiler:
    def test_basic_phase_timing(self):
        profiler = CompilationProfiler()

        with profiler.time_phase("lexing"):
            time.sleep(0.01)

        assert "lexing" in profiler.phases
        assert len(profiler.phases["lexing"]) == 1
        assert profiler.phases["lexing"][0] > 0

    def test_multiple_phases(self):
        profiler = CompilationProfiler()

        with profiler.time_phase("lexing"):
            time.sleep(0.005)
        with profiler.time_phase("parsing"):
            time.sleep(0.005)
        with profiler.time_phase("codegen"):
            time.sleep(0.005)

        assert len(profiler.phases) == 3

    def test_repeated_phase(self):
        profiler = CompilationProfiler()

        for _ in range(3):
            with profiler.time_phase("optimize"):
                time.sleep(0.001)

        assert len(profiler.phases["optimize"]) == 3

    def test_report(self):
        profiler = CompilationProfiler()

        with profiler.time_phase("lexing"):
            time.sleep(0.01)
        with profiler.time_phase("parsing"):
            time.sleep(0.01)

        report = profiler.report()
        assert "lexing" in report
        assert "parsing" in report
        assert "TOTAL" in report

    def test_empty_report(self):
        profiler = CompilationProfiler()
        report = profiler.report()
        assert "Compilation Phase Report" in report
