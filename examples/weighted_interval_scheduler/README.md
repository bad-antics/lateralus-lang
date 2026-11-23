# Weighted interval scheduler

Given jobs with fixed start times, finish times and payouts, find the maximum total payout for one worker. A job can begin the instant the previous one ends. Taking no jobs is allowed.

The input is an ASCII text file. The first token is the job count (0 through 1,000,000). Each job has three signed 32-bit decimal integers giving its start, finish and payout, with start strictly less than finish. Jobs may arrive in any order. Spaces, tabs or line breaks can separate tokens. The CLI prints the maximum as a 64-bit integer. An invalid count, integer, interval or number of tokens gives exit status 2.

```text
3
0 4 9
2 4 6
0 2 6
```

The answer is `12`. Both shorter jobs fit, whereas the single job paying 9 occupies the whole interval.

## Build and run

From the repository root, using Python 3.10+ and a C99 compiler:

```sh
python -X utf8 -m lateralus_lang c examples/weighted_interval_scheduler/scheduler.ltl -o scheduler.c
cc -O2 -std=c99 scheduler.c -o scheduler -lm
./scheduler < jobs.txt
python examples/weighted_interval_scheduler/reference.py < jobs.txt
```

Save the sample above as `jobs.txt` to run it. On Windows, name the binary `scheduler.exe` and use a shell that supports input redirection, such as Git Bash.

## How it works

Sort the jobs by finish time. For the next job, search the sorted prefix for the number of earlier jobs that finish on or before its start. Adding its payout to the optimum over that compatible prefix gives the best schedule that takes the job. Compare this with the best schedule that skips the job. Sorting and all searches take O(n log n) time in total, with O(n) working memory.

## Reproduce the checks

```sh
python -m pytest tests/test_weighted_interval_scheduler.py
python examples/weighted_interval_scheduler/benchmark.py ./scheduler --jobs 100000 --runs 7
```

The tests check both programs against exhaustive subset enumeration for small inputs, including touching endpoints, tied finish times, losses, and payouts whose sum exceeds 32 bits. They also exercise invalid input. The native test needs `cc`, `gcc` or `clang` on the search path.

The benchmark generates an unsorted file with a fixed seed, warms up each implementation once, then alternates which runs first. It checks every output and reports median end-to-end process time, including startup, input parsing, sorting and scheduling. Compilation and input generation are outside the timer.

On Windows x86-64 with CPython 3.11.9 and GCC 16.2.0 (`-O2 -std=c99`), seven timed runs per program gave these medians. To reproduce the second row, change `--jobs` to `250000`.

| Jobs | Maximum payout (both programs) | Python | Native Lateralus | Speedup |
| ---: | ---: | ---: | ---: | ---: |
| 100,000 | 945,754 | 0.528444 s | 0.128493 s | 4.11x |
| 250,000 | 2,360,474 | 1.148747 s | 0.293335 s | 3.92x |
