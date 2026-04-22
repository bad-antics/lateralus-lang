#!/usr/bin/env bash
# Sync docs/linguist/grammar_repo/ with the authoritative grammar files
# inside vscode-lateralus/. The grammar_repo directory is what gets
# mirrored (via publish-grammar-repo.sh) to bad-antics/lateralus-grammar,
# which Linguist vendors.
#
# Run this whenever you edit vscode-lateralus/syntaxes/lateralus.tmLanguage.json
# or vscode-lateralus/language-configuration.json.
#
# Usage:
#   ./scripts/sync-grammar-repo.sh

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SRC_GRAMMAR="$ROOT/vscode-lateralus/syntaxes/lateralus.tmLanguage.json"
SRC_CONFIG="$ROOT/vscode-lateralus/language-configuration.json"
DST_DIR="$ROOT/docs/linguist/grammar_repo"

[[ -f "$SRC_GRAMMAR" ]] || { echo "missing $SRC_GRAMMAR" >&2; exit 1; }
[[ -f "$SRC_CONFIG"  ]] || { echo "missing $SRC_CONFIG"  >&2; exit 1; }

mkdir -p "$DST_DIR/syntaxes"
cp "$SRC_GRAMMAR" "$DST_DIR/syntaxes/lateralus.tmLanguage.json"
cp "$SRC_CONFIG"  "$DST_DIR/language-configuration.json"

echo "synced:"
echo "  $SRC_GRAMMAR -> $DST_DIR/syntaxes/lateralus.tmLanguage.json"
echo "  $SRC_CONFIG  -> $DST_DIR/language-configuration.json"

# Quick sanity check: scopeName must remain source.ltl
if ! grep -q '"scopeName": "source.ltl"' "$DST_DIR/syntaxes/lateralus.tmLanguage.json"; then
  echo "ERROR: scopeName is not 'source.ltl' — Linguist PR will fail!" >&2
  exit 2
fi

# Sanity check: package.json grammar path must match
if ! grep -q '"./syntaxes/lateralus.tmLanguage.json"' "$DST_DIR/package.json"; then
  echo "ERROR: package.json grammar path is stale" >&2
  exit 3
fi

echo "all sanity checks passed."
