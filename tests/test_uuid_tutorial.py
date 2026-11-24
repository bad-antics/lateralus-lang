"""
tests/test_uuid_tutorial.py - Comprehensive tests for stdlib/uuid.ltl
Verifies UUID v4 generation, validation, version extraction, case-insensitive comparison,
compact/expand transformations, and well-known namespace constants.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_uuid_generation_and_validation():
    uuid_src = Path("stdlib/uuid.ltl").read_text(encoding="utf-8")
    driver = """
let u4 = uuid4()
let valid4 = is_valid(u4)
let ver4 = version(u4)

let nil_val = nil_uuid()
let valid_nil = is_valid(nil_val)
let ver_nil = version(nil_val)

let invalid_len = is_valid("1234")
let invalid_dashes = is_valid("550e8400xe29bx41d4xa716x446655440000")
"""
    c = Compiler()
    res = c.compile_source(uuid_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert len(ns["u4"]) == 36
    assert ns["valid4"] is True
    assert ns["ver4"] == 4

    assert ns["nil_val"] == "00000000-0000-0000-0000-000000000000"
    assert ns["valid_nil"] is True
    assert ns["ver_nil"] == 0 # nil UUID has version 0

    assert ns["invalid_len"] is False
    assert ns["invalid_dashes"] is False

def test_uuid_transformations_and_namespaces():
    uuid_src = Path("stdlib/uuid.ltl").read_text(encoding="utf-8")
    driver = """
let sample = "550e8400-e29b-41d4-a716-446655440000"
let sample_upper = "550E8400-E29B-41D4-A716-446655440000"

let eq_same = equals(sample, sample_upper)
let eq_diff = equals(sample, nil_uuid())

let comp = compact(sample)
let exp = expand(comp)

let ns_dns = NAMESPACE_DNS
let ns_url = NAMESPACE_URL
let ns_oid = NAMESPACE_OID
let ns_x500 = NAMESPACE_X500
"""
    c = Compiler()
    res = c.compile_source(uuid_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["eq_same"] is True
    assert ns["eq_diff"] is False

    assert ns["comp"] == "550e8400e29b41d4a716446655440000"
    assert ns["exp"] == "550e8400-e29b-41d4-a716-446655440000"

    assert ns["ns_dns"] == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    assert ns["ns_url"] == "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
    assert ns["ns_oid"] == "6ba7b812-9dad-11d1-80b4-00c04fd430c8"
    assert ns["ns_x500"] == "6ba7b814-9dad-11d1-80b4-00c04fd430c8"
