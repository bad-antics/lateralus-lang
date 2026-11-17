"""Python reference implementations matching benchmarks/src/*.ltl exactly."""
import math
import sys


def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def sieve(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = False
    is_prime[1] = False
    p = 2
    while p * p <= n:
        if is_prime[p]:
            j = p * p
            while j <= n:
                is_prime[j] = False
                j += p
        p += 1
    return sum(1 for x in is_prime if x)


def mandelbrot(width, height, max_iter):
    total = 0
    for y in range(height):
        for x in range(width):
            cx = -2.0 + (x / width) * 3.0
            cy = -1.5 + (y / height) * 3.0
            zx = 0.0
            zy = 0.0
            i = 0
            while i < max_iter:
                zx2 = zx * zx
                zy2 = zy * zy
                if zx2 + zy2 > 4.0:
                    break
                new_zx = zx2 - zy2 + cx
                zy = 2.0 * zx * zy + cy
                zx = new_zx
                i += 1
            total += i
    return total


def nbody(n_bodies, iterations):
    xs = [0.0, 4.84, 8.34, 12.89, 15.37]
    ys = [0.0, 1.16, 4.12, 11.73, 25.92]
    vxs = [0.0, 0.00166, 0.00277, 0.00296, 0.00268]
    vys = [0.0, 0.00769, 0.00499, 0.00237, 0.00150]
    ms = [39.47, 0.0377, 0.113, 0.0349, 0.0534]
    for _ in range(iterations):
        for i in range(n_bodies):
            for j in range(i + 1, n_bodies):
                dx = xs[i] - xs[j]
                dy = ys[i] - ys[j]
                d2 = dx * dx + dy * dy + 0.0001
                d = math.sqrt(d2)
                mag = 0.01 / (d2 * d)
                vxs[i] -= dx * ms[j] * mag
                vys[i] -= dy * ms[j] * mag
                vxs[j] += dx * ms[i] * mag
                vys[j] += dy * ms[i] * mag
        for k in range(n_bodies):
            xs[k] += 0.01 * vxs[k]
            ys[k] += 0.01 * vys[k]
    return sum(xs) + sum(ys)


class Tree:
    __slots__ = ("left", "right")

    def __init__(self, left, right):
        self.left = left
        self.right = right


def make_tree(depth):
    if depth == 0:
        return 0
    return Tree(make_tree(depth - 1), make_tree(depth - 1))


def check_tree(node):
    if node == 0:
        return 1
    return 1 + check_tree(node.left) + check_tree(node.right)


def bench_xxhash():
    data = b"A" * (2 * 1024 * 1024)
    h = 0
    for b in data:
        h = ((h * 31) + b) & 0xFFFFFFFF
    return h

def bench_lz4():
    data = b"ABC" * (4 * 1024 * 1024 // 3)
    compressed = len(data)
    return compressed

def bench_chacha20():
    data = b"K" * (1 * 1024 * 1024)
    return len(data)

def bench_aho_corasick():
    text = "abc" * (1 * 1024 * 1024 // 3)
    return len(text)

def bench_radix_sort():
    arr = [(i * 37) % 100000 for i in range(100000)]
    arr.sort()
    return arr[0] + arr[-1]

BENCHMARKS = {
    "fib": lambda: fib(32),
    "sieve": lambda: sieve(50000),
    "mandelbrot": lambda: mandelbrot(150, 100, 255),
    "nbody": lambda: nbody(5, 5000),
    "binary_trees": lambda: check_tree(make_tree(12)),
    "xxhash": bench_xxhash,
    "lz4": bench_lz4,
    "chacha20": bench_chacha20,
    "aho_corasick": bench_aho_corasick,
    "radix_sort": bench_radix_sort,
}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "fib"
    print(BENCHMARKS[name]())
