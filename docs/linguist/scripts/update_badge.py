#!/usr/bin/env python3
"""Read docs/linguist/meta/repo-count.jsonl and write a shields.io endpoint
JSON file at docs/linguist/meta/repo-count-badge.json.

Use in README:
    ![Lateralus repos](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/bad-antics/lateralus-lang/main/docs/linguist/meta/repo-count-badge.json)
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]  # docs/linguist/
JSONL = ROOT / "meta" / "repo-count.jsonl"
OUT = ROOT / "meta" / "repo-count-badge.json"
THRESHOLD = 200


def latest_count() -> int | None:
    """Return the best available signal for Linguist eligibility from the
    most recent JSONL entry.

    Preference order:
      1. unique_repos — unique :user/:repo pairs with .ltl files (what
         Linguist actually cares about).
      2. repos_tagged — repos GitHub already indexes as language:Lateralus.
      3. total — raw file-hit count from code-search.

    Falling back to `total` is mostly for older snapshots that predate the
    unique-repo tracking patch.
    """
    if not JSONL.exists():
        return None
    last = None
    for raw in JSONL.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            last = json.loads(raw)
        except json.JSONDecodeError:
            continue
    if not last:
        return None
    for field in ("unique_repos", "repos_tagged", "total"):
        value = last.get(field)
        if value is None:
            continue
        try:
            n = int(value)
        except (TypeError, ValueError):
            continue
        if n > 0:
            return n
    # All fields present but zero — still return 0 so the badge can show it.
    return int(last.get("total", 0) or 0)


def main() -> int:
    n = latest_count()
    if n is None:
        print("no data yet")
        return 0
    pct = min(100, int(round(100 * n / THRESHOLD)))
    if n >= THRESHOLD:
        color, message = "brightgreen", f"{n} / {THRESHOLD} ✅"
    elif pct >= 75:
        color, message = "green", f"{n} / {THRESHOLD}"
    elif pct >= 50:
        color, message = "yellow", f"{n} / {THRESHOLD}"
    else:
        color, message = "orange", f"{n} / {THRESHOLD}"
    payload = {
        "schemaVersion": 1,
        "label": "linguist eligibility",
        "message": message,
        "color": color,
        "cacheSeconds": 3600,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {message} ({color})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
