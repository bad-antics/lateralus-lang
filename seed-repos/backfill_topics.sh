#!/usr/bin/env bash
# backfill_topics.sh — add the `ltl` / `lateralus-lang` / `lateralus` topics
# to every repo under bad-antics/ whose name starts with `ltl-` or
# `lateralus-` but is not yet tagged with `topic:ltl`.
#
# This is a zero-cost boost: a repo that already contains .ltl files but
# lacks the topic does not appear in topic:ltl / topic:lateralus-lang
# search results, so it does not count toward the Linguist discoverable
# corpus in any visible way.
#
# Usage:
#   ./backfill_topics.sh               # act
#   ./backfill_topics.sh --dry-run     # list but don't call the API
#
# Requires `gh` authenticated.

set -euo pipefail

OWNER="bad-antics"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# Canonical topics every Lateralus-bearing repo should carry.
CANONICAL=(lateralus lateralus-lang ltl)

echo "=== listing bad-antics/* lateralus-themed repos ==="
mapfile -t REPOS < <(
  gh repo list "$OWNER" --limit 2000 --json name --jq '.[].name' \
    | grep -E '^(ltl-|lateralus)' \
    | sort -u
)
echo "found ${#REPOS[@]} candidate repos"
echo

CHANGED=0
SKIPPED=0
for repo in "${REPOS[@]}"; do
  current=$(gh api "repos/$OWNER/$repo/topics" --jq '.names | join(",")' 2>/dev/null || echo "")
  need_update=0
  for t in "${CANONICAL[@]}"; do
    if [[ ",$current," != *",$t,"* ]]; then
      need_update=1
      break
    fi
  done

  if [[ "$need_update" -eq 0 ]]; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  merged="$current"
  for t in "${CANONICAL[@]}"; do
    if [[ ",$merged," != *",$t,"* ]]; then
      merged="${merged:+$merged,}$t"
    fi
  done

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  would update  $repo   [$current]  ->  [$merged]"
    continue
  fi

  args=()
  IFS=',' read -ra TOPS <<< "$merged"
  for t in "${TOPS[@]}"; do
    [[ -n "$t" ]] && args+=(-f "names[]=$t")
  done

  if gh api --silent -X PUT "repos/$OWNER/$repo/topics" "${args[@]}" 2>/dev/null; then
    echo "  updated       $repo   (+$(echo "$merged" | tr ',' '\n' | wc -l) topics)"
    CHANGED=$((CHANGED + 1))
  else
    echo "  FAILED        $repo"
  fi
done

echo
echo "=== done: $CHANGED updated, $SKIPPED already tagged ==="
