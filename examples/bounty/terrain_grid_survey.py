#!/usr/bin/env python3
"""Terrain-grid survey: integer-only reference for the native-port bounty.

Builds two fixed synthetic height grids with a 32-bit LCG and prints integer
height and roughness statistics. All arithmetic is integer (floor division),
so output is identical across CPython versions, platforms and native ports.
"""

MASK = 0xFFFFFFFF


def lcg_next(state):
    """Advance a 32-bit linear congruential generator (Numerical Recipes)."""
    return (state * 1664525 + 1013904223) & MASK


def build_grid(width, height, seed, max_height):
    """Return a row-major list of heights in [0, max_height)."""
    cells = []
    state = seed & MASK
    for _ in range(width * height):
        state = lcg_next(state)
        cells.append((state >> 16) % max_height)
    return cells


def height_stats(cells):
    """Return (min, max, sum, mean, variance) using integer arithmetic only."""
    lo = cells[0]
    hi = cells[0]
    total = 0
    for h in cells:
        if h < lo:
            lo = h
        if h > hi:
            hi = h
        total += h
    n = len(cells)
    mean = total // n
    sq = 0
    for h in cells:
        d = h - mean
        sq += d * d
    return lo, hi, total, mean, sq // n


def roughness(cells, width, height):
    """Return (sum of |delta| over 4-neighbour edges, max |delta|, edge count)."""
    total = 0
    worst = 0
    edges = 0
    for y in range(height):
        for x in range(width):
            here = cells[y * width + x]
            if x + 1 < width:
                d = abs(here - cells[y * width + x + 1])
                total += d
                edges += 1
                if d > worst:
                    worst = d
            if y + 1 < height:
                d = abs(here - cells[(y + 1) * width + x])
                total += d
                edges += 1
                if d > worst:
                    worst = d
    return total, worst, edges


def checksum(cells):
    """Order-sensitive 32-bit rolling checksum of the grid."""
    acc = 2166136261
    for h in cells:
        acc = ((acc ^ h) * 16777619) & MASK
    return acc


def survey(name, width, height, seed, max_height):
    cells = build_grid(width, height, seed, max_height)
    lo, hi, total, mean, var = height_stats(cells)
    rough, worst, edges = roughness(cells, width, height)
    print("grid", name, "size", width, "x", height, "seed", seed)
    print("  height min", lo, "max", hi, "sum", total, "mean", mean, "var", var)
    print("  roughness sum", rough, "max_step", worst, "edges", edges,
          "avg_x100", (rough * 100) // edges)
    print("  checksum", checksum(cells))


def main():
    survey("alpine", 192, 160, 20240601, 1000)
    survey("plains", 256, 128, 7777, 120)


if __name__ == "__main__":
    main()