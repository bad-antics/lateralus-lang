"""
lateralus_lang  -  LATERALUS Proprietary Language Toolkit
==============================================================
Exports the primary public API.
"""
from .compiler import (
    Compiler, CompileResult, Target,
    get_compiler, compile_file, compile_source, run_file, run_source,
)
from .lexer    import lex, Token, TK, LexError
from .parser   import parse, ParseError
from .ir       import analyze, IRModule
from .repl     import start_repl, REPL
from .vm       import VM, VMError, Bytecode, assemble
from .codegen  import generate_bytecode, transpile_to_python
from .errors   import (
    LTLError, ErrorContext, ErrorReporter, Severity,
    get_bridge, ErrorBridge,
)

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
