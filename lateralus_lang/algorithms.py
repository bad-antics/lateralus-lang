"""
LATERALUS Standard Library — algorithms
Python implementation of stdlib/algorithms.ltl
"""
from __future__ import annotations

# --- Sorting ----------------------------------------------------------

def bubble_sort(arr: list) -> list:
    result = list(arr)
    n = len(result)
    for i in range(n):
        for j in range(0, n - i - 1):
            if result[j] > result[j + 1]:
                result[j], result[j + 1] = result[j + 1], result[j]
    return result


def insertion_sort(arr: list) -> list:
    result = list(arr)
    for i in range(1, len(result)):
        key = result[i]
        j = i - 1
        while j >= 0 and result[j] > key:
            result[j + 1] = result[j]
            j -= 1
        result[j + 1] = key
    return result


def merge_sorted(left: list, right: list) -> list:
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def merge_sort(arr: list) -> list:
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    return merge_sorted(merge_sort(arr[:mid]), merge_sort(arr[mid:]))


def quick_sort(arr: list) -> list:
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left  = [x for x in arr if x < pivot]
    mid   = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + mid + quick_sort(right)


# --- Searching --------------------------------------------------------

def binary_search(arr: list, target) -> int:
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


def linear_search(arr: list, target) -> int:
    for i, v in enumerate(arr):
        if v == target:
            return i
    return -1


def find_min_index(arr: list) -> int:
    return arr.index(min(arr)) if arr else -1


def find_max_index(arr: list) -> int:
    return arr.index(max(arr)) if arr else -1


# --- List utilities ---------------------------------------------------

def unique(arr: list) -> list:
    seen = set()
    return [x for x in arr if not (x in seen or seen.add(x))]


def flatten(arr: list) -> list:
    result = []
    for item in arr:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def chunk(arr: list, size: int) -> list:
    return [arr[i:i + size] for i in range(0, len(arr), size)]


def interleave(a: list, b: list) -> list:
    result = []
    for i in range(max(len(a), len(b))):
        if i < len(a): result.append(a[i])
        if i < len(b): result.append(b[i])
    return result


def rotate(arr: list, n: int) -> list:
    if not arr: return arr
    n = n % len(arr)
    return arr[n:] + arr[:n]


def sliding_window(arr: list, size: int) -> list:
    return [arr[i:i + size] for i in range(len(arr) - size + 1)]


# --- String algorithms ------------------------------------------------

def is_palindrome(s: str) -> bool:
    return s == s[::-1]


def count_occurrences(text: str, pattern: str) -> int:
    return text.count(pattern)


def caesar_cipher(text: str, shift: int) -> str:
    result = []
    for ch in text:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            result.append(ch)
    return ''.join(result)


# --- Math algorithms --------------------------------------------------

def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


def lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b)


def is_prime(n: int) -> bool:
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0: return False
    return True


def primes_up_to(n: int) -> list:
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, n + 1, i):
                sieve[j] = False
    return [i for i in range(2, n + 1) if sieve[i]]


def fibonacci_sequence(n: int) -> list:
    if n <= 0: return []
    if n == 1: return [0]
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq


def power_mod(base: int, exp: int, modulus: int) -> int:
    return pow(base, exp, modulus)


__all__ = [
    'bubble_sort', 'insertion_sort', 'merge_sorted', 'merge_sort', 'quick_sort',
    'binary_search', 'linear_search', 'find_min_index', 'find_max_index',
    'unique', 'flatten', 'chunk', 'interleave', 'rotate', 'sliding_window',
    'is_palindrome', 'count_occurrences', 'caesar_cipher',
    'gcd', 'lcm', 'is_prime', 'primes_up_to', 'fibonacci_sequence', 'power_mod',
]
