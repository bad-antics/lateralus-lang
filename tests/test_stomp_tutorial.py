"""
tests/test_stomp_tutorial.py - Comprehensive verification for stdlib/stomp.ltl
Verifies canonical STOMP 1.2 ASCII frame encoding, header escaping rules,
frame parser robustness against heartbeat pulses, incomplete payloads,
and lifecycle frame builders (CONNECT, SUBSCRIBE, ACK, NACK, DISCONNECT).
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target


def run_stomp_snippet(driver: str) -> dict:
    stomp_src = Path("stdlib/stomp.ltl").read_text(encoding="utf-8")
    c = Compiler()
    res = c.compile_source(stomp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    return ns


def test_stomp_header_escaping_and_roundtrip():
    driver = r"""
let raw = "user:alice\npass\\word\rkey"
let esc = escape_header(raw)
let unesc = unescape_header(esc)
"""
    ns = run_stomp_snippet(driver)
    assert ns["esc"] == "user\\calice\\npass\\\\word\\rkey", f"Escaping mismatch: {ns['esc']}"
    assert ns["unesc"] == "user:alice\npass\\word\rkey", f"Unescaping mismatch: {ns['unesc']}"


def test_stomp_canonical_send_pinned_vector():
    driver = r"""
let send_frame = send("/queue/jobs", "text/plain", "ping")
let parsed = parse_frame(send_frame)
"""
    ns = run_stomp_snippet(driver)
    expected_frame = "SEND\ndestination:/queue/jobs\ncontent-type:text/plain\ncontent-length:4\n\nping\x00"
    assert ns["send_frame"] == expected_frame, f"Canonical SEND frame mismatch: {repr(ns['send_frame'])}"
    assert ns["parsed"]["command"] == "SEND"
    assert ns["parsed"]["body"] == "ping"
    assert ns["parsed"]["consumed"] == len(expected_frame)
    headers = dict(ns["parsed"]["headers"])
    assert headers["destination"] == "/queue/jobs"
    assert headers["content-type"] == "text/plain"
    assert headers["content-length"] == "4"


def test_stomp_heartbeats_and_incomplete_frames():
    driver = r"""
let send_frame = send("/queue/jobs", "text/plain", "ping")
let pulsed = "\r\n\n" + send_frame
let parsed_pulse = parse_frame(pulsed)

let incomplete_no_nul = "SEND\ndestination:/queue/jobs\n\nbody_no_nul"
let parsed_inc = parse_frame(incomplete_no_nul)

let empty_buf = "\n\r\n"
let parsed_empty = parse_frame(empty_buf)
"""
    ns = run_stomp_snippet(driver)
    assert ns["parsed_pulse"]["command"] == "SEND"
    assert ns["parsed_pulse"]["body"] == "ping"
    assert ns["parsed_inc"] is None, "Incomplete frame without NUL must return nil"
    assert ns["parsed_empty"] is None, "Heartbeat-only buffer must return nil"


def test_stomp_connect_and_disconnect():
    driver = r"""
let conn_frame = connect("mq.corp.internal", "admin", "secret123", "5000,5000")
let parsed_conn = parse_frame(conn_frame)

let disc_frame = disconnect("receipt-77")
let parsed_disc = parse_frame(disc_frame)
"""
    ns = run_stomp_snippet(driver)
    assert ns["parsed_conn"]["command"] == "CONNECT"
    conn_headers = dict(ns["parsed_conn"]["headers"])
    assert conn_headers["accept-version"] == "1.2"
    assert conn_headers["host"] == "mq.corp.internal"
    assert conn_headers["login"] == "admin"
    assert conn_headers["passcode"] == "secret123"
    assert conn_headers["heart-beat"] == "5000,5000"

    assert ns["parsed_disc"]["command"] == "DISCONNECT"
    disc_headers = dict(ns["parsed_disc"]["headers"])
    assert disc_headers["receipt"] == "receipt-77"


def test_stomp_subscribe_ack_nack_lifecycle():
    driver = r"""
let sub_frame = subscribe("sub-42", "/topic/telemetry", "client-individual")
let parsed_sub = parse_frame(sub_frame)

let unsub_frame = unsubscribe("sub-42")
let parsed_unsub = parse_frame(unsub_frame)

let ack_frame = ack("msg-100", "tx-9")
let parsed_ack = parse_frame(ack_frame)

let nack_frame = nack("msg-101", "tx-9")
let parsed_nack = parse_frame(nack_frame)
"""
    ns = run_stomp_snippet(driver)
    assert ns["parsed_sub"]["command"] == "SUBSCRIBE"
    sub_headers = dict(ns["parsed_sub"]["headers"])
    assert sub_headers["id"] == "sub-42"
    assert sub_headers["destination"] == "/topic/telemetry"
    assert sub_headers["ack"] == "client-individual"

    assert ns["parsed_unsub"]["command"] == "UNSUBSCRIBE"
    unsub_headers = dict(ns["parsed_unsub"]["headers"])
    assert unsub_headers["id"] == "sub-42"

    assert ns["parsed_ack"]["command"] == "ACK"
    ack_headers = dict(ns["parsed_ack"]["headers"])
    assert ack_headers["id"] == "msg-100"
    assert ack_headers["transaction"] == "tx-9"

    assert ns["parsed_nack"]["command"] == "NACK"
    nack_headers = dict(ns["parsed_nack"]["headers"])
    assert nack_headers["id"] == "msg-101"
    assert nack_headers["transaction"] == "tx-9"


def test_stomp_transactions():
    driver = r"""
let b_frame = begin("tx-500")
let parsed_b = parse_frame(b_frame)

let c_frame = commit("tx-500")
let parsed_c = parse_frame(c_frame)

let a_frame = abort("tx-500")
let parsed_a = parse_frame(a_frame)
"""
    ns = run_stomp_snippet(driver)
    assert ns["parsed_b"]["command"] == "BEGIN"
    assert dict(ns["parsed_b"]["headers"])["transaction"] == "tx-500"

    assert ns["parsed_c"]["command"] == "COMMIT"
    assert dict(ns["parsed_c"]["headers"])["transaction"] == "tx-500"

    assert ns["parsed_a"]["command"] == "ABORT"
    assert dict(ns["parsed_a"]["headers"])["transaction"] == "tx-500"
