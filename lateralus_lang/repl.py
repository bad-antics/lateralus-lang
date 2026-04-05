"""
lateralus_lang/repl.py  -  LATERALUS Interactive REPL
===========================================================================
Provides an interactive Read-Eval-Print Loop for both Lateralus Script
(.ltl) and Lateralus Assembly (.ltasm) modes.

Features
--------
  · Multiline block detection (unbalanced { } opens a continuation)
  · Command history via readline (when available)
  · Magic commands:
      :help       — show this help
      :clear      — clear the screen
      :mode ltl   — switch to .ltl scripting mode
      :mode asm   — switch to .ltasm assembly mode
      :target py  — transpile to Python instead of running
      :reset      — reset the REPL state
      :errors     — show all accumulated errors
      :quit / :q  — exit
  · Colour output (auto-detected)
  · Integrates with Lateralus error_engine when available
===========================================================================
"""
from __future__ import annotations

import sys
import os

try:
    import readline
    _HAS_READLINE = True
except ImportError:
    _HAS_READLINE = False

from .compiler import Compiler, Target, CompileResult
from .errors   import ErrorReporter, Severity

# -----------------------------------------------------------------------------
# Colours
# -----------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

def _bold(t): return _c(t, "1")
def _cyan(t): return _c(t, "36")
def _green(t): return _c(t, "32")
def _red(t):   return _c(t, "31")
def _yellow(t): return _c(t, "33")
def _dim(t):   return _c(t, "2")


# -----------------------------------------------------------------------------
# REPL
# -----------------------------------------------------------------------------

_BANNER = """\
+===================================================+
|  L·A·T·E·R·A·L·U·S          v2.4.0  [JUL-2026]  |
|  ---------------------------------------------  |
|  [ SYSTEM_READY ]  [ PIPELINE_FIRST ]           |
+===================================================+
   :help · :quit · :mode · :target · :ver
"""

_HELP = """
REPL Commands
-------------
  :help            Show this help
  :clear           Clear the screen
  :mode ltl        Switch to Lateralus Script (.ltl) mode  [default]
  :mode asm        Switch to Lateralus Assembly (.ltasm) mode
  :target vm       Execute in the LTasm VM  [default]
  :target py       Transpile to Python and print source
  :target check    Lex/parse/type-check only (no execution)
  :reset           Reset REPL state (clear bindings)
  :errors          Show all errors encountered in this session
  :load <file>     Load and execute a .ltl or .ltasm file
  :ast             Dump the AST of the last REPL input
  :ir              Dump the IR of the last REPL input
  :ver             Show version information
  :quit | :q       Exit the REPL

Keyboard shortcuts (readline)
-----------------------------
  ↑ / ↓           Navigate history
  Ctrl-C           Abort current input
  Ctrl-D           Exit REPL
"""


class REPL:
    def __init__(self):
        self._compiler = Compiler(verbose=True)
        self._mode:   str    = "ltl"      # "ltl" | "asm"
        self._target: Target = Target.BYTECODE
        self._session_errors: list = []
        self._history: list = []
        self._last_source: str = ""   # used by :ast / :ir
        self._setup_readline()

    # -- readline setup --------------------------------------------------------

    def _setup_readline(self) -> None:
        if not _HAS_READLINE:
            return
        hist_file = os.path.expanduser("~/.lateralus/repl_history")
        os.makedirs(os.path.dirname(hist_file), exist_ok=True)
        try:
            readline.read_history_file(hist_file)
        except FileNotFoundError:
            pass
        import atexit
        atexit.register(readline.write_history_file, hist_file)
        readline.set_history_length(2000)

    # -- public entry ----------------------------------------------------------

    def run(self) -> None:
        print(_bold(_cyan(_BANNER)))
        while True:
            try:
                source = self._read_input()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not source.strip():
                continue

            if source.strip().startswith(":"):
                self._handle_command(source.strip())
                continue

            self._eval(source)

    # -- input collection ------------------------------------------------------

    def _read_input(self) -> str:
        mode_str = _cyan(f"[{self._mode}]")
        prompt1  = f"{_bold('ltl')} {mode_str} » "
        prompt2  = f"{'···':>12} "

        lines  = []
        depth  = 0   # brace depth for multi-line input

        while True:
            prompt = prompt1 if not lines else prompt2
            try:
                line = input(prompt)
            except KeyboardInterrupt:
                print()
                return ""
            lines.append(line)

            # Track brace depth
            for ch in line:
                if ch == "{": depth += 1
                if ch == "}": depth -= 1

            # Blank line or balanced braces → done
            if depth <= 0 and (not line.strip() or depth == 0):
                break

        return "\n".join(lines)

    # -- command handler -------------------------------------------------------

    def _handle_command(self, cmd: str) -> None:
        parts = cmd.split()
        c = parts[0].lower()

        if c in (":quit", ":q"):
            print("Bye!")
            sys.exit(0)

        elif c == ":help":
            print(_HELP)

        elif c == ":clear":
            os.system("clear" if os.name != "nt" else "cls")

        elif c == ":mode":
            if len(parts) < 2:
                print(_yellow("Usage: :mode ltl | asm"))
                return
            m = parts[1].lower()
            if m in ("ltl", "asm"):
                self._mode = m
                print(_green(f"Mode → {m}"))
            else:
                print(_red(f"Unknown mode: {m}"))

        elif c == ":target":
            if len(parts) < 2:
                print(_yellow("Usage: :target vm | py | check"))
                return
            t = parts[1].lower()
            if t == "vm":
                self._target = Target.BYTECODE
                print(_green("Target → VM"))
            elif t == "py":
                self._target = Target.PYTHON
                print(_green("Target → Python transpilation"))
            elif t == "check":
                self._target = Target.CHECK
                print(_green("Target → check only"))
            else:
                print(_red(f"Unknown target: {t}"))

        elif c == ":reset":
            self._compiler = Compiler(verbose=True)
            self._session_errors.clear()
            print(_green("REPL state reset."))

        elif c == ":errors":
            if not self._session_errors:
                print(_green("No errors in this session."))
            else:
                for ec in self._session_errors:
                    print(ec)

        elif c == ":load":
            if len(parts) < 2:
                print(_yellow("Usage: :load <file>"))
                return
            path = parts[1]
            if not os.path.exists(path):
                print(_red(f"File not found: {path}"))
                return
            result = self._compiler.run_file(path)
            self._print_result(result)

        elif c == ":ast":
            src = self._last_source or "(no input yet)"
            self._dump_ast(src)

        elif c == ":ir":
            src = self._last_source or "(no input yet)"
            self._dump_ir(src)

        elif c == ":ver":
            from . import __version__
            print(_bold(_cyan(f"LATERALUS  v{__version__}")))
            print(_dim("  Lexer · Parser · IR · Bytecode VM · Python/C99 backends"))
            print(_dim("  HM inference · ADTs · pipelines · async · LSP · DAP"))

        else:
            print(_red(f"Unknown command: {c}  (type :help for commands)"))

    # -- eval ----------------------------------------------------

    def _eval(self, source: str) -> None:
        self._last_source = source   # remember for :ast / :ir
        filename = f"<repl:{self._mode}>"
        if self._mode == "asm":
            filename = "<repl:ltasm>"

        target = Target.ASSEMBLE if self._mode == "asm" else self._target

        if target in (Target.BYTECODE, Target.ASSEMBLE):
            result = self._compiler.run_source(source, filename, target)
        else:
            result = self._compiler.compile_source(source, filename, target)

        self._print_result(result)

        # Accumulate errors
        self._session_errors.extend(result.errors)

    def _dump_ast(self, src: str) -> None:
        from .lexer  import LexError
        from .parser import parse, ParseError
        try:
            import pprint
            tree = parse(src, "<repl>")
            print(_dim("-- AST ----------------------------------------------"))
            pprint.pprint(tree, indent=2, width=100)
            print(_dim("-" * 50))
        except (LexError, ParseError) as exc:
            print(_red(str(exc)))

    def _dump_ir(self, src: str) -> None:
        from .lexer   import LexError
        from .parser  import parse, ParseError
        from .ir      import analyze
        try:
            tree = parse(src, "<repl>")
            ir_module, errors = analyze(tree, "<repl>")
            print(_dim("-- IR ----------------------------------------------"))
            for fn in ir_module.functions:
                print(_cyan(f"fn {fn.name}({', '.join(fn.params)}):"))
                for bb in fn.blocks:
                    print(_yellow(f"  [{bb.label}]"))
                    for instr in bb.instrs:
                        print(f"    {instr}")
            print(_dim("-" * 50))
        except (LexError, ParseError) as exc:
            print(_red(str(exc)))

    # -- output ----------------------------------------------------------------

    def _print_result(self, result: CompileResult) -> None:
        if result.ok:
            if result.python_src:
                print(_dim("-- Python output --------------------------"))
                print(result.python_src)
                print(_dim("-------------------------------------------"))
            elif result.exit_code != 0:
                print(_yellow(f"[exit {result.exit_code}]"))
            if result.elapsed_ms > 0:
                print(_dim(f"  ({result.elapsed_ms:.1f}ms)"))
        else:
            reporter = ErrorReporter()
            for ec in result.errors:
                reporter.add(ec)
            reporter.render()


# -----------------------------------------------------------------------------
# Convenience entry
# -----------------------------------------------------------------------------

def start_repl() -> None:
    """Start the interactive REPL."""
    REPL().run()
