"""Keep the rope tutorial vector executable against the real module."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RopeReleaseNotesTest(unittest.TestCase):
    def test_release_notes_vector(self):
        source_bytes = (ROOT / "stdlib/rope.ltl").read_bytes()
        example_bytes = (ROOT / "examples/rope_release_notes.ltl").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rope.ltl"
            source.write_bytes(source_bytes + b"\n" + example_bytes)
            result = subprocess.run(
                [sys.executable, "-m", "lateralus_lang", "run", str(source)],
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1"},
                capture_output=True,
                text=True,
                timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(
            result.stdout.splitlines(),
            ["release draft notes", "release", " draft notes", "draft notes", "draft", "11"],
        )


if __name__ == "__main__":
    unittest.main()
