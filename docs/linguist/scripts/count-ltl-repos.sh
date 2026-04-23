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
q_repo_lang="language:Lateralus"

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

# Count unique repos containing .ltl files by paging code-search results
# (max 1000 items = 10 pages of 100). This is what Linguist actually cares
# about — 200 unique :user/:repo pairs, not 200 files.
fetch_unique_repos() {
  local query="$1"
  local page seen
  seen="$(mktemp)"
  for page in 1 2 3 4 5 6 7 8 9 10; do
    local body
    body=$(curl -sf -H "Authorization: Bearer $GITHUB_TOKEN" \
                 -H "Accept: application/vnd.github+json" \
                 -H "X-GitHub-Api-Version: 2022-11-28" \
                 "https://api.github.com/search/code?q=${query}&per_page=100&page=${page}" 2>/dev/null) || break
    echo "$body" | jq -r '.items[]?.repository.full_name' >> "$seen" 2>/dev/null || true
    local got
    got=$(echo "$body" | jq -r '.items | length // 0' 2>/dev/null)
    [ "${got:-0}" -lt 100 ] && break
    sleep 2   # be kind to secondary rate limits
  done
  sort -u "$seen" | grep -c '^' || echo 0
  rm -f "$seen"
}

all=$(fetch "$q_all" || true)
community=$(fetch "$q_community" || true)
unique_repos=""
repos_tagged=$(fetch_repos "$q_repo_lang" || true)
fallback_used="false"

# code-search requires extra perms in Actions and is rate-limited; fall back
# to repo-search if it returned nothing.
if [ -z "${all:-}" ]; then
  all=$(fetch_repos "$q_repo_fallback" || true)
  community="${all:-0}"
  fallback_used="true"
else
  # Only try unique-repo counting when code-search is actually working.
  unique_repos=$(fetch_unique_repos "$q_all" || true)
fi

all="${all:-0}"
community="${community:-0}"
unique_repos="${unique_repos:-0}"
repos_tagged="${repos_tagged:-0}"
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

printf '{"ts":"%s","total":%s,"community":%s,"unique_repos":%s,"repos_tagged":%s,"threshold":200,"fallback":%s}\n' \
       "$ts" "$all" "$community" "$unique_repos" "$repos_tagged" "$fallback_used" >> "$OUT"

echo "counted  files=$all  community=$community  unique_repos=$unique_repos  repos_tagged=$repos_tagged  fallback=$fallback_used  (threshold=200)"
