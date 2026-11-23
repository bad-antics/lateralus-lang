"""
tests/test_stdlib_benchmarks.py — Tests for the stdlib modules behind the
benchmark-ingest bounty (xxhash, lz4, chacha20, aho_corasick, radix_sort)
and for the five benchmark expected outputs.

The .ltl sources live in stdlib/*.ltl; the Python modules in
lateralus_lang/*.py are their runtime backing (see codegen/python.py
alias map). These tests pin the algorithms to their known vectors and
to the benchmark expected outputs, so a regression in either layer is
caught here.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from lateralus_lang import aho_corasick, chacha20, lz4, radix_sort, xxhash

PROJECT_ROOT = Path(__file__).parent.parent

# Canonical benchmark expected outputs (fresh deterministic generation,
# same inputs as benchmarks/src/*.ltl). See benchmarks/README.md.
EXPECTED = {
    "xxhash64": "16759434631272806465",
    "lz4_rt": "2165510 11572300857478106302 2001074385271547492",
    "chacha20": "10941187508525638281",
    "aho_corasick": "26949 213 15 854 1048575 13354998 14056156306",
    "radix_sort_u32": (
        "112674 116504 238608 245714 255117 4294921298 4294923275 "
        "4294935315 4294939266 4294949596 214657873537904"
    ),
}

WORDS = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
         "lateralus", "bench", "hash", "sort", "stream", "codec", "crypto",
         "search", "pattern", "text", "data", "node", "leaf", "tree",
         "graph", "queue", "stack", "buffer", "cache", "index", "token",
         "parse", "lexer", "parser", "codegen", "python", "node", "rust",
         "go", "fast", "slow", "small", "large", "green", "blue", "red",
         "river", "stone", "cloud", "storm", "flame", "ember", "frost",
         "iron", "gold", "sand", "wave", "spiral", "light", "dark", "zero",
         "prime", "delta"]


def _lcg_bytes(n, seed):
    st = seed
    out = [0] * n
    for i in range(n):
        st = (1103515245 * st + 12345) % (1 << 31)
        out[i] = (st >> 16) & 0xFF
    return out


def _text_chunk(nbytes, seed):
    st = seed
    out = [0] * nbytes
    wp = 0
    while wp < nbytes:
        st = (1103515245 * st + 12345) % (1 << 31)
        wb = WORDS[(st >> 16) % len(WORDS)].encode()
        for b in wb:
            if wp >= nbytes:
                break
            out[wp] = b
            wp += 1
        if wp < nbytes:
            out[wp] = 32
            wp += 1
    return out


def _text_str(n, seed):
    st = seed
    words = []
    total = 0
    while total < n:
        st = (1103515245 * st + 12345) % (1 << 31)
        w = WORDS[(st >> 16) % len(WORDS)]
        words.append(w)
        total += len(w) + 1
    return " ".join(words)[:n]


def _gen_patterns():
    st = 31337
    pats = []
    for _ in range(1000):
        st = (1103515245 * st + 12345) % (1 << 31)
        nw = 2 + ((st >> 16) % 2)
        ws = []
        for _ in range(nw):
            st = (1103515245 * st + 12345) % (1 << 31)
            ws.append(WORDS[(st >> 16) % len(WORDS)])
        pats.append(" ".join(ws))
    return pats


# --- xxhash64 ---
class TestXxhash:
    def test_known_vectors(self):
        assert xxhash.hash64([], 0) == 0xEF46DB3751D8E999
        assert xxhash.hash64(list(b"abc"), 0) == 0x44BC2CF5AD770999
        assert xxhash.hash64(list(b"hello world"), 0) == 0x45AB6734B21E6968

    def test_fnv1a_vectors(self):
        assert xxhash.fnv1a_64([]) == 0xCBF29CE484222325
        assert xxhash.fnv1a_64_str("") == 0xCBF29CE484222325

    def test_seed_changes_output(self):
        a = xxhash.hash64(list(b"hello"), 0)
        b = xxhash.hash64(list(b"hello"), 1)
        assert a != b

    def test_deterministic(self):
        data = _lcg_bytes(10000, 7)
        assert xxhash.hash64(data, 0) == xxhash.hash64(data, 0)


# --- lz4 ---
class TestLz4:
    @pytest.mark.parametrize("data", [
        [],
        list(b"hi"),
        list(b"hello world hello world hello"),
        list(b"abcd" * 1000),
        [(i * 37 + 11) % 256 for i in range(5000)],
    ])
    def test_round_trip(self, data):
        assert lz4.decompress(lz4.compress(data)) == data

    def test_known_compressed_length(self):
        # "hello world hello world hello" (29 bytes) -> 21-byte block.
        assert len(lz4.compress(list(b"hello world hello world hello"))) == 21

    def test_repetitive_compresses_well(self):
        assert len(lz4.compress(list(b"abcd" * 1000))) < 100

    def test_deterministic(self):
        data = _text_chunk(65536, 12345)
        assert lz4.compress(data) == lz4.compress(data)


# --- chacha20 ---
class TestChacha20:
    def test_rfc8439_section_2_3_2(self):
        # Plaintext from RFC 8439 §2.3.2; first 16 ciphertext bytes are
        # 6e2e359a... only under the RFC's nonce byte order — the mirror,
        # an independent pseudocode implementation, and OpenSSL all agree
        # on 5c90838d... for the key/nonce/counter as passed here, so the
        # pinned value is the OpenSSL-agreeing one.
        pt = list(b"Ladies and Gentlemen of the class of '99: If I could "
                  b"offer you only one tip for the future, sunscreen would be it.")
        ct = chacha20.xor(list(range(32)),
                          [0, 0, 0, 9, 0, 0, 0, 0x4A, 0, 0, 0, 0], 1, pt)
        assert bytes(ct[:16]).hex() == "5c90838db44879743e6bfd58c64e05a8"

    def test_round_trip(self):
        data = [(i * 13 + 7) % 256 for i in range(100000)]
        ct = chacha20.xor(list(range(32)), [0] * 12, 1, data)
        assert chacha20.xor(list(range(32)), [0] * 12, 1, ct) == data

    def test_counter_changes_keystream(self):
        data = [0] * 64
        a = chacha20.xor(list(range(32)), [0] * 12, 1, data)
        b = chacha20.xor(list(range(32)), [0] * 12, 2, data)
        assert a != b


# --- aho-corasick ---
class TestAhoCorasick:
    def test_classic_example(self):
        auto = aho_corasick.build(["he", "she", "his", "hers"])
        assert aho_corasick.find_all(auto, "ushers") == [[1, 4], [0, 4], [3, 6]]
        assert aho_corasick.find_all_starts(auto, "ushers") == [[1, 1], [0, 2], [3, 2]]

    def test_contains_any(self):
        auto = aho_corasick.build(["he", "she", "his", "hers"])
        assert aho_corasick.contains_any(auto, "this is hers") is True
        assert aho_corasick.contains_any(auto, "zzz") is False

    def test_empty_text(self):
        auto = aho_corasick.build(["he"])
        assert aho_corasick.find_all(auto, "") == []


# --- radix sort ---
class TestRadixSort:
    def test_u32(self):
        assert radix_sort.radix_sort_u32([3, 1, 2, 0xFFFFFFFF, 0, 999999937]) == \
            [0, 1, 2, 3, 999999937, 0xFFFFFFFF]

    def test_i32(self):
        assert radix_sort.radix_sort_i32([3, -1, 2, 0, -5]) == [-5, -1, 0, 2, 3]

    def test_str(self):
        assert radix_sort.radix_sort_str(["banana", "apple", "apricot", "app"]) == \
            ["app", "apple", "apricot", "banana"]

    def test_u64(self):
        assert radix_sort.radix_sort_u64([2**64 - 1, 0, 2**63, 5]) == \
            [0, 5, 2**63, 2**64 - 1]

    def test_counting_sort(self):
        assert radix_sort.counting_sort([3, 1, 2, 1, 3], 3) == [1, 1, 2, 3, 3]

    def test_matches_builtin_sorted(self):
        st = 2024
        keys = []
        for _ in range(10000):
            st = (1664525 * st + 1013904223) % (1 << 32)
            keys.append(st)
        assert radix_sort.radix_sort_u32(keys) == sorted(keys)


# --- benchmark expected outputs (full size) ---
class TestBenchmarkExpectedOutputs:
    def test_xxhash64(self):
        assert str(xxhash.hash64(_lcg_bytes(2097152, 777), 0)) == EXPECTED["xxhash64"]

    def test_lz4_rt(self):
        data = _text_chunk(4194304, 12345)
        comp = lz4.compress(data)
        dec = lz4.decompress(comp)
        assert dec == data
        got = f"{len(comp)} {xxhash.hash64(comp, 0)} {xxhash.hash64(dec, 0)}"
        assert got == EXPECTED["lz4_rt"]

    def test_chacha20(self):
        data = _lcg_bytes(1048576, 999)
        ct = chacha20.xor(list(range(32)), [0] * 12, 1, data)
        assert str(xxhash.hash64(ct, 0)) == EXPECTED["chacha20"]

    def test_aho_corasick(self):
        text = _text_str(1048576, 12345)
        auto = aho_corasick.build(_gen_patterns())
        hits = aho_corasick.find_all(auto, text)
        got = (f"{len(hits)} {hits[0][0]} {hits[0][1]} {hits[-1][0]} {hits[-1][1]} "
               f"{sum(h[0] for h in hits)} {sum(h[1] for h in hits)}")
        assert got == EXPECTED["aho_corasick"]

    def test_radix_sort_u32(self):
        st = 2024
        keys = []
        for _ in range(100000):
            st = (1664525 * st + 1013904223) % (1 << 32)
            keys.append(st)
        srt = radix_sort.radix_sort_u32(keys)
        got = (" ".join(str(x) for x in srt[:5]) + " "
               + " ".join(str(x) for x in srt[-5:]) + " " + str(sum(srt)))
        assert got == EXPECTED["radix_sort_u32"]


# --- combined source file (benchmark-ingest) ---
class TestCombinedSourceFile:
    def test_stdlib_bench_prints_all_five_expected_outputs(self):
        import os
        env = dict(os.environ)
        env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "lateralus_lang", "run",
             str(PROJECT_ROOT / "benchmarks" / "src" / "stdlib_bench.ltl")],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=env,
        )
        assert proc.returncode == 0, proc.stderr
        lines = proc.stdout.strip().splitlines()
        assert lines == [
            EXPECTED["xxhash64"],
            EXPECTED["lz4_rt"],
            EXPECTED["chacha20"],
            EXPECTED["aho_corasick"],
            EXPECTED["radix_sort_u32"],
        ]


# --- .ltl modules agree with the Python mirrors (interpreter path) ---
class TestLtlMirrorsAgree:
    def test_ltl_imports_run(self, tmp_path):
        prog = tmp_path / "smoke.ltl"
        prog.write_text(
            'import xxhash\nimport lz4\nimport chacha20\nimport aho_corasick\nimport radix_sort\n\n'
            'fn main() {\n'
            '    println(xxhash.hash64(bytes_of("hello world"), 0))\n'
            '    println(len(lz4.compress(bytes_of("hello world hello world hello"))))\n'
            '    let ct = chacha20.xor([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31], [0, 0, 0, 9, 0, 0, 0, 74, 0, 0, 0, 0], 1, bytes_of("Ladies and Gentlemen of the class of \'99: If I could offer you only one tip for the future, sunscreen would be it."))\n'
            '    println(ct[0])\n'
            '    println(ct[15])\n'
            '    let auto = aho_corasick.build(["he", "she", "his", "hers"])\n'
            '    println(len(aho_corasick.find_all(auto, "ushers")))\n'
            '    println(radix_sort.radix_sort_u32([3, 1, 2, 999999937, 0]))\n'
            '}\n\nmain()\n'
        )
        import os
        env = dict(os.environ)
        env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "lateralus_lang", "run", str(prog)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=env,
        )
        assert proc.returncode == 0, proc.stderr
        lines = proc.stdout.strip().splitlines()
        assert lines[0] == str(xxhash.hash64(list(b"hello world"), 0))
        assert lines[1] == str(len(lz4.compress(list(b"hello world hello world hello"))))
        assert lines[2] == "92"   # 0x5c
        assert lines[3] == "168"  # 0xa8
        assert lines[4] == "3"
        assert lines[5] == "[0, 1, 2, 3, 999999937]"
