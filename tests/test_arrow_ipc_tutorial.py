"""
tests/test_arrow_ipc_tutorial.py - Comprehensive verification for stdlib/arrow_ipc.ltl
Tests Apache Arrow IPC stream framing, 8-byte alignment padding, validity bitmap
little-endian bit twiddling, Int32 columnar buffer encoding, and variable-length UTF-8 buffers.
"""
from pathlib import Path
import struct
from lateralus_lang.compiler import Compiler, Target

def test_validity_bitmap_little_endian_and_padding():
    arrow_src = Path("stdlib/arrow_ipc.ltl").read_text(encoding="utf-8")
    driver = r"""
let flags = [true, false, true, true, false, false, true, false, true]
let bmp = validity_bitmap(flags)
let bmp_len = len(bmp)
"""
    c = Compiler()
    res = c.compile_source(arrow_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    bmp = ns["bmp"]
    assert ns["bmp_len"] % 8 == 0, "Validity bitmap must be 8-byte aligned"
    # Bit 0 = 1, Bit 2 = 1, Bit 3 = 1, Bit 6 = 1 -> 1 + 4 + 8 + 64 = 77 (0x4D)
    assert bmp[0] == 77
    # Bit 8 = Bit 0 of byte 1 -> 1
    assert bmp[1] == 1
    # Trailing padding bytes must be 0
    assert bmp[2:] == [0, 0, 0, 0, 0, 0]

def test_buffer_i32_endianness_and_negative_values():
    arrow_src = Path("stdlib/arrow_ipc.ltl").read_text(encoding="utf-8")
    driver = r"""
let values = [0, 1, -1, 2147483647, -2147483648]
let buf = buffer_i32(values)
let buf_len = len(buf)
"""
    c = Compiler()
    res = c.compile_source(arrow_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    buf = bytes(ns["buf"])
    assert ns["buf_len"] % 8 == 0, "Int32 buffer must be 8-byte aligned"
    unpacked = struct.unpack("<5i", buf[:20])
    assert list(unpacked) == [0, 1, -1, 2147483647, -2147483648]

def test_buffers_utf8_monotonic_offsets_and_payload():
    arrow_src = Path("stdlib/arrow_ipc.ltl").read_text(encoding="utf-8")
    driver = r"""
let words = ["hello", "arrow", "world"]
let bufs = buffers_utf8(words)
let off_buf = bufs[0]
let data_buf = bufs[1]
"""
    c = Compiler()
    res = c.compile_source(arrow_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    off_bytes = bytes(ns["off_buf"])
    data_bytes = bytes(ns["data_buf"])
    assert len(off_bytes) % 8 == 0
    assert len(data_bytes) % 8 == 0

    # Offsets: [0, 5, 10, 15] for lengths 5, 5, 5
    offsets = list(struct.unpack("<4i", off_bytes[:16]))
    assert offsets == [0, 5, 10, 15]
    assert data_bytes[:15] == b"helloarrowworld"

def test_arrow_ipc_framing_and_eos():
    arrow_src = Path("stdlib/arrow_ipc.ltl").read_text(encoding="utf-8")
    driver = r"""
let meta = [10, 20, 30]
let body = [100, 101, 102, 103, 104]
let msg = frame_message(meta, body)
let hdr = parse_frame_header(msg, 0)

let eos = end_of_stream()
let eos_hdr = parse_frame_header(eos, 0)
"""
    c = Compiler()
    res = c.compile_source(arrow_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    msg = ns["msg"]
    hdr = ns["hdr"]
    assert hdr is not None
    assert hdr["metadata_len"] == 8  # 3 bytes padded to 8
    assert hdr["header_size"] == 8
    # 8 header + 8 metadata + 8 body (5 padded to 8) = 24 bytes
    assert len(msg) == 24

    eos = ns["eos"]
    eos_hdr = ns["eos_hdr"]
    assert eos_hdr is not None
    assert eos_hdr["metadata_len"] == 0
    assert len(eos) == 8
