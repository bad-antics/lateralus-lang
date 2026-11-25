"""Validate the Python reference and the compiled Lateralus program."""

import runpy
import shutil
import subprocess
import sys
from math import isqrt
from pathlib import Path

import pytest

PORT = Path(__file__).resolve().parents[1] / "examples" / "ports" / "pythagorean"


def test_reference_against_triangle_side_enumeration():
    count = runpy.run_path(str(PORT / "triples.py"))["count_triangles"]
    # Enumerate sides directly, independently of Euclid's parameterization.
    limit = 240
    by_perimeter = [0] * (limit + 1)
    for a in range(1, limit // 3 + 1):
        for b in range(a, (limit - a) // 2 + 1):
            squared = a * a + b * b
            c = isqrt(squared)
            if c * c == squared and a + b + c <= limit:
                by_perimeter[a + b + c] += 1

    total = 0
    for perimeter, triangles in enumerate(by_perimeter):
        total += triangles
        assert count(perimeter) == total, perimeter


def test_compiled_port_matches_reference(tmp_path):
    cc = shutil.which("cc")
    if cc is None:
        pytest.skip("a C99 compiler is required for the native port test")
    source = tmp_path / "triples.c"
    binary = tmp_path / "triples"
    subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "c", str(PORT / "triples.ltl"), "-o", str(source)],
        check=True,
    )
    subprocess.run([cc, "-std=c99", "-O2", str(source), "-o", str(binary)], check=True)
    reference = subprocess.check_output([sys.executable, str(PORT / "triples.py")])
    assert subprocess.check_output([str(binary)]) == reference
    assert reference.splitlines() == [b"0", b"1", b"2", b"22", b"325", b"9706567"]
