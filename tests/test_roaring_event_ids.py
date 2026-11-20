"""Keep the blog's event replay example and its published output in sync."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RoaringEventIdsTest(unittest.TestCase):
    def test_replayed_ids(self):
        module = (ROOT / "stdlib/roaring.ltl").read_bytes()
        example = (ROOT / "examples/roaring_event_ids.ltl").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "events.ltl"
            source.write_bytes(module + b"\n" + example)
            # The run command starts a child Python process for the compiled code.
            result = subprocess.run(
                [sys.executable, "-m", "lateralus_lang", "run", str(source)],
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1"},
                capture_output=True,
                text=True,
                timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(result.stdout.splitlines(), ["[65537, 131072]", "4"])


if __name__ == "__main__":
    unittest.main()
