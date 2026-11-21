# Calendar Math with `stdlib/datetime.ltl`

`stdlib/datetime.ltl` is a dependency-free civil-date library:
dates and datetimes as plain maps, proleptic-Gregorian calendar
helpers (leap years, month lengths, day-of-year), a Zeller-congruence
day-of-week, ISO-style formatting, durations, `add_days`/`add_hours`
arithmetic with month/year rollover, and comparison helpers. ~225
lines, no `_time` dependency for the calendar parts — fully
deterministic, which makes it ideal for tests and offline logic.

Companion: `examples/datetime_tutorial.ltl`.

---

## Data model

A date/datetime is just a map:

```text
{"year": 2024, "month": 1, "day": 1,
 "hour": 9, "minute": 30, "second": 0, "ms": 0}
```

`date(y,m,d)` validates ranges (`throw ValueError` on bad month/day)
and zero-fills the time fields; `datetime(...)` layers h/m/s on top.

## Calendar helpers

- **`is_leap_year`** — full Gregorian rule: `%400==0` → leap,
  `%100==0` → not, else `%4==0`. Verified: 2024=T, 1900=F, 2000=T.
- **`days_in_month`** — 31/28 table with a Feb-29 override on leap
  years. Verified: (2023,2)=28, (2024,2)=29.
- **`day_of_year`** — sums `days_in_month` for months `< m` plus day.
  Verified: (2024,3,1)=61.
- **`day_of_week`** — Zeller-style congruence returning 0=Monday..6=
  Sunday (with the Jan/Feb → previous-year shift). Verified against
  known dates: 2024-01-01=Monday, 2024-12-25=Wednesday,
  2000-01-01=Saturday.

## Formatting

`format_date` → `YYYY-MM-DD`, `format_datetime` →
`YYYY-MM-DDTHH:MM:SS`, `format_time` → `HH:MM:SS`,
`format_iso8601` appends `Z`. All components zero-padded via the
module's own `pad_left`.

## Arithmetic

- **`add_days(dt, n)`** — walks day overflow/underflow across month
  and year boundaries. Verified: Jan 31 +1 → Feb 1; Dec 31 +1 →
  Jan 1 next year; Mar 1 −1 → Feb 29 (leap-aware!); Jan 15 +45 →
  Feb 29.
- **`add_hours`** — converts to total seconds, splits days/remainder.
- **`diff_days(a, b)`** — ⚠️ **approximate**: `year*365 +
  day_of_year` ignores leap days, so spans crossing Feb 29 drift by
  one. Fine for rough "days between" UI math; use a real epoch-day
  conversion for correctness-critical code.
- **`is_before` / `is_after` / `is_same_day`** — lexicographic
  field-by-field comparison.

## ⚠️ Runtime-shim notes (worked around)

- `/` is float division: `day_of_week`'s `y/100`, `k/4`,
  `(13*(m+1))/5`, `duration_from_seconds`' `total/3600`, and
  `add_hours`' `rem/3600` all produce floats → the tutorial wraps
  every one in `int()`. Sixth confirmed instance of the
  float-division family.
- `throw ValueError(...)` and `let mut` are used by the module;
  the companion uses `let` + `while` and skips constructor
  validation (documented, not reproduced).
- Map literals `{"k": v}` compile in module files; the companion
  builds maps via `{}` + assignment for safety.

## When to use it

**Use it** for due dates, billing cycles, "X days ago" UI labels,
scheduling arithmetic, and anywhere civil-date correctness matters
(leap years, month lengths, rollovers).

**Don't expect** time zones, DST, UTC offsets, or month/year
addition (`add_months` doesn't exist — `add_days(30)` is not the
same thing), or exact `diff_days` across leap days.

That is `stdlib/datetime.ltl`: a civil calendar you can verify by
hand — Zeller's congruence included.
