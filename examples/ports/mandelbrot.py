#!/usr/bin/env python3
"""Mandelbrot escape-time renderer — idiomatic ~50-line Python reference.

Prints the iteration count at which each pixel escapes the Mandelbrot
set, one count per line, row-major order. Fixed 400x200 viewport over
[-2.5, 1.0] x [-1.0, 1.0], max 1000 iterations. Deterministic integer
output so the Lateralus port can be diffed byte-for-byte.
"""
import sys
import time

WIDTH = 400
HEIGHT = 200
MAX_ITER = 1000


def escape_iterations(cx, cy):
    """Iterations until zx*zx + zy*zy > 4, capped at MAX_ITER."""
    zx = 0.0
    zy = 0.0
    i = 0
    while i < MAX_ITER and zx * zx + zy * zy <= 4.0:
        zx, zy = zx * zx - zy * zy + cx, 2.0 * zx * zy + cy
        i += 1
    return i


def render():
    for row in range(HEIGHT):
        cy = (row / (HEIGHT - 1)) * 2.0 - 1.0
        for col in range(WIDTH):
            cx = (col / (WIDTH - 1)) * 3.5 - 2.5
            print(escape_iterations(cx, cy))


def main():
    start = time.time()
    render()
    print(f"elapsed={time.time() - start:.3f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
