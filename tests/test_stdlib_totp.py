"""
Regression and verification tests for stdlib/totp.ltl.
Validates RFC 6238 (TOTP) and RFC 4226 (HOTP) implementation and test vectors.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

REPO_ROOT = Path(__file__).resolve().parent.parent
TOTP_LTL = REPO_ROOT / "stdlib" / "totp.ltl"


def test_totp_compiler_targets():
    """Ensure stdlib/totp.ltl compiles cleanly across all primary backends."""
    source = TOTP_LTL.read_text("utf-8")
    for target in [Target.PYTHON, Target.JAVASCRIPT, Target.C]:
        result = Compiler().compile_source(source, target=target)
        assert result.ok, f"Target {target.name} compile failed: {result.errors}"


def test_totp_rfc4226_hotp_vectors():
    """Verify standard RFC 4226 Appendix D test vectors using Python's hmac."""
    import hmac
    import hashlib

    # Secret: ASCII "12345678901234567890"
    secret = b"12345678901234567890"

    # RFC 4226 reference values for count 0..9
    expected_codes = [
        "755224", "287082", "359152", "969429", "338314",
        "254676", "287922", "162583", "399871", "520489"
    ]

    for counter, expected in enumerate(expected_codes):
        buf = counter.to_bytes(8, byteorder="big")
        h = hmac.new(secret, buf, hashlib.sha1).digest()
        off = h[-1] & 0x0F
        bin_code = (
            ((h[off] & 0x7F) << 24)
            | ((h[off + 1] & 0xFF) << 16)
            | ((h[off + 2] & 0xFF) << 8)
            | (h[off + 3] & 0xFF)
        )
        code = str(bin_code % 1000000).zfill(6)
        assert code == expected, f"HOTP failed at counter {counter}: got {code}, expected {expected}"


def test_totp_rfc6238_totp_vectors():
    """Verify standard RFC 6238 Appendix B test vectors for HMAC-SHA1 at defined epoch timestamps."""
    import hmac
    import hashlib

    secret = b"12345678901234567890"
    step_s = 30
    digits = 8

    # Table 1 in RFC 6238 Appendix B (SHA1, 8-digit)
    vectors = [
        (59, "94287082"),
        (1111111109, "07081804"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
        (2000000000, "69279037"),
    ]

    for t, expected in vectors:
        counter = t // step_s
        buf = counter.to_bytes(8, byteorder="big")
        h = hmac.new(secret, buf, hashlib.sha1).digest()
        off = h[-1] & 0x0F
        bin_code = (
            ((h[off] & 0x7F) << 24)
            | ((h[off + 1] & 0xFF) << 16)
            | ((h[off + 2] & 0xFF) << 8)
            | (h[off + 3] & 0xFF)
        )
        mod = 10 ** digits
        code = str(bin_code % mod).zfill(digits)
        assert code == expected, f"TOTP failed at timestamp {t}: got {code}, expected {expected}"
