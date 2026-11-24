"""
tests/test_argon2_tutorial.py - Comprehensive verification for stdlib/argon2.ltl
Tests RFC 9106 Argon2id profile generation, PHC string encoding/decoding,
password hashing, constant-time verification, and rehash policy inspection.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_argon2_profiles():
    argon2_src = Path("stdlib/argon2.ltl").read_text(encoding="utf-8")
    driver = r"""
let p1 = profile_interactive()
let p2 = profile_sensitive()
let p3 = profile_kdf()
"""
    c = Compiler()
    res = c.compile_source(argon2_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["p1"]["m"] == 65536
    assert ns["p1"]["t"] == 3
    assert ns["p1"]["p"] == 1
    assert ns["p1"]["hash_len"] == 32

    assert ns["p2"]["m"] == 262144
    assert ns["p2"]["t"] == 4

    assert ns["p3"]["m"] == 131072
    assert ns["p3"]["t"] == 3

def test_argon2_phc_encoding_and_decoding():
    argon2_src = Path("stdlib/argon2.ltl").read_text(encoding="utf-8")
    driver = r"""
let p = profile_interactive()
let salt = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
let h = [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65]
let encoded = phc_encode(p, salt, h)
let decoded = phc_decode(encoded)
"""
    c = Compiler()
    res = c.compile_source(argon2_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    encoded = ns["encoded"]
    assert encoded.startswith("$argon2id$v=19$m=65536,t=3,p=1$")
    decoded = ns["decoded"]
    assert decoded["m"] == 65536
    assert decoded["t"] == 3
    assert decoded["p"] == 1
    assert decoded["salt"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    assert decoded["hash"] == [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65]

def test_argon2_hash_and_verify():
    argon2_src = Path("stdlib/argon2.ltl").read_text(encoding="utf-8")
    driver = r"""
let p = profile_interactive()
let h = hash("MySecurePassword2026!", p)
let ok_valid = verify("MySecurePassword2026!", h)
let ok_invalid = verify("TotallyWrongPassword!", h)
"""
    c = Compiler()
    res = c.compile_source(argon2_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["ok_valid"] is True, "Password verification should succeed for correct password"
    assert ns["ok_invalid"] is False, "Password verification should fail for wrong password"

def test_argon2_needs_rehash():
    argon2_src = Path("stdlib/argon2.ltl").read_text(encoding="utf-8")
    driver = r"""
let p_inter = profile_interactive()
let p_sens = profile_sensitive()
let h_inter = hash("password", p_inter)

let needs_upgrade = needs_rehash(h_inter, p_sens)
let no_upgrade = needs_rehash(h_inter, p_inter)
"""
    c = Compiler()
    res = c.compile_source(argon2_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["needs_upgrade"] is True, "Lower memory profile should require rehash against sensitive profile"
    assert ns["no_upgrade"] is False, "Identical profile should not require rehash"
