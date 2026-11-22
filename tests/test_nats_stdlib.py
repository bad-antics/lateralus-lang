"""
Regression tests for stdlib/nats.ltl.

char_at()/index_of()/starts_with()/try_int() are not runtime builtins —
emitters and parse_message raised NameError. Now uses
slice()/_index_of()/str_starts_with()/_try_int().
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "nats.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def test_client_emitters():
    ns = _load()
    assert ns["connect"]('{"verbose":false}') == 'CONNECT {"verbose":false}\r\n'
    assert ns["pub_msg"]("foo.bar", "reply.to", "hello") == "PUB foo.bar reply.to 5\r\nhello\r\n"
    assert ns["pub_msg"]("foo", "", "x") == "PUB foo 1\r\nx\r\n"
    assert ns["sub"]("foo", "q", "sid1") == "SUB foo q sid1\r\n"
    assert ns["sub"]("foo", "", "s2") == "SUB foo s2\r\n"
    assert ns["unsub"]("s1", 0) == "UNSUB s1\r\n"
    assert ns["unsub"]("s1", 10) == "UNSUB s1 10\r\n"
    assert ns["ping"]() == "PING\r\n"
    assert ns["pong"]() == "PONG\r\n"


def test_parse_control_frames():
    ns = _load()
    assert ns["parse_message"]("PING\r\n") == {"op": "PING", "consumed": 6}
    assert ns["parse_message"]("PONG\r\n")["op"] == "PONG"
    assert ns["parse_message"]("+OK\r\n")["op"] == "OK"
    err = ns["parse_message"]("-ERR 'Unknown Protocol Operation'\r\n")
    assert err["op"] == "ERR" and "Unknown" in err["reason"]
    info = ns["parse_message"]('INFO {"server_id":"x"}\r\n')
    assert info["op"] == "INFO" and info["info"] == '{"server_id":"x"}'


def test_parse_msg_and_partial():
    ns = _load()
    m = ns["parse_message"]("MSG foo.bar sid1 reply.to 5\r\nhello\r\n")
    assert m == {"op": "MSG", "subject": "foo.bar", "sid": "sid1",
                 "reply": "reply.to", "payload": "hello", "consumed": 36}
    # no reply subject
    m2 = ns["parse_message"]("MSG foo sid 11\r\nhello world\r\nEXTRA")
    assert m2["reply"] == "" and m2["payload"] == "hello world"
    # incomplete payload -> nil
    assert ns["parse_message"]("MSG foo sid 5\r\nhel") is None
