"""
Regression tests for stdlib/event.ltl.

fire() checked `typeof(h) == "list"`, but typeof() returns the Python
class repr (e.g. <class 'list'>), never the string "list" — so
one-shot handlers never matched, fell into the h(data) branch, and
crashed.  Now compares against typeof([]).
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    from lateralus_lang.compiler import Target, compile_file

    result = compile_file(
        str(REPO_ROOT / "stdlib" / "event.ltl"), target=Target.PYTHON
    )
    assert result.ok, result.errors
    ns: dict = {}
    exec(result.python_src, ns)  # noqa: S102 - test harness runs generated code
    return ns


def _recorder(ns, calls, name):
    def h(d):
        calls.append(name)
    return h


def test_on_and_fire():
    ns = _load()
    calls = []
    em = ns["new"]()
    em = ns["on"](em, "ping", _recorder(ns, calls, "a"))
    em = ns["fire"](em, "ping", "x")
    assert calls == ["a"]


def test_once_fires_exactly_once():
    ns = _load()
    calls = []
    em = ns["new"]()
    em = ns["on"](em, "ping", _recorder(ns, calls, "a"))
    em = ns["once"](em, "ping", _recorder(ns, calls, "once1"))
    em = ns["fire"](em, "ping", "x")
    assert calls == ["a", "once1"]
    assert ns["handler_count"](em, "ping") == 1  # once removed
    em = ns["fire"](em, "ping", "y")
    assert calls == ["a", "once1", "a"]  # once did NOT fire again


def test_off_and_names():
    ns = _load()
    calls = []
    em = ns["new"]()
    h = _recorder(ns, calls, "a")
    em = ns["on"](em, "ping", h)
    em = ns["fire"](em, "ping", "x")
    em = ns["off"](em, "ping", h)
    assert ns["handler_count"](em, "ping") == 0
    em = ns["fire"](em, "ping", "y")
    assert calls == ["a"]
    assert ns["event_names"](em) == []
    assert ns["total_handlers"](em) == 0
