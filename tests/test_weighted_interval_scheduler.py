"""Exercise the weighted scheduler example through both command-line entry points."""

import itertools
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "weighted_interval_scheduler"
Job = tuple[int, int, int]


def exhaustive(jobs: list[Job]) -> int:
    """Check every subset without using the scheduler's dynamic program."""
    best = 0
    for size in range(1, len(jobs) + 1):
        for subset in itertools.combinations(jobs, size):
            ordered = sorted(subset)
            if all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:])):
                best = max(best, sum(job[2] for job in subset))
    return best


@pytest.fixture(scope="module")
def native_command(tmp_path_factory):
    compiler = next((path for name in ("cc", "gcc", "clang") if (path := shutil.which(name))), None)
    if compiler is None:
        pytest.skip("building this example requires a C99 compiler")
    build = tmp_path_factory.mktemp("weighted_scheduler")
    generated = build / "scheduler.c"
    binary = build / ("scheduler.exe" if sys.platform == "win32" else "scheduler")
    subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "lateralus_lang",
            "c",
            str(EXAMPLE / "scheduler.ltl"),
            "-o",
            str(generated),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [compiler, "-O2", "-std=c99", str(generated), "-o", str(binary), "-lm"], check=True
    )
    return [str(binary)]


def check_examples(command: list[str]) -> None:
    # These cases include a counterexample to choosing the best single job,
    # ties, touching endpoints, negative time, and a sum wider than 32 bits.
    cases = [
        [],
        [(0, 1, -10)],
        [(0, 4, 9), (2, 4, 6), (0, 2, 6)],
        [(-9, -5, 7), (-5, -1, 5), (-8, -1, 12), (-9, -5, 7)],
        [(-(2**31), 0, 2**31 - 1), (0, 2**31 - 1, 2**31 - 1)],
    ]
    rng = random.Random(256)
    for count in range(1, 10):
        for _ in range(3):
            starts = [rng.randint(-8, 8) for _ in range(count)]
            cases.append([(s, s + rng.randint(1, 6), rng.randint(-7, 20)) for s in starts])
    for jobs in cases:
        data = str(len(jobs)) + "\n" + "".join(f"{s} {e} {v}\n" for s, e, v in jobs)
        result = subprocess.run(
            command, input=data, capture_output=True, text=True, check=True, timeout=10
        )
        assert result.stdout.strip() == str(exhaustive(jobs)), jobs
    mixed = subprocess.run(
        command, input=b"2\r\n-2\t0 +7\v0 001 6", capture_output=True, check=True, timeout=10
    )
    assert mixed.stdout.strip() == b"13"
    for invalid in (
        b"",
        b"-1",
        b"1 4 4 9",
        b"1 0 1",
        b"1 0 2 2147483648",
        b"not-a-count",
        b"0 99",
        b"1000001",
    ):
        result = subprocess.run(command, input=invalid, capture_output=True, timeout=10)
        assert result.returncode == 2, invalid


def test_python_reference():
    check_examples([sys.executable, str(EXAMPLE / "reference.py")])


def test_native_port(native_command):
    check_examples(native_command)
