"""Time both scheduler CLIs against the same shuffled job file, including I/O."""

import argparse
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import median
from time import perf_counter

REFERENCE = Path(__file__).with_name("reference.py")


def write_workload(path: Path, count: int) -> None:
    """Generate valid overlapping intervals directly to disk outside the timed runs."""
    rng = random.Random(256)
    with path.open("w", encoding="ascii", newline="\n") as out:
        print(count, file=out)
        for _ in range(count):
            start = rng.randrange(-count, count)
            finish = start + rng.randint(1, 200)
            print(start, finish, rng.randint(-20, 200), file=out)


def measure(command: list[str], path: Path) -> tuple[float, int]:
    with path.open("rb") as data:
        start = perf_counter()
        result = subprocess.run(command, stdin=data, stdout=subprocess.PIPE, check=True)
        elapsed = perf_counter() - start
    return elapsed, int(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="native executable produced from scheduler.ltl")
    parser.add_argument("--jobs", type=int, default=100_000)
    parser.add_argument("--runs", type=int, default=7, help="timed runs per program")
    args = parser.parse_args()
    if not 1 <= args.jobs <= 1_000_000 or args.runs < 1:
        parser.error("use 1 to 1000000 jobs and at least one timed run")
    commands = {"python": [sys.executable, str(REFERENCE)], "native": [str(args.binary.resolve())]}
    times = {name: [] for name in commands}
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "jobs.txt"
        write_workload(data, args.jobs)
        # Use each implementation once before timing, and check every subsequent result.
        _, expected = measure(commands["python"], data)
        if measure(commands["native"], data)[1] != expected:
            raise SystemExit("warm-up outputs differ")
        for index in range(args.runs):
            for name in commands if index % 2 == 0 else reversed(commands):
                seconds, payout = measure(commands[name], data)
                if payout != expected:
                    raise SystemExit(f"{name} returned {payout}, expected {expected}")
                times[name].append(seconds)
    print(f"{args.jobs} jobs, maximum payout {expected}, {args.runs} timed runs each")
    for name, samples in times.items():
        print(f"{name}: {median(samples):.6f} s median; runs (s):", *(f"{s:.6f}" for s in samples))
    print(f"speedup: {median(times['python']) / median(times['native']):.2f}x")


if __name__ == "__main__":
    main()
