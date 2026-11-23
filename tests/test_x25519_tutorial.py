"""
tests/test_x25519_tutorial.py - Comprehensive verification for stdlib/x25519.ltl
Tests RFC 7748 Curve25519 scalar clamping, public key derivation,
Montgomery ladder scalar multiplication, and Diffie-Hellman key agreement against PyCA Cryptography.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target
from cryptography.hazmat.primitives.asymmetric import x25519

def test_x25519_scalar_clamping():
    x25519_src = Path("stdlib/x25519.ltl").read_text(encoding="utf-8")
    driver = r"""
let raw = [
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff
]
let clamped = clamp_scalar(raw)
"""
    c = Compiler()
    res = c.compile_source(x25519_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    clamped = ns["clamped"]
    assert clamped[0] == 248  # 0xff & 248 (lowest 3 bits cleared)
    assert clamped[31] == 127 | 64  # (0xff & 127) | 64 == 127
    assert (clamped[31] & 0x80) == 0  # bit 255 cleared
    assert (clamped[31] & 0x40) != 0  # bit 254 set
    assert (clamped[0] & 0x07) == 0   # bits 0, 1, 2 cleared

def test_x25519_alice_and_bob_public_key_derivation():
    x25519_src = Path("stdlib/x25519.ltl").read_text(encoding="utf-8")
    alice_priv = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    bob_priv = bytes.fromhex("5dab087e624a8a4b794bf49b75945f49b98accd6843187130d55a80631f56cf7")

    alice_pyca = x25519.X25519PrivateKey.from_private_bytes(alice_priv)
    bob_pyca = x25519.X25519PrivateKey.from_private_bytes(bob_priv)

    expected_alice_pub = list(alice_pyca.public_key().public_bytes_raw())
    expected_bob_pub = list(bob_pyca.public_key().public_bytes_raw())

    driver = f"""
let alice_priv = {list(alice_priv)}
let bob_priv = {list(bob_priv)}
let alice_pub = derive_public(alice_priv)
let bob_pub = derive_public(bob_priv)
"""
    c = Compiler()
    res = c.compile_source(x25519_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["alice_pub"] == expected_alice_pub, "Alice public key must match RFC 7748 reference"
    assert ns["bob_pub"] == expected_bob_pub, "Bob public key must match RFC 7748 reference"

def test_x25519_diffie_hellman_shared_secret():
    x25519_src = Path("stdlib/x25519.ltl").read_text(encoding="utf-8")
    alice_priv = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    bob_priv = bytes.fromhex("5dab087e624a8a4b794bf49b75945f49b98accd6843187130d55a80631f56cf7")

    alice_pyca = x25519.X25519PrivateKey.from_private_bytes(alice_priv)
    bob_pyca = x25519.X25519PrivateKey.from_private_bytes(bob_priv)
    expected_shared = list(alice_pyca.exchange(bob_pyca.public_key()))

    driver = f"""
let alice_priv = {list(alice_priv)}
let bob_priv = {list(bob_priv)}
let alice_pub = derive_public(alice_priv)
let bob_pub = derive_public(bob_priv)

let shared_alice = scalar_mult(alice_priv, bob_pub)
let shared_bob   = scalar_mult(bob_priv, alice_pub)
"""
    c = Compiler()
    res = c.compile_source(x25519_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["shared_alice"] == expected_shared, "Alice-computed shared secret must match PyCA reference"
    assert ns["shared_bob"] == expected_shared, "Bob-computed shared secret must match PyCA reference"
    assert ns["shared_alice"] == ns["shared_bob"], "Key agreement symmetry requirement failed"

def test_x25519_zero_scalar_multiplication():
    x25519_src = Path("stdlib/x25519.ltl").read_text(encoding="utf-8")
    zero_scalar = [0] * 32
    # Even with all zeros, clamping sets bit 254 and clears lowest bits
    driver = f"""
let zero_priv = {zero_scalar}
let pub_key = derive_public(zero_priv)
"""
    c = Compiler()
    res = c.compile_source(x25519_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert len(ns["pub_key"]) == 32
    assert any(b != 0 for b in ns["pub_key"])
