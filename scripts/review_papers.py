#!/usr/bin/env python3
"""
review_papers.py — Proofread, duplicate-check, and approve bot-generated papers
before they go live on the website.

Commands
--------
  python scripts/review_papers.py list               # list all staged PDFs
  python scripts/review_papers.py show <name.pdf>    # print full text of a draft
  python scripts/review_papers.py dupes              # find near-duplicate papers
  python scripts/review_papers.py approve <name.pdf> # copy PDF to live site
  python scripts/review_papers.py reject  <name.pdf> # mark rejected (logs reason)
  python scripts/review_papers.py approve-all        # approve everything not yet rejected

Staging area (input):   scripts/paper_bot_staging/pdf/
Live site (output):     docs/website/papers/pdf/
Review log:             scripts/paper_bot_staging/review.log
"""

import argparse
import difflib
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT    = Path(__file__).parent.parent
STAGING_PDF  = REPO_ROOT / "scripts" / "paper_bot_staging" / "pdf"
STAGING_CACHE= REPO_ROOT / "scripts" / "paper_bot_staging" / "cache"
LIVE_PDF     = REPO_ROOT / "docs" / "website" / "papers" / "pdf"
REVIEW_LOG   = REPO_ROOT / "scripts" / "paper_bot_staging" / "review.log"
REJECTED_DIR = REPO_ROOT / "scripts" / "paper_bot_staging" / "rejected"

STAGING_PDF.mkdir(parents=True, exist_ok=True)
LIVE_PDF.mkdir(parents=True, exist_ok=True)
REJECTED_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def rlog(action: str, filename: str, note: str = "") -> None:
    entry = {
        "ts":     datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "file":   filename,
        "note":   note,
    }
    with REVIEW_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _all_staged() -> list[Path]:
    """PDFs in staging that have not been rejected."""
    rejected = {p.stem for p in REJECTED_DIR.glob("*.pdf")}
    pdfs = sorted(STAGING_PDF.glob("*.pdf"))
    return [p for p in pdfs if p.stem not in rejected]


def _all_live() -> list[Path]:
    return sorted(LIVE_PDF.glob("*.pdf"))


def _already_approved(name: str) -> bool:
    return (LIVE_PDF / name).exists()


def _already_rejected(name: str) -> bool:
    return (REJECTED_DIR / name).exists()


def _extract_text_from_cache(paper_slug: str) -> str:
    """
    Read the cached section .txt files for a paper and concatenate them.
    Falls back to an empty string if cache not found.
    """
    cache_dir = STAGING_CACHE / paper_slug
    if not cache_dir.exists():
        # Also try local cache
        cache_dir = REPO_ROOT / "scripts" / "paper_bot_cache" / paper_slug
    if not cache_dir.exists():
        return ""
    parts = []
    for f in sorted(cache_dir.glob("*.txt")):
        parts.append(f"=== {f.stem} ===\n")
        parts.append(f.read_text(encoding="utf-8", errors="replace"))
        parts.append("\n\n")
    return "".join(parts)


def _pdf_name_to_slug(pdf_name: str) -> str:
    """
    Guess the paper_bot cache slug from the PDF filename.
    e.g. 'lateralus-ownership-model.pdf' -> tries various slug forms.
    """
    stem = Path(pdf_name).stem
    # paper_bot slugifies the title; cache dir is named after the title slug
    # We find any cache dir whose name contains the stem words
    candidates = []
    for d in (STAGING_CACHE, REPO_ROOT / "scripts" / "paper_bot_cache"):
        if d.exists():
            for sub in d.iterdir():
                if sub.is_dir() and stem.split("-")[0] in sub.name:
                    candidates.append(sub)
    if candidates:
        # Pick the best match by longest common prefix
        candidates.sort(key=lambda p: len(p.name), reverse=True)
        return candidates[0].name
    return stem


def _text_hash(text: str) -> str:
    # Normalise whitespace before hashing for better dupe detection
    normalised = " ".join(text.lower().split())
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]


def _title_from_filename(name: str) -> str:
    return Path(name).stem.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_list(args) -> None:
    staged  = _all_staged()
    live    = {p.name for p in _all_live()}
    rejected= {p.name for p in REJECTED_DIR.glob("*.pdf")}

    print(f"\n{'STATUS':<12} {'SIZE':>6}  {'FILENAME'}")
    print("-" * 70)

    if not staged and not rejected:
        print("  (no staged PDFs — run:  bash scripts/sync_bot_output.sh)")
        return

    for p in staged:
        sz   = p.stat().st_size // 1024
        if p.name in live:
            status = "\033[32mAPPROVED\033[0m"
        elif p.name in rejected:
            status = "\033[31mREJECTED\033[0m"
        else:
            status = "\033[33mPENDING\033[0m "
        print(f"  {status}   {sz:4d}KB  {p.name}")

    for name in rejected:
        p = REJECTED_DIR / name
        sz = p.stat().st_size // 1024 if p.exists() else 0
        print(f"  \033[31mREJECTED\033[0m   {sz:4d}KB  {name}")

    print()
    pending = [p for p in staged if p.name not in live and p.name not in rejected]
    print(f"  {len(pending)} pending review   "
          f"{len(live)} approved   "
          f"{len(rejected)} rejected")
    print()
    print("Next steps:")
    print("  python scripts/review_papers.py show <name.pdf>")
    print("  python scripts/review_papers.py dupes")
    print("  python scripts/review_papers.py approve <name.pdf>")
    print()


def cmd_show(args) -> None:
    name = args.filename
    path = STAGING_PDF / name
    if not path.exists():
        # Try live
        path = LIVE_PDF / name
    if not path.exists():
        print(f"ERROR: {name} not found in staging or live site")
        sys.exit(1)

    slug  = _pdf_name_to_slug(name)
    text  = _extract_text_from_cache(slug)
    title = _title_from_filename(name)

    print(f"\n{'='*70}")
    print(f"  PAPER: {title}")
    print(f"  FILE:  {path}")
    sz = path.stat().st_size // 1024
    status = "APPROVED" if _already_approved(name) else \
             "REJECTED" if _already_rejected(name) else "PENDING"
    print(f"  SIZE:  {sz} KB    STATUS: {status}")
    print(f"{'='*70}\n")

    if text:
        # Wrap long lines for terminal readability
        for line in text.splitlines():
            if len(line) > 100:
                import textwrap
                for wrapped in textwrap.wrap(line, 98):
                    print(wrapped)
            else:
                print(line)
    else:
        print("(Cache text not available — PDF only)")
        print(f"Open: xdg-open {path}")
    print()


def cmd_dupes(args) -> None:
    """
    Check for near-duplicate papers by:
    1. Exact content hash (cache text)
    2. Title similarity (>= 75% ratio)
    3. First-500-word overlap (>= 70% similarity)
    """
    all_pdfs = _all_staged() + _all_live()
    if len(all_pdfs) < 2:
        print("Need at least 2 papers to compare.")
        return

    texts: dict[str, str] = {}
    hashes: dict[str, str] = {}

    for p in all_pdfs:
        slug  = _pdf_name_to_slug(p.name)
        text  = _extract_text_from_cache(slug)
        texts[p.name] = text
        hashes[p.name] = _text_hash(text) if text else ""

    print(f"\nChecking {len(all_pdfs)} papers for duplicates...\n")
    found_any = False

    names = [p.name for p in all_pdfs]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]

            # 1. Exact hash match (only if both have cache text)
            if hashes[a] and hashes[a] == hashes[b]:
                print("  \033[31mEXACT DUPLICATE\033[0m")
                print(f"    {a}")
                print(f"    {b}\n")
                found_any = True
                continue

            # 2. Title similarity
            t_ratio = difflib.SequenceMatcher(
                None,
                _title_from_filename(a).lower(),
                _title_from_filename(b).lower(),
            ).ratio()

            # 3. Content overlap (first 2000 chars of cache text)
            c_ratio = 0.0
            ta, tb = texts[a][:2000], texts[b][:2000]
            if ta and tb:
                c_ratio = difflib.SequenceMatcher(None, ta, tb).ratio()

            if t_ratio >= 0.75 or c_ratio >= 0.70:
                colour = "\033[31m" if c_ratio >= 0.70 else "\033[33m"
                print(f"  {colour}POSSIBLE DUPE\033[0m  "
                      f"title={t_ratio:.0%}  content={c_ratio:.0%}")
                print(f"    {a}")
                print(f"    {b}\n")
                found_any = True

    if not found_any:
        print("  \033[32mNo duplicates detected.\033[0m\n")


def cmd_approve(args) -> None:
    name = args.filename
    src  = STAGING_PDF / name
    if not src.exists():
        print(f"ERROR: {src} not found")
        sys.exit(1)
    if _already_rejected(name):
        print(f"ERROR: {name} is marked rejected — reject first, then re-queue")
        sys.exit(1)

    dst = LIVE_PDF / name
    shutil.copy2(src, dst)
    rlog("APPROVED", name)
    print(f"\033[32mApproved\033[0m  {name}")
    print(f"  -> {dst}")
    print()
    print("To update the site index, rebuild docs:")
    print("  python scripts/build_docs.py")


def cmd_reject(args) -> None:
    name   = args.filename
    reason = getattr(args, "reason", "") or "no reason given"
    src    = STAGING_PDF / name
    if not src.exists():
        # May already have been approved; still let user reject
        src = LIVE_PDF / name
        if src.exists():
            # Remove from live
            (LIVE_PDF / name).unlink(missing_ok=True)
            print(f"Removed from live site: {name}")

    dst = REJECTED_DIR / name
    if (STAGING_PDF / name).exists():
        shutil.move(str(STAGING_PDF / name), dst)
    rlog("REJECTED", name, reason)
    print(f"\033[31mRejected\033[0m  {name}  ({reason})")


def cmd_approve_all(args) -> None:
    staged   = _all_staged()
    live     = {p.name for p in _all_live()}
    rejected = {p.name for p in REJECTED_DIR.glob("*.pdf")}
    pending  = [p for p in staged if p.name not in live and p.name not in rejected]

    if not pending:
        print("No pending papers to approve.")
        return

    print(f"Approving {len(pending)} papers...\n")
    for p in pending:
        dst = LIVE_PDF / p.name
        shutil.copy2(p, dst)
        rlog("APPROVED", p.name, "bulk approve-all")
        print(f"  \033[32m+\033[0m  {p.name}")
    print("\nAll done. Rebuild docs:  python scripts/build_docs.py")


def cmd_log(args) -> None:
    if not REVIEW_LOG.exists():
        print("No review log yet.")
        return
    lines = REVIEW_LOG.read_text().strip().splitlines()
    tail  = lines[-50:]
    print(f"\nReview log  ({len(lines)} entries, showing last {len(tail)}):\n")
    for line in tail:
        try:
            e = json.loads(line)
            colour = "\033[32m" if e["action"] == "APPROVED" else "\033[31m"
            note   = f"  [{e['note']}]" if e.get("note") else ""
            print(f"  {e['ts']}  {colour}{e['action']:<10}\033[0m  {e['file']}{note}")
        except Exception:
            print(f"  {line}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="review_papers",
        description="Proofread and approve bot-generated papers before publishing.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list",        help="List staged PDFs and their status")
    sub.add_parser("dupes",       help="Find near-duplicate papers")
    sub.add_parser("approve-all", help="Approve all pending PDFs at once")
    sub.add_parser("log",         help="Show the review log")

    p_show = sub.add_parser("show",    help="Print full text of a staged paper")
    p_show.add_argument("filename",    help="PDF filename (e.g. my-paper.pdf)")

    p_app = sub.add_parser("approve",  help="Approve a paper and copy to live site")
    p_app.add_argument("filename",     help="PDF filename")

    p_rej = sub.add_parser("reject",   help="Reject a paper")
    p_rej.add_argument("filename",     help="PDF filename")
    p_rej.add_argument("--reason",     default="", help="Optional rejection reason")

    args = parser.parse_args()

    dispatch = {
        "list":        cmd_list,
        "show":        cmd_show,
        "dupes":       cmd_dupes,
        "approve":     cmd_approve,
        "reject":      cmd_reject,
        "approve-all": cmd_approve_all,
        "log":         cmd_log,
    }

    fn = dispatch.get(args.command)
    if fn is None:
        parser.print_help()
        sys.exit(0)

    fn(args)


if __name__ == "__main__":
    main()
