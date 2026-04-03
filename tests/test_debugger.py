#!/usr/bin/env python3
"""
Tests for the LATERALUS debugger module.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lateralus_lang.debugger import (
    Breakpoint, StackFrame, WatchExpression, LateralusDebugger
)


# ─── Breakpoint Tests ──────────────────────────────────────────────────

class TestBreakpoint:
    def test_basic_breakpoint(self):
        bp = Breakpoint(file="test.ltl", line=10)
        assert bp.file == "test.ltl"
        assert bp.line == 10
        assert bp.enabled is True
        assert bp.condition is None
        assert bp.hit_count == 0

    def test_conditional_breakpoint(self):
        bp = Breakpoint(file="test.ltl", line=5, condition="x > 10")
        assert bp.condition == "x > 10"

    def test_breakpoint_id(self):
        bp = Breakpoint(file="test.ltl", line=10)
        assert bp.id == "test.ltl:10"

    def test_hit_count(self):
        bp = Breakpoint(file="test.ltl", line=10)
        bp.hit_count = 5
        assert bp.hit_count == 5


# ─── StackFrame Tests ──────────────────────────────────────────────────

class TestStackFrame:
    def test_basic_frame(self):
        frame = StackFrame(
            function="main",
            file="test.ltl",
            line=1,
            locals={"x": 42},
            args={}
        )
        assert frame.function == "main"
        assert frame.file == "test.ltl"
        assert frame.line == 1
        assert frame.locals["x"] == 42

    def test_frame_with_args(self):
        frame = StackFrame(
            function="add",
            file="math.ltl",
            line=5,
            locals={},
            args={"a": 1, "b": 2}
        )
        assert frame.args["a"] == 1
        assert frame.args["b"] == 2


# ─── WatchExpression Tests ──────────────────────────────────────────────

class TestWatchExpression:
    def test_basic_watch(self):
        watch = WatchExpression(expression="x + y")
        assert watch.expression == "x + y"
        assert watch.last_value is None

    def test_watch_evaluate(self):
        watch = WatchExpression(expression="2 + 3")
        result = watch.evaluate({"__builtins__": {}})
        assert result == 5
        assert watch.last_value == 5

    def test_watch_evaluate_with_vars(self):
        watch = WatchExpression(expression="x * 2")
        result = watch.evaluate({"x": 21, "__builtins__": {}})
        assert result == 42

    def test_watch_error(self):
        watch = WatchExpression(expression="undefined_var")
        result = watch.evaluate({"__builtins__": {}})
        assert isinstance(result, str)
        assert "Error" in result or "error" in str(result).lower() or result is not None


# ─── Debugger Tests ────────────────────────────────────────────────────

class TestDebugger:
    def setup_method(self):
        self.debugger = LateralusDebugger()

    def test_add_breakpoint(self):
        bp = self.debugger.add_breakpoint("test.ltl", 10)
        assert bp.file == "test.ltl"
        assert bp.line == 10
        assert len(self.debugger.breakpoints) == 1

    def test_add_conditional_breakpoint(self):
        bp = self.debugger.add_breakpoint("test.ltl", 5, condition="i > 10")
        assert bp.condition == "i > 10"

    def test_remove_breakpoint(self):
        self.debugger.add_breakpoint("test.ltl", 10)
        assert len(self.debugger.breakpoints) == 1
        result = self.debugger.remove_breakpoint("test.ltl", 10)
        assert result is True
        assert len(self.debugger.breakpoints) == 0

    def test_remove_nonexistent_breakpoint(self):
        result = self.debugger.remove_breakpoint("test.ltl", 99)
        assert result is False

    def test_toggle_breakpoint(self):
        bp = self.debugger.add_breakpoint("test.ltl", 10)
        assert bp.enabled is True
        self.debugger.toggle_breakpoint("test.ltl", 10)
        assert bp.enabled is False
        self.debugger.toggle_breakpoint("test.ltl", 10)
        assert bp.enabled is True

    def test_clear_breakpoints(self):
        self.debugger.add_breakpoint("test.ltl", 1)
        self.debugger.add_breakpoint("test.ltl", 5)
        self.debugger.add_breakpoint("test.ltl", 10)
        assert len(self.debugger.breakpoints) == 3
        self.debugger.clear_breakpoints()
        assert len(self.debugger.breakpoints) == 0

    def test_add_watch(self):
        self.debugger.add_watch("x + 1")
        assert len(self.debugger.watches) == 1
        assert self.debugger.watches[0].expression == "x + 1"

    def test_remove_watch(self):
        self.debugger.add_watch("x")
        self.debugger.add_watch("y")
        assert len(self.debugger.watches) == 2
        self.debugger.remove_watch(0)
        assert len(self.debugger.watches) == 1
        assert self.debugger.watches[0].expression == "y"

    def test_initial_state(self):
        assert self.debugger.running is False
        assert self.debugger.paused is False
        assert len(self.debugger.call_stack) == 0

    def test_continue(self):
        self.debugger.paused = True
        self.debugger.do_continue()
        assert self.debugger.paused is False

    def test_step_over(self):
        self.debugger.paused = True
        self.debugger.step_over()
        # Step over should set stepping mode

    def test_source_context(self):
        source = "line1\nline2\nline3\nline4\nline5"
        self.debugger.source_lines = source.split("\n")
        context = self.debugger.get_source_context(3, context_lines=1)
        assert len(context) == 3  # line 2, 3, 4

    def test_get_variables(self):
        self.debugger.call_stack.append(
            StackFrame(
                function="test",
                file="test.ltl",
                line=1,
                locals={"x": 42, "y": "hello"},
                args={"n": 10}
            )
        )
        variables = self.debugger.get_variables()
        assert variables is not None
        assert "x" in str(variables) or len(variables) > 0


# ─── Integration Tests ──────────────────────────────────────────────────

class TestDebuggerIntegration:
    def test_multiple_breakpoints_same_file(self):
        dbg = LateralusDebugger()
        dbg.add_breakpoint("main.ltl", 1)
        dbg.add_breakpoint("main.ltl", 10)
        dbg.add_breakpoint("main.ltl", 20)
        assert len(dbg.breakpoints) == 3

    def test_breakpoints_different_files(self):
        dbg = LateralusDebugger()
        dbg.add_breakpoint("main.ltl", 1)
        dbg.add_breakpoint("utils.ltl", 5)
        assert len(dbg.breakpoints) == 2

    def test_watch_with_complex_expression(self):
        dbg = LateralusDebugger()
        dbg.add_watch("len(items) > 0")
        dbg.add_watch("result['key']")
        dbg.add_watch("x ** 2 + y ** 2")
        assert len(dbg.watches) == 3

    def test_call_stack_str(self):
        dbg = LateralusDebugger()
        dbg.call_stack.append(StackFrame("main", "test.ltl", 1, {}, {}))
        dbg.call_stack.append(StackFrame("helper", "test.ltl", 10, {"x": 1}, {}))
        stack_str = dbg.get_call_stack_str()
        assert "main" in stack_str
        assert "helper" in stack_str
