"""
lateralus_lang/repl_enhanced.py — Enhanced REPL for LATERALUS

Features:
  - Syntax highlighting
  - Multi-line input
  - History
  - Tab completion for builtins
  - Inline help
  - Performance timing
  - Expression result display
"""

from __future__ import annotations

import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Set


# --- ANSI Colors -------------------------------------------------------

class _C:
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    @classmethod
    def disable(cls):
        for attr in dir(cls):
            if attr.isupper() and not attr.startswith("_"):
                setattr(cls, attr, "")


# --- REPL Keywords & Builtins -----------------------------------------

KEYWORDS = {
    "fn", "let", "const", "if", "else", "for", "while", "return",
    "match", "struct", "interface", "import", "from", "as",
    "throw", "try", "catch", "emit", "probe", "measure",
    "and", "or", "not", "true", "false", "none", "pass",
    "in", "break", "continue",
}

BUILTINS = {
    # Core
    "print", "println", "input", "len", "type_of", "str", "int", "float", "bool",
    "range", "assert_eq", "assert_ne", "assert_true",
    # Collections
    "map", "filter", "reduce", "zip", "enumerate", "sorted", "reversed",
    "flatten", "chunk", "unique", "sum",
    # Strings
    "trim", "split", "join", "upper", "lower", "replace", "contains",
    "starts_with", "ends_with", "char_at", "pad_left", "pad_right",
    # Math
    "abs", "min", "max", "floor", "ceil", "round", "pow", "sqrt",
    "sin", "cos", "tan", "log", "clamp",
    "mean", "median", "variance", "std_dev",
    "derivative", "bisection", "simpson_integrate",
    # Crypto
    "sha256", "sha512", "blake2b", "hmac_sign", "hmac_verify",
    "random_token", "to_base64", "from_base64",
    "hash_password", "verify_password",
    # Types
    "Matrix", "Vector", "Interval", "Dual",
}

SPECIAL_COMMANDS = {
    ":help": "Show help information",
    ":quit": "Exit the REPL",
    ":exit": "Exit the REPL",
    ":clear": "Clear the screen",
    ":reset": "Reset the REPL state",
    ":time": "Toggle timing display",
    ":env": "Show current variables",
    ":version": "Show LATERALUS version",
    ":engines": "Show engine status",
    ":history": "Show command history",
    ":type": "Show type of last result (e.g., :type x)",
    ":save": "Save session history to file (e.g., :save session.ltl)",
    ":doc": "Show documentation for a builtin (e.g., :doc map)",
    ":profile": "Profile the next expression's compilation phases",
}


# --- Syntax Highlighter -----------------------------------------------

def highlight_line(line: str) -> str:
    """Apply syntax highlighting to a line of LATERALUS code."""
    result = []
    i = 0
    while i < len(line):
        # String literals
        if line[i] in ('"', "'"):
            quote = line[i]
            j = i + 1
            while j < len(line) and line[j] != quote:
                if line[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, len(line))
            result.append(f"{_C.GREEN}{line[i:j]}{_C.RESET}")
            i = j
            continue

        # Numbers
        if line[i].isdigit():
            j = i
            while j < len(line) and (line[j].isdigit() or line[j] == "."):
                j += 1
            result.append(f"{_C.CYAN}{line[i:j]}{_C.RESET}")
            i = j
            continue

        # Comments
        if line[i:i+2] == "//":
            result.append(f"{_C.GRAY}{line[i:]}{_C.RESET}")
            break

        # Words (keywords, builtins, identifiers)
        if line[i].isalpha() or line[i] == "_":
            j = i
            while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            if word in KEYWORDS:
                result.append(f"{_C.MAGENTA}{_C.BOLD}{word}{_C.RESET}")
            elif word in BUILTINS:
                result.append(f"{_C.YELLOW}{word}{_C.RESET}")
            elif word in ("true", "false", "none"):
                result.append(f"{_C.CYAN}{word}{_C.RESET}")
            else:
                result.append(word)
            i = j
            continue

        # Pipeline operator
        if line[i:i+2] == "|>":
            result.append(f"{_C.BLUE}{_C.BOLD}|>{_C.RESET}")
            i += 2
            continue

        if line[i:i+2] == "|?":
            result.append(f"{_C.BLUE}{_C.BOLD}|?{_C.RESET}")
            i += 2
            continue

        # Operators
        if line[i] in "+-*/%=<>!&|^~@":
            result.append(f"{_C.RED}{line[i]}{_C.RESET}")
            i += 1
            continue

        # Brackets
        if line[i] in "()[]{}":
            result.append(f"{_C.WHITE}{line[i]}{_C.RESET}")
            i += 1
            continue

        result.append(line[i])
        i += 1

    return "".join(result)


# --- REPL Session -----------------------------------------------------

class REPLSession:
    """An interactive REPL session for LATERALUS."""

    def __init__(self, color: bool = True, timing: bool = False):
        self.color = color
        self.timing = timing
        self.history: List[str] = []
        self.env: Dict[str, Any] = {}
        self.last_result: Any = None
        self._counter = 0
        self._profile_next: bool = False

        if not color:
            _C.disable()

    def banner(self) -> str:
        """Return the REPL banner."""
        try:
            from lateralus_lang import __version__
            version = __version__
        except ImportError:
            version = "2.4.0"

        return (
            f"{_C.CYAN}{_C.BOLD}"
            f"\n+===================================================+"
            f"\n|  L·A·T·E·R·A·L·U·S   v{version}  [ INTERACTIVE ]  |"
            f"\n|  -----------------------------------------------  |"
            f"\n+===================================================+"
            f"{_C.RESET}"
            f"\n{_C.DIM}  :help · :quit · :clear · :env · :time{_C.RESET}\n"
        )

    def prompt(self) -> str:
        """Return the REPL prompt."""
        self._counter += 1
        return f"{_C.BLUE}ltl[{self._counter}]{_C.RESET}> "

    def continuation_prompt(self) -> str:
        """Return the continuation prompt for multi-line input."""
        return f"{_C.DIM}   ...{_C.RESET}> "

    def needs_continuation(self, code: str) -> bool:
        """Check if code needs more lines (unclosed braces, etc.)."""
        opens = code.count("{") + code.count("(") + code.count("[")
        closes = code.count("}") + code.count(")") + code.count("]")
        return opens > closes

    def handle_special(self, command: str) -> Optional[str]:
        """Handle special REPL commands. Returns output or None."""
        cmd = command.strip().lower()
        parts = cmd.split(None, 1)
        base = parts[0]

        if base in (":quit", ":exit", ":q"):
            print(f"\n{_C.DIM}Goodbye!{_C.RESET}")
            sys.exit(0)

        if base == ":help":
            lines = [f"\n{_C.BOLD}LATERALUS REPL Commands:{_C.RESET}\n"]
            for cmd_name, desc in SPECIAL_COMMANDS.items():
                lines.append(f"  {_C.CYAN}{cmd_name:<12}{_C.RESET} {desc}")
            lines.append(f"\n{_C.BOLD}Quick Reference:{_C.RESET}")
            lines.append(f"  {_C.MAGENTA}let{_C.RESET} x = 42           Define a variable")
            lines.append(f"  {_C.MAGENTA}fn{_C.RESET} add(a, b) {{ a+b }}  Define a function")
            lines.append(f"  data {_C.BLUE}|>{_C.RESET} map(f)        Pipeline operator")
            lines.append(f"  data {_C.BLUE}|?{_C.RESET} map(f)        Optional pipeline")
            lines.append("")
            return "\n".join(lines)

        if base == ":clear":
            print("\033[2J\033[H", end="")
            return ""

        if base == ":reset":
            self.env.clear()
            self.history.clear()
            self._counter = 0
            return f"{_C.GREEN}REPL state reset.{_C.RESET}"

        if base == ":time":
            self.timing = not self.timing
            state = "on" if self.timing else "off"
            return f"{_C.GREEN}Timing display: {state}{_C.RESET}"

        if base == ":env":
            if not self.env:
                return f"{_C.DIM}(no variables defined){_C.RESET}"
            lines = [f"{_C.BOLD}Current variables:{_C.RESET}"]
            for name, val in self.env.items():
                typ = type(val).__name__
                lines.append(f"  {_C.CYAN}{name}{_C.RESET}: {_C.DIM}{typ}{_C.RESET} = {val}")
            return "\n".join(lines)

        if base == ":version":
            try:
                from lateralus_lang import __version__
                return f"LATERALUS v{__version__}"
            except ImportError:
                return "LATERALUS v2.4.0"

        if base == ":engines":
            try:
                from lateralus_lang.engines import engine_status
                status = engine_status()
                lines = [f"{_C.BOLD}Engine Status:{_C.RESET}"]
                for name, info in status.items():
                    icon = f"{_C.GREEN}\u2713{_C.RESET}" if info["available"] else f"{_C.RED}\u2717{_C.RESET}"
                    lines.append(f"  {icon} {name}")
                return "\n".join(lines)
            except ImportError:
                return f"{_C.YELLOW}Engine module not available{_C.RESET}"

        if base == ":history":
            if not self.history:
                return f"{_C.DIM}(no history){_C.RESET}"
            lines = [f"{_C.BOLD}History:{_C.RESET}"]
            for i, entry in enumerate(self.history[-20:], 1):
                lines.append(f"  {_C.DIM}{i:3d}{_C.RESET}  {entry}")
            return "\n".join(lines)

        if base == ":type":
            if len(parts) > 1:
                name = parts[1]
                if name in self.env:
                    return f"{_C.CYAN}{name}{_C.RESET}: {type(self.env[name]).__name__}"
                return f"{_C.RED}Unknown variable: {name}{_C.RESET}"
            if self.last_result is not None:
                return f"{type(self.last_result).__name__}"
            return f"{_C.DIM}none{_C.RESET}"

        if base == ":save":
            if len(parts) < 2:
                return f"{_C.YELLOW}Usage: :save <filename.ltl>{_C.RESET}"
            path = parts[1]
            if not self.history:
                return f"{_C.DIM}(no history to save){_C.RESET}"
            code_lines = [h for h in self.history if not h.startswith(":")]
            try:
                with open(path, "w") as f:
                    f.write("// Generated from LATERALUS REPL session\n\n")
                    for h in code_lines:
                        f.write(h + "\n\n")
                return f"{_C.GREEN}Saved {len(code_lines)} expressions to {path}{_C.RESET}"
            except OSError as e:
                return f"{_C.RED}Error writing {path}: {e}{_C.RESET}"

        if base == ":doc":
            if len(parts) < 2:
                return f"{_C.YELLOW}Usage: :doc <builtin_name>{_C.RESET}"
            name = parts[1]
            return self._lookup_doc(name)

        if base == ":profile":
            self._profile_next = True
            return f"{_C.GREEN}Profiling enabled for next expression.{_C.RESET}"

        return f"{_C.RED}Unknown command: {base}{_C.RESET}\nType :help for available commands."

    def format_result(self, value: Any) -> str:
        """Format a result value for display."""
        if value is None:
            return ""

        self.last_result = value

        if isinstance(value, str):
            return f'{_C.GREEN}"{value}"{_C.RESET}'
        if isinstance(value, bool):
            return f"{_C.CYAN}{value}{_C.RESET}"
        if isinstance(value, (int, float)):
            return f"{_C.CYAN}{value}{_C.RESET}"
        if isinstance(value, list):
            return f"{_C.WHITE}{value}{_C.RESET}"
        if isinstance(value, dict):
            return f"{_C.WHITE}{value}{_C.RESET}"

        return str(value)

    def get_completions(self, text: str) -> List[str]:
        """Get tab completions for partial input."""
        candidates = set()
        candidates.update(KEYWORDS)
        candidates.update(BUILTINS)
        candidates.update(self.env.keys())
        candidates.update(cmd for cmd in SPECIAL_COMMANDS)

        if not text:
            return []

        return sorted(c for c in candidates if c.startswith(text))

    def _lookup_doc(self, name: str) -> str:
        """Look up documentation for a builtin function."""
        if name in _BUILTIN_DOCS:
            return f"{_C.BOLD}{name}{_C.RESET}\n  {_BUILTIN_DOCS[name]}"
        # Fuzzy match
        close = [k for k in _BUILTIN_DOCS if name in k or k.startswith(name[:3])]
        if close:
            hint = ", ".join(close[:5])
            return f"{_C.RED}No docs for '{name}'.{_C.RESET}\n  {_C.DIM}Did you mean: {hint}?{_C.RESET}"
        return f"{_C.RED}No documentation found for '{name}'.{_C.RESET}"

    def _run_profiled(self, code: str) -> None:
        """Execute code with per-phase timing breakdown."""
        from lateralus_lang.lexer import Lexer
        from lateralus_lang.parser import Parser
        from lateralus_lang.compiler import Compiler, Target

        print(f"{_C.DIM}-- Profile --{_C.RESET}")

        # Lex
        t0 = time.perf_counter_ns()
        tokens = Lexer(code).tokenize()
        t_lex = (time.perf_counter_ns() - t0) / 1_000_000

        # Parse
        t0 = time.perf_counter_ns()
        ast = Parser(tokens).parse()
        t_parse = (time.perf_counter_ns() - t0) / 1_000_000

        # Full compile
        t0 = time.perf_counter_ns()
        compiler = Compiler()
        result = compiler.compile_source(code, "<repl>", Target.PYTHON)
        t_compile = (time.perf_counter_ns() - t0) / 1_000_000

        print(f"  {_C.CYAN}Lex:{_C.RESET}     {t_lex:8.3f} ms  ({len(tokens)} tokens)")
        print(f"  {_C.CYAN}Parse:{_C.RESET}   {t_parse:8.3f} ms  ({len(ast.body)} top-level nodes)")
        print(f"  {_C.CYAN}Compile:{_C.RESET} {t_compile:8.3f} ms  ({'OK' if result.ok else 'errors'})")
        print(f"  {_C.CYAN}Total:{_C.RESET}   {t_lex + t_parse + t_compile:8.3f} ms")
        print(f"{_C.DIM}-------------{_C.RESET}")

    def run(self):
        """Run the interactive REPL loop."""
        print(self.banner())

        while True:
            try:
                # Read input
                line = input(self.prompt())
                code = line.strip()

                if not code:
                    continue

                # Multi-line input
                while self.needs_continuation(code):
                    continuation = input(self.continuation_prompt())
                    code += "\n" + continuation

                self.history.append(code)

                # Special commands
                if code.startswith(":"):
                    result = self.handle_special(code)
                    if result:
                        print(result)
                    continue

                # Execute code
                start = time.perf_counter_ns()
                do_profile = self._profile_next
                self._profile_next = False

                try:
                    from lateralus_lang.compiler import Compiler, Target

                    if do_profile:
                        self._run_profiled(code)
                    else:
                        compiler = Compiler()
                        result = compiler.run(code, target=Target.PYTHON)
                        elapsed_ns = time.perf_counter_ns() - start

                        formatted = self.format_result(result)
                        if formatted:
                            print(f"{_C.DIM}\u2192{_C.RESET} {formatted}")

                        if self.timing:
                            elapsed_ms = elapsed_ns / 1_000_000
                            print(f"{_C.DIM}  [{elapsed_ms:.3f} ms]{_C.RESET}")

                except Exception as e:
                    elapsed_ns = time.perf_counter_ns() - start
                    # Try to enhance the error
                    try:
                        from lateralus_lang.error_engine import enhance_traceback
                        ltl_error = enhance_traceback(e, code, "<repl>")
                        if ltl_error:
                            print(ltl_error.format(color=self.color))
                        else:
                            print(f"{_C.RED}Error: {e}{_C.RESET}")
                    except ImportError:
                        print(f"{_C.RED}Error: {e}{_C.RESET}")

            except KeyboardInterrupt:
                print(f"\n{_C.DIM}(Use :quit to exit){_C.RESET}")
                continue

            except EOFError:
                print(f"\n{_C.DIM}Goodbye!{_C.RESET}")
                break


# --- Helper methods ----------------------------------------------------

_BUILTIN_DOCS: Dict[str, str] = {
    "println":   "println(value) — Print value with trailing newline.",
    "print":     "print(value) — Print value without newline.",
    "len":       "len(collection) — Return length of list, string, or map.",
    "type_of":   "type_of(value) — Return type name as string.",
    "range":     "range(start, end[, step]) — Generate list of integers.",
    "map":       "map(list, fn) — Apply fn to each element, return new list.",
    "filter":    "filter(list, fn) — Keep elements where fn returns true.",
    "reduce":    "reduce(list, fn, init) — Fold list with accumulator.",
    "sorted":    "sorted(list) — Return sorted copy of list.",
    "reversed":  "reversed(list) — Return reversed copy of list.",
    "zip":       "zip(list_a, list_b) — Pair elements into list of tuples.",
    "enumerate": "enumerate(list) — Return list of [index, element] pairs.",
    "flatten":   "flatten(nested_list) — Flatten one level of nesting.",
    "unique":    "unique(list) — Remove duplicate elements.",
    "sum":       "sum(list) — Sum numeric elements.",
    "mean":      "mean(list) — Arithmetic mean of numeric list.",
    "median":    "median(list) — Median value of sorted numeric list.",
    "join":      "join(list, sep) — Join list elements into string.",
    "split":     "split(str, sep) — Split string into list by separator.",
    "trim":      "trim(str) — Remove leading/trailing whitespace.",
    "upper":     "upper(str) — Convert to uppercase.",
    "lower":     "lower(str) — Convert to lowercase.",
    "contains":  "contains(haystack, needle) — Check if needle is in haystack.",
    "abs":       "abs(n) — Absolute value.",
    "min":       "min(a, b) — Return smaller value.",
    "max":       "max(a, b) — Return larger value.",
    "sqrt":      "sqrt(n) — Square root.",
    "floor":     "floor(n) — Round down to integer.",
    "ceil":      "ceil(n) — Round up to integer.",
    "round":     "round(n, digits) — Round to N decimal places.",
    "clamp":     "clamp(value, lo, hi) — Clamp value to range [lo, hi].",
    "sha256":    "sha256(data) — SHA-256 hash as hex string.",
    "sha512":    "sha512(data) — SHA-512 hash as hex string.",
    "blake2b":   "blake2b(data) — BLAKE2b hash as hex string.",
    "random_token": "random_token(length) — Cryptographically random hex token.",
    "to_base64": "to_base64(data) — Base64-encode a string.",
    "from_base64": "from_base64(data) — Decode a Base64 string.",
    "assert_eq": "assert_eq(a, b) — Assert a equals b, throw on mismatch.",
    "assert_ne": "assert_ne(a, b) — Assert a does not equal b.",
    "assert_true": "assert_true(cond) — Assert condition is truthy.",
    "input":     "input([prompt]) — Read a line from stdin.",
    "str":       "str(value) — Convert value to string.",
    "int":       "int(value) — Convert value to integer.",
    "float":     "float(value) — Convert value to float.",
    "bool":      "bool(value) — Convert value to boolean.",
    "keys":      "keys(map) — Return list of map keys.",
    "values":    "values(map) — Return list of map values.",
    "chunk":     "chunk(list, size) — Split list into chunks of N.",
    "derivative": "derivative(fn, x) — Numerical derivative at point x.",
    "bisection":  "bisection(fn, a, b, tol) — Root-finding by bisection.",
    "simpson_integrate": "simpson_integrate(fn, a, b, n) — Numerical integration.",
}

# --- Entry point -------------------------------------------------------

def start_repl(color: bool = True, timing: bool = False):
    """Start the enhanced LATERALUS REPL."""
    session = REPLSession(color=color, timing=timing)
    session.run()


if __name__ == "__main__":
    start_repl()
