"""
tests/conftest.py — Shared test fixtures & utilities for LATERALUS test suite
===============================================================================
Provides:
  • Compiler/pipeline helper fixtures
  • File-factory fixtures (tmp .ltl / .ltasm / .ltlml)
  • Assertion helpers for compile results
  • Pytest markers registration
  • Parametrize-ready example discovery
"""
import pytest
import sys
import os
import shutil
import time
from pathlib import Path

# -- Project root on path --------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EXAMPLES_DIR = PROJECT_ROOT / "examples"
STDLIB_DIR   = PROJECT_ROOT / "stdlib"


# ==========================================================================
# Marker registration
# ==========================================================================

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with -m 'not slow')")
    config.addinivalue_line("markers", "fuzz: randomized / property-based tests")
    config.addinivalue_line("markers", "snapshot: golden-file regression tests")
    config.addinivalue_line("markers", "e2e: end-to-end CLI tests (subprocess)")
    config.addinivalue_line("markers", "perf: performance regression tests")
    config.addinivalue_line("markers", "stdlib: standard library validation")
    config.addinivalue_line("markers", "examples: example program validation")
    config.addinivalue_line("markers", "requires_gcc: tests that need GCC installed")


# ==========================================================================
# GCC availability check
# ==========================================================================

HAS_GCC = shutil.which("gcc") is not None
skip_no_gcc = pytest.mark.skipif(not HAS_GCC, reason="GCC not installed")


# ==========================================================================
# Compiler fixtures
# ==========================================================================

@pytest.fixture
def compiler():
    """A fresh Compiler instance."""
    from lateralus_lang.compiler import Compiler
    return Compiler()


@pytest.fixture
def freestanding_compiler():
    """A Compiler instance in freestanding (bare-metal) mode."""
    from lateralus_lang.compiler import Compiler
    return Compiler(freestanding=True)


# ==========================================================================
# Compile-and-assert helpers
# ==========================================================================

class CompileHelper:
    """Utility class for quick compile-and-assert workflows."""

    def __init__(self):
        from lateralus_lang.compiler import Compiler, Target
        self._compiler = Compiler()
        self.Target = Target

    def to_python(self, source: str, *, filename: str = "test.ltl") -> str:
        """Compile source to Python; assert success; return Python source."""
        r = self._compiler.compile_source(source, target=self.Target.PYTHON, filename=filename)
        assert r.ok, f"Compile failed: {[e.message for e in r.errors[:5]]}"
        return r.python_src

    def to_c(self, source: str, *, filename: str = "test.ltl") -> str:
        """Compile source to C; assert success; return C source."""
        r = self._compiler.compile_source(source, target=self.Target.C, filename=filename)
        assert r.ok, f"Compile failed: {[e.message for e in r.errors[:5]]}"
        return r.c_src

    def check(self, source: str, *, filename: str = "test.ltl"):
        """Type-check source; assert success; return CompileResult."""
        r = self._compiler.compile_source(source, target=self.Target.CHECK, filename=filename)
        assert r.ok, f"Check failed: {[e.message for e in r.errors[:5]]}"
        return r

    def expect_fail(self, source: str, *, target=None, filename: str = "test.ltl",
                    error_contains: str = None):
        """Compile source; assert failure; optionally check error message."""
        from lateralus_lang.compiler import Target as T
        tgt = target or T.PYTHON
        r = self._compiler.compile_source(source, target=tgt, filename=filename)
        assert not r.ok, "Expected compilation failure but it succeeded"
        if error_contains:
            msgs = " ".join(e.message for e in r.errors)
            assert error_contains.lower() in msgs.lower(), \
                f"Expected error containing '{error_contains}' in: {msgs}"
        return r

    def compile_file(self, path: str, *, target=None):
        """Compile a file path; return CompileResult."""
        from lateralus_lang.compiler import Target as T
        tgt = target or T.PYTHON
        return self._compiler.compile_file(str(path), target=tgt)

    def compile_result(self, source: str, *, target=None, filename: str = "test.ltl"):
        """Compile source; return raw CompileResult (no assertion)."""
        from lateralus_lang.compiler import Target as T
        tgt = target or T.PYTHON
        return self._compiler.compile_source(source, target=tgt, filename=filename)


@pytest.fixture
def ch():
    """CompileHelper fixture — quick compile + assert."""
    return CompileHelper()


# ==========================================================================
# Lex/Parse helpers
# ==========================================================================

class LexParseHelper:
    """Utility class for quick lex/parse workflows."""

    def lex(self, source: str):
        """Lex source; return token list (excluding EOF)."""
        from lateralus_lang.lexer import lex, TK
        tokens = lex(source)
        return [t for t in tokens if t.type != TK.EOF]

    def parse(self, source: str, filename: str = "test.ltl"):
        """Parse source; return AST Program node."""
        from lateralus_lang.parser import parse
        return parse(source, filename)

    def parse_first(self, source: str):
        """Parse source; return the first body statement."""
        ast = self.parse(source)
        assert ast.body, "No statements parsed"
        return ast.body[0]

    def parse_expr(self, source: str):
        """Parse an expression wrapped in a let binding; return the value node."""
        ast = self.parse(f"let _x = {source}")
        assert ast.body, "No statements parsed"
        return ast.body[0].value


@pytest.fixture
def lp():
    """LexParseHelper fixture — quick lex/parse."""
    return LexParseHelper()


# ==========================================================================
# Source-text fixtures
# ==========================================================================@pytest.fixture
def sample_source():
    """A basic LATERALUS source program for testing."""
    return '''
fn greet(name: str) -> str {
    return "Hello, " + name + "!"
}

fn add(a: int, b: int) -> int {
    return a + b
}

fn main() {
    let msg = greet("World")
    println(msg)
    let sum = add(2, 3)
    println(sum)
}
'''


@pytest.fixture
def math_source():
    """A LATERALUS program using math features."""
    return '''
let values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
let avg = values |> mean
let dev = values |> std_dev
println("Mean: " + str(avg))
println("Std Dev: " + str(dev))
'''


@pytest.fixture
def crypto_source():
    """A LATERALUS program using crypto features."""
    return '''
let message = "Hello, LATERALUS!"
let hash = sha256(message)
let token = random_token(32)
let encoded = to_base64(message)
let decoded = from_base64(encoded)
println("Hash: " + hash)
println("Token: " + token)
'''


@pytest.fixture
def ltlml_source():
    """A sample LTLML document for testing."""
    return '''---
title: Test Document
author: LATERALUS Test Suite
date: 2025-01-20
---

# Test Heading

This is a **bold** and _italic_ test paragraph.

## Code Example

```lateralus
fn fibonacci(n: int) -> int {
    if n <= 1 { return n }
    return fibonacci(n - 1) + fibonacci(n - 2)
}
```

## Math

The quadratic formula: $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$

## Table

| Feature | Status |
|---------|--------|
| Pipelines | Done |
| Math Engine | Done |
| Crypto | Done |
'''


@pytest.fixture
def tmp_ltl_file(tmp_path, sample_source):
    """Create a temporary .ltl file."""
    f = tmp_path / "test.ltl"
    f.write_text(sample_source)
    return f


@pytest.fixture
def tmp_ltlml_file(tmp_path, ltlml_source):
    """Create a temporary .ltlml file."""
    f = tmp_path / "test.ltlml"
    f.write_text(ltlml_source)
    return f


@pytest.fixture
def v15_source():
    """A v1.5 ADT program exercising Result/Option/match."""
    return '''
fn safe_divide(a: float, b: float) -> Result<float, str> {
    if b == 0.0 {
        return Result::Err("division by zero")
    }
    return Result::Ok(a / b)
}

fn find_item(items: list, target: str) -> Option<int> {
    for i in range(len(items)) {
        if items[i] == target {
            return Option::Some(i)
        }
    }
    return Option::None
}

fn main() {
    let r = safe_divide(10.0, 3.0)
    let label = match r {
        Result::Ok(v) if v > 5.0 => "high",
        Result::Ok(v)             => "ok: " + str(v),
        Result::Err(msg)          => "error: " + msg,
    }
    println(label)
}
'''


# ==========================================================================
# Temp-file factories
# ==========================================================================

@pytest.fixture
def ltl_file_factory(tmp_path):
    """Factory fixture: call with source code to get a temp .ltl file path."""
    _counter = [0]
    def _make(source: str, name: str = None) -> Path:
        _counter[0] += 1
        fname = name or f"test_{_counter[0]}.ltl"
        f = tmp_path / fname
        f.write_text(source)
        return f
    return _make


@pytest.fixture
def ltasm_file_factory(tmp_path):
    """Factory fixture: call with source code to get a temp .ltasm file path."""
    _counter = [0]
    def _make(source: str, name: str = None) -> Path:
        _counter[0] += 1
        fname = name or f"test_{_counter[0]}.ltasm"
        f = tmp_path / fname
        f.write_text(source)
        return f
    return _make


# ==========================================================================
# Example & stdlib discovery (for parametrize)
# ==========================================================================

def discover_examples(ext: str = ".ltl") -> list[str]:
    """Discover all example files of a given extension."""
    return sorted(str(p) for p in EXAMPLES_DIR.glob(f"*{ext}") if p.is_file())


def discover_stdlib() -> list[str]:
    """Discover all standard library .ltl modules."""
    return sorted(str(p) for p in STDLIB_DIR.glob("*.ltl") if p.is_file())


def example_ids(paths: list[str]) -> list[str]:
    """Generate short test IDs from file paths."""
    return [Path(p).stem for p in paths]


# ==========================================================================
# Timing helper
# ==========================================================================

class Timer:
    """Context manager that records elapsed time."""
    def __init__(self):
        self.elapsed_ms = 0.0
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


@pytest.fixture
def timer():
    """Returns a Timer context manager."""
    return Timer
