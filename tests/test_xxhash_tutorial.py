"""
tests/test_xxhash_tutorial.py - Comprehensive verification for stdlib/xxhash.ltl
Verifies canonical Cyan4973/xxHash 64-bit spec vectors, multi-stripe buffer
processing, seed avalanche sensitivity, and FNV-1a 64-bit hashing.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target


def run_xxhash_snippet(driver: str) -> dict:
    xxhash_src = Path("stdlib/xxhash.ltl").read_text(encoding="utf-8")
    c = Compiler()
    res = c.compile_source(xxhash_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    return ns


def test_xxhash_canonical_empty_vector():
    driver = r"""
let h = hash64([], 0)
let h_hex = hex64(h)
"""
    ns = run_xxhash_snippet(driver)
    assert ns["h_hex"] == "ef46db3751d8e999", f"Expected canonical empty XXH64 vector, got {ns['h_hex']}"
    assert ns["h"] == 0xEF46DB3751D8E999


def test_xxhash_short_vectors():
    driver = r"""
let h_a = hash64([97], 0)
let h_a_hex = hex64(h_a)

let h_8 = hash64([49, 50, 51, 52, 53, 54, 55, 56], 0)
let h_8_hex = hex64(h_8)
"""
    ns = run_xxhash_snippet(driver)
    assert ns["h_a_hex"] == "d24ec4f1a98c6e5b", f"Mismatch on 'a': {ns['h_a_hex']}"
    assert ns["h_8_hex"] == "d2d02f08cf7cfd4a", f"Mismatch on '12345678': {ns['h_8_hex']}"


def test_xxhash_seed_sensitivity():
    driver = r"""
let h_seed0 = hash64([97], 0)
let h_seed42 = hash64([97], 42)
let hex0 = hex64(h_seed0)
let hex42 = hex64(h_seed42)
"""
    ns = run_xxhash_snippet(driver)
    assert ns["hex0"] != ns["hex42"], "Changing seed must change hash output"
    assert ns["hex42"] == "88e4fe59adf7b0cc", f"Expected seeded hash 88e4fe59adf7b0cc, got {ns['hex42']}"


def test_xxhash_multistripe_64bytes():
    arr64 = list(range(64))
    driver = f"""
let buf = {arr64}
let h = hash64(buf, 0)
let h_hex = hex64(h)
"""
    ns = run_xxhash_snippet(driver)
    assert ns["h_hex"] == "f7c67301db6713f0", f"Multi-stripe 64-byte mismatch: {ns['h_hex']}"


def test_fnv1a_canonical_vectors():
    driver = r"""
let fnv_empty = fnv1a_64([])
let hex_empty = hex64(fnv_empty)

let fnv_a = fnv1a_64([97])
let hex_a = hex64(fnv_a)
"""
    ns = run_xxhash_snippet(driver)
    assert ns["hex_empty"] == "cbf29ce484222325", f"FNV-1a offset basis mismatch: {ns['hex_empty']}"
    assert ns["hex_a"] == "af63dc4c8601ec8c", f"FNV-1a 'a' mismatch: {ns['hex_a']}"


def test_xxhash_string_wrappers():
    driver = r"""
let h_str = hash64_str("a", 0)
let fnv_str = fnv1a_64_str("a")
"""
    ns = run_xxhash_snippet(driver)
    assert ns["h_str"] == 0xD24EC4F1A98C6E5B
    assert ns["fnv_str"] == 0xAF63DC4C8601EC8C
