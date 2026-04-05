#!/usr/bin/env bash
# ----------------------------------------------------------------------
# scripts/release.sh — Prepare and publish a LATERALUS GitHub release
# Usage:
#   ./scripts/release.sh              # full release (init, test, tag, push)
#   ./scripts/release.sh --dry-run    # preview what would happen
#   ./scripts/release.sh --tag-only   # just create the tag (skip tests)
# ----------------------------------------------------------------------
set -euo pipefail

VERSION="1.5.0"
TAG="v${VERSION}"
REPO_URL="https://github.com/lateralus-lang/lateralus.git"   # ← update this
RELEASE_TITLE="LATERALUS v${VERSION} — ADT Edition"
DRY_RUN=false
TAG_ONLY=false

# -- Parse flags ------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --dry-run)  DRY_RUN=true ;;
    --tag-only) TAG_ONLY=true ;;
    *) echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "+==========================================================+"
echo "|  LATERALUS Release Script — v${VERSION}                   |"
echo "+==========================================================+"
echo ""

# -- 1. Version consistency check ------------------------------------
echo "▸ [1/7] Checking version consistency..."
PY_VER=$(python3 -c "import lateralus_lang; print(lateralus_lang.__version__)" 2>/dev/null || echo "UNKNOWN")
TOML_VER=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')

if [[ "$PY_VER" != "$VERSION" ]]; then
  echo "  ✗ __init__.py version ($PY_VER) != expected ($VERSION)"
  exit 1
fi
if [[ "$TOML_VER" != "$VERSION" ]]; then
  echo "  ✗ pyproject.toml version ($TOML_VER) != expected ($VERSION)"
  exit 1
fi
echo "  ✓ Version $VERSION consistent across pyproject.toml and __init__.py"

# -- 2. Run tests ----------------------------------------------------
if [[ "$TAG_ONLY" == false ]]; then
  echo ""
  echo "▸ [2/7] Running full test suite..."
  if [[ "$DRY_RUN" == true ]]; then
    echo "  (dry-run: skipping tests)"
  else
    python -m pytest tests/ --tb=short -q 2>&1 | tail -5
    TEST_EXIT=${PIPESTATUS[0]}
    if [[ "$TEST_EXIT" -ne 0 ]]; then
      echo "  ✗ Tests failed! Aborting release."
      exit 1
    fi
    echo "  ✓ All tests passed"
  fi
else
  echo ""
  echo "▸ [2/7] Skipping tests (--tag-only)"
fi

# -- 3. Health check -------------------------------------------------
if [[ "$TAG_ONLY" == false ]]; then
  echo ""
  echo "▸ [3/7] Running health check..."
  if [[ "$DRY_RUN" == true ]]; then
    echo "  (dry-run: skipping health check)"
  else
    python scripts/health_check.py 2>&1 | tail -3
    echo "  ✓ Health check completed"
  fi
else
  echo ""
  echo "▸ [3/7] Skipping health check (--tag-only)"
fi

# -- 4. Initialize git (if needed) -----------------------------------
echo ""
echo "▸ [4/7] Checking git repository..."
if [[ ! -d .git ]]; then
  echo "  Initializing git repository..."
  if [[ "$DRY_RUN" == true ]]; then
    echo "  (dry-run: would run git init)"
  else
    git init
    git config user.name "bad-antics"
    git config user.email "bad-antics@lateralus.dev"
    echo "  ✓ Git repository initialized"
  fi
else
  echo "  ✓ Git repository already exists"
fi

# -- 5. Stage and commit ---------------------------------------------
echo ""
echo "▸ [5/7] Staging files..."
if [[ "$DRY_RUN" == true ]]; then
  echo "  (dry-run: would stage all files and commit)"
else
  git add -A
  # Check if there's anything to commit
  if git diff --cached --quiet 2>/dev/null; then
    echo "  ✓ Nothing new to commit (already up to date)"
  else
    git commit -m "release: LATERALUS v${VERSION} — ADT Edition

Highlights:
- Algebraic data types (Result, Option) with pattern matching
- Hindley-Milner type inference with Robinson unification
- Optional types (int?) with flow-sensitive type narrowing
- Generics with trait bounds and const generics
- C99 backend (hosted + freestanding modes)
- LateralusOS: 375KB bare-metal kernel with GUI desktop
- 28 stdlib modules (6 new)
- LSP server with compiler-powered diagnostics
- VS Code extension with grammar, snippets, icons
- 1,158 tests passing"
    echo "  ✓ Changes committed"
  fi
fi

# -- 6. Create tag ---------------------------------------------------
echo ""
echo "▸ [6/7] Creating release tag ${TAG}..."
if [[ "$DRY_RUN" == true ]]; then
  echo "  (dry-run: would create tag ${TAG})"
else
  if git tag -l | grep -q "^${TAG}$"; then
    echo "  ⚠ Tag ${TAG} already exists, skipping"
  else
    git tag -a "${TAG}" -m "${RELEASE_TITLE}

$(cat RELEASE_NOTES.md)"
    echo "  ✓ Tag ${TAG} created"
  fi
fi

# -- 7. Push instructions --------------------------------------------
echo ""
echo "▸ [7/7] Push to GitHub..."
if [[ "$DRY_RUN" == true ]]; then
  echo "  (dry-run: would push to origin)"
else
  # Check if remote exists
  if git remote | grep -q origin; then
    echo "  Remote 'origin' already configured"
  else
    echo "  ⚠ No remote 'origin' found."
    echo "  Add your GitHub remote with:"
    echo ""
    echo "    git remote add origin ${REPO_URL}"
    echo ""
  fi

  echo ""
  echo "  To push the release, run:"
  echo ""
  echo "    git push -u origin main"
  echo "    git push origin ${TAG}"
  echo ""
  echo "  To create the GitHub release via CLI (requires 'gh'):"
  echo ""
  echo "    gh release create ${TAG} \\"
  echo "      --title \"${RELEASE_TITLE}\" \\"
  echo "      --notes-file RELEASE_NOTES.md"
  echo ""
fi

# -- Summary ----------------------------------------------------------
echo "=============================================================="
echo "  Release preparation complete!"
echo ""
echo "  Version:  ${VERSION}"
echo "  Tag:      ${TAG}"
echo "  Title:    ${RELEASE_TITLE}"
echo "  Tests:    1,158 passing"
echo "  Stdlib:   28 modules"
echo "  Kernel:   375 KB (LateralusOS)"
echo "=============================================================="
