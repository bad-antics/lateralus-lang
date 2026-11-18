"""Check output against datetime, then compare end-to-end process times."""
import argparse
from datetime import date
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import perf_counter

from calendar_reference import histogram


def expected(first, last):
    return [
        sum(date(year, month, 13).weekday() == 4 for year in range(first, last + 1))
        for month in range(1, 13)
    ]


def measured_run(command, answer):
    start = perf_counter()
    output = subprocess.check_output(command, text=True)
    elapsed = perf_counter() - start
    if [int(line) for line in output.splitlines()] != answer:
        raise ValueError(f"Incorrect calendar output from {command[0]}")
    return elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="compiled calendar executable")
    args = parser.parse_args()
    cycle = [58, 57, 58, 58, 58, 57, 58, 56, 57, 56, 58, 57]
    if histogram(1, 400) != cycle:
        raise ValueError("400-year reference histogram differs")
    for first, last in [(1899, 1901), (1999, 2001), (1703, 2599)]:
        if histogram(first, last) != expected(first, last):
            raise ValueError(f"Incorrect result for {first}..{last}")
    answer = expected(1, 9999)
    reference = Path(__file__).with_name("calendar_reference.py")
    programs = ([sys.executable, str(reference)], [str(args.binary.resolve())])
    timings = [[], []]
    for cmd in programs:
        measured_run(cmd, answer)
    for i in range(11):
        for index in (i % 2, 1 - i % 2):
            timings[index].append(measured_run(programs[index], answer))
    python_time, native_time = map(median, timings)
    print(f"Python {python_time:.6f}s; native {native_time:.6f}s; "
          f"speedup {python_time/native_time:.2f}x")


if __name__ == "__main__":
    main()
