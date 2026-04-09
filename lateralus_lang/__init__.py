"""
lateralus_lang  -  LATERALUS Proprietary Language Toolkit
==============================================================
Exports the primary public API.
"""
from .codegen import generate_bytecode, transpile_to_python
from .compiler import (
    Compiler,
    CompileResult,
    Target,
    compile_file,
    compile_source,
    get_compiler,
    run_file,
    run_source,
)
from .errors import (
    ErrorBridge,
    ErrorContext,
    ErrorReporter,
    LTLError,
    Severity,
    get_bridge,
)
from .ir import IRModule, analyze
from .lexer import TK, LexError, Token, lex
from .parser import ParseError, parse
from .repl import REPL, start_repl
from .vm import VM, Bytecode, VMError, assemble

__version__ = "3.0.0"
__author__  = "bad-antics"

__all__ = [
    # Compiler
    "Compiler", "CompileResult", "Target",
    "get_compiler", "compile_file", "compile_source",
    "run_file", "run_source",
    # Lexer / Parser
    "lex", "Token", "TK", "LexError",
    "parse", "ParseError",
    # IR
    "analyze", "IRModule",
    # REPL
    "start_repl", "REPL",
    # VM
    "VM", "VMError", "Bytecode", "assemble",
    # Codegen
    "generate_bytecode", "transpile_to_python",
    # Errors
    "LTLError", "ErrorContext", "ErrorReporter", "Severity",
    "get_bridge", "ErrorBridge",
    # Meta
    "__version__",
]
