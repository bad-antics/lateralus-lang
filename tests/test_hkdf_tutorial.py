"""Run the original stdlib/hkdf tutorial against the Lateralus Python backend.

No network or third-party packages. Python 3.10+ required.

The companion example imports only `crypto` (a lateralus_lang module), so no
PYTHONPATH tricks and no generated backend module are needed.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "bin" / "ltlc"
EXAMPLE = ROOT / "examples" / "hkdf_tutorial.ltl"

# RFC 5869 (SHA-256) pinned vectors: Test Case 1 and Test Case 2.
EXPECTED = [
    "TC1 PRK: 077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5",
    "TC1 OKM: 3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865",
    "TC2 PRK: 06a6b88c5853361a06104c9ceb35b45cef760014904671014a193f40c15fc244",
    "TC2 OKM: b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71cc30c58179ec3e87c14c01d5c1f3434f1d87",
]


def invoke(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(COMPILER), *args],
        cwd=ROOT,
        env={**os.environ, **(env or {}), "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise AssertionError(
            f"{' '.join(args)} failed ({result.returncode}):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def test_tutorial() -> None:
    invoke("check", str(EXAMPLE))
    result = invoke("run", str(EXAMPLE))
    got = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert got == EXPECTED, f"Pinned hkdf output differs: expected {EXPECTED!r}, got {got!r}"


if __name__ == "__main__":
    test_tutorial()
    print("PASS: 4 pinned HKDF vectors (RFC 5869 Test Case 1 and 2)")
