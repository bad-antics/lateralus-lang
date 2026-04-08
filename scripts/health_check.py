#!/usr/bin/env python3
"""
LATERALUS Project Health Dashboard

Checks project integrity: file existence, module imports, test discovery,
and generates a health report. Run without any dependencies beyond the
standard library and the lateralus_lang package.

Usage:
    python scripts/health_check.py
"""
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_file(path: str, required: bool = True) -> tuple[str, bool]:
    """Check if a file exists."""
    full = PROJECT_ROOT / path
    exists = full.exists()
    status = "OK" if exists else ("MISSING" if required else "OPTIONAL")
    return status, exists


def check_module(module: str) -> tuple[str, bool]:
    """Try importing a Python module."""
    try:
        importlib.import_module(module)
        return "OK", True
    except Exception as e:
        return f"ERROR: {e}", False


def main():
    print("\n  LATERALUS Health Check")
    print("  " + "=" * 60)

    # Core files
    print("\n  Core Compiler Files:")
    core_files = [
        "lateralus_lang/__init__.py",
        "lateralus_lang/__main__.py",
        "lateralus_lang/lexer.py",
        "lateralus_lang/parser.py",
        "lateralus_lang/ast_nodes.py",
        "lateralus_lang/compiler.py",
        "lateralus_lang/ir.py",
        "lateralus_lang/codegen/python.py",
    ]
    for f in core_files:
        status, _ = check_file(f)
        print(f"    {status:8} {f}")

    # Engine modules
    print("\n  Engine Modules:")
    engine_files = [
        "lateralus_lang/math_engine.py",
        "lateralus_lang/crypto_engine.py",
        "lateralus_lang/markup.py",
        "lateralus_lang/bytecode_format.py",
        "lateralus_lang/error_engine.py",
        "lateralus_lang/science.py",
        "lateralus_lang/engines.py",
    ]
    for f in engine_files:
        status, _ = check_file(f)
        print(f"    {status:8} {f}")

    # Infrastructure
    print("\n  Infrastructure Modules:")
    infra_files = [
        "lateralus_lang/optimizer.py",
        "lateralus_lang/type_system.py",
        "lateralus_lang/async_runtime.py",
        "lateralus_lang/repl_enhanced.py",
        "lateralus_lang/integration_patch.py",
        "lateralus_lang/cli_extensions.py",
    ]
    for f in infra_files:
        status, _ = check_file(f)
        print(f"    {status:8} {f}")

    # Developer tools
    print("\n  Developer Tools:")
    tool_files = [
        "lateralus_lang/lsp_server.py",
        "lateralus_lang/package_manager.py",
        "lateralus_lang/formatter.py",
        "lateralus_lang/linter.py",
        "lateralus_lang/debugger.py",
        "lateralus_lang/bench.py",
        "lateralus_lang/test_runner.py",
    ]
    for f in tool_files:
        status, _ = check_file(f)
        print(f"    {status:8} {f}")

    # Standard library
    print("\n  Standard Library:")
    stdlib_files = [
        "stdlib/math.ltl",
        "stdlib/strings.ltl",
        "stdlib/collections.ltl",
        "stdlib/time.ltl",
        "stdlib/random.ltl",
        "stdlib/core.ltl",
        "stdlib/io.ltl",
        "stdlib/science.ltl",
        "stdlib/optimize.ltl",
        "stdlib/functional.ltl",
        "stdlib/algorithms.ltl",
        "stdlib/data.ltl",
        "stdlib/testing.ltl",
        "stdlib/stats.ltl",
        "stdlib/crypto.ltl",
        "stdlib/linalg.ltl",
        "stdlib/os.ltl",
        "stdlib/datetime.ltl",
        "stdlib/regex.ltl",
        "stdlib/http.ltl",
        "stdlib/result.ltl",
        "stdlib/iter.ltl",
    ]
    for f in stdlib_files:
        status, _ = check_file(f, required=False)
        print(f"    {status:8} {f}")

    # Bootstrap
    print("\n  Self-Hosting Bootstrap:")
    bootstrap_files = [
        "bootstrap/v2_lexer.ltl",
        "bootstrap/v2_parser.ltl",
        "bootstrap/v2_codegen.ltl",
    ]
    for f in bootstrap_files:
        status, _ = check_file(f)
        print(f"    {status:8} {f}")

    # Documentation
    print("\n  Documentation:")
    doc_files = [
        "docs/grammar.ebnf",
        "docs/index.ltlml",
        "docs/language-spec.ltlml",
        "docs/quick-reference.ltlml",
        "docs/blog/release-v1.3.ltlml",
        "docs/blog/release-v1.5.ltlml",
        "docs/tutorial.ltlml",
        "docs/cookbook.ltlml",
        "docs/papers/lateralus-design-paper.ltlml",
    ]
    for f in doc_files:
        status, _ = check_file(f)
        print(f"    {status:8} {f}")

    # VS Code extension
    print("\n  VS Code Extension:")
    ext_files = [
        "vscode-lateralus/package.json",
        "vscode-lateralus/syntaxes/lateralus.tmLanguage.json",
        "vscode-lateralus/snippets/lateralus.json",
        "vscode-lateralus/language-configuration.json",
    ]
    for f in ext_files:
        status, _ = check_file(f)
        print(f"    {status:8} {f}")

    # Tests
    print("\n  Test Files:")
    test_dir = PROJECT_ROOT / "tests"
    if test_dir.exists():
        test_files = sorted(test_dir.glob("test_*.py"))
        for f in test_files:
            rel = f.relative_to(PROJECT_ROOT)
            print(f"    OK       {rel}")
        print(f"\n    Total test files: {len(test_files)}")
    else:
        print("    MISSING  tests/ directory")

    # Module imports
    print("\n  Module Import Check:")
    modules = [
        "lateralus_lang",
        "lateralus_lang.lexer",
        "lateralus_lang.parser",
        "lateralus_lang.ast_nodes",
        "lateralus_lang.math_engine",
        "lateralus_lang.crypto_engine",
        "lateralus_lang.error_engine",
        "lateralus_lang.optimizer",
        "lateralus_lang.type_system",
        "lateralus_lang.science",
        "lateralus_lang.compiler",
        "lateralus_lang.lsp_server",
    ]
    ok_count = 0
    for mod in modules:
        status, success = check_module(mod)
        icon = "OK" if success else "ERR"
        print(f"    {icon:8} {mod}")
        if success:
            ok_count += 1

    print(f"\n    Importable: {ok_count}/{len(modules)}")

    # Summary
    print("\n  " + "=" * 60)

    total_files = (
        len(core_files) + len(engine_files) + len(infra_files) +
        len(tool_files) + len(stdlib_files) + len(bootstrap_files) +
        len(doc_files) + len(ext_files)
    )
    existing = sum(
        1 for files in [
            core_files, engine_files, infra_files, tool_files,
            bootstrap_files, doc_files, ext_files
        ]
        for f in files
        if (PROJECT_ROOT / f).exists()
    )
    stdlib_existing = sum(1 for f in stdlib_files if (PROJECT_ROOT / f).exists())

    print(f"  Project files: {existing} present (of {total_files - len(stdlib_files)} required)")
    print(f"  Stdlib files:  {stdlib_existing} present (of {len(stdlib_files)} total)")
    print(f"  Modules:       {ok_count}/{len(modules)} importable")
    print("  LATERALUS v2.4.0 Ecosystem Health: ", end="")

    if existing >= total_files - len(stdlib_files) - 2 and ok_count >= len(modules) - 2:
        print("HEALTHY")
    elif existing >= total_files * 0.7:
        print("PARTIAL")
    else:
        print("NEEDS ATTENTION")

    print()


if __name__ == "__main__":
    main()
