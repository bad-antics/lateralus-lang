#!/usr/bin/env bash
# Count discoverable Lateralus repos on GitHub for Linguist purposes.
# Appends one JSON line per run to meta/repo-count.jsonl.
#
# Usage:
#   GITHUB_TOKEN=ghp_... ./scripts/count-ltl-repos.sh
#
# Thresholds:
#   - Linguist requires >= 200 unique repositories using the language.
#   - We poll daily and stop polling once we clear the threshold
#     twice in a row (guard against transient API glitches).

set -euo pipefail

: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"
OUT="${OUT:-meta/repo-count.jsonl}"
mkdir -p "$(dirname "$OUT")"

q_all="extension:ltl"
q_community="extension:ltl+NOT+user:bad-antics"

fetch() {
  curl -sf -H "Authorization: Bearer $GITHUB_TOKEN" \
       -H "Accept: application/vnd.github+json" \
       "https://api.github.com/search/code?q=$1&per_page=1" \
     | jq -r '.total_count'
}

all=$(fetch "$q_all")
community=$(fetch "$q_community")
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

printf '{"ts":"%s","total":%s,"community":%s,"threshold":200}\n' \
       "$ts" "$all" "$community" >> "$OUT"

echo "counted  total=$all  community=$community  (threshold=200)"
