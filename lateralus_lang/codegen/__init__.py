"""lateralus_lang/codegen/__init__.py"""
from .bytecode   import BytecodeGenerator, BytecodeGenError, generate_bytecode
from .python     import PythonTranspiler, transpile_to_python
from .c          import CTranspiler, CMode, transpile_to_c
from .javascript import JavaScriptTranspiler, transpile_to_js
from .wasm       import WasmCompiler, WasmModule, compile_to_wasm
from .llvm       import LLVMTranspiler, transpile_to_llvm
from .x86_64     import X86_64Transpiler, transpile_to_x86_64

__all__ = [
    "BytecodeGenerator", "BytecodeGenError", "generate_bytecode",
    "PythonTranspiler",  "transpile_to_python",
    "CTranspiler",       "CMode", "transpile_to_c",
    "JavaScriptTranspiler", "transpile_to_js",
    "WasmCompiler", "WasmModule", "compile_to_wasm",
    "LLVMTranspiler", "transpile_to_llvm",
    "X86_64Transpiler", "transpile_to_x86_64",
]
