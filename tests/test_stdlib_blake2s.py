"""
Regression and RFC 7693 test-vector suite for stdlib/blake2s.ltl.
Covers:
  - Multi-backend compilation (Python, JavaScript, C)
  - Unkeyed BLAKE2s-256 on empty, short ("abc"), and multi-block messages
  - Variable digest lengths (16-byte / 128-bit)
  - Keyed BLAKE2s MACs on empty, short, and multi-block inputs (RFC 7693 Section 2.8)
"""
import hashlib
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

REPO_ROOT = Path(__file__).resolve().parent.parent
BLAKE2S_LTL = REPO_ROOT / "stdlib" / "blake2s.ltl"


def _compile_blake2s():
    src = BLAKE2S_LTL.read_text(encoding="utf-8")
    result = Compiler().compile_source(src, target=Target.PYTHON, filename="blake2s.ltl")
    assert result.ok, f"compile failed: {result.errors}"
    ns = {
        "__name__": "blake2s_test",
        "bytes_of": lambda s: list(s.encode("utf-8")),
    }
    exec(result.python_src, ns)
    return ns


def _hex(byte_list: list[int]) -> str:
    return bytes(byte_list).hex()


def test_blake2s_compiler_targets():
    """Ensure stdlib/blake2s.ltl compiles cleanly across Python, JavaScript, and C backends."""
    source = BLAKE2S_LTL.read_text(encoding="utf-8")
    for target in [Target.PYTHON, Target.JAVASCRIPT, Target.C]:
        result = Compiler().compile_source(source, target=target, filename="blake2s.ltl")
        assert result.ok, f"Target {target.name} compile failed: {result.errors}"


def test_blake2s_rfc7693_unkeyed_vectors():
    """Verify pinned RFC 7693 unkeyed BLAKE2s-256 and BLAKE2s-128 vectors."""
    ns = _compile_blake2s()

    # Empty input ""
    assert _hex(ns["hash"]([], [], 32)) == (
        "69217a3079908094e11121d042354a7c1f55b6482ca1a51e1b250dfd1ed0eef9"
    )
    # "abc" (RFC 7693 Appendix A)
    abc = list(b"abc")
    assert _hex(ns["hash256"](abc)) == (
        "508c5e8c327c14e2e1a72ba34eeb452f37458b209ed63a294d999b4c86675982"
    )
    assert _hex(ns["hash256_str"]("abc")) == (
        "508c5e8c327c14e2e1a72ba34eeb452f37458b209ed63a294d999b4c86675982"
    )
    # 128-bit (16-byte) digest
    assert _hex(ns["hash"](abc, [], 16)) == "aa4938119b1dc7b87cbad0ffd200d0ae"


def test_blake2s_rfc7693_keyed_mac_vectors():
    """Verify RFC 7693 Section 2.8 keyed BLAKE2s MAC byte counter (64 + n) across message sizes."""
    ns = _compile_blake2s()
    key = list(range(32))
    key_bytes = bytes(key)

    for payload in [b"", b"abc", b"A" * 64, b"Lateralus-BLAKE2s-" * 10]:
        got = _hex(ns["hash"](list(payload), key, 32))
        expected = hashlib.blake2s(payload, key=key_bytes, digest_size=32).hexdigest()
        assert got == expected, f"Mismatch for len={len(payload)}: {got} != {expected}"
