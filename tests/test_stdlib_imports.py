"""Regression tests for stdlib import resolution.

`import <name>` used to emit a plain Python import, so a stdlib module was
never loaded unless its name also happened to be an installed Python package.
These tests pin the fixed behaviour: stdlib/<name>.ltl is inlined and its
functions are callable, while modules that do not exist still raise.
"""

import pathlib

import pytest

C = pytest.importorskip("lateralus_lang.compiler")
from lateralus_lang.compiler import Compiler


def _run(tmp_path: pathlib.Path, source: str):
    f = tmp_path / "prog.ltl"
    f.write_text(source, encoding="utf-8")
    return Compiler().run_file(str(f))


def test_stdlib_module_import_exposes_functions(tmp_path):
    """A stdlib-only module name must resolve, not raise ModuleNotFoundError."""
    res = _run(
        tmp_path,
        "import crc\n"
        'fn main() { println(crc32([0x31, 0x32, 0x33])) }\n',
    )
    assert res.ok, getattr(res, "errors", None)


def test_crc32_check_value(tmp_path, capfd):
    """CRC-32 of the ASCII string "123456789" is the standard 0xCBF43926."""
    src = (
        "import crc\n"
        "fn main() {\n"
        "    let d = [0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39]\n"
        "    println(crc32(d))\n"
        "    println(crc16_arc(d))\n"
        "    println(crc16_ccitt(d))\n"
        "    println(crc8(d))\n"
        "}\n"
    )
    res = _run(tmp_path, src)
    assert res.ok, getattr(res, "errors", None)
    out = capfd.readouterr().out.split()
    assert out == ["3421780262", "47933", "10673", "244"]


def test_crc_self_test(tmp_path, capfd):
    res = _run(tmp_path, "import crc\nfn main() { println(self_test()) }\n")
    assert res.ok, getattr(res, "errors", None)
    assert "True" in capfd.readouterr().out


def test_unknown_module_still_raises(tmp_path):
    """Resolution must not swallow a genuinely missing module."""
    res = _run(tmp_path, "import defnot_a_real_module\nfn main() { println(1) }\n")
    assert not res.ok


def test_python_package_name_still_imports(tmp_path):
    """A name that is both a Python package and absent from stdlib keeps working."""
    pytest.importorskip("yaml")
    res = _run(tmp_path, "import yaml\nfn main() { println(1) }\n")
    assert res.ok, getattr(res, "errors", None)
