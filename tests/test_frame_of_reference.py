"""
tests/test_frame_of_reference.py - Tests for stdlib/frame_of_reference.ltl
Verifies delta-of-delta (dod) encoding/decoding on short columns.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_dod_short_columns_roundtrip():
    for_text = Path("stdlib/frame_of_reference.ltl").read_text(encoding="utf-8")
    driver = """
for xs in [[], [0], [0, 0], [7, 7], [7, 8], [7, 7, 8], [10, 20, 30, 40]] {
    let frame = encode_dod(xs)
    let dec = decode_dod(frame)
    if len(xs) != len(dec) {
        panic("Length mismatch")
    }
    let j = 0
    while j < len(xs) {
        if xs[j] != dec[j] {
            panic("Value mismatch")
        }
        j = j + 1
    }
}
"""
    c = Compiler()
    res = c.compile_source(for_text + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    exec(res.python_src, {})
