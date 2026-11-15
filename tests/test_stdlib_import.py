"""
tests/test_stdlib_import.py — `import <module>` of stdlib/*.ltl, and the
runtime pieces those modules rely on (char_at, bytes_of, regex_*, ...).

Before this, `import logfmt` transpiled to a Python `import logfmt` and
failed with ModuleNotFoundError; the stdlib .ltl modules were unusable
from programs run with `lateralus run`.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from lateralus_lang.compiler import Compiler, Target
from lateralus_lang.lexer import lex

REPO = Path(__file__).resolve().parent.parent


def run_ltl(tmp_path, src, *args, stdin=b""):
    f = tmp_path / "prog.ltl"
    f.write_text(src, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(f), *args],
        input=stdin, capture_output=True, timeout=120, env=env, cwd=str(REPO))


def out(proc):
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return proc.stdout.decode("utf-8").splitlines()


def test_import_stdlib_module(tmp_path):
    proc = run_ltl(tmp_path, """
import logfmt
import aho_corasick
fn main() {
    let p = logfmt.parse("a=1 msg=\\"two words\\"")
    print(p[1][1])
    let a = aho_corasick.build(["he", "she", "hers"])
    print(str(len(aho_corasick.find_all(a, "ushers"))))
}
""")
    assert out(proc) == ["two words", "3"]


def test_imported_module_is_embedded_in_output():
    res = Compiler().compile_source("import logfmt\nprint(logfmt.format_value(\"a b\"))\n",
                                    "<t>", Target.PYTHON)
    assert res.ok
    assert "logfmt = _ltl_load_module('logfmt'," in res.python_src
    assert "import logfmt" not in res.python_src.replace("# ", "")


def test_unknown_import_unchanged():
    res = Compiler().compile_source("import no_such_module_xyz\n", "<t>", Target.PYTHON)
    assert res.ok
    assert "import no_such_module_xyz as no_such_module_xyz" in res.python_src


def test_module_that_does_not_compile_keeps_python_import():
    # stdlib/json.ltl is written in an older dialect and does not parse;
    # `import json` keeps meaning Python's json module, as before.
    res = Compiler().compile_source("import json\n", "<t>", Target.PYTHON)
    assert res.ok
    assert "import json as json" in res.python_src


def test_regex_module(tmp_path):
    proc = run_ltl(tmp_path, """
import regex
fn main() {
    print(str(regex.is_ipv4("10.0.0.1")) + " " + str(regex.is_ipv4("10.0.0")))
    print(str(regex.is_email("a.b@example.com")) + " " + str(regex.is_email("a@b")))
    print(str(regex.groups("(\\\\w+)@(\\\\w+)", "x me@host y")))
    print(regex.replace_all("\\\\d", "a1b22", "#"))
}
""")
    assert out(proc) == ["True False", "True False", "['me', 'host']", "a#b##"]


def test_args_reach_the_program(tmp_path):
    proc = run_ltl(tmp_path, "fn main() { print(str(args())) }\n", "x", "--flag", "-v")
    assert out(proc) == ["['x', '--flag', '-v']"]


def test_stdin_and_byte_builtins(tmp_path):
    proc = run_ltl(tmp_path, """
fn main() {
    let n = 0
    let line = stdin_read_line()
    while line != nil {
        n = n + len(bytes_of(line))
        line = stdin_read_line()
    }
    print(str(n) + " " + char_at("abc", 1) + " " + str(index_of("abc", "c")))
    stdout_write(str_of_bytes(bytes_of("hé")) + "\\n")
    print(json_encode(json_parse("[1, \\"x\\"]")))
}
""", stdin=b"h\xc3\xa9\r\nab\n\xff\xfe")
    # "hé" = 3 UTF-8 bytes (CRLF stripped), "ab" = 2, and the two invalid
    # bytes decode to two U+FFFD (3 bytes each) instead of raising.
    assert out(proc) == ["11 b 2", "hé", '[1,"x"]']


def test_double_brace_is_a_literal_brace():
    toks = lex('"{{x} {y}"', "<t>")
    assert toks[0].value == [("str", "{x} "), ("expr", "y"), ("str", "")]
    assert lex('"{{}"', "<t>")[0].value == "{}"


def test_fn_named_match_parses():
    # stdlib/regex.ltl declares `pub fn match`; `match` stays a keyword
    # everywhere else.
    res = Compiler().compile_source(
        "pub fn match(a: int) -> int { return a + 1 }\n", "<t>", Target.PYTHON)
    assert res.ok, res.errors
    assert "def match(a: int)" in res.python_src


@pytest.mark.parametrize("size", [0, 5, 100, 70000])
def test_lz4_and_chacha20_reference_vectors(size):
    lz4_block = pytest.importorskip("lz4.block")
    import random
    import types
    rnd = random.Random(size)
    data = bytes(rnd.choice(b"abcdefgh ") for _ in range(size))

    def load(name):
        src = Compiler().compile_file(str(REPO / "stdlib" / f"{name}.ltl"),
                                      Target.PYTHON).python_src
        m = types.ModuleType(name)
        exec(compile(src, name, "exec"), m.__dict__)
        return m

    lz4 = load("lz4")
    comp = lz4.compress(list(data))
    assert lz4_block.decompress(bytes(comp), uncompressed_size=size) == data
    assert lz4.decompress(list(lz4_block.compress(data, store_size=False))) == list(data)

    aead = pytest.importorskip("cryptography.hazmat.primitives.ciphers")
    cc = load("chacha20")
    key, nonce = bytes(range(32)), bytes(range(12))
    # RFC 8439 ChaCha20 with a 32-bit counter; `cryptography` takes the
    # 4-byte little-endian counter followed by the 96-bit nonce.
    ref = aead.Cipher(aead.algorithms.ChaCha20(key, (1).to_bytes(4, "little") + nonce),
                      mode=None).encryptor().update(data)
    assert bytes(cc.xor(list(key), list(nonce), 1, list(data))) == ref
