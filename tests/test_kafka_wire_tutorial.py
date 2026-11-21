"""
tests/test_kafka_wire_tutorial.py - Comprehensive tests for stdlib/kafka_wire.ltl
Verifies integer codecs, varints, strings, compact formats, request header v1/v2,
request framing, and response parsing.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_kafka_wire_primitives_and_varints():
    kw_src = Path("stdlib/kafka_wire.ltl").read_text(encoding="utf-8")
    driver = """
// 1. Fixed width integer round-trips
let b8 = enc_i8(42)
let r8 = dec_i8(b8, 0)
let v8 = r8[0]

let b16 = enc_i16(1337)
let r16 = dec_i16(b16, 0)
let v16 = r16[0]

let b32 = enc_i32(1000000)
let r32 = dec_i32(b32, 0)
let v32 = r32[0]

let b64 = enc_i64(9876543210)
let r64 = dec_i64(b64, 0)
let v64 = r64[0]

// 2. Varint & Zig-Zag round-trips
let uvar1 = enc_uvarint(300)
let ru1 = dec_uvarint(uvar1, 0)
let vu1 = ru1[0]

let zz_pos = zz_encode(15)
let zz_neg = zz_encode(0 - 15)
let dec_pos = zz_decode(zz_pos)
let dec_neg = zz_decode(zz_neg)

let var_neg = enc_varint(0 - 42)
let rvn = dec_varint(var_neg, 0)
let v_neg = rvn[0]
"""
    c = Compiler()
    res = c.compile_source(kw_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["v8"] == 42
    assert ns["v16"] == 1337
    assert ns["v32"] == 1000000
    assert ns["v64"] == 9876543210
    assert ns["vu1"] == 300
    assert ns["dec_pos"] == 15
    assert ns["dec_neg"] == -15
    assert ns["v_neg"] == -42

def test_kafka_wire_strings_and_framing():
    kw_src = Path("stdlib/kafka_wire.ltl").read_text(encoding="utf-8")
    driver = """
// 1. Classic string & nullable string
let s_bytes = enc_string("orders-topic")
let r_str = dec_string(s_bytes, 0)
let val_str = r_str[0]

let null_bytes = enc_nullable_string(nil)
let r_null = dec_string(null_bytes, 0)
let val_null = r_null[0]

// 2. Compact string (KIP-482)
let cs_bytes = enc_compact_string("compact-payload")
let r_cstr = dec_compact_string(cs_bytes, 0)
let val_cstr = r_cstr[0]

// 3. Request Header v1 & v2
let h1 = request_header_v1(api_produce(), 3, 101, "client-app")
let h2 = request_header_v2(api_api_versions(), 0, 102, "client-app")

// 4. Request Framing
let frame = frame_request(h1)
let frame_len = len(frame)

// 5. Response Parsing
// Build simulated broker response frame: 4 bytes length, 4 bytes corr_id (101), payload [1, 2, 3]
let resp_payload = [1, 2, 3]
let sim_corr = enc_i32(101)
let sim_body = sim_corr + resp_payload
let sim_resp = frame_request(sim_body)

let parsed = parse_response_frame(sim_resp, 0)
let parsed_corr = parsed[0]
let parsed_body = parsed[1]
"""
    c = Compiler()
    res = c.compile_source(kw_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["val_str"] == "orders-topic"
    assert ns["val_null"] is None
    assert ns["val_cstr"] == "compact-payload"
    assert len(ns["h1"]) > 0
    assert len(ns["h2"]) == len(ns["h1"]) + 1 # exactly 1 extra byte for empty tagged fields (uvarint 0)
    assert ns["frame_len"] == len(ns["h1"]) + 4
    assert ns["parsed_corr"] == 101
    assert ns["parsed_body"] == [1, 2, 3]
