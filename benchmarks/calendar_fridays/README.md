# Counting Friday-the-13ths

The Python program and Lateralus port print one count per month, January to December, for years 1 through 9999 in the proleptic Gregorian calendar. Both use the same 400-year cycle and compute the remaining partial cycle from the requested start year. The Python reference also accepts an inclusive year range on the command line.

For years 1 through 400 the expected monthly counts are `58 57 58 58 58 57 58 56 57 56 58 57`. The sum is 688. A century year is a leap year only when divisible by 400, so 1900 and 2000 exercise different branches.

From the repository root on Linux:

```sh
python -m lateralus_lang c benchmarks/calendar_fridays/calendar.ltl -o /tmp/calendar.c
cc -O2 -std=c99 /tmp/calendar.c -lm -o /tmp/calendar
python benchmarks/calendar_fridays/compare.py /tmp/calendar
```

The comparison checks the monthly output independently with Python's `datetime.date`, warms both executables, and measures eleven alternating runs of each. The elapsed times include process startup and output. Compilation is outside the timed section. Process startup can dominate this small workload, so compare results on the same machine.
