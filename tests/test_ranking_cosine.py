"""Check the shipped sparse-vector scorer through the Lateralus CLI."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(("left", "right", "expected"), [
    ([["a"], [1e-7]], [["a"], [1e-7]], 1.0),
    ([["a", "b"], [3e-200, 4e-200]], [["b"], [1e200]], 0.8),
    ([["a"], [1e200]], [["a"], [-1e200]], -1.0),
    ([["a"], [1.0]], [["b"], [1.0]], 0.0),
    ([["a"], [0.0]], [["a"], [1.0]], 0.0),
    ([["a"], [1.0]], [[], []], 0.0),
])
def test_cosine_similarity(tmp_path, left, right, expected):
    library = (ROOT / "stdlib" / "ranking.ltl").read_text(encoding="utf-8")
    call = f"cosine_similarity({json.dumps(left)}, {json.dumps(right)})"
    program = tmp_path / "cosine.ltl"
    program.write_text(f"{library}\nprint_ltl({call})\n", encoding="utf-8")
    run = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "ltlc"), "run", str(program)],
        capture_output=True, text=True, timeout=30,
    )
    assert run.returncode == 0, run.stderr
    assert float(run.stdout) == pytest.approx(expected, abs=1e-12, rel=1e-12)
