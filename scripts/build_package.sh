#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# scripts/build_package.sh — Build distributable packages for testers
# ──────────────────────────────────────────────────────────────────────
# Produces:
#   dist/lateralus_lang-1.5.0.tar.gz   (sdist — full source archive)
#   dist/lateralus_lang-1.5.0-py3-none-any.whl  (wheel — pip-installable)
#
# Testers install with:
#   pip install lateralus_lang-1.5.0-py3-none-any.whl
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
VERSION=$(python3 -c "import re; print(re.search(r'version\s*=\s*\"([^\"]+)\"', open('pyproject.toml').read()).group(1))")

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  LATERALUS Package Builder — v${VERSION}                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Clean previous builds ────────────────────────────────────────
echo "▸ [1/5] Cleaning previous build artifacts..."
rm -rf dist/ build/ *.egg-info lateralus_lang.egg-info
echo "  ✓ Clean"

# ── 2. Ensure build tool is available ────────────────────────────────
echo "▸ [2/5] Checking build dependencies..."
if ! python3 -m build --version &>/dev/null; then
    echo "  → Installing 'build' package..."
    pip install --quiet build
fi
echo "  ✓ python3 -m build $(python3 -m build --version 2>&1 | head -1)"

# ── 3. Build sdist + wheel ──────────────────────────────────────────
echo "▸ [3/5] Building sdist and wheel..."
python3 -m build --sdist --wheel --outdir dist/ 2>&1 | sed 's/^/  /'
echo "  ✓ Build complete"

# ── 4. Show the artifacts ───────────────────────────────────────────
echo ""
echo "▸ [4/5] Build artifacts:"
ls -lh dist/
echo ""

# ── 5. Quick sanity check ───────────────────────────────────────────
echo "▸ [5/5] Sanity checks..."

WHL=$(ls dist/*.whl 2>/dev/null | head -1)
SDIST=$(ls dist/*.tar.gz 2>/dev/null | head -1)

if [[ -z "$WHL" ]]; then
    echo "  ✗ No .whl file produced"
    exit 1
fi
if [[ -z "$SDIST" ]]; then
    echo "  ✗ No .tar.gz file produced"
    exit 1
fi

# Check wheel contains key modules
echo "  Wheel contents (key files):"
python3 -m zipfile -l "$WHL" 2>/dev/null | grep -E '(compiler|lexer|parser|vm/|codegen/|__main__)' | head -10 | sed 's/^/    /' || true

# Check sdist contains stdlib and examples
echo "  Sdist contents (data directories):"
tar tzf "$SDIST" 2>/dev/null | grep -E '(stdlib/|examples/|vscode-lateralus/)' | head -10 | sed 's/^/    /' || true

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ✓ Package ready for distribution!"
echo ""
echo "  Your testers can install with:"
echo "    pip install dist/$(basename "$WHL")"
echo ""
echo "  Or from the source archive:"
echo "    pip install dist/$(basename "$SDIST")"
echo ""
echo "  VS Code extension is bundled in the sdist under"
echo "  vscode-lateralus/ — testers can copy it manually:"
echo "    cp -r vscode-lateralus ~/.vscode/extensions/lateralus-lang.lateralus-${VERSION}"
echo "══════════════════════════════════════════════════════════"
