"""lateralus_lang/codegen/__init__.py"""
from .bytecode import BytecodeGenerator, BytecodeGenError, generate_bytecode
from .c import CMode, CTranspiler, transpile_to_c
from .javascript import JavaScriptTranspiler, transpile_to_js
from .python import PythonTranspiler, transpile_to_python
from .wasm import WasmCompiler, WasmModule, compile_to_wasm

__all__ = [
    "BytecodeGenerator", "BytecodeGenError", "generate_bytecode",
    "PythonTranspiler",  "transpile_to_python",
    "CTranspiler",       "CMode", "transpile_to_c",
    "JavaScriptTranspiler", "transpile_to_js",
    "WasmCompiler", "WasmModule", "compile_to_wasm",
]

# Optional backends — only available when their dependencies are installed
try:
    from .llvm import LLVMTranspiler, transpile_to_llvm
    __all__ += ["LLVMTranspiler", "transpile_to_llvm"]
except ImportError:
    pass

try:
    from .x86_64 import X86_64Transpiler, transpile_to_x86_64
    __all__ += ["X86_64Transpiler", "transpile_to_x86_64"]
except ImportError:
    pass
