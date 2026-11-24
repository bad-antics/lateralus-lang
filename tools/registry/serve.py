#!/usr/bin/env python3
"""A throwaway registry server for local testing only.

The real registries are static: an S3 bucket, an R2 bucket, a Cloudflare Pages
project, an nginx document root. None of them run Python. This script exists so
that ``publish --registry-url`` and ``add --registry-url`` can be exercised end
to end on a laptop without provisioning a bucket.

    python tools/registry/serve.py /tmp/registry --port 8777
    lateralus add hello --registry-url http://127.0.0.1:8777

It speaks GET and PUT, refuses every path that resolves outside the root, and
refuses to bind to anything but loopback. Do not deploy it.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import sys
from pathlib import Path


class RegistryHandler(http.server.SimpleHTTPRequestHandler):
    """GET serves files; PUT writes them, atomically and only inside the root."""

    server_version = "LateralusRegistryDev/1.0"

    def _safe_target(self) -> Path | None:
        relative = self.path.split("?", 1)[0].lstrip("/")
        if not relative:
            return None
        root = Path(self.directory).resolve()
        candidate = (root / relative).resolve()
        if not str(candidate).startswith(str(root) + os.sep):
            return None
        return candidate

    def do_PUT(self):  # noqa: N802 — http.server naming
        target = self._safe_target()
        if target is None:
            self.send_error(403, "path escapes the registry root")
            return
        length = self.headers.get("Content-Length")
        if length is None:
            self.send_error(411, "Content-Length required")
            return
        try:
            size = int(length)
        except ValueError:
            self.send_error(400, "bad Content-Length")
            return
        if size > 64 * 1024 * 1024:
            self.send_error(413, "payload too large")
            return

        payload = self.rfile.read(size)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".upload")
        temp.write_bytes(payload)
        temp.replace(target)
        self.send_response(201)
        self.send_header("Content-Length", "0")
        self.end_headers()
        sys.stderr.write(f"  PUT {target.name} ({size:,} bytes)\n")

    def do_POST(self):  # noqa: N802
        self.send_error(405, "use PUT")

    def log_message(self, fmt, *args):  # keep the console readable
        sys.stderr.write("  " + (fmt % args) + "\n")


def serve(root: Path, port: int = 8777, host: str = "127.0.0.1") -> None:
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(RegistryHandler, directory=str(root))
    with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"serving {root}")
        print(f"  http://{host}:{port}/index.json")
        print("  ctrl-c to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve a Lateralus registry over HTTP (development only)")
    parser.add_argument("root", nargs="?", default=".",
                        help="registry root directory (default: current directory)")
    parser.add_argument("--port", "-p", type=int, default=8777)
    args = parser.parse_args(argv)
    serve(Path(args.root), port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
