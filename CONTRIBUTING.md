# Contributing to LATERALUS

Thank you for your interest in LATERALUS! This document will help you
get started contributing.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/lateralus-lang/lateralus
cd lateralus

# Create a virtual environment (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode (zero external deps)
pip install -e .

# Verify
lateralus --version
# LATERALUS 2.4.0
```

## Running Tests

```bash
# All tests (1,976 tests across 43 files)
pytest tests/ -v

# Specific suite
pytest tests/test_math_engine.py -v
pytest tests/test_crypto_engine.py -v
pytest tests/test_optimizer.py -v
pytest tests/test_vm_expanded.py -v
pytest tests/test_repl.py -v

# Quick summary
pytest tests/ --tb=short -q

# Health check
python scripts/health_check.py
```

## Project Structure

See [docs/architecture.ltlml](docs/architecture.ltlml) for the full
architecture overview.

The key directories:

- `lateralus_lang/` — Python implementation of the compiler, engines, and tooling
- `lateralus_lang/codegen/` — Code generators (Python, C, JS, WASM, Bytecode)
- `lateralus_lang/vm/` — Stack-based VM, assembler, disassembler (102 opcodes)
- `stdlib/` — Standard library (59 modules written in LATERALUS)
- `tests/` — Python test suites (43 files, 1,976 tests via pytest)
- `bootstrap/` — Self-hosting compiler (LATERALUS source)
- `docs/` — Documentation in LTLML format + website
- `examples/` — 38 example programs
- `vscode-lateralus/` — VS Code extension
- `lateralus-os/` — LateralusOS bare-metal x86_64 kernel
- `scripts/` — Build, health-check, and maintenance scripts

## Code Style

### Python Code
- Python 3.10+
- Type hints on all public functions
- Docstrings on all classes and public methods
- 100-character line limit
- Use `dataclass` for data structures
- Use `enum.Enum` for enumerations

### LATERALUS Code
- Use `let` (not `var`) for variable declarations
- Use pipeline operators for data transformations
- Use `snake_case` for functions and variables
- Use `PascalCase` for struct names
- Use `UPPER_CASE` for constants

You can format LATERALUS code with:
```bash
lateralus fmt src/
```

And lint it with:
```bash
lateralus lint src/ --strict
```

## Adding a New Built-in Function

1. Choose the appropriate engine module (math_engine, crypto_engine, etc.)
2. Add the Python implementation
3. Add the function to the engine's `*_BUILTINS` dictionary
4. Add tests in `tests/test_<engine>.py`
5. Document the function in the language specification

Example:
```python
# In math_engine.py
def ltl_my_function(x):
    """Compute something useful."""
    return result

MATH_BUILTINS["my_function"] = ltl_my_function
```

## Adding a New Standard Library Module

1. Create `stdlib/my_module.ltl`
2. Write LATERALUS functions
3. Add example usage in `examples/`
4. Test by running: `lateralus run examples/my_example.ltl`

## Adding a Lint Rule

1. Add the rule method to `LateralusLinter` in `linter.py`
2. Call it from `lint()` or `lint_strict()`
3. Add tests in `test_formatter_linter.py`

## Commit Messages

Use conventional commits:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `test:` — Test changes
- `refactor:` — Code restructuring
- `perf:` — Performance improvement

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for your changes
4. Ensure all tests pass: `pytest tests/ -v`
5. Submit a pull request with a clear description

## Reporting Issues

When reporting bugs, please include:
- LATERALUS version (`lateralus --version`)
- Python version (`python --version`)
- Operating system
- Minimal reproduction code
- Expected vs actual behavior
- Full error output

## Philosophy

LATERALUS is built on the idea that programming should spiral outward —
from simple ideas to profound compositions. When contributing, keep in
mind:

1. **Clarity over cleverness** — Code should read naturally
2. **Pipelines are central** — Data flows through transformations
3. **Errors should help** — Error messages should suggest fixes
4. **Math should be beautiful** — Numeric code should be precise and elegant
5. **Test everything** — If it's worth building, it's worth testing

## License

By contributing, you agree that your contributions will be licensed
under the same license as the project.

---

*Spiral outward. Build something beautiful.*

---

## ⚠️ NO BOX-DRAWING CHARACTERS — MANDATORY POLICY

**Unicode box-drawing characters are permanently banned from this project.**

Do **NOT** use any of the following characters anywhere — code, comments,
strings, output, documentation, READMEs, or data files:

```
BANNED:  = | + + + + + + + + + + + + + - | + + + + + - | + + + + + + + + +
```

Use **plain ASCII** instead:

| Need             | Use   | Example                  |
|------------------|-------|--------------------------|
| Horizontal line  | `-`   | `----------`             |
| Thick h-line     | `=`   | `==========`             |
| Vertical line    | `\|`  | `\|  content  \|`        |
| Corner / joint   | `+`   | `+----------+`           |
| Section break    | `=`   | `# ==================`   |

### Correct box style

```
+==================================+
|  LateralusOS v0.3.0             |
+==================================+
```

### Wrong box style (REJECTED)

```
+==================================+
|  LateralusOS v0.3.0             |
+==================================+
```

This policy applies to **all files** — `.py`, `.ltl`, `.c`, `.h`, `.sh`,
`.md`, `.asm`, `.json`, and everything else in the repository.

PRs containing box-drawing characters will not be merged.
