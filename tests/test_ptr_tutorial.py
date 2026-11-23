"""
tests/test_ptr_tutorial.py - Verification suite for stdlib/ptr.ltl
Verifies pointer null checks, pointer arithmetic, power-of-two alignment,
typed memory access, volatile access, and block copy/zero helpers.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target


def run_ptr_snippet(driver: str) -> dict:
    ptr_src = Path("stdlib/ptr.ltl").read_text(encoding="utf-8")
    c = Compiler()
    res = c.compile_source(ptr_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    return ns


def test_ptr_null_and_validity():
    driver = r"""
let p0 = null()
let check_null = is_null(p0)
let check_valid_p0 = is_valid(p0)

let p100 = offset(p0, 100)
let check_null_p100 = is_null(p100)
let check_valid_p100 = is_valid(p100)
"""
    ns = run_ptr_snippet(driver)
    assert ns["check_null"] is True, "null() pointer must evaluate is_null() to True"
    assert ns["check_valid_p0"] is False, "null() pointer must evaluate is_valid() to False"
    assert ns["check_null_p100"] is False, "Offset non-zero pointer must not be null"
    assert ns["check_valid_p100"] is True, "Offset non-zero pointer must be valid"


def test_ptr_arithmetic_and_diff():
    driver = r"""
let base = offset(null(), 500)
let p_byte = offset(base, 64)
let p_elem = offset_elements(base, 8, 4)
let d1 = diff(p_byte, base)
let d2 = diff(p_elem, base)
let d_rev = diff(base, p_byte)
"""
    ns = run_ptr_snippet(driver)
    assert ns["p_byte"] == 564
    assert ns["p_elem"] == 532  # 500 + 8 * 4
    assert ns["d1"] == 64
    assert ns["d2"] == 32
    assert ns["d_rev"] == -64


def test_ptr_alignment_vectors():
    driver = r"""
let base = offset(null(), 13)
let up4 = align_up(base, 4)
let down4 = align_down(base, 4)
let is_al4 = is_aligned(up4, 4)
let is_not_al = is_aligned(base, 4)

let up64 = align_up(offset(null(), 65), 64)
let down64 = align_down(offset(null(), 65), 64)
"""
    ns = run_ptr_snippet(driver)
    assert ns["up4"] == 16, f"Expected 16, got {ns['up4']}"
    assert ns["down4"] == 12, f"Expected 12, got {ns['down4']}"
    assert ns["is_al4"] is True
    assert ns["is_not_al"] is False
    assert ns["up64"] == 128
    assert ns["down64"] == 64


def test_ptr_typed_rw():
    driver = r"""
let p = offset(null(), 1024)
write_u8(p, 0xFE)
let val8 = read_u8(p)

let p16 = offset(null(), 1040)
write_u16(p16, 0x1234)
let val16 = read_u16(p16)

let p32 = offset(null(), 1080)
write_u32(p32, 0xCAFEBABE)
let val32 = read_u32(p32)

let p64 = offset(null(), 1120)
write_u64(p64, 0x1122334455667788)
let val64 = read_u64(p64)
"""
    ns = run_ptr_snippet(driver)
    assert ns["val8"] == 0xFE
    assert ns["val16"] == 0x1234
    assert ns["val32"] == 0xCAFEBABE
    assert ns["val64"] == 0x1122334455667788


def test_ptr_volatile_mmio():
    driver = r"""
let mmio_reg = offset(null(), 0xF000)
write_volatile_u32(mmio_reg, 0x55AA55AA)
let readback = read_volatile_u32(mmio_reg)
"""
    ns = run_ptr_snippet(driver)
    assert ns["readback"] == 0x55AA55AA


def test_ptr_block_memory_operations():
    driver = r"""
let src = offset(null(), 2000)
let dst = offset(null(), 3000)

write_bytes(src, 0x77, 8)
zero(dst, 8)
let pre_copy = read_u8(dst)

copy_nonoverlapping(dst, src, 8, 1)
let post_copy = read_u8(dst)
let post_copy_last = read_u8(offset(dst, 7))
"""
    ns = run_ptr_snippet(driver)
    assert ns["pre_copy"] == 0
    assert ns["post_copy"] == 0x77
    assert ns["post_copy_last"] == 0x77
