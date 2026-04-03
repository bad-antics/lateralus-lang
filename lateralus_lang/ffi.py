"""
lateralus_lang/ffi.py
═════════════════════════════════════════════════════════════════════════════
LATERALUS v1.9 — C Foreign Function Interface (FFI) Runtime Bridge

Provides runtime support for calling native C functions from LATERALUS
programs via Python's ctypes. Handles:
  • Loading shared libraries (.so, .dylib, .dll)
  • Declaring function signatures (parameter types, return types)
  • Type mapping between LATERALUS types and C types
  • Struct layout for passing/receiving structured data
  • Automatic pointer management and memory safety wrappers

Usage from LATERALUS source::

    @foreign("c")
    fn abs(x: int) -> int

    // With library specification:
    @foreign("c", lib="libm.so.6")
    fn sin(x: float) -> float

    // FFI struct
    @foreign("c")
    struct Point { x: float, y: float }

The Python transpiler emits calls to this module for @foreign("c") decls.
═════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Type mapping: LATERALUS type name → ctypes type
# ─────────────────────────────────────────────────────────────────────────────

LTL_TO_CTYPE = {
    "int":     ctypes.c_int64,
    "i8":      ctypes.c_int8,
    "i16":     ctypes.c_int16,
    "i32":     ctypes.c_int32,
    "i64":     ctypes.c_int64,
    "u8":      ctypes.c_uint8,
    "u16":     ctypes.c_uint16,
    "u32":     ctypes.c_uint32,
    "u64":     ctypes.c_uint64,
    "float":   ctypes.c_double,
    "f32":     ctypes.c_float,
    "f64":     ctypes.c_double,
    "bool":    ctypes.c_bool,
    "str":     ctypes.c_char_p,
    "ptr":     ctypes.c_void_p,
    "void":    None,
    "nil":     None,
}


def _resolve_ctype(ltl_type: str) -> Any:
    """Map a LATERALUS type name to a ctypes type."""
    # Handle pointer types: ptr[int] → POINTER(c_int64)
    if ltl_type.startswith("ptr[") and ltl_type.endswith("]"):
        inner = ltl_type[4:-1]
        inner_ct = _resolve_ctype(inner)
        if inner_ct is None:
            return ctypes.c_void_p
        return ctypes.POINTER(inner_ct)

    # Handle array types: [int; N] or list[int] → POINTER
    if ltl_type.startswith("[") or ltl_type.startswith("list["):
        return ctypes.c_void_p

    return LTL_TO_CTYPE.get(ltl_type, ctypes.c_void_p)


# ─────────────────────────────────────────────────────────────────────────────
# Library loader (cached)
# ─────────────────────────────────────────────────────────────────────────────

_lib_cache: Dict[str, ctypes.CDLL] = {}


def load_library(name: str) -> ctypes.CDLL:
    """Load a shared library by name or path.

    Searches in order:
      1. Exact path (if exists)
      2. ctypes.util.find_library (standard search paths)
      3. Common directories (/usr/lib, /usr/local/lib, etc.)

    Raises FileNotFoundError if not found.
    """
    if name in _lib_cache:
        return _lib_cache[name]

    lib = None

    # 1. Exact path
    if os.path.isfile(name):
        lib = ctypes.CDLL(name)
    else:
        # 2. ctypes.util search
        found = ctypes.util.find_library(name.replace("lib", "").split(".")[0])
        if found:
            try:
                lib = ctypes.CDLL(found)
            except OSError:
                pass

        # 3. Direct load attempt (system linker search)
        if lib is None:
            try:
                lib = ctypes.CDLL(name)
            except OSError:
                pass

        # 4. Common library directories
        if lib is None:
            search_dirs = [
                "/usr/lib", "/usr/local/lib",
                "/usr/lib/x86_64-linux-gnu",
                "/usr/lib64",
            ]
            for d in search_dirs:
                candidate = os.path.join(d, name)
                if os.path.isfile(candidate):
                    try:
                        lib = ctypes.CDLL(candidate)
                        break
                    except OSError:
                        continue

    if lib is None:
        raise FileNotFoundError(
            f"FFI: Cannot find shared library '{name}'. "
            f"Searched: exact path, LD_LIBRARY_PATH, and system dirs."
        )

    _lib_cache[name] = lib
    return lib


# Pre-load libc and libm for common use
_libc: Optional[ctypes.CDLL] = None
_libm: Optional[ctypes.CDLL] = None


def _get_libc() -> ctypes.CDLL:
    global _libc
    if _libc is None:
        found = ctypes.util.find_library("c")
        _libc = ctypes.CDLL(found or "libc.so.6")
    return _libc


def _get_libm() -> ctypes.CDLL:
    global _libm
    if _libm is None:
        found = ctypes.util.find_library("m")
        _libm = ctypes.CDLL(found or "libm.so.6")
    return _libm


# ─────────────────────────────────────────────────────────────────────────────
# FFI Function declaration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FFIFunction:
    """A declared foreign C function binding."""
    name:        str
    lib_name:    str                       # library name or path
    param_types: List[str]                 # LATERALUS type names
    return_type: str                       # LATERALUS return type name
    c_name:      Optional[str] = None      # override C symbol name
    _func:       Optional[Callable] = field(default=None, repr=False)

    @property
    def symbol(self) -> str:
        return self.c_name or self.name

    def bind(self) -> Callable:
        """Bind the ctypes function pointer. Called lazily on first call."""
        if self._func is not None:
            return self._func

        # Resolve library
        if self.lib_name in ("libc", "c"):
            lib = _get_libc()
        elif self.lib_name in ("libm", "m", "math"):
            lib = _get_libm()
        else:
            lib = load_library(self.lib_name)

        # Get function pointer
        try:
            cfunc = getattr(lib, self.symbol)
        except AttributeError:
            raise AttributeError(
                f"FFI: Symbol '{self.symbol}' not found in '{self.lib_name}'"
            )

        # Set argument types
        argtypes = []
        for pt in self.param_types:
            ct = _resolve_ctype(pt)
            if ct is not None:
                argtypes.append(ct)
        cfunc.argtypes = argtypes

        # Set return type
        ret_ct = _resolve_ctype(self.return_type)
        cfunc.restype = ret_ct

        self._func = cfunc
        return cfunc

    def __call__(self, *args: Any) -> Any:
        """Call the foreign function with automatic type coercion."""
        func = self.bind()

        # Coerce string arguments to bytes for c_char_p
        coerced = []
        for i, arg in enumerate(args):
            if i < len(self.param_types) and self.param_types[i] == "str":
                if isinstance(arg, str):
                    arg = arg.encode("utf-8")
            coerced.append(arg)

        result = func(*coerced)

        # Coerce bytes result back to str
        if self.return_type == "str" and isinstance(result, bytes):
            return result.decode("utf-8", errors="replace")

        return result


# ─────────────────────────────────────────────────────────────────────────────
# FFI Struct definition
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FFIStructField:
    """A single field in an FFI struct."""
    name: str
    type_name: str


def define_ffi_struct(name: str, fields: List[Tuple[str, str]]) -> type:
    """Create a ctypes.Structure subclass from LATERALUS field definitions.

    Args:
        name:   The struct name.
        fields: List of (field_name, lateralus_type) tuples.

    Returns:
        A ctypes.Structure subclass that can be instantiated and
        passed to/from C functions.
    """
    cfields = []
    for fname, ftype in fields:
        ct = _resolve_ctype(ftype)
        if ct is None:
            ct = ctypes.c_void_p
        cfields.append((fname, ct))

    struct_cls = type(name, (ctypes.Structure,), {"_fields_": cfields})
    return struct_cls


# ─────────────────────────────────────────────────────────────────────────────
# FFI Registry — global function/struct table
# ─────────────────────────────────────────────────────────────────────────────

class FFIRegistry:
    """Central registry for all declared FFI bindings in a program."""

    def __init__(self):
        self.functions: Dict[str, FFIFunction] = {}
        self.structs:   Dict[str, type]        = {}
        self._libs:     Dict[str, ctypes.CDLL] = {}

    def declare_function(self, name: str, param_types: List[str],
                         return_type: str = "void",
                         lib: str = "libc",
                         c_name: Optional[str] = None) -> FFIFunction:
        """Declare and register an FFI function."""
        ffi_fn = FFIFunction(
            name=name, lib_name=lib,
            param_types=param_types, return_type=return_type,
            c_name=c_name,
        )
        self.functions[name] = ffi_fn
        return ffi_fn

    def declare_struct(self, name: str,
                       fields: List[Tuple[str, str]]) -> type:
        """Declare and register an FFI struct."""
        cls = define_ffi_struct(name, fields)
        self.structs[name] = cls
        return cls

    def call(self, name: str, *args: Any) -> Any:
        """Call a registered FFI function by name."""
        if name not in self.functions:
            raise NameError(f"FFI: No foreign function '{name}' declared")
        return self.functions[name](*args)

    def get_function(self, name: str) -> FFIFunction:
        """Get a registered FFI function by name."""
        if name not in self.functions:
            raise NameError(f"FFI: No foreign function '{name}' declared")
        return self.functions[name]

    def get_struct(self, name: str) -> type:
        """Get a registered FFI struct class by name."""
        if name not in self.structs:
            raise NameError(f"FFI: No foreign struct '{name}' declared")
        return self.structs[name]


# Module-level default registry
_default_registry = FFIRegistry()


def get_ffi_registry() -> FFIRegistry:
    """Get the default FFI registry."""
    return _default_registry


def ffi_declare(name: str, param_types: List[str],
                return_type: str = "void",
                lib: str = "libc",
                c_name: Optional[str] = None) -> FFIFunction:
    """Convenience: declare a foreign function on the default registry."""
    return _default_registry.declare_function(
        name, param_types, return_type, lib, c_name
    )


def ffi_call(name: str, *args: Any) -> Any:
    """Convenience: call a foreign function from the default registry."""
    return _default_registry.call(name, *args)


def ffi_struct(name: str, fields: List[Tuple[str, str]]) -> type:
    """Convenience: declare an FFI struct on the default registry."""
    return _default_registry.declare_struct(name, fields)


# ─────────────────────────────────────────────────────────────────────────────
# Memory utilities
# ─────────────────────────────────────────────────────────────────────────────

def ffi_alloc(size: int) -> int:
    """Allocate `size` bytes of C heap memory via malloc. Returns pointer."""
    libc = _get_libc()
    libc.malloc.argtypes = [ctypes.c_size_t]
    libc.malloc.restype = ctypes.c_void_p
    ptr = libc.malloc(size)
    if not ptr:
        raise MemoryError(f"FFI: malloc({size}) failed")
    return ptr


def ffi_free(ptr: int) -> None:
    """Free C heap memory."""
    libc = _get_libc()
    libc.free.argtypes = [ctypes.c_void_p]
    libc.free.restype = None
    libc.free(ptr)


def ffi_read_string(ptr: int, max_len: int = 4096) -> str:
    """Read a C string from a pointer."""
    return ctypes.string_at(ptr, max_len).split(b'\0')[0].decode(
        "utf-8", errors="replace"
    )


def ffi_write_string(s: str) -> int:
    """Allocate a C string and copy `s` into it. Returns pointer.
    Caller must ffi_free() the result."""
    encoded = s.encode("utf-8") + b'\0'
    ptr = ffi_alloc(len(encoded))
    ctypes.memmove(ptr, encoded, len(encoded))
    return ptr


# ─────────────────────────────────────────────────────────────────────────────
# Exports for preamble injection
# ─────────────────────────────────────────────────────────────────────────────

def get_ffi_builtins() -> dict:
    """Return dict of FFI functions for injection into transpiler preamble."""
    return {
        "ffi_declare":      ffi_declare,
        "ffi_call":         ffi_call,
        "ffi_struct":       ffi_struct,
        "ffi_alloc":        ffi_alloc,
        "ffi_free":         ffi_free,
        "ffi_read_string":  ffi_read_string,
        "ffi_write_string": ffi_write_string,
        "FFIRegistry":      FFIRegistry,
        "FFIFunction":      FFIFunction,
        "load_library":     load_library,
        "get_ffi_registry": get_ffi_registry,
    }
