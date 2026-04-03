#!/usr/bin/env python3
"""
LATERALUS Documentation Generator

Compiles all .ltlml documentation files to HTML.
Generates a documentation site in docs/_build/.

Usage:
    python scripts/build_docs.py [--output DIR] [--watch]
"""
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def build_docs(output_dir: Path = None):
    """Build all documentation files."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "docs" / "_build"

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from lateralus_lang.markup import render_ltlml
    except ImportError:
        print("Error: lateralus_lang not installed. Run: pip install -e .")
        sys.exit(1)

    docs_dir = PROJECT_ROOT / "docs"
    ltlml_files = list(docs_dir.rglob("*.ltlml"))

    if not ltlml_files:
        print("No .ltlml files found in docs/")
        return

    print(f"  Building LATERALUS Documentation")
    print(f"  {'='*50}")
    print(f"  Source: {docs_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Files:  {len(ltlml_files)}")
    print()

    success = 0
    failed = 0

    for ltlml_file in sorted(ltlml_files):
        rel = ltlml_file.relative_to(docs_dir)
        html_file = output_dir / rel.with_suffix(".html")
        html_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            source = ltlml_file.read_text(encoding="utf-8")

            # If file is in polyglot HTML format, extract the LTLML source
            if source.strip().startswith('<!DOCTYPE'):
                import re as _re2
                m = _re2.search(
                    r'<script[^>]*type="text/ltlml"[^>]*>(.*?)</script>',
                    source, _re2.DOTALL
                )
                if m:
                    source = m.group(1).strip()

            full_html = render_ltlml(source)

            # Inject nav bar after <body...>
            nav_html = (
                '\n<nav style="margin-bottom:2rem;padding:1rem;'
                'background:#16213e;border-radius:8px">'
                '<a href="index.html" style="margin-right:1rem;color:#e94560;'
                'text-decoration:none">Home</a>'
                '<a href="tutorial.html" style="margin-right:1rem;color:#e94560;'
                'text-decoration:none">Tutorial</a>'
                '<a href="language-spec.html" style="margin-right:1rem;color:#e94560;'
                'text-decoration:none">Spec</a>'
                '<a href="architecture.html" style="margin-right:1rem;color:#e94560;'
                'text-decoration:none">Architecture</a>'
                '<a href="quick-reference.html" style="color:#e94560;'
                'text-decoration:none">Reference</a>'
                '</nav>\n'
            )
            footer_html = (
                '\n<footer style="margin-top:3rem;padding-top:1rem;'
                'border-top:1px solid #0f3460;color:#8888aa;font-size:0.85rem;'
                'text-align:center">'
                '<p>LATERALUS v1.5.0 — Spiraling Outward</p>'
                '</footer>\n'
            )

            # Inject after first <body...> tag
            import re as _re
            full_html = _re.sub(
                r'(<body[^>]*>)',
                r'\1' + nav_html,
                full_html,
                count=1,
            )
            # Inject before </body>
            full_html = full_html.replace('</body>', footer_html + '</body>', 1)

            # Rewrite any remaining .ltlml hrefs → .html so pages resolve
            full_html = full_html.replace('.ltlml"', '.html"')
            full_html = full_html.replace(".ltlml'", ".html'")

            html_file.write_text(full_html, encoding="utf-8")
            print(f"    OK   {rel} -> {html_file.name}")
            success += 1

        except Exception as e:
            print(f"    FAIL {rel}: {e}")
            failed += 1

    print()
    print(f"  Built {success} files, {failed} failed")

    # Generate index if it doesn't exist already
    index_html = output_dir / "index.html"
    if not index_html.exists():
        print(f"  Note: No index.ltlml found, skipping index generation")

    return success, failed


def watch_mode(output_dir: Path = None):
    """Watch for changes and rebuild."""
    docs_dir = PROJECT_ROOT / "docs"
    print(f"  Watching {docs_dir} for changes...")
    print(f"  Press Ctrl+C to stop")

    last_build = 0
    while True:
        try:
            newest = max(
                (f.stat().st_mtime for f in docs_dir.rglob("*.ltlml")),
                default=0
            )
            if newest > last_build:
                print(f"\n  Change detected, rebuilding...")
                build_docs(output_dir)
                last_build = time.time()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Stopped watching.")
            break


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="LATERALUS Documentation Generator"
    )
    parser.add_argument("--output", "-o", type=Path, default=None,
                       help="Output directory (default: docs/_build/)")
    parser.add_argument("--watch", "-w", action="store_true",
                       help="Watch for changes and rebuild")

    args = parser.parse_args()

    if args.watch:
        build_docs(args.output)
        watch_mode(args.output)
    else:
        success, failed = build_docs(args.output)
        sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
