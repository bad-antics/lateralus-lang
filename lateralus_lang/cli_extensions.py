"""
lateralus_lang/cli_extensions.py — Extended CLI commands for LATERALUS

Provides the implementation for new CLI subcommands:
  - compile   : Compile .ltl to .ltlc binary
  - decompile : Decompile .ltlc back to readable .ltl
  - inspect   : Inspect a .ltlc binary and print a report
  - doc       : Compile .ltlml markup to .html
  - engines   : Show engine status
  - hash      : Hash a file or string
  - bench     : Benchmark a .ltl program

These can be wired into __main__.py's argparse setup.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def cmd_compile(args) -> int:
    """Compile a .ltl source file to .ltlc binary format."""
    from lateralus_lang.bytecode_format import LTLCCompiler

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    output_path = args.output or input_path.with_suffix(".ltlc")

    compiler = LTLCCompiler(
        compress=not args.no_compress,
        include_debug=args.debug,
        signing_key=args.sign_key,
    )

    try:
        source = input_path.read_text(encoding="utf-8")
        result_path = compiler.compile_to_file(source, str(output_path), str(input_path))
        size = os.path.getsize(result_path)
        print(f"Compiled: {input_path} -> {result_path} ({size:,} bytes)", file=sys.stderr)
        if args.sign_key:
            print("  Signed with key", file=sys.stderr)
        if not args.no_compress:
            print("  Compressed: yes", file=sys.stderr)
        if args.debug:
            print("  Debug info: included", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        return 1


def cmd_decompile(args) -> int:
    """Decompile a .ltlc binary back to readable .ltl source."""
    from lateralus_lang.bytecode_format import LTLCDecompiler

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    output_path = args.output or input_path.with_suffix(".decompiled.ltl")

    decompiler = LTLCDecompiler(signing_key=args.sign_key)

    try:
        result_path = decompiler.decompile_to_file(str(input_path), str(output_path))
        print(f"Decompiled: {input_path} -> {result_path}")
        return 0
    except ValueError as e:
        print(f"Decompilation error: {e}", file=sys.stderr)
        return 1


def cmd_inspect(args) -> int:
    """Inspect a .ltlc binary and print detailed report."""
    from lateralus_lang.bytecode_format import LTLCInspector

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    inspector = LTLCInspector()

    try:
        data = input_path.read_bytes()
        if args.json:
            import json
            report = inspector.inspect(data)
            print(json.dumps(report, indent=2, default=str))
        else:
            inspector.print_report(data)
        return 0
    except ValueError as e:
        print(f"Inspection error: {e}", file=sys.stderr)
        return 1


def cmd_doc(args) -> int:
    """Compile .ltlml markup files to HTML documents."""
    from lateralus_lang.markup import compile_ltlml_file

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    output_path = args.output or input_path.with_suffix(".html")

    try:
        result_path = compile_ltlml_file(str(input_path), str(output_path))
        size = os.path.getsize(result_path)
        print(f"Rendered: {input_path} -> {result_path} ({size:,} bytes)")
        return 0
    except Exception as e:
        print(f"Documentation error: {e}", file=sys.stderr)
        return 1


def cmd_engines(args) -> int:
    """Show status of all LATERALUS engines."""
    from lateralus_lang.engines import print_engine_status
    print_engine_status()
    return 0


def cmd_hash(args) -> int:
    """Hash a file or string using LATERALUS crypto engine."""
    from lateralus_lang.crypto_engine import checksum_file, hash_data

    algo = args.algorithm or "sha256"

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            return 1
        result = checksum_file(str(path), algo)
        print(f"{algo}:{result}  {path}")
    elif args.string:
        result = hash_data(args.string, algo)
        print(f"{algo}:{result}")
    else:
        # Read from stdin
        data = sys.stdin.read()
        result = hash_data(data, algo)
        print(f"{algo}:{result}")

    return 0


def cmd_bench(args) -> int:
    """Benchmark execution of a .ltl program."""
    from lateralus_lang.compiler import Compiler, Target

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    iterations = args.iterations or 10
    source = input_path.read_text(encoding="utf-8")

    times = []
    print(f"Benchmarking: {input_path}")
    print(f"Iterations: {iterations}")
    print()

    for i in range(iterations):
        start = time.perf_counter_ns()
        try:
            compiler = Compiler()
            compiler.compile(source, target=Target.PYTHON)
        except Exception as e:
            print(f"  Run {i+1}: ERROR - {e}", file=sys.stderr)
            continue
        elapsed_ns = time.perf_counter_ns() - start
        elapsed_ms = elapsed_ns / 1_000_000
        times.append(elapsed_ms)
        if args.verbose:
            print(f"  Run {i+1}: {elapsed_ms:.3f} ms")

    if not times:
        print("All runs failed.", file=sys.stderr)
        return 1

    avg = sum(times) / len(times)
    mn = min(times)
    mx = max(times)
    med = sorted(times)[len(times) // 2]

    print()
    print(f"Results ({len(times)} successful runs):")
    print(f"  Average : {avg:.3f} ms")
    print(f"  Median  : {med:.3f} ms")
    print(f"  Min     : {mn:.3f} ms")
    print(f"  Max     : {mx:.3f} ms")
    print(f"  Total   : {sum(times):.3f} ms")
    return 0


# --- Argparse registration ---------------------------------------------

def register_subcommands(subparsers):
    """
    Register all extended CLI subcommands into an argparse subparsers object.

    Usage in __main__.py:
        from lateralus_lang.cli_extensions import register_subcommands
        subparsers = parser.add_subparsers(...)
        register_subcommands(subparsers)
    """

    # compile
    p_compile = subparsers.add_parser("compile", help="Compile .ltl to .ltlc binary")
    p_compile.add_argument("file", help="Source .ltl file")
    p_compile.add_argument("-o", "--output", help="Output .ltlc file path")
    p_compile.add_argument("--no-compress", action="store_true", help="Disable compression")
    p_compile.add_argument("--debug", action="store_true", help="Include debug info")
    p_compile.add_argument("--sign-key", help="HMAC signing key")
    p_compile.set_defaults(func=cmd_compile)

    # decompile
    p_decompile = subparsers.add_parser("decompile", help="Decompile .ltlc to .ltl")
    p_decompile.add_argument("file", help="Compiled .ltlc file")
    p_decompile.add_argument("-o", "--output", help="Output .ltl file path")
    p_decompile.add_argument("--sign-key", help="HMAC verification key")
    p_decompile.set_defaults(func=cmd_decompile)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect .ltlc binary")
    p_inspect.add_argument("file", help="Compiled .ltlc file")
    p_inspect.add_argument("--json", action="store_true", help="Output as JSON")
    p_inspect.set_defaults(func=cmd_inspect)

    # doc
    p_doc = subparsers.add_parser("doc", help="Compile .ltlml to HTML")
    p_doc.add_argument("file", help="Source .ltlml file")
    p_doc.add_argument("-o", "--output", help="Output .html file path")
    p_doc.set_defaults(func=cmd_doc)

    # engines
    p_engines = subparsers.add_parser("engines", help="Show engine status")
    p_engines.set_defaults(func=cmd_engines)

    # hash
    p_hash = subparsers.add_parser("hash", help="Hash a file or string")
    p_hash.add_argument("-f", "--file", help="File to hash")
    p_hash.add_argument("-s", "--string", help="String to hash")
    p_hash.add_argument("-a", "--algorithm", choices=["sha256", "sha512", "blake2b", "md5"],
                        default="sha256", help="Hash algorithm")
    p_hash.set_defaults(func=cmd_hash)

    # bench
    p_bench = subparsers.add_parser("bench", help="Benchmark a .ltl program")
    p_bench.add_argument("file", help="Source .ltl file")
    p_bench.add_argument("-n", "--iterations", type=int, default=10, help="Number of iterations")
    p_bench.add_argument("-v", "--verbose", action="store_true", help="Show per-run times")
    p_bench.set_defaults(func=cmd_bench)
