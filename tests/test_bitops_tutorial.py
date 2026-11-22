"""Run the original bitops tutorial against the Lateralus Python backend.

No network or third-party packages. Python 3.10+ required.
The generated Python backend module is confined to a temporary directory.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "bin" / "ltlc"
LIBRARY = ROOT / "stdlib" / "bitops.ltl"
EXAMPLE = ROOT / "examples" / "bitops_tutorial.ltl"
EXPECTED = ["34", "2", "3", "True", "13330"]


def invoke(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(COMPILER), *args],
        cwd=ROOT,
        env={**os.environ, **(env or {}), "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise AssertionError(
            f"{' '.join(args)} failed ({result.returncode}):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def test_tutorial() -> None:
    invoke("check", str(LIBRARY))
    invoke("check", str(EXAMPLE))
    with tempfile.TemporaryDirectory(prefix="lateralus-bitops-") as folder:
        python_module = Path(folder) / "bitops.py"
        invoke("py", str(LIBRARY), "-o", str(python_module))
        assert python_module.exists(), "bitops Python backend was not generated"

        env = os.environ.copy()
        env["PYTHONPATH"] = folder + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        result = invoke("run", str(EXAMPLE), env=env)
        got = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert got == EXPECTED, f"Pinned bitops output differs: expected {EXPECTED!r}, got {got!r}"


if __name__ == "__main__":
    test_tutorial()
    print("PASS: 5 pinned bitops vectors")
