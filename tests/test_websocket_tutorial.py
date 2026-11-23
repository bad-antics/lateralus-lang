"""
tests/test_websocket_tutorial.py - Comprehensive verification for stdlib/websocket.ltl
Tests RFC 6455 WebSocket framing, FIN and opcode extraction, masking key XOR transformations,
126/127 extended length encoding, close frames, and canonical Sec-WebSocket-Accept handshakes.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_websocket_text_frame_roundtrip():
    ws_src = Path("stdlib/websocket.ltl").read_text(encoding="utf-8")
    driver = r"""
let msg = "Hello, WebSocket!"
let payload = bytes_of(msg)
let frame = encode_frame(1, op_text(), payload)
let decoded = decode_frame(frame)

let is_fin = decoded["fin"]
let op = decoded["opcode"]
let got_payload = decoded["payload"]
let consumed = decoded["consumed"]
"""
    c = Compiler()
    res = c.compile_source(ws_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["is_fin"] == 1
    assert ns["op"] == 1  # op_text()
    assert bytes(ns["got_payload"]).decode("utf-8") == "Hello, WebSocket!"
    assert ns["consumed"] == len(ns["frame"])

def test_websocket_payload_length_tiers():
    ws_src = Path("stdlib/websocket.ltl").read_text(encoding="utf-8")
    driver = r"""
// Tier 1: Small (< 126 bytes)
let p_small = [1, 2, 3, 4, 5]
let f_small = encode_frame(1, op_binary(), p_small)
let d_small = decode_frame(f_small)

// Tier 2: Medium (>= 126 and < 65536 bytes)
let p_med = []
let i = 0
while i < 300 { p_med = p_med + [65]; i = i + 1 }
let f_med = encode_frame(1, op_binary(), p_med)
let d_med = decode_frame(f_med)
"""
    c = Compiler()
    res = c.compile_source(ws_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    # Small frame header: 2 bytes
    assert len(ns["f_small"]) == 7
    assert ns["d_small"]["payload"] == [1, 2, 3, 4, 5]

    # Medium frame header: 4 bytes (header byte + 126 indicator + 2-byte length)
    assert len(ns["f_med"]) == 304
    assert len(ns["d_med"]["payload"]) == 300

def test_websocket_masked_client_frame():
    ws_src = Path("stdlib/websocket.ltl").read_text(encoding="utf-8")
    driver = r"""
let data = [10, 20, 30, 40, 50]
let mask = [0xFA, 0xCE, 0xB0, 0x0C]
let frame = encode_masked(1, op_binary(), data, mask)
let decoded = decode_frame(frame)
let unmasked = decoded["payload"]
let mask_key = decoded["mask"]
"""
    c = Compiler()
    res = c.compile_source(ws_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["mask_key"] == [0xFA, 0xCE, 0xB0, 0x0C]
    assert ns["unmasked"] == [10, 20, 30, 40, 50]

def test_websocket_close_frame_code_and_reason():
    ws_src = Path("stdlib/websocket.ltl").read_text(encoding="utf-8")
    driver = r"""
let f_close = close_frame(1001, "going away")
let d_close = decode_frame(f_close)
let p = d_close["payload"]
let status_code = (p[0] << 8) | p[1]
let reason_bytes = slice(p, 2, len(p))
"""
    c = Compiler()
    res = c.compile_source(ws_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["d_close"]["opcode"] == 8  # op_close()
    assert ns["status_code"] == 1001
    assert bytes(ns["reason_bytes"]).decode("utf-8") == "going away"

def test_websocket_rfc6455_handshake_accept():
    ws_src = Path("stdlib/websocket.ltl").read_text(encoding="utf-8")
    driver = r"""
let client_key = "dGhlIHNhbXBsZSBub25jZQ=="
let accept = compute_accept(client_key)
"""
    c = Compiler()
    res = c.compile_source(ws_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    # Official RFC 6455 Section 1.3 test vector
    assert ns["accept"] == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
