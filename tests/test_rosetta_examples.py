"""Run every Rosetta Code port under examples/rosetta/ end to end.

Each example is self-checking: it asserts its output against the task's
published vectors with ``assert_eq`` / ``assert_true``, so a wrong answer
makes the generated program exit non-zero.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from lateralus_lang.compiler import Compiler, Target

REPO_ROOT = Path(__file__).resolve().parent.parent
ROSETTA_DIR = REPO_ROOT / "examples" / "rosetta"
EXAMPLES = sorted(ROSETTA_DIR.glob("*.ltl"))


def test_examples_discovered():
    assert len(EXAMPLES) >= 31


def test_readme_lists_every_example():
    readme = (ROSETTA_DIR / "README.md").read_text(encoding="utf-8")
    missing = [p.name for p in EXAMPLES if f"({p.name})" not in readme]
    assert not missing, f"examples missing from README: {missing}"


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.stem for p in EXAMPLES])
def test_rosetta_example_runs(path: Path, tmp_path: Path):
    result = Compiler().compile_source(
        path.read_text(encoding="utf-8"), target=Target.PYTHON, filename=str(path)
    )
    assert result.ok, [e.message for e in result.errors[:5]]

    script = tmp_path / f"{path.stem}.py"
    script.write_text(result.python_src, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO_ROOT), env.get("PYTHONPATH", "")) if p
    )
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
