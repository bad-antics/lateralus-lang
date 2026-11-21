"""
tests/test_base64_tutorial.py - Comprehensive verification for stdlib/base64.ltl
Tests RFC 4648 standard base64 encoding/decoding, URL-safe transforms,
validation checks, and length estimation formulas.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_base64_standard_encoding_and_decoding():
    base64_src = Path("stdlib/base64.ltl").read_text(encoding="utf-8")
    driver = r"""
let msg1 = "Hello, World!"
let enc1 = encode(msg1)
let dec1 = decode(enc1)

let msg2 = "a"
let enc2 = encode(msg2)
let dec2 = decode(enc2)

let msg3 = "ab"
let enc3 = encode(msg3)
let dec3 = decode(enc3)

let msg4 = "abc"
let enc4 = encode(msg4)
let dec4 = decode(enc4)
"""
    c = Compiler()
    res = c.compile_source(base64_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["enc1"] == "SGVsbG8sIFdvcmxkIQ=="
    assert ns["dec1"] == "Hello, World!"

    assert ns["enc2"] == "YQ=="
    assert ns["dec2"] == "a"

    assert ns["enc3"] == "YWI="
    assert ns["dec3"] == "ab"

    assert ns["enc4"] == "YWJj"
    assert ns["dec4"] == "abc"

def test_base64_url_safe_and_utilities():
    base64_src = Path("stdlib/base64.ltl").read_text(encoding="utf-8")
    driver = r"""
let special = "query?param=+data/val=="
let url_enc = encode_url(special)
let url_dec = decode_url(url_enc)

let valid1 = is_valid("YWJj")
let valid2 = is_valid("SGVsbG8=")
let invalid1 = is_valid("abc")
let invalid2 = is_valid("SGVsbG8!")

let len0 = encoded_length(0)
let len1 = encoded_length(1)
let len2 = encoded_length(2)
let len3 = encoded_length(3)
let len4 = encoded_length(4)

let dlen1 = decoded_length("YWJj")
let dlen2 = decoded_length("YWI=")
let dlen3 = decoded_length("YQ==")
"""
    c = Compiler()
    res = c.compile_source(base64_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert "+" not in ns["url_enc"]
    assert "/" not in ns["url_enc"]
    assert ns["url_dec"] == "query?param=+data/val=="

    assert ns["valid1"] is True
    assert ns["valid2"] is True
    assert ns["invalid1"] is False
    assert ns["invalid2"] is False

    assert ns["len0"] == 0
    assert ns["len1"] == 4
    assert ns["len2"] == 4
    assert ns["len3"] == 4
    assert ns["len4"] == 8

    assert ns["dlen1"] == 3
    assert ns["dlen2"] == 2
    assert ns["dlen3"] == 1
