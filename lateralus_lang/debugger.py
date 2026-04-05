"""
LATERALUS Debug Protocol
Interactive debugger for LATERALUS programs.

Supports:
  - Breakpoints (line-based)
  - Step over / step into / step out
  - Variable inspection
  - Call stack viewing
  - Watch expressions
  - Conditional breakpoints
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional


class DebugAction(Enum):
    CONTINUE = auto()
    STEP_OVER = auto()
    STEP_INTO = auto()
    STEP_OUT = auto()
    PAUSE = auto()


@dataclass
class Breakpoint:
    """A debugger breakpoint."""
    file: str
    line: int
    condition: Optional[str] = None
    hit_count: int = 0
    enabled: bool = True

    @property
    def id(self) -> str:
        return f"{self.file}:{self.line}"

    def should_break(self, locals_dict: dict) -> bool:
        """Check if this breakpoint should trigger."""
        if not self.enabled:
            return False
        self.hit_count += 1
        if self.condition:
            try:
                return bool(eval(self.condition, {}, locals_dict))
            except Exception:
                return True
        return True


@dataclass
class StackFrame:
    """A call stack frame."""
    function: str
    file: str
    line: int
    locals: dict[str, Any] = field(default_factory=dict)
    args: dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        return f"  {self.function} at {self.file}:{self.line}"


@dataclass
class WatchExpression:
    """A watched expression."""
    expression: str
    id: int = 0
    last_value: Any = None
    error: Optional[str] = None

    def evaluate(self, locals_dict: dict) -> Any:
        try:
            self.last_value = eval(self.expression, {}, locals_dict)
            self.error = None
            return self.last_value
        except Exception as e:
            self.error = f"Error: {e}"
            self.last_value = None
            return self.error


class LateralusDebugger:
    """Interactive debugger for LATERALUS programs."""

    def __init__(self):
        self.breakpoints: list[Breakpoint] = []
        self.watches: list[WatchExpression] = []
        self.call_stack: list[StackFrame] = []
        self.current_action: DebugAction = DebugAction.CONTINUE
        self.running: bool = False
        self.paused: bool = False
        self._step_depth: int = 0
        self._on_break: Optional[Callable] = None
        self._source_cache: dict[str, list[str]] = {}
        self.source_lines: list[str] = []

    # --- Breakpoint Management -------------------------------------

    def add_breakpoint(self, file: str, line: int,
                       condition: Optional[str] = None) -> Breakpoint:
        """Add a breakpoint."""
        bp = Breakpoint(
            file=file,
            line=line,
            condition=condition,
        )
        self.breakpoints.append(bp)
        return bp

    def remove_breakpoint(self, file: str, line: int) -> bool:
        """Remove a breakpoint by file and line."""
        for i, bp in enumerate(self.breakpoints):
            if bp.file == file and bp.line == line:
                self.breakpoints.pop(i)
                return True
        return False

    def toggle_breakpoint(self, file: str, line: int):
        """Toggle a breakpoint on/off."""
        for bp in self.breakpoints:
            if bp.file == file and bp.line == line:
                bp.enabled = not bp.enabled
                return

    def clear_breakpoints(self):
        """Remove all breakpoints."""
        self.breakpoints.clear()

    # --- Watch Expressions -----------------------------------------

    def add_watch(self, expression: str) -> WatchExpression:
        """Add a watch expression."""
        watch = WatchExpression(expression=expression)
        self.watches.append(watch)
        return watch

    def remove_watch(self, index: int) -> bool:
        """Remove a watch expression by index."""
        if 0 <= index < len(self.watches):
            self.watches.pop(index)
            return True
        return False

    # --- Execution Control -----------------------------------------

    def continue_execution(self):
        self.current_action = DebugAction.CONTINUE
        self.paused = False

    def do_continue(self):
        """Alias for continue_execution."""
        self.continue_execution()

    def step_over(self):
        self.current_action = DebugAction.STEP_OVER
        self._step_depth = len(self.call_stack)
        self.paused = False

    def step_into(self):
        self.current_action = DebugAction.STEP_INTO
        self.paused = False

    def step_out(self):
        self.current_action = DebugAction.STEP_OUT
        self._step_depth = len(self.call_stack) - 1
        self.paused = False

    def pause(self):
        self.current_action = DebugAction.PAUSE
        self.paused = True

    # --- Stack Management ------------------------------------------

    def push_frame(self, function_name: str, file: str, line: int,
                   args: Optional[dict] = None):
        """Push a new stack frame."""
        frame = StackFrame(
            function=function_name,
            file=file,
            line=line,
            args=args or {},
        )
        self.call_stack.append(frame)

    def pop_frame(self) -> Optional[StackFrame]:
        """Pop the current stack frame."""
        if self.call_stack:
            return self.call_stack.pop()
        return None

    def current_frame(self) -> Optional[StackFrame]:
        """Get the current (top) stack frame."""
        return self.call_stack[-1] if self.call_stack else None

    # --- Debug Hook ------------------------------------------------

    def on_line(self, file: str, line: int, locals_dict: dict) -> DebugAction:
        """
        Called on each line execution. This is the main debug hook.
        Returns the action to take.
        """
        # Update current frame
        if self.call_stack:
            self.call_stack[-1].line = line
            self.call_stack[-1].locals = dict(locals_dict)

        should_break = False

        # Check breakpoints
        for bp in self.breakpoints:
            if bp.file == file and bp.line == line:
                if bp.should_break(locals_dict):
                    should_break = True
                    break

        # Check stepping
        if self.current_action == DebugAction.STEP_INTO:
            should_break = True
        elif self.current_action == DebugAction.STEP_OVER:
            if len(self.call_stack) <= self._step_depth:
                should_break = True
        elif self.current_action == DebugAction.STEP_OUT:
            if len(self.call_stack) <= self._step_depth:
                should_break = True
        elif self.current_action == DebugAction.PAUSE:
            should_break = True

        if should_break:
            self.paused = True
            # Update watches
            for watch in self.watches:
                watch.evaluate(locals_dict)
            # Notify callback
            if self._on_break:
                self._on_break(self, file, line)

        return self.current_action

    # --- Source Viewing --------------------------------------------

    def get_source_line(self, file: str, line: int) -> Optional[str]:
        """Get a source line from a file."""
        if file not in self._source_cache:
            try:
                from pathlib import Path
                self._source_cache[file] = Path(file).read_text().split("\n")
            except Exception:
                return None

        lines = self._source_cache[file]
        if 0 < line <= len(lines):
            return lines[line - 1]
        return None

    def get_source_context(self, file_or_line=None, line: int = 0,
                           context: int = 3, context_lines: int = 0) -> list:
        # Support both: get_source_context(file, line, context) and
        #               get_source_context(line_number, context_lines=N)
        if isinstance(file_or_line, int):
            # New API: get_source_context(line, context_lines=N)
            target = file_or_line
            ctx = context_lines if context_lines else context
            start = max(0, target - ctx - 1)
            end = min(len(self.source_lines), target + ctx)
            return self.source_lines[start:end]
        else:
            # Old API: get_source_context(file, line, context)
            result = []
            for i in range(line - context, line + context + 1):
                text = self.get_source_line(file_or_line, i)
                if text is not None:
                    result.append((i, text, i == line))
            return result

    # --- State Inspection ------------------------------------------

    def get_variables(self) -> dict[str, Any]:
        """Get all variables in the current scope."""
        frame = self.current_frame()
        if frame:
            return {**frame.args, **frame.locals}
        return {}

    def evaluate(self, expression: str) -> tuple[Any, Optional[str]]:
        """Evaluate an expression in the current context."""
        try:
            result = eval(expression, {}, self.get_variables())
            return result, None
        except Exception as e:
            return None, str(e)

    def get_call_stack_str(self) -> str:
        """Get a formatted call stack."""
        if not self.call_stack:
            return "  (empty stack)"
        lines = []
        for i, frame in enumerate(reversed(self.call_stack)):
            marker = "→ " if i == 0 else "  "
            lines.append(f"  {marker}{frame}")
        return "\n".join(lines)

    # --- REPL Integration ------------------------------------------

    def interactive_break(self, file: str, line: int):
        """Enter interactive debug mode at a breakpoint."""
        print(f"\n  Break at {file}:{line}")

        # Show context
        context = self.get_source_context(file, line)
        for lineno, text, is_current in context:
            marker = "→" if is_current else " "
            print(f"  {marker} {lineno:4d} | {text}")

        print()

        # Show watches
        if self.watches:
            print("  Watches:")
            for w in self.watches:
                if w.error:
                    print(f"    {w.expression} = <error: {w.error}>")
                else:
                    print(f"    {w.expression} = {w.last_value}")
            print()

        # Interactive loop
        while self.paused:
            try:
                cmd = input("  (debug) ").strip()
            except (EOFError, KeyboardInterrupt):
                self.continue_execution()
                break

            if cmd in ("c", "continue"):
                self.continue_execution()
            elif cmd in ("n", "next", "step"):
                self.step_over()
            elif cmd in ("s", "stepin"):
                self.step_into()
            elif cmd in ("o", "out"):
                self.step_out()
            elif cmd in ("q", "quit"):
                sys.exit(0)
            elif cmd in ("bt", "backtrace", "stack"):
                print(self.get_call_stack_str())
            elif cmd in ("vars", "locals"):
                for name, val in self.get_variables().items():
                    print(f"    {name} = {val}")
            elif cmd.startswith("p ") or cmd.startswith("print "):
                expr = cmd.split(" ", 1)[1]
                val, err = self.evaluate(expr)
                if err:
                    print(f"    Error: {err}")
                else:
                    print(f"    {val}")
            elif cmd.startswith("w ") or cmd.startswith("watch "):
                expr = cmd.split(" ", 1)[1]
                w = self.add_watch(expr)
                w.evaluate(self.get_variables())
                print(f"    Watch #{w.id}: {expr} = {w.last_value}")
            elif cmd in ("h", "help"):
                print("    c/continue  — Continue execution")
                print("    n/next      — Step over")
                print("    s/stepin    — Step into")
                print("    o/out       — Step out")
                print("    bt/stack    — Show call stack")
                print("    vars        — Show local variables")
                print("    p <expr>    — Evaluate expression")
                print("    w <expr>    — Add watch expression")
                print("    q/quit      — Quit")
            else:
                # Try to evaluate as expression
                val, err = self.evaluate(cmd)
                if err:
                    print(f"    Unknown command. Type 'h' for help.")
                else:
                    print(f"    {val}")
