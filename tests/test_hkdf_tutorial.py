"""
tests/test_hkdf_tutorial.py - Comprehensive verification for stdlib/hkdf.ltl
Verifies RFC 5869 Appendix A Test Cases 1, 2, and 3 (SHA-256), multi-key
domain isolation via derive_many, and block count limits.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target


def run_hkdf_snippet(driver: str) -> dict:
    hkdf_src = Path("stdlib/hkdf.ltl").read_text(encoding="utf-8")
    c = Compiler()
    res = c.compile_source(hkdf_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    return ns


def test_hkdf_rfc5869_test_case_1():
    # RFC 5869 Test Case 1: SHA-256, IKM=22 bytes, Salt=13 bytes, Info=10 bytes, L=42
    driver = r"""
let ikm = [11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11]
let salt = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
let info = [240, 241, 242, 243, 244, 245, 246, 247, 248, 249]
let l = 42

let prk = extract(salt, ikm)
let prk_hex = bytes_to_hex(prk)

let okm = expand(prk, info, l)
let okm_hex = bytes_to_hex(okm)
"""
    ns = run_hkdf_snippet(driver)
    expected_prk = "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
    expected_okm = "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"

    assert ns["prk_hex"] == expected_prk, f"PRK mismatch: {ns['prk_hex']}"
    assert ns["okm_hex"] == expected_okm, f"OKM mismatch: {ns['okm_hex']}"
    assert len(ns["okm"]) == 42


def test_hkdf_rfc5869_test_case_2():
    # RFC 5869 Test Case 2: SHA-256, 80-octet inputs, L=82 (> 2 * HashLen)
    ikm_bytes = list(range(80))
    salt_bytes = list(range(96, 96 + 80))
    info_bytes = list(range(176, 176 + 80))

    driver = f"""
let ikm = {ikm_bytes}
let salt = {salt_bytes}
let info = {info_bytes}
let l = 82

let prk = extract(salt, ikm)
let prk_hex = bytes_to_hex(prk)

let okm = expand(prk, info, l)
let okm_hex = bytes_to_hex(okm)
"""
    ns = run_hkdf_snippet(driver)
    expected_prk = "06a6b88c5853361a06104c9ceb35b45cef760014904671014a193f40c15fc244"
    expected_okm = (
        "b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c"
        "59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71"
        "cc30c58179ec3e87c14c01d5c1f3434f1d87"
    )

    assert ns["prk_hex"] == expected_prk, f"PRK mismatch: {ns['prk_hex']}"
    assert ns["okm_hex"] == expected_okm, f"OKM mismatch: {ns['okm_hex']}"
    assert len(ns["okm"]) == 82


def test_hkdf_rfc5869_test_case_3_zero_salt_and_info():
    # RFC 5869 Test Case 3: Zero-length salt (defaults to 32 zero octets) and zero-length info
    driver = r"""
let ikm = [11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11]
let salt = []
let info = []
let l = 42

let prk = extract(salt, ikm)
let prk_hex = bytes_to_hex(prk)

let okm = expand(prk, info, l)
let okm_hex = bytes_to_hex(okm)
"""
    ns = run_hkdf_snippet(driver)
    expected_prk = "19ef24a32c717b167f33a91d6f648bdf96596776afdb6377ac434c1c293ccb04"
    expected_okm = "8da4e775a563c18f715f802a063c5a31b8a11f5c5ee1879ec3454e5f3c738d2d9d201395faa4b61a96c8"

    assert ns["prk_hex"] == expected_prk, f"PRK mismatch: {ns['prk_hex']}"
    assert ns["okm_hex"] == expected_okm, f"OKM mismatch: {ns['okm_hex']}"
    assert len(ns["okm"]) == 42


def test_hkdf_derive_many_key_isolation():
    driver = r"""
let master = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
let prk = extract([], master)
let keys = derive_many(prk, [97, 112, 112], 32, 3)

let k0 = bytes_to_hex(keys[0])
let k1 = bytes_to_hex(keys[1])
let k2 = bytes_to_hex(keys[2])
"""
    ns = run_hkdf_snippet(driver)
    assert len(ns["keys"]) == 3
    assert len(ns["k0"]) == 64
    assert len(ns["k1"]) == 64
    assert len(ns["k2"]) == 64
    # Ensure distinct non-overlapping cryptographic keys
    assert ns["k0"] != ns["k1"]
    assert ns["k1"] != ns["k2"]
    assert ns["k0"] != ns["k2"]


def test_hkdf_expand_limit_rfc5869():
    driver = r"""
let prk = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
// 256 * 32 = 8192 bytes, which exceeds 255 * HashLen limit
let too_long = expand(prk, [], 8192)
"""
    ns = run_hkdf_snippet(driver)
    assert ns["too_long"] == [], "Expand should reject length exceeding 255 * HashLen"
