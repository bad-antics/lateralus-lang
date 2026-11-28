"""Check both fixtures, then time complete Python and native processes."""

from pathlib import Path
from statistics import median
from subprocess import check_output
import sys
from time import perf_counter


EXPECTED_LINES = (
    b"8x8 min_m=400 max_m=746 mean_mm=597625 high_cells=0 "
    b"east_step_mm=28714 south_step_mm=23714",
    b"1536x1536 min_m=316 max_m=952 mean_mm=630824 high_cells=282089 "
    b"east_step_mm=26321 south_step_mm=18907",
)


def measure(command: list[str]) -> float:
    start = perf_counter()
    output = check_output(command)
    elapsed_ms = (perf_counter() - start) * 1000
    if tuple(output.splitlines()) != EXPECTED_LINES:
        raise ValueError(f"{command[0]} returned unexpected output: {output!r}")
    return elapsed_ms


def main() -> None:
    directory = Path(__file__).resolve().parent
    commands = {
        "Python": [sys.executable, str(directory / "terrain_grid.py")],
        "Native": [str(directory / "terrain_grid.exe")],
    }
    samples = {name: [] for name in commands}
    order = tuple(commands)
    for command in commands.values():
        measure(command)

    print("pair,python_ms,native_ms")
    for pair in range(11):
        for name in order:
            samples[name].append(measure(commands[name]))
        print(f"{pair + 1},{samples['Python'][-1]:.3f},{samples['Native'][-1]:.3f}")
        order = order[::-1]

    python_ms = median(samples["Python"])
    native_ms = median(samples["Native"])
    print(f"median,{python_ms:.3f},{native_ms:.3f}")
    print(f"Python/native ratio: {python_ms / native_ms:.2f}x")


if __name__ == "__main__":
    main()
