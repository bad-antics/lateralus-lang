#!/usr/bin/env python3
"""
LATERALUS Documentation Server

Serves .ltlml files as compiled HTML pages in the browser.
Any request for a .ltlml file is compiled on-the-fly via render_ltlml().
Static assets (.css, .js, .png, etc.) are served normally.
Supports auto-rebuild and live reload.

Usage:
    python scripts/serve_docs.py [--port PORT] [--dir DIR] [--no-reload]
    lateralus serve [--port PORT] [--dir DIR]
"""
import sys
import os
import re
import mimetypes
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from functools import lru_cache

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# MIME Types — register .ltlml so it's served as text/html
# ─────────────────────────────────────────────────────────────────────────────

mimetypes.add_type("text/html", ".ltlml")
mimetypes.add_type("text/html", ".ltlm")


# ─────────────────────────────────────────────────────────────────────────────
# Live-reload script injected into every served page
# ─────────────────────────────────────────────────────────────────────────────

_LIVE_RELOAD_SCRIPT = """
<script>
(function() {
    var lastCheck = Date.now();
    setInterval(function() {
        fetch('/__ltlml_check?t=' + lastCheck)
            .then(function(r) { return r.text(); })
            .then(function(t) {
                if (t === 'reload') { location.reload(); }
            })
            .catch(function() {});
    }, 1500);
})();
</script>
"""


class LTLMLHandler(SimpleHTTPRequestHandler):
    """HTTP handler that compiles .ltlml to HTML on the fly."""

    # Class-level config set before server starts
    docs_dir: Path = PROJECT_ROOT / "docs"
    enable_reload: bool = True
    _file_mtimes: dict = {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        # ── Live-reload check endpoint ────────────────────────────
        if path == "/__ltlml_check":
            changed = self._check_changes()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(b"reload" if changed else b"ok")
            return

        # ── Resolve the file path ─────────────────────────────────
        # Strip leading /
        rel = path.lstrip("/")
        if not rel:
            rel = "index"

        # Try: exact path, .ltlml fallback, .html fallback, directory index
        candidates = [
            self.docs_dir / rel,
            self.docs_dir / (rel + ".ltlml"),
            self.docs_dir / (rel + ".html"),
            self.docs_dir / rel / "index.ltlml",
            self.docs_dir / rel / "index.html",
        ]

        # If URL ends with .html, also try the corresponding .ltlml
        if rel.endswith(".html"):
            ltlml_path = self.docs_dir / rel.replace(".html", ".ltlml")
            candidates.insert(1, ltlml_path)

        resolved = None
        for c in candidates:
            if c.is_file():
                resolved = c
                break

        if resolved is None:
            self.send_error(404, f"Not found: {path}")
            return

        # ── Serve .ltlml by compiling to HTML ─────────────────────
        if resolved.suffix in (".ltlml", ".ltlm"):
            self._serve_ltlml(resolved)
        else:
            self._serve_static(resolved)

    def _serve_ltlml(self, filepath: Path):
        """Compile a .ltlml file and serve as HTML."""
        try:
            from lateralus_lang.markup import render_ltlml
        except ImportError:
            self.send_error(500, "lateralus_lang not installed")
            return

        try:
            source = filepath.read_text(encoding="utf-8")

            # If file is in polyglot HTML format, extract the LTLML source
            if source.strip().startswith('<!DOCTYPE'):
                m = re.search(
                    r'<script[^>]*type="text/ltlml"[^>]*>(.*?)</script>',
                    source, re.DOTALL
                )
                if m:
                    source = m.group(1).strip()

            html = render_ltlml(source)

            # Rewrite .ltlml links → .html for browser navigation
            html = html.replace('.ltlml"', '.html"')
            html = html.replace(".ltlml'", ".html'")

            # Inject nav bar
            nav_html = self._build_nav(filepath)
            html = re.sub(r'(<body[^>]*>)', r'\1' + nav_html, html, count=1)

            # Inject live-reload script
            if self.enable_reload:
                html = html.replace('</body>',
                                    _LIVE_RELOAD_SCRIPT + '</body>', 1)

            content = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            error_html = (
                f'<!DOCTYPE html><html><body style="background:#1a1a2e;'
                f'color:#e94560;font-family:monospace;padding:2rem">'
                f'<h1>LTLML Compile Error</h1>'
                f'<pre>{str(e)}</pre>'
                f'<p><a href="javascript:location.reload()"'
                f' style="color:#58a6ff">Retry</a></p>'
                f'</body></html>'
            ).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(error_html)))
            self.end_headers()
            self.wfile.write(error_html)

    def _serve_static(self, filepath: Path):
        """Serve a static file with proper MIME type."""
        try:
            content = filepath.read_bytes()
            mime, _ = mimetypes.guess_type(str(filepath))
            if mime is None:
                mime = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

    def _build_nav(self, current: Path) -> str:
        """Build a navigation bar for the current document."""
        pages = [
            ("index", "Home"),
            ("tutorial", "Tutorial"),
            ("language-spec", "Spec"),
            ("architecture", "Architecture"),
            ("quick-reference", "Reference"),
            ("cookbook", "Cookbook"),
        ]
        links = []
        for slug, label in pages:
            # Link to .html so the browser resolves correctly
            href = f"{slug}.html"
            style = (
                'margin-right:1rem;color:#e94560;'
                'text-decoration:none;font-weight:600'
                if current.stem == slug else
                'margin-right:1rem;color:#e94560;text-decoration:none'
            )
            links.append(f'<a href="{href}" style="{style}">{label}</a>')

        return (
            '\n<nav style="margin-bottom:2rem;padding:1rem;'
            'background:#16213e;border-radius:8px">'
            + ''.join(links) +
            '</nav>\n'
        )

    def _check_changes(self) -> bool:
        """Check if any .ltlml file has been modified since last check."""
        changed = False
        for ltlml in self.docs_dir.rglob("*.ltlml"):
            mtime = ltlml.stat().st_mtime
            prev = self._file_mtimes.get(str(ltlml), 0)
            if mtime > prev:
                self._file_mtimes[str(ltlml)] = mtime
                if prev > 0:  # Don't trigger on first scan
                    changed = True
        return changed

    def log_message(self, format, *args):
        """Custom log format."""
        path = args[0] if args else ""
        if "/__ltlml_check" in str(path):
            return  # Suppress reload-check noise
        sys.stderr.write(
            f"  \033[90m{self.log_date_time_string()}\033[0m  "
            f"{format % args}\n"
        )


def serve(port: int = 8400, docs_dir: Path = None, reload: bool = True):
    """Start the LTLML documentation server."""
    if docs_dir is None:
        docs_dir = PROJECT_ROOT / "docs"

    docs_dir = Path(docs_dir).resolve()
    if not docs_dir.exists():
        print(f"Error: docs directory not found: {docs_dir}", file=sys.stderr)
        sys.exit(1)

    LTLMLHandler.docs_dir = docs_dir
    LTLMLHandler.enable_reload = reload
    LTLMLHandler._file_mtimes = {}

    # Prime the mtime cache
    for ltlml in docs_dir.rglob("*.ltlml"):
        LTLMLHandler._file_mtimes[str(ltlml)] = ltlml.stat().st_mtime

    httpd = HTTPServer(("127.0.0.1", port), LTLMLHandler)

    ltlml_count = len(list(docs_dir.rglob("*.ltlml")))

    print()
    print(f"  \033[1;36mLATERALUS Documentation Server\033[0m")
    print(f"  {'='*45}")
    print(f"  Serving:  {docs_dir}")
    print(f"  Files:    {ltlml_count} .ltlml documents")
    print(f"  URL:      \033[4;34mhttp://127.0.0.1:{port}/\033[0m")
    print(f"  Reload:   {'enabled' if reload else 'disabled'}")
    print(f"  {'='*45}")
    print(f"  Press Ctrl+C to stop\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        httpd.server_close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="LATERALUS Documentation Server — serves .ltlml as HTML"
    )
    parser.add_argument("--port", "-p", type=int, default=8400,
                        help="Port to listen on (default: 8400)")
    parser.add_argument("--dir", "-d", type=Path, default=None,
                        help="Docs directory (default: docs/)")
    parser.add_argument("--no-reload", action="store_true",
                        help="Disable live reload")

    args = parser.parse_args()
    serve(port=args.port, docs_dir=args.dir, reload=not args.no_reload)


if __name__ == "__main__":
    main()
