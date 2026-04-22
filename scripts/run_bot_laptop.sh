#!/usr/bin/env bash
# =============================================================================
# run_bot_laptop.sh — Low-resource paper_bot runner for the laptop
#
# - Runs paper_bot with --slow (4s between API calls) so it doesn't spike CPU
# - Stores PDFs in staging area, NOT directly on the live site
# - Nice'd to 19 (lowest priority)
# - Exits immediately if less than 600MB RAM is free (laptop protection)
#
# Typical setup (one-off or via cron):
#   # Run once for a specific outline:
#   bash scripts/run_bot_laptop.sh outlines/my-paper.yaml
#
#   # Install a cron job that processes the queue every 30 min:
#   bash scripts/run_bot_laptop.sh --install-cron
#
#   # Remove the cron job:
#   bash scripts/run_bot_laptop.sh --remove-cron
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGING="$REPO_ROOT/scripts/paper_bot_staging"
QUEUE="$REPO_ROOT/outlines/laptop_queue"
DONE="$REPO_ROOT/outlines/laptop_done"
LOG="$STAGING/laptop_runner.log"
MIN_FREE_MB=600

mkdir -p "$STAGING/pdf" "$QUEUE" "$DONE"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*" | tee -a "$LOG"; }

# ── RAM guard ─────────────────────────────────────────────────────────────────
free_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
if (( free_mb < MIN_FREE_MB )); then
    log "SKIP: only ${free_mb}MB free (need ${MIN_FREE_MB}MB) -- try again later"
    exit 0
fi

# ── Install / remove cron ─────────────────────────────────────────────────────
CMD="${1:-}"

if [[ "$CMD" == "--install-cron" ]]; then
    CRON_LINE="*/30 * * * * bash $REPO_ROOT/scripts/run_bot_laptop.sh --run-queue >> $LOG 2>&1"
    ( crontab -l 2>/dev/null | grep -v "run_bot_laptop"; echo "$CRON_LINE" ) | crontab -
    echo "Cron installed: runs every 30 minutes"
    echo "  $CRON_LINE"
    crontab -l | grep run_bot_laptop
    exit 0
fi

if [[ "$CMD" == "--remove-cron" ]]; then
    crontab -l 2>/dev/null | grep -v "run_bot_laptop" | crontab -
    echo "Cron entry removed."
    exit 0
fi

# ── Process a specific outline ────────────────────────────────────────────────
if [[ "$CMD" != "--run-queue" && -n "$CMD" ]]; then
    OUTLINE="$CMD"
    if [[ ! -f "$OUTLINE" ]]; then
        echo "ERROR: file not found: $OUTLINE"
        exit 1
    fi
    log "Running (laptop, slow mode): $OUTLINE"
    nice -n 19 python3 "$REPO_ROOT/scripts/paper_bot.py" "$OUTLINE" --slow
    exit 0
fi

# ── Queue mode ────────────────────────────────────────────────────────────────
log "--- laptop queue run ---"

OUTLINES=("$QUEUE"/*.yaml 2>/dev/null) || true
# Filter glob that matched nothing
REAL=()
for f in "${OUTLINES[@]}"; do [[ -f "$f" ]] && REAL+=("$f"); done

if (( ${#REAL[@]} == 0 )); then
    log "Laptop queue empty (add outlines to $QUEUE/)"
    exit 0
fi

for OUTLINE in "${REAL[@]}"; do
    NAME="$(basename "$OUTLINE")"

    # Re-check RAM before each paper
    free_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
    if (( free_mb < MIN_FREE_MB )); then
        log "STOP: only ${free_mb}MB free -- deferring remaining ${#REAL[@]} outlines"
        break
    fi

    log "Processing (laptop): $NAME  [${free_mb}MB free]"

    if nice -n 19 python3 "$REPO_ROOT/scripts/paper_bot.py" "$OUTLINE" --slow \
            >> "$LOG" 2>&1; then
        mv "$OUTLINE" "$DONE/$NAME"
        log "Done: $NAME"

        # Copy generated PDF to staging (not live)
        SLUG="$(python3 -c "
import yaml, pathlib
m = yaml.safe_load(open('$DONE/$NAME'))
fn = m.get('output_filename','')
print(fn)
" 2>/dev/null || true)"
        if [[ -n "$SLUG" ]]; then
            SRC="$REPO_ROOT/docs/website/papers/pdf/$SLUG"
            if [[ -f "$SRC" ]]; then
                cp "$SRC" "$STAGING/pdf/$SLUG"
                log "PDF staged for review: $SLUG"
            fi
        fi
    else
        log "FAILED: $NAME -- leaving in queue"
    fi

    sleep 15   # longer pause between papers on laptop
done

log "--- laptop queue run done ---"
