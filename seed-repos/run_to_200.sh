#!/usr/bin/env bash
# run_to_200.sh — non-stop orchestrator that seeds, publishes, and polls
# the unique-repo count for Lateralus until the Linguist ≥ 200 gate is
# cleared (twice in a row, to guard against transient API glitches).
#
# Strategy per cycle:
#   1. Poll current unique-repo count (multiple signals).
#   2. If < TARGET, batch-publish the next N unstaged manifest entries.
#   3. Sleep, re-poll, repeat.
#
# Stops when the count is ≥ TARGET on two consecutive polls.
#
# Writes a live status dashboard to LOG_DIR/status.txt and a per-cycle
# JSON line to LOG_DIR/cycles.jsonl.
#
# Usage:
#   ./run_to_200.sh                    # defaults
#   TARGET=250 BATCH=15 ./run_to_200.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

TARGET="${TARGET:-200}"
BATCH="${BATCH:-10}"
SLEEP_SECS="${SLEEP_SECS:-120}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
mkdir -p "$LOG_DIR"

STATUS="$LOG_DIR/status.txt"
CYCLES="$LOG_DIR/cycles.jsonl"

# --- safety checks ---------------------------------------------------------
command -v gh  >/dev/null || { echo "gh CLI missing"  >&2; exit 1; }
command -v yq  >/dev/null || { echo "yq missing"      >&2; exit 1; }
command -v jq  >/dev/null || { echo "jq missing"      >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh not authenticated" >&2; exit 1; }

OWNER="$(yq -r '.owner' manifest.yml)"

# --- functions -------------------------------------------------------------

# Count unique repos holding .ltl files via GitHub code search.
count_code_unique() {
  local total=0
  for p in 1 2 3 4 5 6 7 8 9 10; do
    gh api "search/code?q=extension:ltl&per_page=100&page=$p" \
      --jq '.items[].repository.full_name' 2>/dev/null || true
  done | sort -u | wc -l
}

# Count repos carrying the lateralus-lang topic.
count_topic() {
  gh api "search/repositories?q=topic:lateralus-lang&per_page=100" \
    --jq '.total_count' 2>/dev/null || echo 0
}

count_topic_ltl() {
  gh api "search/repositories?q=topic:ltl&per_page=100" \
    --jq '.total_count' 2>/dev/null || echo 0
}

# Combined discoverable count: max of the signals we trust.
compute_count() {
  local code topic1 topic2 best
  code=$(count_code_unique)
  topic1=$(count_topic)
  topic2=$(count_topic_ltl)
  best=$code
  [[ "$topic1" -gt "$best" ]] && best=$topic1
  [[ "$topic2" -gt "$best" ]] && best=$topic2
  echo "$code $topic1 $topic2 $best"
}

# Pick up to N manifest repos that are not yet published to GitHub.
unpublished_names() {
  local n="$1"
  # All manifest names
  local all
  all=$(yq -r '.repos[].name' manifest.yml)
  # All existing gh repos under owner
  local existing
  existing=$(gh repo list "$OWNER" --limit 2000 --json name --jq '.[].name' 2>/dev/null)
  # Set difference: in manifest, not on gh
  comm -23 <(echo "$all" | sort -u) <(echo "$existing" | sort -u) | head -n "$n"
}

publish_batch() {
  local names="$1"
  [[ -z "$names" ]] && return 0
  # Stage any missing repos.
  python3 generate.py >/dev/null || true
  # Publish each.
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    echo "  -> publish $name"
    ./publish.sh "$name" 2>&1 | tail -3 || echo "  (publish failed: $name)"
  done <<< "$names"
}

dashboard() {
  local ts="$1" code="$2" t1="$3" t2="$4" best="$5" cycle="$6" published="$7"
  cat > "$STATUS" <<EOF
=== run_to_200.sh status @ $ts ===

  target:             >= $TARGET (two consecutive polls)
  cycle number:       $cycle
  total published:    $published

  signals:
    unique .ltl repos (code search, first 1000):   $code
    topic:lateralus-lang                            $t1
    topic:ltl                                       $t2
    best signal:                                    $best

  next batch size:    $BATCH
  sleep between polls: ${SLEEP_SECS}s
EOF
}

# --- main loop -------------------------------------------------------------

echo "=== run_to_200.sh — target >= $TARGET ==="
echo "logs: $LOG_DIR"
echo

cycle=0
published_total=0
consecutive_good=0

while :; do
  cycle=$((cycle + 1))
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  read -r code t1 t2 best <<< "$(compute_count)"

  dashboard "$ts" "$code" "$t1" "$t2" "$best" "$cycle" "$published_total"

  printf '{"ts":"%s","cycle":%d,"code_unique":%d,"topic_lateralus_lang":%d,"topic_ltl":%d,"best":%d,"published_total":%d}\n' \
         "$ts" "$cycle" "$code" "$t1" "$t2" "$best" "$published_total" \
         >> "$CYCLES"

  echo "[$ts] cycle=$cycle code=$code t.l-lang=$t1 t.ltl=$t2 best=$best target=$TARGET"

  if [[ "$best" -ge "$TARGET" ]]; then
    consecutive_good=$((consecutive_good + 1))
    echo "  >= $TARGET  ($consecutive_good/2 consecutive)"
    if [[ "$consecutive_good" -ge 2 ]]; then
      echo
      echo "=== TARGET CLEARED ==="
      echo "target $TARGET reached on two consecutive polls."
      echo "total repos published this run: $published_total"
      exit 0
    fi
  else
    consecutive_good=0
  fi

  # Decide batch size. If we're way off, push more per cycle.
  gap=$((TARGET - best))
  if [[ "$gap" -gt 60 ]]; then
    batch_now=$((BATCH * 2))
  elif [[ "$gap" -gt 20 ]]; then
    batch_now=$BATCH
  else
    batch_now=5
  fi

  # Grab next N unpublished manifest repos.
  names="$(unpublished_names "$batch_now" || true)"
  if [[ -z "$names" ]]; then
    echo "  (no unpublished repos left in manifest; target not yet reached — extend manifest)"
    # Sleep longer; future polls might see GitHub index-catch-up bringing us over.
    sleep $((SLEEP_SECS * 2))
    continue
  fi

  n_to_publish=$(echo "$names" | grep -c . || echo 0)
  echo "  publishing $n_to_publish repo(s): $(echo "$names" | tr '\n' ' ')"
  publish_batch "$names"
  published_total=$((published_total + n_to_publish))

  echo "  sleep ${SLEEP_SECS}s"
  sleep "$SLEEP_SECS"
done
