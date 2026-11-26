"""Regression tests for stdlib/smtp.ltl bounty #1065.

Covers:
  1. CRLF / SMTP command injection in cmd_ehlo / cmd_mail_from / cmd_rcpt_to
  2. parse_line: bare 3-digit replies, non-numeric status, multi-line markers
  3. encode_body: no extra blank line when the body ends with LF
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _run(source: str):
    """Compile+run a Lateralus snippet through the reference interpreter."""
    from lateralus_lang import api  # noqa: WPS433

    return api.run_source(source)


def test_cmd_mail_from_rejects_crlf_injection():
    out = _run(
        'import smtp\n'
        'let a = "a@b.com>\\r\\nRCPT TO:<evil@attacker.com"\n'
        'emit(smtp.cmd_mail_from(a))\n'
    )
    assert "\r\n" in out
    # Only the single terminator may appear on the wire.
    assert out.count("\r\n") == 1
    assert "RCPT TO" not in out


def test_cmd_rcpt_to_rejects_crlf_injection():
    out = _run(
        'import smtp\n'
        'let a = "victim@x.com\\nMAIL FROM:<evil@y.com>"\n'
        'emit(smtp.cmd_rcpt_to(a))\n'
    )
    assert out.count("\r\n") == 1
    assert "MAIL FROM" not in out


def test_cmd_ehlo_rejects_crlf_injection():
    out = _run(
        'import smtp\n'
        'emit(smtp.cmd_ehlo("host\\r\\nAUTH PLAIN c2VjcmV0"))\n'
    )
    assert out.count("\r\n") == 1
    assert "AUTH PLAIN" not in out


def test_parse_line_accepts_bare_three_digit_reply():
    out = _run('import smtp\nemit(smtp.parse_line("250"))\n')
    assert "250" in out


def test_parse_line_rejects_non_numeric_status():
    out = _run('import smtp\nemit(smtp.parse_line("abc OK"))\n')
    assert "0" in out


def test_parse_line_marks_continued_reply():
    out = _run('import smtp\nemit(smtp.parse_line("250-PIPELINING"))\n')
    assert "true" in out


def test_encode_body_no_extra_blank_line_on_trailing_lf():
    out = _run('import smtp\nemit(smtp.encode_body("line1\\n"))\n')
    assert "line1\r\n.\r\n" in out
    assert "line1\r\n\r\n.\r\n" not in out
