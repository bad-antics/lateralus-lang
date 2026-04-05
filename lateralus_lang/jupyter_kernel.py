"""
lateralus_lang/jupyter_kernel.py
=============================================================================
LATERALUS v1.9 — Jupyter Kernel

A full Jupyter kernel for LATERALUS, enabling interactive notebooks with:
  • Code execution (transpile → Python → exec)
  • Syntax error reporting with rich diagnostics
  • Tab completion for keywords and builtins
  • Inspection (hover-style info for functions)
  • Kernel info and banner

Install:
    python -m lateralus_lang jupyter install

Then select "LATERALUS" from the Jupyter kernel list.

Requires: ipykernel (optional dependency)
=============================================================================
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Kernel specification (no ipykernel dependency needed)
# -----------------------------------------------------------------------------

KERNEL_NAME = "lateralus"
KERNEL_DISPLAY_NAME = "LATERALUS"
KERNEL_LANGUAGE = "lateralus"
KERNEL_MIMETYPE = "text/x-lateralus"
KERNEL_FILE_EXT = ".ltl"
KERNEL_CODEMIRROR = "rust"   # closest syntax highlighting mode

KERNEL_SPEC = {
    "argv": [sys.executable, "-m", "lateralus_lang.jupyter_kernel", "-f", "{connection_file}"],
    "display_name": KERNEL_DISPLAY_NAME,
    "language": KERNEL_LANGUAGE,
    "metadata": {
        "debugger": False,
    },
}

LATERALUS_KEYWORDS = [
    "fn", "let", "mut", "const", "return", "if", "else", "elif",
    "while", "for", "in", "loop", "break", "continue", "match",
    "struct", "enum", "impl", "trait", "pub", "import", "from",
    "try", "recover", "ensure", "throw", "yield", "spawn",
    "async", "await", "nursery", "select", "channel", "cancel",
    "macro", "comptime", "derive", "reflect", "foreign",
    "type", "guard", "where", "module", "pass",
    "true", "false", "nil", "self",
    "emit", "probe", "measure",
]

LATERALUS_BUILTINS = [
    "println", "print", "len", "str", "int", "float", "bool",
    "range", "map", "filter", "reduce", "sort", "reverse",
    "keys", "values", "zip", "enumerate", "sum", "min", "max",
    "abs", "sqrt", "pow", "log", "sin", "cos", "tan",
    "push", "pop", "append", "insert", "remove", "contains",
    "split", "join", "trim", "upper", "lower", "replace",
    "sha256", "blake2b", "hmac_sha256", "base64_encode",
    "fft", "solve_ode", "mean", "variance", "correlation",
    "Result", "Option", "Some", "None", "Ok", "Err",
]


# -----------------------------------------------------------------------------
# Kernel installation
# -----------------------------------------------------------------------------

def install_kernel(user: bool = True) -> str:
    """Install the LATERALUS Jupyter kernel spec.

    Returns the installation path.
    """
    try:
        from jupyter_client.kernelspec import KernelSpecManager
    except ImportError:
        # Fallback: manual installation
        return _install_kernel_manual(user)

    ksm = KernelSpecManager()

    # Create a temp directory with kernel.json
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        kernel_json = Path(td) / "kernel.json"
        kernel_json.write_text(json.dumps(KERNEL_SPEC, indent=2))

        # Write a simple logo (text-based)
        logo_path = Path(td) / "logo-64x64.png"
        # Skip logo for now — Jupyter works without it

        dest = ksm.install_kernel_spec(
            str(td),
            kernel_name=KERNEL_NAME,
            user=user,
        )
    return dest


def _install_kernel_manual(user: bool) -> str:
    """Manual kernel spec installation without jupyter_client."""
    if user:
        base = Path.home() / ".local" / "share" / "jupyter" / "kernels"
    else:
        base = Path("/usr/local/share/jupyter/kernels")

    dest = base / KERNEL_NAME
    dest.mkdir(parents=True, exist_ok=True)

    (dest / "kernel.json").write_text(json.dumps(KERNEL_SPEC, indent=2))
    return str(dest)


# -----------------------------------------------------------------------------
# Kernel implementation
# -----------------------------------------------------------------------------

class LateralusKernel:
    """LATERALUS Jupyter kernel.

    If ipykernel is available, subclass its Kernel. Otherwise, provide
    a standalone implementation that speaks the Jupyter wire protocol.
    """

    implementation = "lateralus"
    implementation_version = "1.9.0"
    language_info = {
        "name": KERNEL_LANGUAGE,
        "version": "1.9.0",
        "mimetype": KERNEL_MIMETYPE,
        "file_extension": KERNEL_FILE_EXT,
        "codemirror_mode": KERNEL_CODEMIRROR,
    }
    banner = (
        "LATERALUS v1.9.0 — Jupyter Kernel\n"
        "Pipeline-driven. Type-safe. Mathematically elegant.\n"
        "Type LATERALUS code and press Shift+Enter to execute."
    )

    def __init__(self):
        self._exec_count = 0
        self._namespace: Dict[str, Any] = {}
        self._compiler = None

    def _get_compiler(self):
        if self._compiler is None:
            from .compiler import Compiler
            self._compiler = Compiler()
        return self._compiler

    def do_execute(self, code: str, silent: bool = False,
                   store_history: bool = True,
                   user_expressions: Optional[dict] = None,
                   allow_stdin: bool = False) -> dict:
        """Execute a cell of LATERALUS code."""
        self._exec_count += 1

        if not code.strip():
            return self._ok_reply()

        from .compiler import Target

        try:
            compiler = self._get_compiler()
            result = compiler.compile_source(
                code,
                filename=f"<cell_{self._exec_count}>",
                target=Target.PYTHON,
            )

            if not result.ok:
                error_text = "\n".join(
                    f"  {e.line}:{e.col} {e.message}" for e in result.errors
                )
                return self._error_reply(
                    "CompileError",
                    f"Compilation failed:\n{error_text}",
                    [error_text],
                )

            # Execute the transpiled Python
            import io
            from contextlib import redirect_stdout, redirect_stderr

            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()

            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    exec(result.python_src, self._namespace)
            except Exception as exc:
                tb = traceback.format_exc()
                return self._error_reply(
                    type(exc).__name__,
                    str(exc),
                    tb.splitlines(),
                )

            stdout_text = stdout_buf.getvalue()
            stderr_text = stderr_buf.getvalue()

            if stdout_text and not silent:
                self._send_stream("stdout", stdout_text)
            if stderr_text and not silent:
                self._send_stream("stderr", stderr_text)

            return self._ok_reply()

        except Exception as exc:
            tb = traceback.format_exc()
            return self._error_reply(
                type(exc).__name__,
                str(exc),
                tb.splitlines(),
            )

    def do_complete(self, code: str, cursor_pos: int) -> dict:
        """Provide tab completion."""
        # Extract the word being completed
        text = code[:cursor_pos]
        # Find last word boundary
        start = cursor_pos
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == '_'):
            start -= 1
        prefix = text[start:cursor_pos]

        if not prefix:
            return {
                "status": "ok",
                "matches": [],
                "cursor_start": cursor_pos,
                "cursor_end": cursor_pos,
            }

        matches = []
        for kw in LATERALUS_KEYWORDS:
            if kw.startswith(prefix):
                matches.append(kw)
        for bi in LATERALUS_BUILTINS:
            if bi.startswith(prefix):
                matches.append(bi)
        # Also search the namespace
        for name in self._namespace:
            if name.startswith(prefix) and not name.startswith("_"):
                matches.append(name)

        return {
            "status": "ok",
            "matches": sorted(set(matches)),
            "cursor_start": start,
            "cursor_end": cursor_pos,
        }

    def do_inspect(self, code: str, cursor_pos: int,
                   detail_level: int = 0) -> dict:
        """Provide hover/inspection info."""
        # Extract word at cursor
        text = code[:cursor_pos]
        start = cursor_pos
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == '_'):
            start -= 1
        word = text[start:cursor_pos]

        info = None
        if word in LATERALUS_KEYWORDS:
            info = f"**{word}** — LATERALUS keyword"
        elif word in LATERALUS_BUILTINS:
            info = f"**{word}** — LATERALUS built-in function"
        elif word in self._namespace:
            obj = self._namespace[word]
            info = f"**{word}** : {type(obj).__name__} = {repr(obj)[:200]}"

        if info:
            return {
                "status": "ok",
                "found": True,
                "data": {"text/plain": info},
            }
        return {"status": "ok", "found": False, "data": {}}

    def do_is_complete(self, code: str) -> dict:
        """Check if a code cell is syntactically complete."""
        stripped = code.strip()
        if not stripped:
            return {"status": "incomplete", "indent": ""}

        # Quick heuristic: unbalanced braces
        if stripped.count("{") > stripped.count("}"):
            return {"status": "incomplete", "indent": "    "}
        if stripped.count("(") > stripped.count(")"):
            return {"status": "incomplete", "indent": "    "}

        return {"status": "complete"}

    # -- Helper methods ----------------------------------------------------

    def _ok_reply(self) -> dict:
        return {
            "status": "ok",
            "execution_count": self._exec_count,
            "payload": [],
            "user_expressions": {},
        }

    def _error_reply(self, ename: str, evalue: str,
                     traceback_lines: List[str]) -> dict:
        return {
            "status": "error",
            "execution_count": self._exec_count,
            "ename": ename,
            "evalue": evalue,
            "traceback": traceback_lines,
        }

    def _send_stream(self, name: str, text: str) -> None:
        """Send stream output. In full ipykernel, this uses send_response."""
        # When running under ipykernel, this is overridden
        if name == "stdout":
            sys.stdout.write(text)
        else:
            sys.stderr.write(text)


# -----------------------------------------------------------------------------
# ipykernel integration (if available)
# -----------------------------------------------------------------------------

_IpykernelKernel = None

try:
    from ipykernel.kernelbase import Kernel as _IpykernelKernel
except ImportError:
    pass


def _make_ipykernel_class():
    """Dynamically create an ipykernel-compatible kernel class."""
    if _IpykernelKernel is None:
        return None

    class LateralusIPyKernel(_IpykernelKernel):
        implementation = LateralusKernel.implementation
        implementation_version = LateralusKernel.implementation_version
        language_info = LateralusKernel.language_info
        banner = LateralusKernel.banner

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._ltl = LateralusKernel()

        def do_execute(self, code, silent, store_history=True,
                       user_expressions=None, allow_stdin=False):
            reply = self._ltl.do_execute(
                code, silent, store_history, user_expressions, allow_stdin
            )

            if reply["status"] == "error":
                self.send_response(self.iopub_socket, "error", {
                    "ename": reply["ename"],
                    "evalue": reply["evalue"],
                    "traceback": reply["traceback"],
                })
            else:
                # Check if there was stdout
                import io
                from contextlib import redirect_stdout, redirect_stderr
                stdout_buf = io.StringIO()
                stderr_buf = io.StringIO()

                from .compiler import Compiler, Target
                compiler = self._ltl._get_compiler()
                result = compiler.compile_source(code, target=Target.PYTHON)

                if result.ok and result.python_src:
                    try:
                        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                            exec(result.python_src, self._ltl._namespace)
                    except Exception:
                        pass

                    out = stdout_buf.getvalue()
                    if out and not silent:
                        self.send_response(self.iopub_socket, "stream", {
                            "name": "stdout",
                            "text": out,
                        })

            return reply

        def do_complete(self, code, cursor_pos):
            return self._ltl.do_complete(code, cursor_pos)

        def do_inspect(self, code, cursor_pos, detail_level=0, omit_sections=()):
            return self._ltl.do_inspect(code, cursor_pos, detail_level)

        def do_is_complete(self, code):
            return self._ltl.do_is_complete(code)

    return LateralusIPyKernel


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main():
    """Entry point: either install kernel or start it."""
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        user_flag = "--user" in sys.argv or "--system" not in sys.argv
        dest = install_kernel(user=user_flag)
        print(f"✓ LATERALUS Jupyter kernel installed → {dest}")
        return

    # Start the kernel
    IPyKernelClass = _make_ipykernel_class()
    if IPyKernelClass is not None:
        from ipykernel.kernelapp import IPKernelApp
        IPKernelApp.launch_instance(kernel_class=IPyKernelClass)
    else:
        print("ipykernel is required to run the LATERALUS Jupyter kernel.")
        print("Install it: pip install ipykernel")
        print("Or install the kernel spec: python -m lateralus_lang jupyter install")
        sys.exit(1)


if __name__ == "__main__":
    main()
