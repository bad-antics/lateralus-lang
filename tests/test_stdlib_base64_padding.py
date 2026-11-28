"""Execute the real stdlib validator and compare padding with an independent decoder."""
import pytest

from lateralus_lang.compiler import Compiler, Target


def test_base64_is_valid_padding_validation():
    """Verify stdlib/base64.ltl is_valid rejects invalid padding positions/quantities."""
    with open("stdlib/base64.ltl") as f:
        src = f.read()

    res = Compiler().compile_source(src, target=Target.PYTHON, filename="base64.ltl")
    assert res.ok, f"Compilation failed: {res.errors}"

    scope = {}
    exec(res.python_src, scope)
    is_valid_fn = scope["is_valid"]

    invalid_inputs = [
        "====",
        "=AAA",
        "AA=A",
        "AA==AAAA",
        "==AA",
        "===A",
        "A===",
        "=A==",
        "A=AA",
    ]
    for s in invalid_inputs:
        assert not is_valid_fn(s), f"Expected false for {s!r}"

    valid_inputs = [
        "",
        "AAAA",
        "AA==",
        "AAA=",
        "QUJD",
        "QUI=",
        "QQ==",
    ]
    for s in valid_inputs:
        assert is_valid_fn(s), f"Expected true for {s!r}"
"""Execute the real stdlib validator and compare padding with an independent decoder."""
import pytest

from lateralus_lang.compiler import Compiler, Target


def test_base64_is_valid_padding_validation():
    """Verify stdlib/base64.ltl is_valid rejects invalid padding positions/quantities."""
    with open("stdlib/base64.ltl") as f:
        src = f.read()

    res = Compiler().compile_source(src, target=Target.PYTHON, filename="base64.ltl")
    assert res.ok, f"Compilation failed: {res.errors}"

    scope = {}
    exec(res.python_src, scope)
    is_valid_fn = scope["is_valid"]

    invalid_inputs = [
        "====",
        "=AAA",
        "AA=A",
        "AA==AAAA",
        "==AA",
        "===A",
        "A===",
        "=A==",
        "A=AA",
    ]
    for s in invalid_inputs:
        assert not is_valid_fn(s), f"Expected false for {s!r}"

    valid_inputs = [
        "",
        "AAAA",
        "AA==",
        "AAA=",
        "QUJD",
        "QUI=",
        "QQ==",
    ]
    for s in valid_inputs:
        assert is_valid_fn(s), f"Expected true for {s!r}"
"""Execute the real stdlib validator and compare padding with an independent decoder."""
import pytest

from lateralus_lang.compiler import Compiler, Target


def test_base64_is_valid_padding_validation():
    """Verify stdlib/base64.ltl is_valid rejects invalid padding positions/quantities."""
    with open("stdlib/base64.ltl") as f:
        src = f.read()

    res = Compiler().compile_source(src, target=Target.PYTHON, filename="base64.ltl")
    assert res.ok, f"Compilation failed: {res.errors}"

    scope = {}
    exec(res.python_src, scope)
    is_valid_fn = scope["is_valid"]

    invalid_inputs = [
        "====",
        "=AAA",
        "AA=A",
        "AA==AAAA",
        "==AA",
        "===A",
        "A===",
        "=A==",
        "A=AA",
    ]
    for s in invalid_inputs:
        assert not is_valid_fn(s), f"Expected false for {s!r}"

    valid_inputs = [
        "",
        "AAAA",
        "AA==",
        "AAA=",
        "QUJD",
        "QUI=",
        "QQ==",
    ]
    for s in valid_inputs:
        assert is_valid_fn(s), f"Expected true for {s!r}"
