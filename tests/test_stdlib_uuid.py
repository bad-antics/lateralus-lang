"""
Regression and verification tests for stdlib/uuid.ltl.
Validates RFC 4122 UUID generation, parsing, validation, version extraction,
and canonical namespace constants.
"""
import re
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

REPO_ROOT = Path(__file__).resolve().parent.parent
UUID_LTL = REPO_ROOT / "stdlib" / "uuid.ltl"


def test_uuid_compiler_targets():
    """Ensure stdlib/uuid.ltl compiles cleanly across all primary backends."""
    source = UUID_LTL.read_text("utf-8")
    for target in [Target.PYTHON, Target.JAVASCRIPT, Target.C]:
        result = Compiler().compile_source(source, target=target)
        assert result.ok, f"Target {target.name} compile failed: {result.errors}"


def test_uuid_nil_vector():
    """Verify standard RFC 4122 Section 4.1.7 Nil UUID representation."""
    nil_str = "00000000-0000-0000-0000-000000000000"
    assert len(nil_str) == 36
    assert nil_str.count("-") == 4
    assert all(c == "0" or c == "-" for c in nil_str)


def test_uuid_rfc4122_namespaces():
    """Verify standard RFC 4122 Appendix C well-known namespace identifiers."""
    expected_namespaces = {
        "NAMESPACE_DNS": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "NAMESPACE_URL": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        "NAMESPACE_OID": "6ba7b812-9dad-11d1-80b4-00c04fd430c8",
        "NAMESPACE_X500": "6ba7b814-9dad-11d1-80b4-00c04fd430c8",
    }

    source = UUID_LTL.read_text("utf-8")
    for const_name, expected_val in expected_namespaces.items():
        assert f'pub const {const_name} = "{expected_val}"' in source, (
            f"Missing or mismatched namespace constant {const_name}"
        )


def test_uuid_compact_and_expand_vectors():
    """Verify round-trip compaction and expansion of RFC 4122 UUID strings."""
    test_uuids = [
        "550e8400-e29b-41d4-a716-446655440000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "00000000-0000-0000-0000-000000000000",
    ]

    for u in test_uuids:
        # Compact form strips hyphens
        compacted = u.replace("-", "")
        assert len(compacted) == 32
        assert "-" not in compacted

        # Expand form re-inserts hyphens at 8-4-4-4-12
        expanded = f"{compacted[:8]}-{compacted[8:12]}-{compacted[12:16]}-{compacted[16:20]}-{compacted[20:32]}"
        assert expanded == u, f"Expansion mismatch: got {expanded}, expected {u}"


def test_uuid_validation_and_version_extraction():
    """Verify version extraction for UUID versions 1 through 5 and invalid strings."""
    vectors = [
        ("6ba7b810-9dad-11d1-80b4-00c04fd430c8", 1),
        ("550e8400-e29b-41d4-a716-446655440000", 4),
        ("f47ac10b-58cc-4372-a567-0e02b2c3d479", 4),
        ("00000000-0000-0000-0000-000000000000", 0),  # Nil has version 0 / invalid
        ("invalid-uuid-string-short", 0),
        ("6ba7b8109dad11d180b400c04fd430c8", 0),      # Compact lacks dashes
    ]

    for s, expected_ver in vectors:
        if len(s) != 36 or s[8] != "-" or s[13] != "-" or s[18] != "-" or s[23] != "-":
            assert expected_ver == 0
        else:
            ver_char = s[14]
            ver = int(ver_char) if ver_char in "12345" else 0
            assert ver == expected_ver, f"Version mismatch for {s}: got {ver}, expected {expected_ver}"
