#!/usr/bin/env python3
"""
LATERALUS Debug Adapter Protocol (DAP) Server

Implements a subset of the Debug Adapter Protocol for integration
with VS Code and other DAP-compatible editors. This enables:
- Setting breakpoints from the editor
- Step-by-step execution
- Variable inspection
- Watch expressions
- Call stack navigation

Protocol: https://microsoft.github.io/debug-adapter-protocol/
"""
from __future__ import annotations

import json
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DAPMessage:
    """Base DAP protocol message."""
    seq: int
    type: str  # "request", "response", "event"


@dataclass
class DAPRequest(DAPMessage):
    command: str
    arguments: dict = field(default_factory=dict)


@dataclass
class DAPResponse(DAPMessage):
    request_seq: int = 0
    success: bool = True
    command: str = ""
    body: dict = field(default_factory=dict)
    message: str = ""


@dataclass
class DAPEvent(DAPMessage):
    event: str = ""
    body: dict = field(default_factory=dict)


class DAPServer:
    """
    Debug Adapter Protocol server for LATERALUS.

    Handles communication over stdin/stdout using the DAP wire format:
    Content-Length: <length>\r\n\r\n<JSON payload>
    """

    def __init__(self):
        self.seq = 0
        self.running = False
        self.initialized = False
        self.breakpoints: dict[str, list[dict]] = {}
        self.source_files: dict[str, list[str]] = {}
        self.variables: dict[int, dict] = {}
        self._var_ref_counter = 1000

        # Import debugger if available
        try:
            from lateralus_lang.debugger import LateralusDebugger
            self.debugger = LateralusDebugger()
        except ImportError:
            self.debugger = None

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq

    # ─── Wire Protocol ─────────────────────────────────────────────

    def read_message(self) -> dict | None:
        """Read a DAP message from stdin."""
        headers = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            line = line.decode("utf-8").strip()
            if not line:
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        content_length = int(headers.get("Content-Length", 0))
        if content_length == 0:
            return None

        content = sys.stdin.buffer.read(content_length)
        return json.loads(content.decode("utf-8"))

    def send_message(self, msg: dict):
        """Send a DAP message to stdout."""
        body = json.dumps(msg)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        sys.stdout.buffer.write(header.encode("utf-8"))
        sys.stdout.buffer.write(body.encode("utf-8"))
        sys.stdout.buffer.flush()

    def send_response(self, request: dict, body: dict = None,
                      success: bool = True, message: str = ""):
        """Send a response to a request."""
        response = {
            "seq": self.next_seq(),
            "type": "response",
            "request_seq": request.get("seq", 0),
            "success": success,
            "command": request.get("command", ""),
            "body": body or {},
        }
        if message:
            response["message"] = message
        self.send_message(response)

    def send_event(self, event: str, body: dict = None):
        """Send an event notification."""
        msg = {
            "seq": self.next_seq(),
            "type": "event",
            "event": event,
            "body": body or {},
        }
        self.send_message(msg)

    # ─── Request Handlers ──────────────────────────────────────────

    def handle_initialize(self, request: dict):
        """Handle initialize request — declare capabilities."""
        capabilities = {
            "supportsConfigurationDoneRequest": True,
            "supportsFunctionBreakpoints": False,
            "supportsConditionalBreakpoints": True,
            "supportsHitConditionalBreakpoints": True,
            "supportsEvaluateForHovers": True,
            "supportsStepBack": False,
            "supportsSetVariable": False,
            "supportsRestartFrame": False,
            "supportsGotoTargetsRequest": False,
            "supportsStepInTargetsRequest": False,
            "supportsCompletionsRequest": False,
            "supportsModulesRequest": False,
            "supportsExceptionOptions": False,
            "supportsValueFormattingOptions": False,
            "supportsExceptionInfoRequest": False,
            "supportTerminateDebuggee": True,
            "supportsDelayedStackTraceLoading": False,
            "supportsLoadedSourcesRequest": True,
        }
        self.send_response(request, capabilities)
        self.send_event("initialized")

    def handle_launch(self, request: dict):
        """Handle launch request — start debugging a program."""
        args = request.get("arguments", {})
        program = args.get("program", "")
        stop_on_entry = args.get("stopOnEntry", False)

        if not program:
            self.send_response(request, success=False,
                             message="No program specified")
            return

        path = Path(program)
        if not path.exists():
            self.send_response(request, success=False,
                             message=f"File not found: {program}")
            return

        # Load source
        source = path.read_text(encoding="utf-8")
        self.source_files[program] = source.split("\n")

        self.send_response(request)

        if stop_on_entry:
            self.send_event("stopped", {
                "reason": "entry",
                "threadId": 1,
            })

    def handle_set_breakpoints(self, request: dict):
        """Handle setBreakpoints request."""
        args = request.get("arguments", {})
        source = args.get("source", {})
        source_path = source.get("path", "")
        breakpoint_specs = args.get("breakpoints", [])

        verified_breakpoints = []
        self.breakpoints[source_path] = []

        for bp_spec in breakpoint_specs:
            line = bp_spec.get("line", 0)
            condition = bp_spec.get("condition")

            bp = {
                "id": len(verified_breakpoints) + 1,
                "verified": True,
                "line": line,
                "source": source,
            }

            if condition:
                bp["condition"] = condition

            verified_breakpoints.append(bp)
            self.breakpoints[source_path].append({
                "line": line,
                "condition": condition,
            })

            # Register with debugger
            if self.debugger:
                self.debugger.add_breakpoint(source_path, line,
                                            condition=condition)

        self.send_response(request, {
            "breakpoints": verified_breakpoints,
        })

    def handle_threads(self, request: dict):
        """Handle threads request — LATERALUS is single-threaded."""
        self.send_response(request, {
            "threads": [
                {"id": 1, "name": "Main Thread"},
            ]
        })

    def handle_stack_trace(self, request: dict):
        """Handle stackTrace request."""
        frames = []

        if self.debugger and self.debugger.call_stack:
            for i, frame in enumerate(reversed(self.debugger.call_stack)):
                frames.append({
                    "id": i,
                    "name": frame.function,
                    "source": {
                        "name": Path(frame.file).name,
                        "path": frame.file,
                    },
                    "line": frame.line,
                    "column": 1,
                })
        else:
            frames.append({
                "id": 0,
                "name": "<module>",
                "line": 1,
                "column": 1,
            })

        self.send_response(request, {
            "stackFrames": frames,
            "totalFrames": len(frames),
        })

    def handle_scopes(self, request: dict):
        """Handle scopes request — return variable scopes."""
        frame_id = request.get("arguments", {}).get("frameId", 0)

        local_ref = self._new_var_ref()
        self.variables[local_ref] = {"type": "locals", "frame": frame_id}

        scopes = [
            {
                "name": "Locals",
                "variablesReference": local_ref,
                "expensive": False,
            },
        ]

        self.send_response(request, {"scopes": scopes})

    def handle_variables(self, request: dict):
        """Handle variables request — return variables in a scope."""
        ref = request.get("arguments", {}).get("variablesReference", 0)
        scope_info = self.variables.get(ref, {})

        variables = []

        if self.debugger and self.debugger.call_stack:
            frame_idx = scope_info.get("frame", 0)
            if frame_idx < len(self.debugger.call_stack):
                frame = self.debugger.call_stack[-(frame_idx + 1)]
                for name, value in frame.locals.items():
                    variables.append({
                        "name": name,
                        "value": str(value),
                        "type": type(value).__name__,
                        "variablesReference": 0,
                    })

        self.send_response(request, {"variables": variables})

    def handle_evaluate(self, request: dict):
        """Handle evaluate request (hover, watch, repl)."""
        args = request.get("arguments", {})
        expression = args.get("expression", "")
        context = args.get("context", "hover")  # hover, watch, repl

        result = expression  # Fallback

        if self.debugger:
            try:
                result = str(self.debugger.evaluate(expression))
            except Exception as e:
                result = f"Error: {e}"

        self.send_response(request, {
            "result": str(result),
            "variablesReference": 0,
        })

    def handle_continue(self, request: dict):
        """Handle continue request."""
        if self.debugger:
            self.debugger.do_continue()

        self.send_response(request, {"allThreadsContinued": True})

    def handle_next(self, request: dict):
        """Handle next (step over) request."""
        if self.debugger:
            self.debugger.step_over()

        self.send_response(request)
        self.send_event("stopped", {
            "reason": "step",
            "threadId": 1,
        })

    def handle_step_in(self, request: dict):
        """Handle stepIn request."""
        if self.debugger:
            self.debugger.step_into()

        self.send_response(request)
        self.send_event("stopped", {
            "reason": "step",
            "threadId": 1,
        })

    def handle_step_out(self, request: dict):
        """Handle stepOut request."""
        if self.debugger:
            self.debugger.step_out()

        self.send_response(request)
        self.send_event("stopped", {
            "reason": "step",
            "threadId": 1,
        })

    def handle_disconnect(self, request: dict):
        """Handle disconnect request."""
        self.running = False
        self.send_response(request)

    def handle_configuration_done(self, request: dict):
        """Handle configurationDone request."""
        self.initialized = True
        self.send_response(request)

    def handle_loaded_sources(self, request: dict):
        """Handle loadedSources request."""
        sources = [
            {"name": Path(f).name, "path": f}
            for f in self.source_files
        ]
        self.send_response(request, {"sources": sources})

    # ─── Dispatch ──────────────────────────────────────────────────

    HANDLERS = {
        "initialize": "handle_initialize",
        "launch": "handle_launch",
        "setBreakpoints": "handle_set_breakpoints",
        "threads": "handle_threads",
        "stackTrace": "handle_stack_trace",
        "scopes": "handle_scopes",
        "variables": "handle_variables",
        "evaluate": "handle_evaluate",
        "continue": "handle_continue",
        "next": "handle_next",
        "stepIn": "handle_step_in",
        "stepOut": "handle_step_out",
        "disconnect": "handle_disconnect",
        "configurationDone": "handle_configuration_done",
        "loadedSources": "handle_loaded_sources",
    }

    def dispatch(self, message: dict):
        """Dispatch a DAP message to the appropriate handler."""
        msg_type = message.get("type", "")
        if msg_type != "request":
            return

        command = message.get("command", "")
        handler_name = self.HANDLERS.get(command)

        if handler_name:
            handler = getattr(self, handler_name, None)
            if handler:
                try:
                    handler(message)
                except Exception as e:
                    self.send_response(message, success=False,
                                     message=f"Internal error: {e}")
        else:
            self.send_response(message, success=False,
                             message=f"Unknown command: {command}")

    # ─── Helpers ───────────────────────────────────────────────────

    def _new_var_ref(self) -> int:
        self._var_ref_counter += 1
        return self._var_ref_counter

    # ─── Main Loop ─────────────────────────────────────────────────

    def run(self):
        """Main message loop."""
        self.running = True
        while self.running:
            try:
                message = self.read_message()
                if message is None:
                    break
                self.dispatch(message)
            except Exception as e:
                # Log error but keep running
                sys.stderr.write(f"DAP Error: {e}\n")
                sys.stderr.flush()


def main():
    """Entry point for the DAP server."""
    server = DAPServer()
    server.run()


if __name__ == "__main__":
    main()
