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

set -uo pipefail   # tolerate non-zero exits so we can fall back gracefully

: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"
OUT="${OUT:-meta/repo-count.jsonl}"
mkdir -p "$(dirname "$OUT")"

q_all="extension:ltl"
q_community="extension:ltl+NOT+user:bad-antics"
q_repo_fallback="lateralus+in:name,description,readme"

fetch() {
  # Returns total_count or empty string on any non-2xx.
  curl -sf -H "Authorization: Bearer $GITHUB_TOKEN" \
       -H "Accept: application/vnd.github+json" \
       -H "X-GitHub-Api-Version: 2022-11-28" \
       "https://api.github.com/search/code?q=$1&per_page=1" 2>/dev/null \
     | jq -r '.total_count // empty' 2>/dev/null
}

fetch_repos() {
  curl -sf -H "Authorization: Bearer $GITHUB_TOKEN" \
       -H "Accept: application/vnd.github+json" \
       -H "X-GitHub-Api-Version: 2022-11-28" \
       "https://api.github.com/search/repositories?q=$1&per_page=1" 2>/dev/null \
     | jq -r '.total_count // empty' 2>/dev/null
}

all=$(fetch "$q_all" || true)
community=$(fetch "$q_community" || true)
fallback_used="false"

# code-search requires extra perms in Actions and is rate-limited; fall back
# to repo-search if it returned nothing.
if [ -z "${all:-}" ]; then
  all=$(fetch_repos "$q_repo_fallback" || true)
  community="${all:-0}"
  fallback_used="true"
fi

all="${all:-0}"
community="${community:-0}"
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

printf '{"ts":"%s","total":%s,"community":%s,"threshold":200,"fallback":%s}\n' \
       "$ts" "$all" "$community" "$fallback_used" >> "$OUT"

echo "counted  total=$all  community=$community  fallback=$fallback_used  (threshold=200)"
