#!/usr/bin/env bash
# =============================================================================
# sync_bot_output.sh — Pull paper_bot results from r420 → laptop staging area
#
# Staging area:   scripts/paper_bot_staging/
#   ├── cache/      (r420 cache text files — same format as local cache)
#   ├── pdf/        (generated PDFs waiting for review)
#   └── sync.log   (timestamped sync history)
#
# Usage:
#   bash scripts/sync_bot_output.sh           # pull everything new
#   bash scripts/sync_bot_output.sh --watch   # pull every 5 minutes (background-safe)
# =============================================================================
set -euo pipefail

REMOTE_HOST="r420"
REMOTE_USER="root"
REMOTE_BASE="/root/paper_bot"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGING="$REPO_ROOT/scripts/paper_bot_staging"
LOG="$STAGING/sync.log"

mkdir -p "$STAGING/cache" "$STAGING/pdf"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*" | tee -a "$LOG"; }

sync_once() {
    log "--- sync start ---"

    # 1. Pull cache directories (text files, small)
    rsync -az --progress \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/cache/" \
        "$STAGING/cache/" 2>&1 | tee -a "$LOG"

    # 2. Pull PDFs (don't overwrite ones already reviewed/approved)
    rsync -az --progress \
        --exclude='*.approved' \
        --exclude='*.rejected' \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/pdf/" \
        "$STAGING/pdf/" 2>&1 | tee -a "$LOG"

    # 3. Also pull the done outlines (so we know what ran)
    rsync -az --progress \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/outlines/done/" \
        "$STAGING/outlines_done/" 2>&1 | tee -a "$LOG"

    # 4. Pull log tail for visibility
    ssh -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" \
        "tail -20 $REMOTE_BASE/logs/runner.log 2>/dev/null || echo '(no log)'" \
        >> "$LOG" 2>&1

    NEW_PDFS=$(ls "$STAGING/pdf/"*.pdf 2>/dev/null | wc -l)
    log "Sync done.  Staging PDFs: $NEW_PDFS"
    echo ""
    echo "Staging area: $STAGING/"
    echo "  cache/        : $(find "$STAGING/cache" -name '*.txt' 2>/dev/null | wc -l) section files"
    echo "  pdf/          : $NEW_PDFS PDFs waiting for review"
    echo ""
    echo "Next step:  python scripts/review_papers.py"
}

if [[ "${1:-}" == "--watch" ]]; then
    INTERVAL="${2:-300}"   # default 5 min
    echo "Watch mode: syncing every ${INTERVAL}s  (Ctrl-C to stop)"
    while true; do
        sync_once
        sleep "$INTERVAL"
    done
else
    sync_once
fi
