"""
lateralus_lang/compiler.py  -  LATERALUS Compiler Pipeline
===========================================================================
Orchestrates the full compilation pipeline:

  .ltl source
       |
       ▼  lexer.py
  Token stream
       |
       ▼  parser.py
  AST (Program)
       |
       ▼  ir.py  (SemanticAnalyzer)
  IRModule  +  semantic errors
       |
       +------------------------+
       ▼ codegen/bytecode.py    ▼ codegen/python.py
  LTasm Bytecode          Python 3 source
       |
       ▼ vm/vm.py
  Execution result

  .ltasm source
       |
       ▼  vm/assembler.py
  LTasm Bytecode
       |
       ▼  vm/vm.py
  Execution result

All errors are collected by ErrorReporter and forwarded to the
ErrorBridge for integration with the Lateralus error_engine.
===========================================================================
"""
from __future__ import annotations

import pathlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from .codegen.bytecode import BytecodeGenError, generate_bytecode
from .codegen.c import CMode, transpile_to_c
from .codegen.python import transpile_to_python
from sysconfig import get_path as _sysconfig_path
from .errors import (
    ErrorContext,
    ErrorReporter,
    Severity,
    get_bridge,
)
from .ir import IRModule, analyze
from .lexer import LexError, lex
from .parser import ParseError, parse
from .vm.assembler import AssemblerError, Bytecode, assemble
from .vm.vm import VM, VMError

# -----------------------------------------------------------------------------
# Compilation target
# -----------------------------------------------------------------------------

class Target(Enum):
    BYTECODE   = auto()   # LTasm Bytecode → VM execution
    PYTHON     = auto()   # Python 3 source transpilation
    C          = auto()   # C99 source transpilation (hosted or freestanding)
    JAVASCRIPT = auto()   # JavaScript ES2022+ transpilation
    WASM       = auto()   # WebAssembly Text Format (.wat) compilation
    ASSEMBLE   = auto()   # .ltasm source → Bytecode → VM
    CHECK      = auto()   # Lex + parse + semantic analysis only (no codegen)
    LLVM       = auto()   # LLVM IR source (.ll) — compile with clang or llc
    X86_64     = auto()   # Native x86_64 NASM assembly (.asm)


# -----------------------------------------------------------------------------
# CompileResult
# -----------------------------------------------------------------------------

@dataclass
class CompileResult:
    ok:          bool
    target:      Target               = Target.CHECK   # default: check only
    source_file: str                  = "<unknown>"
    bytecode:    Optional[Bytecode]   = None
    python_src:  Optional[str]        = None
    c_src:       Optional[str]        = None
    js_src:      Optional[str]        = None
    wasm_src:    Optional[str]        = None
    llvm_src:    Optional[str]        = None
    x86_src:     Optional[str]        = None
    ir_module:   Optional[IRModule]   = None
    exit_code:   int                  = 0
    elapsed_ms:  float                = 0.0
    errors:      List[ErrorContext]   = field(default_factory=list)
    warnings:    List[ErrorContext]   = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok

    def summary(self) -> str:
        status = "✓ OK" if self.ok else "✗ FAILED"
        return (f"{status}  {self.source_file}  "
                f"({self.elapsed_ms:.1f}ms  "
                f"{len(self.errors)} error(s)  {len(self.warnings)} warning(s))")


# -----------------------------------------------------------------------------
# Compiler
# -----------------------------------------------------------------------------

class Compiler:
    """
    Main compiler orchestrator.

    Usage::
        cc = Compiler()
        result = cc.compile_file("hello.ltl", Target.BYTECODE)
        if result:
            result.bytecode.run()   # or: VM(result.bytecode).run()
    """

    def __init__(self, verbose: bool = False, freestanding: bool = False):
        self.verbose = verbose
        self.freestanding = freestanding

    # -- public API ------------------------------------------------------------

    def compile_file(self, path: str,
                     target: Target = Target.BYTECODE) -> CompileResult:
        src = pathlib.Path(path).read_text(encoding="utf-8")
        ext = pathlib.Path(path).suffix.lower()
        if ext == ".ltasm":
            return self._compile_asm(src, path)
        return self._compile_ltl(src, path, target)

    def compile_source(self, source: str, filename: str = "<source>",
                       target: Target = Target.BYTECODE) -> CompileResult:
        if filename.endswith(".ltasm"):
            return self._compile_asm(source, filename)
        return self._compile_ltl(source, filename, target)

    def run_file(self, path: str, target: Target = Target.PYTHON) -> CompileResult:
        result = self.compile_file(path, target)
        if result.ok and target == Target.PYTHON:
            result = self._run_python(result)
        elif result.ok and target in (Target.BYTECODE, Target.ASSEMBLE):
            result = self._run_bytecode(result)
        return result

    def run_source(self, source: str, filename: str = "<source>",
                   target: Target = Target.PYTHON) -> CompileResult:
        result = self.compile_source(source, filename, target)
        if result.ok and target == Target.PYTHON:
            result = self._run_python(result)
        elif result.ok and target in (Target.BYTECODE, Target.ASSEMBLE):
            result = self._run_bytecode(result)
        return result

    # -- .ltl pipeline ---------------------------------------------------------

    def _compile_ltl(self, source: str, filename: str,
                     target: Target) -> CompileResult:
        t0       = time.monotonic()
        reporter = ErrorReporter(source_lines=source.splitlines())
        bridge   = get_bridge(reporter)

        # -- 1. Lex ------------------------------------------------------------
        try:
            tokens = lex(source, filename)
        except LexError as exc:
            ctx = ErrorContext(
                severity    = Severity.FATAL,
                code        = "LexError",
                message     = str(exc),
                file        = filename,
                line        = getattr(exc, "line", 0),
                col         = getattr(exc, "col",  0),
            )
            reporter.add(ctx)
            bridge.submit(ctx)
            return self._failed(reporter, filename, target, t0)

        # -- 2. Parse ----------------------------------------------------------
        try:
            ast = parse(source, filename)
        except ParseError as exc:
            tok = exc.token
            ctx = ErrorContext(
                severity    = Severity.FATAL,
                code        = "ParseError",
                message     = str(exc),
                file        = getattr(tok, "file", filename),
                line        = getattr(tok, "line", 0),
                col         = getattr(tok, "col",  0),
            )
            reporter.add(ctx)
            bridge.submit(ctx)
            return self._failed(reporter, filename, target, t0)

        if target == Target.CHECK:
            return self._success(reporter, filename, target, t0)

        # -- 3. Semantic analysis + IR ------------------------------------------
        ir_module, sem_errors = analyze(ast, filename)
        for se in sem_errors:
            sev = Severity.ERROR if se.level == "error" else Severity.WARNING
            ctx = ErrorContext(
                severity = sev,
                code     = "SemanticError",
                message  = se.message,
                file     = se.span.file if se.span else filename,
                line     = se.span.line if se.span else 0,
                col      = se.span.col  if se.span else 0,
            )
            reporter.add(ctx)
        if reporter.has_errors and any(
                c.severity == Severity.ERROR for c in reporter.all()):
            bridge.submit_all()
            return self._failed(reporter, filename, target, t0, ir_module=ir_module)

        if target == Target.PYTHON:
            try:
                prelude, resolved = self._python_module_prelude(ast, filename)
                py_src = transpile_to_python(ast, skip_imports=resolved)
                if prelude:
                    # future-imports were stripped from inlined modules;
                    # keep exactly one at the top of the combined source.
                    py_src = "\n".join(
                        l for l in py_src.splitlines()
                        if not l.startswith("from __future__"))
                    py_src = ("from __future__ import annotations\n\n"
                              + prelude + py_src)
            except Exception as exc:
                reporter.add_exception(exc, Severity.FATAL)
                return self._failed(reporter, filename, target, t0, ir_module=ir_module)
            elapsed = (time.monotonic() - t0) * 1000
            return CompileResult(ok=True, target=target, source_file=filename,
                                 python_src=py_src, ir_module=ir_module,
                                 elapsed_ms=elapsed,
                                 errors=[], warnings=reporter.all())

        if target == Target.C:
            try:
                c_mode = CMode.FREESTANDING if self.freestanding else CMode.HOSTED
                c_src = transpile_to_c(ast, mode=c_mode)
            except Exception as exc:
                reporter.add_exception(exc, Severity.FATAL)
                return self._failed(reporter, filename, target, t0, ir_module=ir_module)
            elapsed = (time.monotonic() - t0) * 1000
            return CompileResult(ok=True, target=target, source_file=filename,
                                 c_src=c_src, ir_module=ir_module,
                                 elapsed_ms=elapsed,
                                 errors=[], warnings=reporter.all())

        if target == Target.JAVASCRIPT:
            try:
                from .codegen.javascript import transpile_to_js
                js_src = transpile_to_js(source)
            except Exception as exc:
                reporter.add_exception(exc, Severity.FATAL)
                return self._failed(reporter, filename, target, t0, ir_module=ir_module)
            elapsed = (time.monotonic() - t0) * 1000
            return CompileResult(ok=True, target=target, source_file=filename,
                                 js_src=js_src, ir_module=ir_module,
                                 elapsed_ms=elapsed,
                                 errors=[], warnings=reporter.all())

        if target == Target.WASM:
            try:
                from .codegen.wasm import compile_to_wasm
                wasm_mod = compile_to_wasm(source)
                wasm_src = wasm_mod.to_wat()
            except Exception as exc:
                reporter.add_exception(exc, Severity.FATAL)
                return self._failed(reporter, filename, target, t0, ir_module=ir_module)
            elapsed = (time.monotonic() - t0) * 1000
            return CompileResult(ok=True, target=target, source_file=filename,
                                 wasm_src=wasm_src, ir_module=ir_module,
                                 elapsed_ms=elapsed,
                                 errors=[], warnings=reporter.all())

        if target == Target.LLVM:
            try:
                from .codegen.llvm import transpile_to_llvm
                llvm_src = transpile_to_llvm(ast, source_file=filename)
            except Exception as exc:
                reporter.add_exception(exc, Severity.FATAL)
                return self._failed(reporter, filename, target, t0, ir_module=ir_module)
            elapsed = (time.monotonic() - t0) * 1000
            return CompileResult(ok=True, target=target, source_file=filename,
                                 llvm_src=llvm_src, ir_module=ir_module,
                                 elapsed_ms=elapsed,
                                 errors=[], warnings=reporter.all())

        if target == Target.X86_64:
            try:
                from .codegen.x86_64 import transpile_to_x86_64
                x86_src = transpile_to_x86_64(ast, source_file=filename)
            except Exception as exc:
                reporter.add_exception(exc, Severity.FATAL)
                return self._failed(reporter, filename, target, t0, ir_module=ir_module)
            elapsed = (time.monotonic() - t0) * 1000
            return CompileResult(ok=True, target=target, source_file=filename,
                                 x86_src=x86_src, ir_module=ir_module,
                                 elapsed_ms=elapsed,
                                 errors=[], warnings=reporter.all())

        # -- 4. Bytecode generation ---------------------------------------------
        try:
            bc = generate_bytecode(ir_module)
        except BytecodeGenError as exc:
            ctx = ErrorContext(severity=Severity.FATAL, code="CodegenError",
                               message=str(exc), file=filename)
            reporter.add(ctx)
            bridge.submit(ctx)
            return self._failed(reporter, filename, target, t0, ir_module=ir_module)

        elapsed = (time.monotonic() - t0) * 1000
        return CompileResult(ok=True, target=target, source_file=filename,
                             bytecode=bc, ir_module=ir_module,
                             elapsed_ms=elapsed,
                             errors=[], warnings=reporter.all())

    # -- .ltasm pipeline -------------------------------------------------------

    def _compile_asm(self, source: str, filename: str) -> CompileResult:
        t0       = time.monotonic()
        reporter = ErrorReporter(source_lines=source.splitlines())
        bridge   = get_bridge(reporter)
        try:
            bc = assemble(source, filename)
        except AssemblerError as exc:
            ctx = ErrorContext(severity=Severity.FATAL, code="AssemblerError",
                               message=str(exc), file=filename,
                               line=getattr(exc, "line", 0))
            reporter.add(ctx)
            bridge.submit(ctx)
            return self._failed(reporter, filename, Target.ASSEMBLE, t0)
        elapsed = (time.monotonic() - t0) * 1000
        return CompileResult(ok=True, target=Target.ASSEMBLE,
                             source_file=filename, bytecode=bc,
                             elapsed_ms=elapsed)

    # -- .ltl module inlining (Python target) ---------------------------------

    _MODULE_NODES = ()  # filled lazily in _rename_module_symbols

    def _ltl_module_candidates(self, path: str, filename: str):
        """Yield candidate .ltl files for an import path."""
        rel = path.replace(".", "/") + ".ltl"
        src_dir = pathlib.Path(filename).resolve().parent
        candidates = [
            src_dir / rel,
            pathlib.Path(__file__).resolve().parents[1] / "stdlib" / rel,
            pathlib.Path(_sysconfig_path("data")) / "lateralus" / "stdlib" / rel,
        ]
        for c in candidates:
            if c.is_file():
                yield c

    def _python_module_prelude(self, ast, filename: str, _depth: int = 0):
        """Resolve `import x` / `from x import a` to .ltl module files,
        transpile them inline (functions prefixed `<mod>_`), and return
        (prelude_source, resolved_import_paths)."""
        import dataclasses
        from .ast_nodes import (AsyncForStmt, BindingPattern, ComprehensionExpr,
                                 FnDecl, ForStmt, Ident, LetDecl, Param,
                                 RecoverClause)
        from .codegen.python import transpile_to_python as _tp
        _PY_KEYWORDS = frozenset({
            "False", "None", "True", "and", "as", "assert", "async",
            "await", "break", "class", "continue", "def", "del", "elif",
            "else", "except", "finally", "for", "from", "global", "if",
            "import", "in", "is", "lambda", "nonlocal", "not", "or",
            "pass", "raise", "return", "try", "while", "with", "yield",
        })
        from .parser import parse

        RENAME_TYPES = (Ident, FnDecl, LetDecl, Param, ForStmt,
                        ComprehensionExpr, AsyncForStmt, RecoverClause,
                        BindingPattern)

        def rename_syms(node, fn_names, prefix):
            stack = [node]
            while stack:
                n = stack.pop()
                if not dataclasses.is_dataclass(n) or isinstance(n, type):
                    continue
                for f in dataclasses.fields(n):
                    v = getattr(n, f.name)
                    if (f.name in ("name", "var", "binding")
                            and isinstance(v, str) and v in fn_names
                            and isinstance(n, RENAME_TYPES)):
                        setattr(n, f.name, prefix + v)
                    elif dataclasses.is_dataclass(v) and not isinstance(v, type):
                        stack.append(v)
                    elif isinstance(v, (list, tuple)):
                        stack.extend(x for x in v
                                     if dataclasses.is_dataclass(x)
                                     and not isinstance(x, type))

        prelude_parts = []
        resolved = set()
        visited = set()

        def process_program(program_ast, prog_filename, depth):
            nonlocal prelude_parts
            if depth > 6:
                return
            for imp in getattr(program_ast, "imports", []) or []:
                path = imp.path
                if path in visited:
                    continue
                mod_file = next(self._ltl_module_candidates(path, prog_filename), None)
                if mod_file is None:
                    continue
                try:
                    msrc = mod_file.read_text(encoding="utf-8")
                    mast = parse(msrc, str(mod_file))
                except Exception:
                    continue
                prefix = path.replace(".", "_") + "_"
                # Recurse into the module's own imports first
                sub_prelude, sub_resolved = self._python_module_prelude(
                    mast, str(mod_file), depth + 1)
                prelude_parts.append(sub_prelude)
                fn_names = [st.name for st in getattr(mast, "body", [])
                            if isinstance(st, FnDecl)]
                if fn_names:
                    rename_syms(mast, set(fn_names), prefix)
                try:
                    mod_py = _tp(mast, skip_imports=sub_resolved)
                    # `from __future__` must be the first statement — the
                    # prelude is prepended, so strip it here and emit one
                    # copy at the top of the combined source.
                    mod_py = "\n".join(
                        l for l in mod_py.splitlines()
                        if not l.startswith("from __future__"))
                    compile(mod_py, str(mod_file), "exec")
                except Exception:
                    continue
                prelude_parts.append(mod_py)
                resolved.add(path)
                visited.add(path)
                # Namespace object for qualified access: mod.fn(...)
                alias = imp.alias or path.split(".")[-1]
                exports = ", ".join(
                    f"{n}={prefix}{n}" for n in fn_names)
                segs = path.split(".")
                if len(segs) == 1:
                    prelude_parts.append(
                        f"{alias} = _LTL_NS({exports})")
                else:
                    # build nested: a = _LTL_NS(b=_LTL_NS(fns))
                    expr = f"_LTL_NS({exports})"
                    for seg in reversed(segs[:-1]):
                        expr = f"_LTL_NS({seg}={expr})"
                    prelude_parts.append(f"{alias} = {expr}")
                # from X import a, b → a = x_a
                for item in (imp.items or []):
                    safe_item = item + "_" if item in _PY_KEYWORDS else item
                    prelude_parts.append(f"{safe_item} = {prefix}{item}")

        process_program(ast, filename, _depth)
        if not prelude_parts:
            return "", resolved
        return ("from types import SimpleNamespace as _LTL_NS\n\n"
                + "\n\n".join(prelude_parts) + "\n\n"), resolved

    # -- Python execution (transpile → exec) -----------------------------------

    def _run_python(self, result: CompileResult) -> CompileResult:
        """Transpile to Python source and exec it in-process."""
        import subprocess as _sp
        import sys as _sys
        import tempfile
        src = result.python_src
        if not src:
            result.ok = False
            result.errors.append(ErrorContext(
                severity=Severity.FATAL, code="RunError",
                message="No Python source produced by transpiler",
                file=result.source_file,
            ))
            return result
        # Write to a temp file and run via subprocess so print() goes to stdout
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                         delete=False, encoding="utf-8") as f:
            f.write(src)
            tmp_path = f.name
        try:
            proc = _sp.run(
                [_sys.executable, tmp_path],
                timeout=60,
            )
            result.exit_code = proc.returncode
            if proc.returncode != 0:
                result.ok = False
        except _sp.TimeoutExpired:
            result.ok = False
            result.errors.append(ErrorContext(
                severity=Severity.ERROR, code="TimeoutError",
                message="Script execution timed out (60s)",
                file=result.source_file,
            ))
        except Exception as exc:
            result.ok = False
            result.errors.append(ErrorContext(
                severity=Severity.ERROR, code="RunError",
                message=str(exc), file=result.source_file,
            ))
        finally:
            import os as _os
            try:
                _os.unlink(tmp_path)
            except OSError:
                pass
        return result

    # -- VM execution ----------------------------------------------------------

    def _run_bytecode(self, result: CompileResult) -> CompileResult:
        reporter = ErrorReporter()
        bridge   = get_bridge(reporter)
        try:
            vm = VM(result.bytecode)
            exit_code = vm.run()
            result.exit_code = exit_code
        except VMError as exc:
            ctx = ErrorContext(
                severity = Severity.ERROR,
                code     = type(exc).__name__,
                message  = str(exc),
                file     = result.source_file,
                notes    = [f"VM pc={exc.pc}  op={exc.op}"],
            )
            reporter.add(ctx)
            bridge.submit(ctx)
            # Attempt self-healing lookup
            heal = bridge.check_heal(type(exc).__name__, ctx)
            if heal:
                ctx.notes.append(f"Suggested healing: {heal}")
            if self.verbose:
                reporter.render()
            result.ok       = False
            result.errors   = reporter.all()
        except SystemExit as exc:
            result.exit_code = int(exc.code or 0)
        return result

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _failed(reporter: ErrorReporter, filename: str, target: Target,
                t0: float, ir_module: Optional[IRModule] = None) -> CompileResult:
        elapsed = (time.monotonic() - t0) * 1000
        errs  = [c for c in reporter.all()
                 if c.severity in (Severity.FATAL, Severity.ERROR)]
        warns = [c for c in reporter.all() if c.severity == Severity.WARNING]
        return CompileResult(ok=False, target=target, source_file=filename,
                             ir_module=ir_module, elapsed_ms=elapsed,
                             errors=errs, warnings=warns)

    @staticmethod
    def _success(reporter: ErrorReporter, filename: str, target: Target,
                 t0: float) -> CompileResult:
        elapsed = (time.monotonic() - t0) * 1000
        warns = [c for c in reporter.all() if c.severity == Severity.WARNING]
        return CompileResult(ok=True, target=target, source_file=filename,
                             elapsed_ms=elapsed, warnings=warns)


# -----------------------------------------------------------------------------
# Module-level convenience
# -----------------------------------------------------------------------------

_default_compiler: Optional[Compiler] = None


def get_compiler(verbose: bool = False) -> Compiler:
    global _default_compiler
    if _default_compiler is None:
        _default_compiler = Compiler(verbose=verbose)
    return _default_compiler


def compile_file(path: str, target: Target = Target.BYTECODE) -> CompileResult:
    return get_compiler().compile_file(path, target)


def compile_source(source: str, filename: str = "<source>",
                   target: Target = Target.BYTECODE) -> CompileResult:
    return get_compiler().compile_source(source, filename, target)


def run_file(path: str) -> CompileResult:
    return get_compiler().run_file(path)


def run_source(source: str, filename: str = "<source>") -> CompileResult:
    return get_compiler().run_source(source, filename)
