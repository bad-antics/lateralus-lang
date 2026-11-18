"""Count Friday-the-13ths by month in the proleptic Gregorian calendar."""
import argparse
from calendar import isleap, mdays


def january_weekday(year):
    """Return Monday=0 through Sunday=6 for January 1."""
    previous = year - 1
    leap_days = previous // 4 - previous // 100 + previous // 400
    return (previous + leap_days) % 7


def count_month(first, last, month):
    """Count matching thirteenths in one month over an inclusive year range."""
    common_offset = sum(mdays[1:month])
    january = january_weekday(first)
    cycles, tail = divmod(last - first + 1, 400)
    count = tail_count = 0
    for index in range(400 if cycles else tail):
        year = first + index
        leap = isleap(year)
        offset = common_offset + (month > 2 and leap)
        if (january + offset + 12) % 7 == 4:
            count += 1
            if index < tail:
                tail_count += 1
        january = (january + 1 + leap) % 7
    return cycles * count + tail_count


def histogram(first, last):
    """The twelve counts are returned in January-to-December order."""
    if not 1 <= first <= last <= 9999:
        raise ValueError("expected 1 <= FIRST <= LAST <= 9999")
    return [count_month(first, last, month) for month in range(1, 13)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=int, nargs="?", default=1,
                        help="first year to include (default: 1)")
    parser.add_argument("last", type=int, nargs="?", default=9999,
                        help="last year to include (default: 9999)")
    args = parser.parse_args()
    try:
        counts = histogram(args.first, args.last)
    except ValueError as error:
        parser.error(str(error))
    for count in counts:
        print(count)


if __name__ == "__main__":
    main()
