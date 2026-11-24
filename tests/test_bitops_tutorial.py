"""
tests/test_bitops_tutorial.py - Comprehensive verification for stdlib/bitops.ltl
Tests bit twiddling (bit_set, bit_clear, bit_toggle, bit_test), bitfield insertion/extraction,
popcount, leading/trailing zero counting, endian bswaps, circular rotations, and power-of-two helpers.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_bitops_manipulation_and_counting():
    bitops_src = Path("stdlib/bitops.ltl").read_text(encoding="utf-8")
    driver = r"""
let s = bit_set(0, 3)
let t_true = bit_test(s, 3)
let t_false = bit_test(s, 2)
let c = bit_clear(s, 3)
let tog1 = bit_toggle(0, 5)
let tog2 = bit_toggle(tog1, 5)

let field = extract_bits(0b10111100, 2, 4)
let inserted = insert_bits(0, 0b1010, 4, 4)

let pop = popcount(0b1011001)
let tz = ctz(0b1011000)
let lz = clz(1)
let hbit = highest_bit(0b1000)
let lbit = lowest_bit(0b1000)
"""
    c = Compiler()
    res = c.compile_source(bitops_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["s"] == 8
    assert ns["t_true"] is True
    assert ns["t_false"] is False
    assert ns["c"] == 0
    assert ns["tog1"] == 32
    assert ns["tog2"] == 0

    assert ns["field"] == 15
    assert ns["inserted"] == 0xA0

    assert ns["pop"] == 4
    assert ns["tz"] == 3
    assert ns["lz"] == 63
    assert ns["hbit"] == 3
    assert ns["lbit"] == 3

def test_bitops_endian_rotations_and_math():
    bitops_src = Path("stdlib/bitops.ltl").read_text(encoding="utf-8")
    driver = r"""
let bs16 = bswap16(0x1234)
let bs32 = bswap32(0x12345678)

let rl32 = rotl32(0x80000000, 1)
let rr32 = rotr32(0x00000001, 1)
let rl64 = rotl64(0x8000000000000000, 1)
let rr64 = rotr64(0x0000000000000001, 1)

let p2_true = is_power_of_2(16)
let p2_false = is_power_of_2(18)
let np2 = next_power_of_2(17)
let lg = log2(64)
"""
    c = Compiler()
    res = c.compile_source(bitops_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["bs16"] == 0x3412
    assert ns["bs32"] == 0x78563412

    assert ns["rl32"] == 1
    assert ns["rr32"] == 0x80000000
    assert ns["rl64"] == 1
    assert ns["rr64"] == 0x8000000000000000

    assert ns["p2_true"] is True
    assert ns["p2_false"] is False
    assert ns["np2"] == 32
    assert ns["lg"] == 6
