"""
tests/test_dap_server.py — Tests for the LATERALUS Debug Adapter Protocol server
═════════════════════════════════════════════════════════════════════════════════
"""
import json
import pytest
import sys
import os
import io
from unittest.mock import patch, MagicMock
from pathlib import Path

from lateralus_lang.dap_server import DAPServer, DAPMessage, DAPRequest, DAPResponse, DAPEvent


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_request(command: str, seq: int = 1, arguments: dict = None) -> dict:
    """Build a DAP request dict."""
    msg = {
        "seq": seq,
        "type": "request",
        "command": command,
    }
    if arguments:
        msg["arguments"] = arguments
    return msg


def _encode_dap(msg: dict) -> bytes:
    """Encode a dict as a DAP wire-format message."""
    body = json.dumps(msg).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    return header + body


class CaptureDAP:
    """Captures DAP messages sent by the server."""

    def __init__(self):
        self.messages: list[dict] = []
        self._buffer = io.BytesIO()

    def install(self, server: DAPServer):
        """Monkey-patch server.send_message to capture output."""
        original = server.send_message

        def capture(msg):
            self.messages.append(msg)

        server.send_message = capture

    @property
    def responses(self) -> list[dict]:
        return [m for m in self.messages if m.get("type") == "response"]

    @property
    def events(self) -> list[dict]:
        return [m for m in self.messages if m.get("type") == "event"]

    def last_response(self) -> dict:
        return self.responses[-1] if self.responses else {}

    def last_event(self) -> dict:
        return self.events[-1] if self.events else {}


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def server():
    """Create a fresh DAPServer instance."""
    return DAPServer()


@pytest.fixture
def capture(server):
    """Create a CaptureDAP and install it on the server."""
    cap = CaptureDAP()
    cap.install(server)
    return cap


@pytest.fixture
def ltl_file(tmp_path):
    """Create a temporary .ltl file for testing."""
    p = tmp_path / "test_program.ltl"
    p.write_text("""\
fn greet(name: str) -> str {
    return "Hello, " + name
}

fn main() {
    let msg = greet("World")
    println(msg)
}
""")
    return str(p)


# ─────────────────────────────────────────────────────────────────────────────
# DAPMessage dataclass tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDAPDataclasses:
    def test_dap_message(self):
        msg = DAPMessage(seq=1, type="request")
        assert msg.seq == 1
        assert msg.type == "request"

    def test_dap_request(self):
        req = DAPRequest(seq=2, type="request", command="initialize")
        assert req.command == "initialize"
        assert req.seq == 2

    def test_dap_response(self):
        resp = DAPResponse(seq=3, type="response", request_seq=1,
                          success=True, command="initialize")
        assert resp.success is True
        assert resp.request_seq == 1

    def test_dap_event(self):
        evt = DAPEvent(seq=4, type="event", event="stopped")
        assert evt.event == "stopped"


# ─────────────────────────────────────────────────────────────────────────────
# Server construction
# ─────────────────────────────────────────────────────────────────────────────

class TestDAPServerInit:
    def test_initial_state(self, server):
        assert server.seq == 0
        assert server.running is False
        assert server.initialized is False
        assert server.breakpoints == {}
        assert server.source_files == {}
        assert server.variables == {}

    def test_next_seq_increments(self, server):
        s1 = server.next_seq()
        s2 = server.next_seq()
        s3 = server.next_seq()
        assert s1 == 1
        assert s2 == 2
        assert s3 == 3

    def test_new_var_ref(self, server):
        r1 = server._new_var_ref()
        r2 = server._new_var_ref()
        assert r1 == 1001
        assert r2 == 1002


# ─────────────────────────────────────────────────────────────────────────────
# Initialize
# ─────────────────────────────────────────────────────────────────────────────

class TestInitialize:
    def test_initialize_returns_capabilities(self, server, capture):
        req = _make_request("initialize", seq=1, arguments={
            "clientID": "vscode",
            "adapterID": "lateralus",
        })
        server.handle_initialize(req)

        # Should send a response + an "initialized" event
        assert len(capture.responses) == 1
        assert len(capture.events) == 1

        resp = capture.last_response()
        assert resp["success"] is True
        assert resp["command"] == "initialize"

        body = resp["body"]
        assert body["supportsConfigurationDoneRequest"] is True
        assert body["supportsConditionalBreakpoints"] is True
        assert body["supportsEvaluateForHovers"] is True
        assert body["supportsLoadedSourcesRequest"] is True
        assert body["supportTerminateDebuggee"] is True

        evt = capture.last_event()
        assert evt["event"] == "initialized"


# ─────────────────────────────────────────────────────────────────────────────
# Launch
# ─────────────────────────────────────────────────────────────────────────────

class TestLaunch:
    def test_launch_with_valid_program(self, server, capture, ltl_file):
        req = _make_request("launch", seq=2, arguments={
            "program": ltl_file,
        })
        server.handle_launch(req)

        resp = capture.last_response()
        assert resp["success"] is True
        assert ltl_file in server.source_files
        assert len(server.source_files[ltl_file]) > 0

    def test_launch_no_program(self, server, capture):
        req = _make_request("launch", seq=3, arguments={})
        server.handle_launch(req)

        resp = capture.last_response()
        assert resp["success"] is False
        assert "No program" in resp.get("message", "")

    def test_launch_missing_file(self, server, capture):
        req = _make_request("launch", seq=4, arguments={
            "program": "/nonexistent/path.ltl",
        })
        server.handle_launch(req)

        resp = capture.last_response()
        assert resp["success"] is False
        assert "not found" in resp.get("message", "").lower()

    def test_launch_stop_on_entry(self, server, capture, ltl_file):
        req = _make_request("launch", seq=5, arguments={
            "program": ltl_file,
            "stopOnEntry": True,
        })
        server.handle_launch(req)

        resp = capture.last_response()
        assert resp["success"] is True

        # Should emit "stopped" event with reason "entry"
        stopped_events = [e for e in capture.events if e["event"] == "stopped"]
        assert len(stopped_events) == 1
        assert stopped_events[0]["body"]["reason"] == "entry"
        assert stopped_events[0]["body"]["threadId"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Breakpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestBreakpoints:
    def test_set_breakpoints(self, server, capture, ltl_file):
        req = _make_request("setBreakpoints", seq=6, arguments={
            "source": {"path": ltl_file},
            "breakpoints": [
                {"line": 2},
                {"line": 7},
            ],
        })
        server.handle_set_breakpoints(req)

        resp = capture.last_response()
        assert resp["success"] is True
        bps = resp["body"]["breakpoints"]
        assert len(bps) == 2
        assert bps[0]["verified"] is True
        assert bps[0]["line"] == 2
        assert bps[1]["verified"] is True
        assert bps[1]["line"] == 7

        # Internal state
        assert ltl_file in server.breakpoints
        assert len(server.breakpoints[ltl_file]) == 2

    def test_set_conditional_breakpoint(self, server, capture, ltl_file):
        req = _make_request("setBreakpoints", seq=7, arguments={
            "source": {"path": ltl_file},
            "breakpoints": [
                {"line": 2, "condition": "name == \"Test\""},
            ],
        })
        server.handle_set_breakpoints(req)

        resp = capture.last_response()
        bps = resp["body"]["breakpoints"]
        assert len(bps) == 1
        assert bps[0]["condition"] == "name == \"Test\""

    def test_set_empty_breakpoints_clears(self, server, capture, ltl_file):
        # First set a breakpoint
        req1 = _make_request("setBreakpoints", seq=8, arguments={
            "source": {"path": ltl_file},
            "breakpoints": [{"line": 3}],
        })
        server.handle_set_breakpoints(req1)

        # Then clear
        req2 = _make_request("setBreakpoints", seq=9, arguments={
            "source": {"path": ltl_file},
            "breakpoints": [],
        })
        server.handle_set_breakpoints(req2)

        resp = capture.last_response()
        assert resp["body"]["breakpoints"] == []
        assert server.breakpoints[ltl_file] == []


# ─────────────────────────────────────────────────────────────────────────────
# Threads
# ─────────────────────────────────────────────────────────────────────────────

class TestThreads:
    def test_threads_single(self, server, capture):
        req = _make_request("threads", seq=10)
        server.handle_threads(req)

        resp = capture.last_response()
        assert resp["success"] is True
        threads = resp["body"]["threads"]
        assert len(threads) == 1
        assert threads[0]["id"] == 1
        assert threads[0]["name"] == "Main Thread"


# ─────────────────────────────────────────────────────────────────────────────
# Stack Trace
# ─────────────────────────────────────────────────────────────────────────────

class TestStackTrace:
    def test_stack_trace_no_debugger(self, server, capture):
        server.debugger = None
        req = _make_request("stackTrace", seq=11)
        server.handle_stack_trace(req)

        resp = capture.last_response()
        frames = resp["body"]["stackFrames"]
        assert len(frames) == 1
        assert frames[0]["name"] == "<module>"

    def test_stack_trace_total_frames(self, server, capture):
        server.debugger = None
        req = _make_request("stackTrace", seq=12)
        server.handle_stack_trace(req)

        resp = capture.last_response()
        assert resp["body"]["totalFrames"] == len(resp["body"]["stackFrames"])


# ─────────────────────────────────────────────────────────────────────────────
# Scopes
# ─────────────────────────────────────────────────────────────────────────────

class TestScopes:
    def test_scopes_returns_locals(self, server, capture):
        req = _make_request("scopes", seq=13, arguments={"frameId": 0})
        server.handle_scopes(req)

        resp = capture.last_response()
        scopes = resp["body"]["scopes"]
        assert len(scopes) == 1
        assert scopes[0]["name"] == "Locals"
        assert scopes[0]["expensive"] is False
        assert scopes[0]["variablesReference"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Variables
# ─────────────────────────────────────────────────────────────────────────────

class TestVariables:
    def test_variables_no_debugger(self, server, capture):
        server.debugger = None
        ref = server._new_var_ref()
        server.variables[ref] = {"type": "locals", "frame": 0}

        req = _make_request("variables", seq=14, arguments={
            "variablesReference": ref,
        })
        server.handle_variables(req)

        resp = capture.last_response()
        assert resp["success"] is True
        assert resp["body"]["variables"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Evaluate
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluate:
    def test_evaluate_no_debugger(self, server, capture):
        server.debugger = None
        req = _make_request("evaluate", seq=15, arguments={
            "expression": "2 + 2",
            "context": "hover",
        })
        server.handle_evaluate(req)

        resp = capture.last_response()
        assert resp["success"] is True
        assert resp["body"]["result"] == "2 + 2"  # no debugger → returns expression
        assert resp["body"]["variablesReference"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Stepping
# ─────────────────────────────────────────────────────────────────────────────

class TestStepping:
    def test_continue(self, server, capture):
        req = _make_request("continue", seq=16)
        server.handle_continue(req)

        resp = capture.last_response()
        assert resp["success"] is True
        assert resp["body"]["allThreadsContinued"] is True

    def test_next_sends_stopped_event(self, server, capture):
        req = _make_request("next", seq=17)
        server.handle_next(req)

        assert len(capture.responses) == 1
        assert len(capture.events) == 1
        evt = capture.last_event()
        assert evt["event"] == "stopped"
        assert evt["body"]["reason"] == "step"
        assert evt["body"]["threadId"] == 1

    def test_step_in(self, server, capture):
        req = _make_request("stepIn", seq=18)
        server.handle_step_in(req)

        resp = capture.last_response()
        assert resp["success"] is True

        evt = capture.last_event()
        assert evt["event"] == "stopped"
        assert evt["body"]["reason"] == "step"

    def test_step_out(self, server, capture):
        req = _make_request("stepOut", seq=19)
        server.handle_step_out(req)

        resp = capture.last_response()
        assert resp["success"] is True

        evt = capture.last_event()
        assert evt["event"] == "stopped"


# ─────────────────────────────────────────────────────────────────────────────
# Disconnect / ConfigurationDone / LoadedSources
# ─────────────────────────────────────────────────────────────────────────────

class TestLifecycle:
    def test_disconnect(self, server, capture):
        server.running = True
        req = _make_request("disconnect", seq=20)
        server.handle_disconnect(req)

        assert server.running is False
        resp = capture.last_response()
        assert resp["success"] is True

    def test_configuration_done(self, server, capture):
        req = _make_request("configurationDone", seq=21)
        server.handle_configuration_done(req)

        assert server.initialized is True
        resp = capture.last_response()
        assert resp["success"] is True

    def test_loaded_sources_empty(self, server, capture):
        req = _make_request("loadedSources", seq=22)
        server.handle_loaded_sources(req)

        resp = capture.last_response()
        assert resp["body"]["sources"] == []

    def test_loaded_sources_after_launch(self, server, capture, ltl_file):
        launch_req = _make_request("launch", seq=23, arguments={
            "program": ltl_file,
        })
        server.handle_launch(launch_req)

        req = _make_request("loadedSources", seq=24)
        server.handle_loaded_sources(req)

        resp = capture.last_response()
        sources = resp["body"]["sources"]
        assert len(sources) == 1
        assert sources[0]["path"] == ltl_file


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────────────

class TestDispatch:
    def test_dispatch_known_command(self, server, capture):
        msg = _make_request("threads", seq=30)
        server.dispatch(msg)

        assert len(capture.responses) == 1
        assert capture.last_response()["command"] == "threads"

    def test_dispatch_unknown_command(self, server, capture):
        msg = _make_request("nonExistentCommand", seq=31)
        server.dispatch(msg)

        resp = capture.last_response()
        assert resp["success"] is False
        assert "Unknown command" in resp.get("message", "")

    def test_dispatch_ignores_non_requests(self, server, capture):
        msg = {"seq": 1, "type": "event", "event": "output"}
        server.dispatch(msg)
        assert len(capture.messages) == 0

    def test_dispatch_handler_exception(self, server, capture):
        """If a handler raises, dispatch sends error response."""
        def bad_handler(req):
            raise RuntimeError("handler exploded")

        server.handle_threads = bad_handler
        msg = _make_request("threads", seq=32)
        server.dispatch(msg)

        resp = capture.last_response()
        assert resp["success"] is False
        assert "Internal error" in resp.get("message", "")


# ─────────────────────────────────────────────────────────────────────────────
# Wire format
# ─────────────────────────────────────────────────────────────────────────────

class TestWireFormat:
    def test_send_response_structure(self, server, capture):
        req = _make_request("threads", seq=40)
        server.send_response(req, body={"threads": []}, success=True)

        msg = capture.last_response()
        assert msg["type"] == "response"
        assert msg["request_seq"] == 40
        assert msg["success"] is True
        assert msg["command"] == "threads"
        assert "seq" in msg

    def test_send_response_with_message(self, server, capture):
        req = _make_request("launch", seq=41)
        server.send_response(req, success=False, message="File not found")

        msg = capture.last_response()
        assert msg["success"] is False
        assert msg["message"] == "File not found"

    def test_send_event_structure(self, server, capture):
        server.send_event("stopped", {"reason": "breakpoint", "threadId": 1})

        msg = capture.last_event()
        assert msg["type"] == "event"
        assert msg["event"] == "stopped"
        assert msg["body"]["reason"] == "breakpoint"
        assert "seq" in msg


# ─────────────────────────────────────────────────────────────────────────────
# Full session flow
# ─────────────────────────────────────────────────────────────────────────────

class TestFullSession:
    def test_init_launch_set_bp_continue_disconnect(self, server, capture, ltl_file):
        """End-to-end DAP session simulation."""
        # 1. Initialize
        server.dispatch(_make_request("initialize", seq=1, arguments={
            "clientID": "test",
        }))

        # 2. Launch
        server.dispatch(_make_request("launch", seq=2, arguments={
            "program": ltl_file,
        }))

        # 3. Configuration done
        server.dispatch(_make_request("configurationDone", seq=3))
        assert server.initialized

        # 4. Set breakpoints
        server.dispatch(_make_request("setBreakpoints", seq=4, arguments={
            "source": {"path": ltl_file},
            "breakpoints": [{"line": 2}],
        }))

        # 5. Threads
        server.dispatch(_make_request("threads", seq=5))

        # 6. Continue
        server.dispatch(_make_request("continue", seq=6))

        # 7. Disconnect
        server.dispatch(_make_request("disconnect", seq=7))
        assert not server.running

        # All responses should have succeeded (except the init capability check)
        for resp in capture.responses:
            assert resp["success"] is True, f"Failed: {resp.get('command')}: {resp.get('message')}"
