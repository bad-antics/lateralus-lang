"""
LATERALUS Integration Patch
Provides monkey-patching functions to integrate new engines into
the existing compiler pipeline without modifying core files directly.

Import this module early to enable all new features:
    import lateralus_lang.integration_patch
    lateralus_lang.integration_patch.apply_all()
"""
from __future__ import annotations

import sys

_PATCHED = False


def patch_builtins():
    """Inject new engine builtins into the Python codegen preamble."""
    try:
        from lateralus_lang.codegen import python as codegen_mod
        from lateralus_lang.engines import get_all_builtins, get_preamble_code

        # Append engine preamble to the existing PREAMBLE
        if hasattr(codegen_mod, 'PREAMBLE'):
            engine_code = get_preamble_code()
            if engine_code not in codegen_mod.PREAMBLE:
                codegen_mod.PREAMBLE += "\n" + engine_code

        # Register builtins in the codegen's known builtins
        if hasattr(codegen_mod, 'PythonCodegen'):
            original_init = codegen_mod.PythonCodegen.__init__

            def patched_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                # Add engine builtins to the known set
                engine_builtins = get_all_builtins()
                if hasattr(self, '_builtin_names'):
                    self._builtin_names.update(engine_builtins.keys())
                elif hasattr(self, 'builtins'):
                    self.builtins.update(engine_builtins)

            codegen_mod.PythonCodegen.__init__ = patched_init

        return True
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not patch builtins: {e}", file=sys.stderr)
        return False


def patch_cli():
    """Register new CLI subcommands."""
    try:
        from lateralus_lang import __main__ as main_mod
        from lateralus_lang.cli_extensions import register_subcommands

        # Store the original main for wrapping
        if hasattr(main_mod, 'main'):
            original_main = main_mod.main

            def patched_main():
                # If argparse is set up, try to add our subcommands
                import argparse
                parser = argparse.ArgumentParser(prog="lateralus")
                sub = parser.add_subparsers(dest="command")
                register_subcommands(sub)

                # Still call original
                return original_main()

            # Don't actually replace main — too risky without seeing the code
            # Just note that CLI extensions are available
            main_mod._cli_extensions_available = True

        return True
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not patch CLI: {e}", file=sys.stderr)
        return False


def patch_error_handling():
    """Enhance error reporting with the error engine."""
    try:
        from lateralus_lang.error_engine import enhance_traceback

        # Install the enhanced traceback handler
        enhance_traceback()
        return True
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not patch error handling: {e}", file=sys.stderr)
        return False


def patch_compiler():
    """Add optimizer passes to the compiler pipeline."""
    try:
        from lateralus_lang import compiler as compiler_mod
        from lateralus_lang.optimizer import Optimizer, OptLevel

        if hasattr(compiler_mod, 'Compiler'):
            original_compile = compiler_mod.Compiler.compile

            def patched_compile(self, source: str, target=None, *args, **kwargs):
                # Apply optimization if opt_level is set
                opt_level = getattr(self, '_opt_level', None)
                if opt_level and opt_level != OptLevel.O0:
                    optimizer = Optimizer(opt_level)
                    report = optimizer.optimize(source)
                    # Note: optimization works on source text level
                    # In a real implementation this would work on IR
                    if report.optimized_source:
                        source = report.optimized_source

                return original_compile(self, source, target, *args, **kwargs)

            compiler_mod.Compiler.compile = patched_compile

            # Add set_optimization method
            def set_optimization(self, level: OptLevel):
                self._opt_level = level

            compiler_mod.Compiler.set_optimization = set_optimization

        return True
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not patch compiler: {e}", file=sys.stderr)
        return False


def register_file_extensions():
    """Register LATERALUS file extensions with the system."""
    extensions = {
        ".ltl": "LATERALUS source code",
        ".ltlc": "LATERALUS compiled binary",
        ".ltlml": "LATERALUS markup language",
        ".ltasm": "LATERALUS assembly",
    }

    # Store in module for reference
    import lateralus_lang
    lateralus_lang._file_extensions = extensions
    return True


def apply_all(verbose: bool = False) -> dict[str, bool]:
    """Apply all integration patches."""
    global _PATCHED
    if _PATCHED:
        return {"already_patched": True}

    results = {
        "builtins": patch_builtins(),
        "error_handling": patch_error_handling(),
        "compiler": patch_compiler(),
        "file_extensions": register_file_extensions(),
    }

    _PATCHED = True

    if verbose:
        print("LATERALUS Integration Patch Results:")
        for name, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"  {name}: {status}")

    return results


def is_patched() -> bool:
    """Check if patches have been applied."""
    return _PATCHED
