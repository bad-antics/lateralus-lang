"""Run the LRU tutorial through the real compiler, without stdlib import shims."""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Compile the unchanged module plus example, run it, and check pinned output."""
    source = (ROOT / "stdlib/lru.ltl").read_text(encoding="utf-8")
    source += "\n" + (ROOT / "examples/lru_catalog.ltl").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="lateralus-lru-") as directory:
        program = Path(directory) / "catalog.ltl"
        program.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "lateralus_lang", "run", str(program)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode:
        return result.returncode
    expected = (ROOT / "examples/lru_catalog.expected.txt").read_text(encoding="utf-8")
    if result.stdout != expected:
        sys.stderr.write("LRU tutorial output differs from the pinned vector.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
