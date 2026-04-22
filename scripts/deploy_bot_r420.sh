#!/usr/bin/env bash
# =============================================================================
# deploy_bot_r420.sh — Push paper_bot to the r420 and start the queue runner
#
# Usage:
#   bash scripts/deploy_bot_r420.sh            # deploy + (re)start tmux runner
#   bash scripts/deploy_bot_r420.sh --stop      # stop the tmux session
#   bash scripts/deploy_bot_r420.sh --status    # show queue / session status
#   bash scripts/deploy_bot_r420.sh --push-outline outlines/foo.yaml
#                                               # queue one outline remotely
# =============================================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REMOTE_HOST="r420"
REMOTE_USER="root"
REMOTE_BASE="/root/paper_bot"
TMUX_SESSION="paper_bot"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGING_DIR="$REPO_ROOT/scripts/paper_bot_staging"  # local review area

# API key — read from local .bashrc / env
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    # Try sourcing .bashrc if not in env
    if grep -q ANTHROPIC_API_KEY ~/.bashrc 2>/dev/null; then
        ANTHROPIC_API_KEY="$(bash -c 'source ~/.bashrc 2>/dev/null; echo $ANTHROPIC_API_KEY')"
    fi
fi
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    echo "ERROR: ANTHROPIC_API_KEY not found. Export it or add it to ~/.bashrc"
    exit 1
fi

SSH="ssh -o ConnectTimeout=5 ${REMOTE_USER}@${REMOTE_HOST}"

# ── Helpers ───────────────────────────────────────────────────────────────────
r() { $SSH "$@"; }   # run remote command

banner() { echo ""; echo "=== $* ==="; }

# ── Subcommands ───────────────────────────────────────────────────────────────
cmd="${1:-deploy}"

if [[ "$cmd" == "--stop" ]]; then
    banner "Stopping tmux session $TMUX_SESSION on r420"
    r "tmux kill-session -t $TMUX_SESSION 2>/dev/null && echo 'stopped' || echo 'not running'"
    exit 0
fi

if [[ "$cmd" == "--status" ]]; then
    banner "Queue status on r420"
    r "
        echo '--- tmux ---'
        tmux ls 2>/dev/null | grep $TMUX_SESSION || echo 'session not running'
        echo '--- queue ---'
        ls -1 $REMOTE_BASE/outlines/queue/ 2>/dev/null | head -20 || echo '(empty)'
        echo '--- done ---'
        ls -1 $REMOTE_BASE/outlines/done/ 2>/dev/null | wc -l
        echo 'completed outlines'
        echo '--- PDFs ---'
        ls -1 $REMOTE_BASE/pdf/ 2>/dev/null | wc -l
        echo 'PDFs generated'
        echo '--- log (last 10 lines) ---'
        tail -10 $REMOTE_BASE/logs/runner.log 2>/dev/null || echo '(no log yet)'
    "
    exit 0
fi

if [[ "$cmd" == "--push-outline" ]]; then
    OUTLINE="${2:-}"
    if [[ -z "$OUTLINE" || ! -f "$OUTLINE" ]]; then
        echo "ERROR: provide a valid outline path:  --push-outline outlines/foo.yaml"
        exit 1
    fi
    BASENAME="$(basename "$OUTLINE")"
    banner "Pushing $BASENAME to r420 queue"
    scp "$OUTLINE" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/outlines/queue/${BASENAME}"
    echo "Queued: $BASENAME"
    r "ls -1 $REMOTE_BASE/outlines/queue/"
    exit 0
fi

# ── Deploy ────────────────────────────────────────────────────────────────────
banner "1/6  Creating remote directories"
r "mkdir -p $REMOTE_BASE/{outlines/{queue,done},cache,pdf,logs}"

banner "2/6  Syncing scripts and outlines"
# Only sync what the bot needs — not the whole repo
rsync -az --progress \
    "$REPO_ROOT/scripts/paper_bot.py" \
    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/"

# Sync any local outlines into the queue (skip ones already done)
if ls "$REPO_ROOT/outlines/"*.yaml &>/dev/null 2>&1; then
    for f in "$REPO_ROOT/outlines/"*.yaml; do
        name="$(basename "$f")"
        # Only queue if not already done or in-queue
        done_check="$( r "ls $REMOTE_BASE/outlines/done/$name 2>/dev/null || true" )"
        queue_check="$( r "ls $REMOTE_BASE/outlines/queue/$name 2>/dev/null || true" )"
        if [[ -z "$done_check" && -z "$queue_check" ]]; then
            scp "$f" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/outlines/queue/$name"
            echo "  Queued: $name"
        else
            echo "  Skip (already queued/done): $name"
        fi
    done
fi

banner "3/6  Installing Python dependencies on r420"
r "pip3 install -q anthropic fpdf2 pyyaml 2>&1 | tail -3"

banner "4/6  Writing API key to r420 environment"
# Write to /etc/paper_bot.env (not to .bashrc to keep it isolated)
r "cat > /etc/paper_bot.env << 'ENVEOF'
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ENVEOF
chmod 600 /etc/paper_bot.env"
echo "  API key written to /etc/paper_bot.env (mode 600)"

banner "5/6  Writing queue runner script"
r "cat > $REMOTE_BASE/run_queue.sh << 'RUNEOF'
#!/usr/bin/env bash
# Queue runner — processes one outline at a time, loops forever
set -euo pipefail
source /etc/paper_bot.env
BASE=/root/paper_bot
LOG=\$BASE/logs/runner.log
mkdir -p \$BASE/logs

log() { echo \"\$(date '+%Y-%m-%d %H:%M:%S')  \$*\" | tee -a \$LOG; }

log \"=== Queue runner started ===\"

while true; do
    # Pick the oldest queued outline
    NEXT=\"\$(ls -1t \$BASE/outlines/queue/*.yaml 2>/dev/null | tail -1 || true)\"

    if [[ -z \"\$NEXT\" ]]; then
        log \"Queue empty — sleeping 60s\"
        sleep 60
        continue
    fi

    NAME=\"\$(basename \"\$NEXT\")\"
    log \"Processing: \$NAME\"

    # Override output dir so PDFs land in /root/paper_bot/pdf/
    # We do this by passing --pdf-only after generating, then copying
    python3 \$BASE/paper_bot.py \"\$NEXT\" \\
        2>&1 | tee -a \$LOG

    EXIT=\${PIPESTATUS[0]}

    if [[ \$EXIT -eq 0 ]]; then
        mv \"\$NEXT\" \$BASE/outlines/done/\$NAME
        log \"Done: \$NAME  -> outlines/done/\"

        # Copy any newly created PDF to local pdf/ dir
        SLUG=\$(python3 -c \"
import yaml, re, unicodedata
m = yaml.safe_load(open('\$NEXT.bak', 'r') if False else open('\$BASE/outlines/done/\$NAME'))
fn = m.get('output_filename', '')
if fn: print(fn)
\" 2>/dev/null || true)
        if [[ -n \"\$SLUG\" ]]; then
            SRC=\"/root/lateralus-lang/docs/website/papers/pdf/\$SLUG\"
            if [[ -f \"\$SRC\" ]]; then
                cp \"\$SRC\" \$BASE/pdf/\$SLUG
                log \"PDF copied: \$SLUG\"
            fi
        fi
    else
        log \"FAILED: \$NAME (exit \$EXIT) — leaving in queue for retry\"
        sleep 30
    fi

    # Rate-limit between papers
    sleep 10
done
RUNEOF
chmod +x $REMOTE_BASE/run_queue.sh"

banner "6/7  Writing Python queue runner"
# This file is what systemd (and tmux) actually runs
r "cat > $REMOTE_BASE/paper_bot_runner.py << 'PYEOF'
#!/usr/bin/env python3
\"\"\"
Queue runner for paper_bot on r420.
Reads outlines from /root/paper_bot/outlines/queue/,
calls paper_bot.py for each one, moves done outlines to outlines/done/.
\"\"\"
import os, sys, time, shutil, subprocess
from pathlib import Path

BASE     = Path('/root/paper_bot')
QUEUE    = BASE / 'outlines' / 'queue'
DONE     = BASE / 'outlines' / 'done'
LOG      = BASE / 'logs' / 'runner.log'
PDF_DST  = BASE / 'pdf'
BOT      = BASE / 'paper_bot.py'

# Repo PDF dir (paper_bot writes PDFs here)
REPO_PDF = Path('/root/lateralus-lang/docs/website/papers/pdf')

for d in (QUEUE, DONE, PDF_DST, LOG.parent):
    d.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts}  {msg}\n'
    print(line, end='', flush=True)
    with LOG.open('a') as f:
        f.write(line)

log('=== Queue runner started ===')

while True:
    outlines = sorted(QUEUE.glob('*.yaml'))
    if not outlines:
        log('Queue empty -- sleeping 60s')
        time.sleep(60)
        continue

    outline = outlines[-1]   # oldest last after sort
    log(f'Processing: {outline.name}')

    result = subprocess.run(
        [sys.executable, str(BOT), str(outline)],
        capture_output=False,   # let stdout/stderr flow to journalctl
    )

    if result.returncode == 0:
        dst = DONE / outline.name
        shutil.move(str(outline), dst)
        log(f'Done: {outline.name}')

        # Copy PDF to local pdf/ staging
        import yaml
        try:
            meta = yaml.safe_load(outline.read_text() if outline.exists() else dst.read_text())
            fn   = meta.get('output_filename', '')
            if fn:
                src = REPO_PDF / fn
                if src.exists():
                    shutil.copy2(src, PDF_DST / fn)
                    log(f'PDF staged: {fn}')
        except Exception as e:
            log(f'PDF copy skipped: {e}')
    else:
        log(f'FAILED: {outline.name} (exit {result.returncode}) -- retry in 30s')
        time.sleep(30)

    time.sleep(10)   # rate-limit between papers
PYEOF
chmod +x $REMOTE_BASE/paper_bot_runner.py"

banner "7/8  Installing systemd service on r420"
scp "$REPO_ROOT/scripts/paper-bot.service" \
    "${REMOTE_USER}@${REMOTE_HOST}:/etc/systemd/system/paper-bot.service"

r "
    systemctl daemon-reload
    systemctl enable paper-bot.service
    systemctl restart paper-bot.service
    sleep 2
    systemctl is-active paper-bot.service && echo 'systemd service: ACTIVE' || echo 'WARNING: service not active'
"

banner "8/8  Also starting tmux session (for easy live attachment)"
r "
    tmux kill-session -t $TMUX_SESSION 2>/dev/null || true
    sleep 1
    tmux new-session -d -s $TMUX_SESSION -x 200 -y 50 \
        'journalctl -u paper-bot.service -f'
    echo 'Attach: ssh r420 tmux attach -t $TMUX_SESSION  (shows live log)'
"

banner "Deployment complete"
echo ""
echo "  r420 queue runner : tmux session '$TMUX_SESSION'"
echo "  Attach to watch   : ssh r420 'tmux attach -t $TMUX_SESSION'"
echo "  Check status      : bash scripts/deploy_bot_r420.sh --status"
echo "  Pull results      : bash scripts/sync_bot_output.sh"
echo "  Review + deploy   : python scripts/review_papers.py"
echo ""
mkdir -p "$STAGING_DIR"
