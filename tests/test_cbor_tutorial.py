"""
tests/test_cbor_tutorial.py - Tests for stdlib/cbor.ltl
Verifies RFC 8949 canonical pinned test vectors, roundtrip decoding,
and stream offset progression with decode_at.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_cbor_rfc8949_canonical_vectors():
    cbor_src = Path("stdlib/cbor.ltl").read_text(encoding="utf-8")
    driver = """
let enc_u0 = encode(0)
let enc_u1 = encode(1)
let enc_u10 = encode(10)
let enc_u23 = encode(23)
let enc_u24 = encode(24)
let enc_u100 = encode(100)
let enc_u1000 = encode(1000)

let enc_n1 = encode(-1)
let enc_n10 = encode(-10)
let enc_n100 = encode(-100)

let enc_f = encode(false)
let enc_t = encode(true)
let enc_nil = encode(nil)

let enc_str = encode("hello")
let enc_arr = encode([1, 2, 3])
let enc_map = encode({ a: 1 })

let dec_u0 = decode(enc_u0)
let dec_u1 = decode(enc_u1)
let dec_u10 = decode(enc_u10)
let dec_u23 = decode(enc_u23)
let dec_u24 = decode(enc_u24)
let dec_u100 = decode(enc_u100)
let dec_u1000 = decode(enc_u1000)

let dec_n1 = decode(enc_n1)
let dec_n10 = decode(enc_n10)
let dec_n100 = decode(enc_n100)

let dec_f = decode(enc_f)
let dec_t = decode(enc_t)
let dec_nil = decode(enc_nil)

let dec_str = decode(enc_str)
let dec_arr = decode(enc_arr)
let dec_map = decode(enc_map)
"""
    c = Compiler()
    res = c.compile_source(cbor_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    # 1. Exact RFC 8949 Appendix A canonical vectors
    assert ns["enc_u0"] == [0x00]
    assert ns["enc_u1"] == [0x01]
    assert ns["enc_u10"] == [0x0a]
    assert ns["enc_u23"] == [0x17]
    assert ns["enc_u24"] == [0x18, 0x18]
    assert ns["enc_u100"] == [0x18, 0x64]
    assert ns["enc_u1000"] == [0x19, 0x03, 0xe8]

    assert ns["enc_n1"] == [0x20]
    assert ns["enc_n10"] == [0x29]
    assert ns["enc_n100"] == [0x38, 0x63]

    assert ns["enc_f"] == [0xf4]
    assert ns["enc_t"] == [0xf5]
    assert ns["enc_nil"] == [0xf6]

    assert ns["enc_str"] == [0x65, ord('h'), ord('e'), ord('l'), ord('l'), ord('o')]
    assert ns["enc_arr"] == [0x83, 1, 2, 3]
    assert ns["enc_map"] == [0xa1, 0x61, ord('a'), 1]

    # 2. Decoded values match originals
    assert ns["dec_u0"] == 0
    assert ns["dec_u1"] == 1
    assert ns["dec_u10"] == 10
    assert ns["dec_u23"] == 23
    assert ns["dec_u24"] == 24
    assert ns["dec_u100"] == 100
    assert ns["dec_u1000"] == 1000

    assert ns["dec_n1"] == -1
    assert ns["dec_n10"] == -10
    assert ns["dec_n100"] == -100

    assert ns["dec_f"] is False
    assert ns["dec_t"] is True
    assert ns["dec_nil"] is None

    assert ns["dec_str"] == "hello"
    assert ns["dec_arr"] == [1, 2, 3]
    assert ns["dec_map"] == {"a": 1}

def test_cbor_stream_decoding():
    cbor_src = Path("stdlib/cbor.ltl").read_text(encoding="utf-8")
    driver = """
let stream = encode("telemetry") + encode(42) + encode(true)

let p1 = decode_at(stream, 0)
let v1 = p1[0]
let idx1 = p1[1]

let p2 = decode_at(stream, idx1)
let v2 = p2[0]
let idx2 = p2[1]

let p3 = decode_at(stream, idx2)
let v3 = p3[0]
let idx3 = p3[1]
"""
    c = Compiler()
    res = c.compile_source(cbor_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["v1"] == "telemetry"
    assert ns["v2"] == 42
    assert ns["v3"] is True
    assert ns["idx3"] == len(ns["stream"])
