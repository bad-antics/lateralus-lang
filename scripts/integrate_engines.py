#!/usr/bin/env python3
"""
scripts/integrate_engines.py — Integration script for LATERALUS v1.3 engines

This script patches the existing compiler and CLI to integrate the new
engine subsystems (math, crypto, markup, bytecode, error).

Run from the project root:
    python scripts/integrate_engines.py

What it does:
  1. Patches codegen/python.py to include engine preamble
  2. Patches __main__.py to register new CLI subcommands
  3. Verifies all engines can be imported
  4. Runs a quick smoke test
"""

import sys
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LANG_DIR = PROJECT_ROOT / "lateralus_lang"


def patch_codegen():
    """Inject engine preamble into codegen/python.py"""
    codegen_path = LANG_DIR / "codegen" / "python.py"
    if not codegen_path.exists():
        print(f"  SKIP: {codegen_path} not found")
        return False

    content = codegen_path.read_text(encoding="utf-8")

    # Check if already patched
    if "LATERALUS Engine Extensions" in content:
        print("  SKIP: codegen/python.py already patched")
        return True

    # Find the PREAMBLE string and append engine imports
    engine_preamble = '''
# ─── LATERALUS Engine Extensions ────────────────────────────────────
try:
    from lateralus_lang.math_engine import (
        LTLNumber, Matrix, Vector, Interval, Dual,
        derivative, gradient,
        dual_sin, dual_cos, dual_exp, dual_log, dual_sqrt,
        mean, median, variance, std_dev, covariance, correlation, linear_regression,
        newton_raphson, bisection, trapezoidal_integrate, simpson_integrate,
        PI, E, PHI, TAU, SQRT2, set_precision,
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
'''

    # Strategy: find the PREAMBLE = """ or PREAMBLE = ''' block and append before closing quotes
    # Or if there's a preamble variable, append to it

    # Look for PREAMBLE pattern
    preamble_match = re.search(r'(PREAMBLE\s*=\s*(?:"""|\'\'\'))(.*?)((?:"""|\'\'\'))', content, re.DOTALL)

    if preamble_match:
        # Insert engine preamble before the closing triple-quote
        closing = preamble_match.group(3)
        insert_pos = preamble_match.end(2)
        content = content[:insert_pos] + engine_preamble + content[insert_pos:]
        codegen_path.write_text(content, encoding="utf-8")
        print("  OK: Patched PREAMBLE in codegen/python.py")
        return True
    else:
        # Alternative: append a post-preamble import block
        # Find the class definition or the generate method
        class_match = re.search(r'class\s+PythonCodegen', content)
        if class_match:
            insert_pos = class_match.start()
            extra = f'''
# Engine preamble extension
_ENGINE_PREAMBLE = """{engine_preamble}"""

'''
            content = content[:insert_pos] + extra + content[insert_pos:]
            codegen_path.write_text(content, encoding="utf-8")
            print("  OK: Added _ENGINE_PREAMBLE to codegen/python.py")
            return True

    print("  WARN: Could not find insertion point in codegen/python.py")
    print("        Please manually add engine imports to the PREAMBLE string.")
    return False


def patch_main():
    """Add CLI extension registration to __main__.py"""
    main_path = LANG_DIR / "__main__.py"
    if not main_path.exists():
        print(f"  SKIP: {main_path} not found")
        return False

    content = main_path.read_text(encoding="utf-8")

    # Check if already patched
    if "cli_extensions" in content:
        print("  SKIP: __main__.py already patched")
        return True

    # Find the subparsers creation and add our registration
    # Look for add_subparsers
    subparsers_match = re.search(r'(subparsers\s*=\s*\w+\.add_subparsers\([^)]*\))', content)
    if subparsers_match:
        insert_pos = subparsers_match.end()
        patch = '''

    # Register extended CLI commands (engines, compile, decompile, inspect, doc, hash, bench)
    try:
        from lateralus_lang.cli_extensions import register_subcommands
        register_subcommands(subparsers)
    except ImportError:
        pass
'''
        content = content[:insert_pos] + patch + content[insert_pos:]
        main_path.write_text(content, encoding="utf-8")
        print("  OK: Patched __main__.py with CLI extensions")
        return True

    # Alternative: add at end of main() function or at module level
    # Look for if __name__ == "__main__"
    main_block = re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', content)
    if main_block:
        insert_pos = main_block.start()
        patch = '''
# Register CLI extension commands
def _register_extensions(parser):
    try:
        from lateralus_lang.cli_extensions import register_subcommands
        subparsers = parser.add_subparsers(dest="command")
        register_subcommands(subparsers)
    except ImportError:
        pass

'''
        content = content[:insert_pos] + patch + content[insert_pos:]
        main_path.write_text(content, encoding="utf-8")
        print("  OK: Added _register_extensions to __main__.py")
        return True

    print("  WARN: Could not find insertion point in __main__.py")
    print("        Please manually import and call register_subcommands.")
    return False


def verify_engines():
    """Verify all engines can be imported."""
    engines = [
        ("math_engine", "lateralus_lang.math_engine"),
        ("crypto_engine", "lateralus_lang.crypto_engine"),
        ("markup", "lateralus_lang.markup"),
        ("bytecode_format", "lateralus_lang.bytecode_format"),
        ("error_engine", "lateralus_lang.error_engine"),
        ("engines", "lateralus_lang.engines"),
        ("cli_extensions", "lateralus_lang.cli_extensions"),
    ]

    all_ok = True
    for name, module in engines:
        try:
            __import__(module)
            print(f"  OK: {name}")
        except ImportError as e:
            print(f"  FAIL: {name} — {e}")
            all_ok = False

    return all_ok


def smoke_test():
    """Run a quick smoke test of engine functionality."""
    print("\n  Testing math engine...")
    from lateralus_lang.math_engine import LTLNumber, Matrix, mean
    n = LTLNumber(42) + LTLNumber(8)
    assert n.value == 50, f"Expected 50, got {n.value}"
    m = Matrix([[1, 2], [3, 4]])
    assert m.det() == -2.0
    assert mean([1, 2, 3, 4, 5]) == 3.0
    print("    Math engine: OK")

    print("  Testing crypto engine...")
    from lateralus_lang.crypto_engine import sha256, to_base64, from_base64, lbe_encode, lbe_decode
    h = sha256("test")
    assert len(h) == 64
    encoded = to_base64("hello")
    assert from_base64(encoded) == "hello"
    data = {"key": "value", "nums": [1, 2, 3]}
    assert lbe_decode(lbe_encode(data)) == data
    print("    Crypto engine: OK")

    print("  Testing markup engine...")
    from lateralus_lang.markup import render_ltlml
    html = render_ltlml("# Hello\n\nWorld")
    assert "<h1" in html
    print("    Markup engine: OK")

    print("  Testing bytecode format...")
    from lateralus_lang.bytecode_format import LTLCCompiler, LTLCDecompiler
    src = 'fn hello() {\n    println("hi")\n}\n'
    data = LTLCCompiler().compile_source(src, "test.ltl")
    ltlc = LTLCDecompiler().decompile(data)
    assert ltlc.metadata.source_file == "test.ltl"
    print("    Bytecode format: OK")

    print("  Testing error engine...")
    from lateralus_lang.error_engine import ErrorCode, Severity, LateralusError, ErrorCollector
    ec = ErrorCollector()
    ec.error(ErrorCode.E1001, "Test error")
    assert ec.error_count() == 1
    print("    Error engine: OK")

    print("\n  All smoke tests passed!")


def main():
    print("=" * 50)
    print("LATERALUS v1.3 Engine Integration")
    print("=" * 50)

    # Ensure we're in the right directory
    if not (LANG_DIR / "__init__.py").exists():
        print(f"ERROR: Cannot find lateralus_lang at {LANG_DIR}")
        print("       Run this script from the project root.")
        sys.exit(1)

    # Add project root to path
    sys.path.insert(0, str(PROJECT_ROOT))

    print("\n1. Verifying engines...")
    if not verify_engines():
        print("\n   Some engines failed to import. Fix errors above first.")
        sys.exit(1)

    print("\n2. Patching codegen/python.py...")
    patch_codegen()

    print("\n3. Patching __main__.py...")
    patch_main()

    print("\n4. Running smoke tests...")
    try:
        smoke_test()
    except Exception as e:
        print(f"\n   Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 50)
    print("Integration complete!")
    print()
    print("New CLI commands available:")
    print("  lateralus compile  <file.ltl>     Compile to .ltlc binary")
    print("  lateralus decompile <file.ltlc>    Decompile to .ltl")
    print("  lateralus inspect  <file.ltlc>     Inspect binary contents")
    print("  lateralus doc      <file.ltlml>    Render markup to HTML")
    print("  lateralus engines                  Show engine status")
    print("  lateralus hash     -s 'text'       Hash a string")
    print("  lateralus bench    <file.ltl>      Benchmark a program")
    print()
    print("Run tests with:")
    print("  pytest tests/ -v")
    print("=" * 50)


if __name__ == "__main__":
    main()
