#!/usr/bin/env python3
"""mypy ratchet gate.

The lateralus-lang codebase carries a large body of pre-existing mypy findings
(historic compiler code). Rather than block every PR on an unachievable
"zero mypy errors" bar -- or, worse, silently ignoring types entirely -- this
gate implements a *ratchet*: it records the current set of normalised mypy
findings in ``ci/mypy_baseline.txt`` and fails the build only when a change
introduces a NEW kind of finding that is not already in the baseline.

Normalisation drops the line/column numbers so that ordinary code movement
does not create false positives; the file path, error code and message text
are kept, so a genuinely new type error still trips the gate.

Exit codes:
  0  -- no new findings (baseline respected)
  1  -- one or more new findings were introduced
  2  -- mypy itself failed to run / errored out
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / "ci" / "mypy_baseline.txt"
TARGET = "lateralus_lang"

# Matches: path/to/file.py:LINE:COL: error: message  [error-code]
# (also tolerates the ": note:" lines, which we drop)
_ERR_RE = re.compile(
    r"^(?P<path>[^\s:][^:]*?):(?P<line>\d+):(?:(?P<col>\d+):)?\s*"
    r"error:\s*(?P<msg>.*?)\s*\[(?P<code>[a-z0-9-]+)\]\s*$"
)


def normalise(output: str) -> set[str]:
    """Return the set of normalised finding signatures from mypy output."""
    findings: set[str] = set()
    for raw in output.splitlines():
        m = _ERR_RE.match(raw.strip())
        if not m:
            continue
        findings.add(f"{m['path']}: error: {m['msg']} [{m['code']}]")
    return findings


def run_mypy() -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", TARGET],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # mypy returns 1 when it finds errors, 0 when clean, 2 on usage/internal error.
    return proc.returncode, proc.stdout + proc.stderr


def main() -> int:
    code, output = run_mypy()
    if code not in (0, 1):
        sys.stderr.write("mypy failed to run cleanly (exit %d):\n%s\n" % (code, output))
        return 2

    current = normalise(output)
    total = len(current)

    if not BASELINE.exists():
        sys.stderr.write(
            "mypy baseline missing at %s -- generate it with "
            "`python scripts/mypy_gate.py --write-baseline`\n" % BASELINE
        )
        return 2

    baseline = {ln.strip() for ln in BASELINE.read_text().splitlines() if ln.strip()}
    new_findings = sorted(current - baseline)

    print("mypy ratchet gate")
    print("  current findings : %d" % total)
    print("  baseline findings: %d" % len(baseline))

    if new_findings:
        sys.stderr.write("\nNEW mypy findings introduced (%d):\n" % len(new_findings))
        for f in new_findings:
            sys.stderr.write("  + %s\n" % f)
        sys.stderr.write(
            "\nFix the new type errors, or (if intentional) regenerate the "
            "baseline with `python scripts/mypy_gate.py --write-baseline`.\n"
        )
        return 1

    print("  new findings     : 0  -- OK (no regressions vs baseline)")
    return 0


if __name__ == "__main__":
    if "--write-baseline" in sys.argv:
        code, output = run_mypy()
        if code not in (0, 1):
            sys.stderr.write("mypy failed to run cleanly (exit %d)\n" % code)
            sys.exit(2)
        findings = sorted(normalise(output))
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text("\n".join(findings) + "\n")
        print("Wrote %d findings to %s" % (len(findings), BASELINE))
        sys.exit(0)
    sys.exit(main())
