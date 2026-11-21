"""
tests/test_msgpack_tutorial.py - Tests for stdlib/msgpack.ltl
Verifies MessagePack specification pinned vectors, roundtrip encoding/decoding,
and stream offset progression.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_msgpack_canonical_pinned_vectors():
    msgpack_src = Path("stdlib/msgpack.ltl").read_text(encoding="utf-8")
    driver = """
let enc_nil = encode(nil)
let enc_false = encode(false)
let enc_true = encode(true)
let enc_fixint = encode(42)
let enc_neg_fixint = encode(-10)
let enc_u8 = encode(200)
let enc_u16 = encode(1000)
let enc_str = encode("hello")
let enc_arr = encode([10, 20, 30])
let enc_map = encode({ x: 5 })

let dec_nil = decode(enc_nil)[0]
let dec_false = decode(enc_false)[0]
let dec_true = decode(enc_true)[0]
let dec_fixint = decode(enc_fixint)[0]
let dec_neg_fixint = decode(enc_neg_fixint)[0]
let dec_u8 = decode(enc_u8)[0]
let dec_u16 = decode(enc_u16)[0]
let dec_str = decode(enc_str)[0]
let dec_arr = decode(enc_arr)[0]
let dec_map = decode(enc_map)[0]
"""
    c = Compiler()
    res = c.compile_source(msgpack_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    # 1. Pinned vector checks per MessagePack specification
    assert ns["enc_nil"] == [0xc0]
    assert ns["enc_false"] == [0xc2]
    assert ns["enc_true"] == [0xc3]
    assert ns["enc_fixint"] == [42]
    assert ns["enc_neg_fixint"] == [0xe0 | (-10 & 31)]
    assert ns["enc_u8"] == [0xcc, 200]
    assert ns["enc_u16"] == [0xcd, 3, 232]
    assert ns["enc_str"] == [0xa5, 104, 101, 108, 108, 111]
    assert ns["enc_arr"] == [0x93, 10, 20, 30]
    assert ns["enc_map"] == [0x81, 0xa1, ord('x'), 5]

    # 2. Deserialization identity checks
    assert ns["dec_nil"] is None
    assert ns["dec_false"] is False
    assert ns["dec_true"] is True
    assert ns["dec_fixint"] == 42
    assert ns["dec_neg_fixint"] == -10
    assert ns["dec_u8"] == 200
    assert ns["dec_u16"] == 1000
    assert ns["dec_str"] == "hello"
    assert ns["dec_arr"] == [10, 20, 30]
    assert ns["dec_map"] == {"x": 5}

def test_msgpack_stream_decoding():
    msgpack_src = Path("stdlib/msgpack.ltl").read_text(encoding="utf-8")
    driver = """
let stream = encode("first") + encode(999) + encode(true)

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
    res = c.compile_source(msgpack_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["v1"] == "first"
    assert ns["v2"] == 999
    assert ns["v3"] is True
    assert ns["idx3"] == len(ns["stream"])
