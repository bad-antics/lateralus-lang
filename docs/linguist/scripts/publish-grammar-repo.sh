#!/usr/bin/env bash
# One-shot publisher for docs/linguist/grammar_repo/ -> bad-antics/lateralus-grammar.
#
# This turns the grammar_repo/ directory into the root of a standalone
# git repository and pushes it to github.com/bad-antics/lateralus-grammar.
# Linguist requires the grammar to live in its own public repo (not as a
# subfolder of a larger repo) so it can be added as a git submodule.
#
# Prerequisites:
#   - Empty repository exists at https://github.com/bad-antics/lateralus-grammar
#   - gh CLI is authenticated, OR your git remote credentials are cached
#
# Usage:
#   ./scripts/publish-grammar-repo.sh [--create] [--tag v1.0.0]
#
# Flags:
#   --create   Create the remote repo via gh CLI first (requires gh auth).
#   --tag <v>  Tag the initial commit with <v> and push the tag.
#
# Idempotency: re-running will force-push the current grammar_repo/
# contents as a fresh initial commit. Never run with uncommitted manual
# edits inside grammar_repo/.git.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/docs/linguist/grammar_repo"
REMOTE_URL="git@github.com:bad-antics/lateralus-grammar.git"
TAG=""
CREATE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --create) CREATE=1; shift ;;
    --tag)    TAG="$2"; shift 2 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

[[ -d "$SRC" ]] || { echo "missing $SRC" >&2; exit 1; }

# Refresh from authoritative sources first.
"$ROOT/docs/linguist/scripts/sync-grammar-repo.sh"

# Stage in a temp dir so we don't pollute the main workspace.
WORK="$(mktemp -d)"
cp -a "$SRC/." "$WORK/"

cd "$WORK"
rm -rf .git

git init -q -b main
git add -A
git -c user.name="Lateralus Bot" \
    -c user.email="bot@lateralus.dev" \
    commit -q -m "Initial public release of Lateralus TextMate grammar (v1.0.0)

Extracted from bad-antics/lateralus-lang at the v3.1.0 release tag.
Grammar scope: source.ltl. See CHANGELOG.md for coverage."

if [[ "$CREATE" -eq 1 ]]; then
  command -v gh >/dev/null || { echo "gh CLI not installed" >&2; exit 3; }
  gh repo create bad-antics/lateralus-grammar \
     --public \
     --description "Official TextMate grammar for the Lateralus programming language (vendored by github-linguist/linguist)." \
     --homepage "https://lateralus.dev" || true
fi

git remote add origin "$REMOTE_URL"
git push -u origin main --force

if [[ -n "$TAG" ]]; then
  git tag -a "$TAG" -m "Lateralus grammar $TAG"
  git push origin "$TAG"
fi

echo
echo "published: $REMOTE_URL"
echo "tag:       ${TAG:-<none>}"
echo "next:      add as git submodule in a Linguist fork:"
echo "           git submodule add $REMOTE_URL vendor/grammars/lateralus-grammar"
