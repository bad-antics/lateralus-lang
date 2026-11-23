"""
tests/test_webauthn_tutorial.py - Comprehensive verification for stdlib/webauthn.ltl
Tests W3C WebAuthn Level 2/3 Registration Options, Authentication Options,
clientDataJSON validation, authenticatorData flags & counter parsing, and ceremony orchestration.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_webauthn_registration_options():
    webauthn_src = Path("stdlib/webauthn.ltl").read_text(encoding="utf-8")
    driver = r"""
let reg = new_registration_options(
    "usr_42",
    "bob@example.com",
    "Bob Doe",
    "example.com",
    "Example Portal",
    "chal_register_999",
    45000
)
"""
    c = Compiler()
    res = c.compile_source(webauthn_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    reg = ns["reg"]
    assert reg["rp"]["id"] == "example.com"
    assert reg["rp"]["name"] == "Example Portal"
    assert reg["user"]["id"] == "usr_42"
    assert reg["user"]["name"] == "bob@example.com"
    assert reg["user"]["displayName"] == "Bob Doe"
    assert reg["challenge"] == "chal_register_999"
    assert reg["timeout"] == 45000
    assert reg["attestation"] == "none"
    assert len(reg["pubKeyCredParams"]) == 2
    assert reg["pubKeyCredParams"][0]["alg"] == -7
    assert reg["pubKeyCredParams"][1]["alg"] == -257

def test_webauthn_authentication_options():
    webauthn_src = Path("stdlib/webauthn.ltl").read_text(encoding="utf-8")
    driver = r"""
let auth = new_authentication_options(
    "example.com",
    "chal_auth_888",
    ["cred_alpha", "cred_beta"],
    30000
)
"""
    c = Compiler()
    res = c.compile_source(webauthn_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    auth = ns["auth"]
    assert auth["rpId"] == "example.com"
    assert auth["challenge"] == "chal_auth_888"
    assert auth["timeout"] == 30000
    assert auth["userVerification"] == "preferred"
    assert len(auth["allowCredentials"]) == 2
    assert auth["allowCredentials"][0]["id"] == "cred_alpha"
    assert auth["allowCredentials"][0]["type"] == "public-key"
    assert auth["allowCredentials"][1]["id"] == "cred_beta"

def test_webauthn_client_data_verification():
    webauthn_src = Path("stdlib/webauthn.ltl").read_text(encoding="utf-8")
    driver = r"""
let cdata = {}
cdata["type"] = "webauthn.get"
cdata["challenge"] = "chal_auth_888"
cdata["origin"] = "https://example.com"

let valid_res = verify_client_data(cdata, "webauthn.get", "chal_auth_888", "https://example.com", "")
let bad_type = verify_client_data(cdata, "webauthn.create", "chal_auth_888", "https://example.com", "")
let bad_chal = verify_client_data(cdata, "webauthn.get", "chal_wrong", "https://example.com", "")
let bad_orig = verify_client_data(cdata, "webauthn.get", "chal_auth_888", "https://phish.com", "")
"""
    c = Compiler()
    res = c.compile_source(webauthn_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["valid_res"] == [True, "ok"]
    assert ns["bad_type"][0] is False and "type mismatch" in ns["bad_type"][1]
    assert ns["bad_chal"][0] is False and "challenge mismatch" in ns["bad_chal"][1]
    assert ns["bad_orig"][0] is False and "origin mismatch" in ns["bad_orig"][1]

def test_webauthn_authenticator_data_and_counter():
    webauthn_src = Path("stdlib/webauthn.ltl").read_text(encoding="utf-8")
    driver = r"""
let rp_hash = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
let flags = 0x45 // UP (0x01) | UV (0x04) | AT (0x40)
let count = [0, 0, 1, 0] // 256 in big-endian

let aaguid = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
let cred_id_len = [0, 4]
let cred_id = [100, 101, 102, 103]
let cose_key = [161, 1, 2] // mock CBOR key

let buf = rp_hash + [flags] + count + aaguid + cred_id_len + cred_id + cose_key
let ad = parse_authenticator_data(buf)

let c_ok = check_counter(200, 256)
let c_replay = check_counter(300, 256)
let c_zeros = check_counter(0, 0)
"""
    c = Compiler()
    res = c.compile_source(webauthn_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    ad = ns["ad"]
    assert ad["ok"] is True
    assert ad["flag_up"] is True
    assert ad["flag_uv"] is True
    assert ad["flag_at"] is True
    assert ad["sign_count"] == 256
    assert ad["aaguid"] == [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
    assert ad["credential_id"] == [100, 101, 102, 103]
    assert ad["cose_public_key"] == [161, 1, 2]

    assert ns["c_ok"] is True
    assert ns["c_replay"] is False
    assert ns["c_zeros"] is True

def test_webauthn_end_to_end_verification():
    webauthn_src = Path("stdlib/webauthn.ltl").read_text(encoding="utf-8")
    driver = r"""
let rp_hash = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
let flags = 0x05 // UP (0x01) | UV (0x04)
let count = [0, 0, 0, 50]
let auth_data_buf = rp_hash + [flags] + count

let cdata = {}
cdata["type"] = "webauthn.get"
cdata["challenge"] = "chal_xyz"
cdata["origin"] = "https://example.com"

fn mock_sig_verifier(pk, msg, sig) {
    return true
}

fn mock_bad_sig_verifier(pk, msg, sig) {
    return false
}

let auth_success = verify_authentication(
    cdata,
    "chal_xyz",
    "https://example.com",
    rp_hash,
    auth_data_buf,
    40,
    "mock_pk",
    [1, 2, 3],
    [4, 5, 6],
    mock_sig_verifier
)

let auth_bad_sig = verify_authentication(
    cdata,
    "chal_xyz",
    "https://example.com",
    rp_hash,
    auth_data_buf,
    40,
    "mock_pk",
    [1, 2, 3],
    [4, 5, 6],
    mock_bad_sig_verifier
)
"""
    c = Compiler()
    res = c.compile_source(webauthn_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["auth_success"][0] is True
    assert ns["auth_success"][1]["sign_count"] == 50
    assert ns["auth_bad_sig"][0] is False
    assert "bad signature" in ns["auth_bad_sig"][1]
