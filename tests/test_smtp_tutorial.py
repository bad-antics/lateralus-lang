"""
tests/test_smtp_tutorial.py - Comprehensive verification for stdlib/smtp.ltl
Tests RFC 5321 ESMTP response parsing, command emission, RFC 4954 SASL auth,
RFC 5321 §4.5.2 dot-stuffing, and end-to-end send_mail session orchestration.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_smtp_parse_line_and_multiline_responses():
    smtp_src = Path("stdlib/smtp.ltl").read_text(encoding="utf-8")
    driver = r"""
let r1 = parse_line("220 mx.example.com ESMTP\r\n")
let r2 = parse_line("250-SIZE 35882577\r\n")
let r3 = parse_line("250 8BITMIME\r\n")
let r4 = parse_line("550 User not found\r\n")
"""
    c = Compiler()
    res = c.compile_source(smtp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["r1"] == [220, "mx.example.com ESMTP", False]
    assert ns["r2"] == [250, "SIZE 35882577", True]
    assert ns["r3"] == [250, "8BITMIME", False]
    assert ns["r4"] == [550, "User not found", False]

def test_smtp_command_emission_and_formatting():
    smtp_src = Path("stdlib/smtp.ltl").read_text(encoding="utf-8")
    driver = r"""
let ehlo = cmd_ehlo("mail.example.org")
let m_from = cmd_mail_from("alice@example.org")
let r_to = cmd_rcpt_to("bob@example.com")
let data = cmd_data()
let quit = cmd_quit()
"""
    c = Compiler()
    res = c.compile_source(smtp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["ehlo"] == "EHLO mail.example.org\r\n"
    assert ns["m_from"] == "MAIL FROM:<alice@example.org>\r\n"
    assert ns["r_to"] == "RCPT TO:<bob@example.com>\r\n"
    assert ns["data"] == "DATA\r\n"
    assert ns["quit"] == "QUIT\r\n"

def test_smtp_authentication_payloads():
    smtp_src = Path("stdlib/smtp.ltl").read_text(encoding="utf-8")
    driver = r"""
let plain = auth_plain("testuser", "secretpass")
let login = auth_login("testuser", "secretpass")
"""
    c = Compiler()
    res = c.compile_source(smtp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    # Base64 of "\0testuser\0secretpass" == "AHRlc3R1c2VyAHNlY3JldHBhc3M="
    assert ns["plain"] == "AUTH PLAIN AHRlc3R1c2VyAHNlY3JldHBhc3M=\r\n"
    # AUTH LOGIN: 3-step sequence
    assert len(ns["login"]) == 3
    assert ns["login"][0] == "AUTH LOGIN\r\n"
    assert ns["login"][1] == "dGVzdHVzZXI=\r\n"      # base64("testuser")
    assert ns["login"][2] == "c2VjcmV0cGFzcw==\r\n"  # base64("secretpass")

def test_smtp_body_dot_stuffing():
    smtp_src = Path("stdlib/smtp.ltl").read_text(encoding="utf-8")
    driver = r"""
let raw = "Hello world\n.This line started with a dot\nAnother line"
let encoded = encode_body(raw)
"""
    c = Compiler()
    res = c.compile_source(smtp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    expected = "Hello world\r\n..This line started with a dot\r\nAnother line\r\n.\r\n"
    assert ns["encoded"] == expected

def test_smtp_session_orchestration_mock():
    smtp_src = Path("stdlib/smtp.ltl").read_text(encoding="utf-8")
    driver = r"""
let state = {}
state["idx"] = 0
state["sent"] = []
let server_replies = [
    "220 mail.example.com ESMTP Postfix\r\n",
    "250-mail.example.com\r\n",
    "250-PIPELINING\r\n",
    "250 8BITMIME\r\n",
    "250 2.1.0 Ok\r\n",
    "250 2.1.5 Ok\r\n",
    "354 Start mail input; end with <CRLF>.<CRLF>\r\n",
    "250 2.0.0 Ok: queued as 12345\r\n"
]

fn mock_send(cmd: str) {
    state["sent"] = state["sent"] + [cmd]
}

fn mock_recv() -> str {
    let r = server_replies[state["idx"]]
    state["idx"] = state["idx"] + 1
    return r
}

let transport = {}
transport["send"] = mock_send
transport["recv_line"] = mock_recv

let res = send_mail(transport, "alice@example.com", ["bob@example.com"], "Test email body")
let sent_cmds = state["sent"]
"""
    c = Compiler()
    res = c.compile_source(smtp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["res"] == [True, "ok"]
    assert len(ns["sent_cmds"]) == 6
    assert ns["sent_cmds"][0] == "EHLO localhost\r\n"
    assert ns["sent_cmds"][1] == "MAIL FROM:<alice@example.com>\r\n"
    assert ns["sent_cmds"][2] == "RCPT TO:<bob@example.com>\r\n"
    assert ns["sent_cmds"][3] == "DATA\r\n"
    assert ns["sent_cmds"][4] == "Test email body\r\n.\r\n"
    assert ns["sent_cmds"][5] == "QUIT\r\n"
