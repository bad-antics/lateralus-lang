"""
lateralus_lang/engines.py — Unified engine interface for LATERALUS

This module provides a single entry point to all engine subsystems,
making it easy to import and use from the compiler pipeline, CLI, and REPL.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# --- Lazy engine loaders ------------------------------------------------
# We use lazy imports so that importing engines.py doesn't force loading
# every heavy engine at startup — only when first accessed.

_math_engine = None
_crypto_engine = None
_markup_engine = None
_bytecode_engine = None
_error_engine = None


def math():
    """Access the mathematical computation engine."""
    global _math_engine
    if _math_engine is None:
        from lateralus_lang import math_engine as _m
        _math_engine = _m
    return _math_engine


def crypto():
    """Access the cryptography engine."""
    global _crypto_engine
    if _crypto_engine is None:
        from lateralus_lang import crypto_engine as _c
        _crypto_engine = _c
    return _crypto_engine


def markup():
    """Access the LTLML markup engine."""
    global _markup_engine
    if _markup_engine is None:
        from lateralus_lang import markup as _mk
        _markup_engine = _mk
    return _markup_engine


def bytecode():
    """Access the .ltlc binary format engine."""
    global _bytecode_engine
    if _bytecode_engine is None:
        from lateralus_lang import bytecode_format as _bf
        _bytecode_engine = _bf
    return _bytecode_engine


def errors():
    """Access the rich error diagnostics engine."""
    global _error_engine
    if _error_engine is None:
        from lateralus_lang import error_engine as _ee
        _error_engine = _ee
    return _error_engine


# --- Unified builtins registry -----------------------------------------

def get_all_builtins() -> Dict[str, Any]:
    """
    Return a unified dictionary of all builtins from every engine,
    suitable for injection into the transpiler preamble.
    """
    builtins = {}

    # Math engine builtins
    m = math()
    builtins.update({
        # Core types
        "LTLNumber": m.LTLNumber,
        "Matrix": m.Matrix,
        "Vector": m.Vector,
        "Interval": m.Interval,
        "Dual": m.Dual,
        # Math functions
        "derivative": m.derivative,
        "gradient": m.gradient,
        "dual_sin": m.dual_sin,
        "dual_cos": m.dual_cos,
        "dual_exp": m.dual_exp,
        "dual_log": m.dual_log,
        "dual_sqrt": m.dual_sqrt,
        # Statistics
        "mean": m.mean,
        "median": m.median,
        "variance": m.variance,
        "std_dev": m.std_dev,
        "covariance": m.covariance,
        "correlation": m.correlation,
        "linear_regression": m.linear_regression,
        # Numerical methods
        "newton_raphson": m.newton_raphson,
        "bisection": m.bisection,
        "trapezoidal_integrate": m.trapezoidal_integrate,
        "simpson_integrate": m.simpson_integrate,
        # Constants
        "PI": m.PI,
        "E": m.E,
        "PHI": m.PHI,
        "TAU": m.TAU,
        "SQRT2": m.SQRT2,
    })

    # Crypto engine builtins
    c = crypto()
    builtins.update({
        # Hashing
        "sha256": c.sha256,
        "sha512": c.sha512,
        "blake2b": c.blake2b,
        "md5": c.md5,
        "hash_data": c.hash_data,
        # HMAC
        "hmac_sign": c.hmac_sign,
        "hmac_verify": c.hmac_verify,
        # Passwords
        "hash_password": c.hash_password,
        "verify_password": c.verify_password,
        # Random
        "random_token": c.random_token,
        "random_urlsafe": c.random_urlsafe,
        "random_bytes": c.random_bytes,
        # Encoding
        "to_base64": c.to_base64,
        "from_base64": c.from_base64,
        "to_hex": c.to_hex,
        "from_hex": c.from_hex,
        # XOR
        "xor_encrypt": c.xor_encrypt,
        "xor_decrypt": c.xor_decrypt,
        # LBE
        "lbe_encode": c.lbe_encode,
        "lbe_decode": c.lbe_decode,
    })

    return builtins


def get_preamble_code() -> str:
    """
    Return Python source code that, when exec'd, makes all engine builtins
    available in the transpiled program's namespace.

    This is designed to be prepended to the transpiler's existing preamble.
    """
    return '''
# --- LATERALUS Engine Extensions ------------------------------------
try:
    from lateralus_lang.math_engine import (
        LTLNumber, Matrix, Vector, Interval, Dual,
        derivative, gradient,
        dual_sin, dual_cos, dual_exp, dual_log, dual_sqrt,
        mean, median, variance, std_dev, covariance, correlation, linear_regression,
        newton_raphson, bisection, trapezoidal_integrate, simpson_integrate,
        PI, E, PHI, TAU, SQRT2,
        set_precision,
    )
except ImportError:
    pass

try:
    from lateralus_lang.crypto_engine import (
        sha256, sha512, blake2b, md5, hash_data,
        hmac_sign, hmac_verify,
        hash_password, verify_password,
        random_token, random_urlsafe, random_bytes,
        to_base64, from_base64, to_hex, from_hex,
        xor_encrypt, xor_decrypt,
        lbe_encode, lbe_decode, lbe_save, lbe_load,
        sign_data, checksum_file, verify_file,
    )
except ImportError:
    pass

try:
    from lateralus_lang.error_engine import (
        ErrorCode, Severity, SourceLocation, LateralusError,
        ErrorCollector, enhance_traceback,
    )
except ImportError:
    pass
'''


# --- Engine info --------------------------------------------------------

ENGINE_VERSIONS = {
    "math_engine": "1.5.0",
    "crypto_engine": "1.5.0",
    "markup": "1.5.0",
    "bytecode_format": "1.5.0",
    "error_engine": "1.5.0",
}


def engine_status() -> Dict[str, Dict[str, Any]]:
    """Check which engines are available and return status info."""
    status = {}

    for name, version in ENGINE_VERSIONS.items():
        try:
            __import__(f"lateralus_lang.{name}")
            status[name] = {"available": True, "version": version}
        except ImportError as e:
            status[name] = {"available": False, "error": str(e)}

    return status


def print_engine_status():
    """Print a human-readable engine status report."""
    status = engine_status()
    print("LATERALUS Engine Status")
    print("=" * 40)
    for name, info in status.items():
        icon = "\u2713" if info["available"] else "\u2717"
        ver = info.get("version", "n/a")
        line = f"  {icon} {name:<20} v{ver}"
        if not info["available"]:
            line += f"  ({info['error']})"
        print(line)
    print()


# --- New engine lazy loaders (added in session 4) ----------------------

_query_engine = None
_reactive_engine = None
_notebook_engine = None
_pattern_engine = None
_ltlcfg_engine = None


def query():
    """Access the LQL query engine."""
    global _query_engine
    if _query_engine is None:
        from lateralus_lang import query_engine as _qe
        _query_engine = _qe
    return _query_engine


def reactive():
    """Access the reactive programming engine."""
    global _reactive_engine
    if _reactive_engine is None:
        from lateralus_lang import reactive as _re
        _reactive_engine = _re
    return _reactive_engine


def notebook():
    """Access the .ltlnb notebook engine."""
    global _notebook_engine
    if _notebook_engine is None:
        from lateralus_lang import notebook as _nb
        _notebook_engine = _nb
    return _notebook_engine


def patterns():
    """Access the pattern matching engine."""
    global _pattern_engine
    if _pattern_engine is None:
        from lateralus_lang import pattern_engine as _pe
        _pattern_engine = _pe
    return _pattern_engine


def config():
    """Access the .ltlcfg configuration engine."""
    global _ltlcfg_engine
    if _ltlcfg_engine is None:
        from lateralus_lang import ltlcfg as _cfg
        _ltlcfg_engine = _cfg
    return _ltlcfg_engine


def get_extended_builtins() -> dict:
    """
    Return builtins from all new session-4 engines:
    query_engine, reactive, notebook, pattern_engine, ltlcfg.
    Combined with get_all_builtins() for full runtime.
    """
    builtins = {}

    try:
        from lateralus_lang.query_engine import get_query_builtins
        builtins.update(get_query_builtins())
    except ImportError:
        pass

    try:
        from lateralus_lang.reactive import get_reactive_builtins
        builtins.update(get_reactive_builtins())
    except ImportError:
        pass

    try:
        from lateralus_lang.notebook import get_notebook_builtins
        builtins.update(get_notebook_builtins())
    except ImportError:
        pass

    try:
        from lateralus_lang.pattern_engine import get_pattern_builtins
        builtins.update(get_pattern_builtins())
    except ImportError:
        pass

    try:
        from lateralus_lang.ltlcfg import get_ltlcfg_builtins
        builtins.update(get_ltlcfg_builtins())
    except ImportError:
        pass

    try:
        from lateralus_lang.watch import get_watch_builtins
        builtins.update(get_watch_builtins())
    except ImportError:
        pass

    try:
        from lateralus_lang.codegen.javascript import get_js_transpiler_builtins
        builtins.update(get_js_transpiler_builtins())
    except ImportError:
        pass

    try:
        from lateralus_lang.codegen.wasm import get_wasm_builtins
        builtins.update(get_wasm_builtins())
    except ImportError:
        pass

    return builtins


def get_full_builtins() -> dict:
    """Return ALL builtins from every engine (base + extended)."""
    combined = get_all_builtins()
    combined.update(get_extended_builtins())
    return combined


# Update ENGINE_VERSIONS with new modules
ENGINE_VERSIONS.update({
    "query_engine":   "1.5.0",
    "reactive":       "1.5.0",
    "notebook":       "1.5.0",
    "pattern_engine": "1.5.0",
    "ltlcfg":         "1.5.0",
    "watch":          "1.5.0",
})
