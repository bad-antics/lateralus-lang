#!/usr/bin/env python3
"""Convert .ltlml files into polyglot HTML format that self-renders in browsers.

Each .ltlml file gets wrapped in minimal HTML that loads ltlml.js + ltlml.css
and renders the {block} content client-side. The original LTLML source is
preserved inside a <script type="text/ltlml"> element so it remains parseable
by both the browser renderer and the Python build pipeline.
"""

import os
import sys

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DOCS_DIR)

POLYGLOT_PREFIX = '<!DOCTYPE html>'

# Relative path from a file to docs/ root for asset resolution
def rel_path_to_docs(filepath):
    """Get relative path from the file's directory to docs/."""
    filedir = os.path.dirname(os.path.abspath(filepath))
    docsdir = os.path.abspath(DOCS_DIR)
    return os.path.relpath(docsdir, filedir)

def extract_title(source):
    """Extract title from {document} block or {h1} block."""
    for line in source.splitlines():
        line = line.strip()
        if line.startswith('title:'):
            t = line.split(':', 1)[1].strip().strip('"').strip("'")
            return t
        if line.startswith('{h1 '):
            return line[4:].rstrip('}').strip()
    return "LATERALUS Document"

def build_nav(rel):
    """Build navigation bar with links."""
    return f'''<nav class="ltlml-nav">
    <span class="nav-brand">LATERALUS</span>
    <a href="{rel}/index.ltlml">Home</a>
    <a href="{rel}/tutorial.ltlml">Tutorial</a>
    <a href="{rel}/cookbook.ltlml">Cookbook</a>
    <a href="{rel}/language-spec.ltlml">Spec</a>
    <a href="{rel}/quick-reference.ltlml">Quick Ref</a>
    <a href="{rel}/architecture.ltlml">Architecture</a>
  </nav>'''

def wrap_ltlml(filepath):
    """Wrap an .ltlml file in polyglot HTML."""
    with open(filepath, 'r') as f:
        source = f.read()

    # Already converted?
    if source.strip().startswith('<!DOCTYPE'):
        print(f"  SKIP (already polyglot): {filepath}")
        return False

    title = extract_title(source)
    rel = rel_path_to_docs(filepath)

    # Use '.' if file is directly in docs/
    if rel == '.':
        css_path = 'ltlml.css'
        js_path = 'ltlml.js'
    else:
        css_path = f'{rel}/ltlml.css'
        js_path = f'{rel}/ltlml.js'

    nav = build_nav(rel)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{css_path}">
</head>
<body>
  {nav}
  <div id="ltlml-render" class="ltlml-document"></div>
  <script id="ltlml-source" type="text/ltlml">
{source}
  </script>
  <script src="{js_path}"></script>
</body>
</html>
'''
    with open(filepath, 'w') as f:
        f.write(html)

    return True


def main():
    """Find and convert all .ltlml files under docs/."""
    count = 0
    skipped = 0

    for dirpath, dirnames, filenames in os.walk(DOCS_DIR):
        # Skip build directories
        dirnames[:] = [d for d in dirnames if d not in ('_build', 'html')]

        for fn in sorted(filenames):
            if fn.endswith('.ltlml'):
                fp = os.path.join(dirpath, fn)
                relname = os.path.relpath(fp, DOCS_DIR)
                if wrap_ltlml(fp):
                    print(f"  OK: {relname}")
                    count += 1
                else:
                    skipped += 1

    print(f"\nConverted {count} files, skipped {skipped}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
