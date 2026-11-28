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


BENCHMARKS = {
    "fib": lambda: fib(32),
    "sieve": lambda: sieve(50000),
    "mandelbrot": lambda: mandelbrot(150, 100, 255),
    "nbody": lambda: nbody(5, 5000),
    "binary_trees": lambda: check_tree(make_tree(12)),
}


# ---------------------------------------------------------------------------
# stdlib micro-benchmark references (bounty: benchmark-ingest, issue #156).
# Each mirrors the matching benchmarks/src/stdlib/*_driver.ltl exactly:
# same input generation, same operation, same printed output.
# ---------------------------------------------------------------------------

M32 = 0xFFFFFFFF
M64 = 0xFFFFFFFFFFFFFFFF


def _gen_byte(x):
    return (x * 31 + 7) & 0xFF


def _gen_key(x):
    return (x * 2654435761) & M32


# --- xxhash64 (stdlib/xxhash.ltl) -----------------------------------------
XXH_P1 = 0x9E3779B185EBCA87
XXH_P2 = 0xC2B2AE3D27D4EB4F
XXH_P3 = 0x165667B19E3779F9
XXH_P4 = 0x85EBCA77C2B2AE63
XXH_P5 = 0x27D4EB2F165667C5


def _rotl64(v, r):
    v &= M64
    return ((v << r) | (v >> (64 - r))) & M64


def _round64(acc, inp):
    acc = (acc + (inp * XXH_P2)) & M64
    acc = _rotl64(acc, 31)
    return (acc * XXH_P1) & M64


def _merge_round(acc, val):
    val = _round64(0, val)
    acc ^= val
    return ((acc * XXH_P1) & M64) + XXH_P4 & M64


def _read_u64_le(buf, i):
    return (buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)
            | (buf[i + 4] << 32) | (buf[i + 5] << 40) | (buf[i + 6] << 48)
            | (buf[i + 7] << 56))


def _read_u32_le(buf, i):
    return buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)


def xxhash64(buf, seed):
    n = len(buf)
    if n >= 32:
        v1 = (seed + XXH_P1 + XXH_P2) & M64
        v2 = (seed + XXH_P2) & M64
        v3 = seed & M64
        v4 = (seed - XXH_P1) & M64
        i = 0
        limit = n - 32
        while i <= limit:
            v1 = _round64(v1, _read_u64_le(buf, i)); i += 8
            v2 = _round64(v2, _read_u64_le(buf, i)); i += 8
            v3 = _round64(v3, _read_u64_le(buf, i)); i += 8
            v4 = _round64(v4, _read_u64_le(buf, i)); i += 8
        h = (_rotl64(v1, 1) + _rotl64(v2, 7) + _rotl64(v3, 12) + _rotl64(v4, 18)) & M64
        h = _merge_round(h, v1); h = _merge_round(h, v2)
        h = _merge_round(h, v3); h = _merge_round(h, v4)
    else:
        h = (seed + XXH_P5) & M64
        i = 0
    h = (h + n) & M64
    while i + 8 <= n:
        k1 = _round64(0, _read_u64_le(buf, i))
        h ^= k1
        h = (_rotl64(h, 27) * XXH_P1 + XXH_P4) & M64
        i += 8
    if i + 4 <= n:
        h ^= (_read_u32_le(buf, i) * XXH_P1) & M64
        h = (_rotl64(h, 23) * XXH_P2 + XXH_P3) & M64
        i += 4
    while i < n:
        h ^= (buf[i] * XXH_P5) & M64
        h = (_rotl64(h, 11) * XXH_P1) & M64
        i += 1
    h ^= h >> 33; h = (h * XXH_P2) & M64
    h ^= h >> 29; h = (h * XXH_P3) & M64
    h ^= h >> 32
    return h


def bench_xxhash():
    buf = [_gen_byte(x) for x in range(2000000)]
    return xxhash64(buf, 0)


# --- lz4 compress + decompress round-trip (stdlib/lz4.ltl) ----------------
LZ4_MINMATCH = 4
LZ4_HASH_BITS = 12
LZ4_HASH_SIZE = 1 << LZ4_HASH_BITS
LZ4_HASH_MASK = LZ4_HASH_SIZE - 1
LZ4_MF_LIMIT = 12
LZ4_LAST_LITS = 5
LZ4_MAXD = 65535


def _hash4(buf, i):
    v = (buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24))
    return ((v * 2654435761) >> (32 - LZ4_HASH_BITS)) & LZ4_HASH_MASK


def _emit_var_len(out, v):
    while v >= 255:
        out.append(255)
        v -= 255
    out.append(v)


def lz4_compress(src):
    n = len(src)
    out = []
    anchor = 0
    i = 0
    if n < LZ4_MF_LIMIT + LZ4_LAST_LITS:
        lit_len = n
        if lit_len >= 15:
            out.append(0xF0)
            _emit_var_len(out, lit_len - 15)
        else:
            out.append((lit_len << 4) & 0xFF)
        out.extend(src)
        return out
    htab = [-1] * LZ4_HASH_SIZE
    end_limit = n - LZ4_MF_LIMIT - LZ4_LAST_LITS
    while i <= end_limit:
        hv = _hash4(src, i)
        ref_pos = htab[hv]
        htab[hv] = i
        if (ref_pos >= 0 and i - ref_pos <= LZ4_MAXD
                and src[ref_pos] == src[i]
                and src[ref_pos + 1] == src[i + 1]
                and src[ref_pos + 2] == src[i + 2]
                and src[ref_pos + 3] == src[i + 3]):
            mlen = 4
            while i + mlen < n - LZ4_LAST_LITS and src[ref_pos + mlen] == src[i + mlen]:
                mlen += 1
            lit_len = i - anchor
            mlen_t = mlen - LZ4_MINMATCH
            t_lit = min(lit_len, 15)
            t_m = min(mlen_t, 15)
            out.append(((t_lit << 4) | t_m) & 0xFF)
            if lit_len >= 15:
                _emit_var_len(out, lit_len - 15)
            out.extend(src[anchor:anchor + lit_len])
            off = i - ref_pos
            out.append(off & 0xFF)
            out.append((off >> 8) & 0xFF)
            if mlen_t >= 15:
                _emit_var_len(out, mlen_t - 15)
            i += mlen
            anchor = i
        else:
            i += 1
    lit_len = n - anchor
    if lit_len >= 15:
        out.append(0xF0)
        _emit_var_len(out, lit_len - 15)
    else:
        out.append((lit_len << 4) & 0xFF)
    out.extend(src[anchor:n])
    return out


def lz4_decompress(src):
    n = len(src)
    out = []
    i = 0
    while i < n:
        tok = src[i]; i += 1
        lit_len = (tok >> 4) & 0x0F
        if lit_len == 15:
            while True:
                b = src[i]; i += 1
                lit_len += b
                if b != 255:
                    break
        out.extend(src[i:i + lit_len]); i += lit_len
        if i >= n:
            return out
        off = src[i] | (src[i + 1] << 8); i += 2
        mlen = tok & 0x0F
        if mlen == 15:
            while True:
                b = src[i]; i += 1
                mlen += b
                if b != 255:
                    break
        mlen += LZ4_MINMATCH
        start = len(out) - off
        for m in range(mlen):
            out.append(out[start + m])
    return out


def bench_lz4():
    src = [_gen_byte(x) for x in range(100000)]
    c = lz4_compress(src)
    d = lz4_decompress(c)
    return f"{len(src)} {len(c)} {len(d)}"


# --- chacha20 (stdlib/chacha20.ltl) ---------------------------------------
def _rotl32(x, n):
    return ((x << n) | (x >> (32 - n))) & M32


def _qr(s, a, b, c, d):
    s[a] = (s[a] + s[b]) & M32; s[d] ^= s[a]; s[d] = _rotl32(s[d], 16)
    s[c] = (s[c] + s[d]) & M32; s[b] ^= s[c]; s[b] = _rotl32(s[b], 12)
    s[a] = (s[a] + s[b]) & M32; s[d] ^= s[a]; s[d] = _rotl32(s[d], 8)
    s[c] = (s[c] + s[d]) & M32; s[b] ^= s[c]; s[b] = _rotl32(s[b], 7)


def _u32_to_le(v):
    return [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF]


def _cc_block(key, nonce, counter):
    s = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]
    for i in range(0, 32, 4):
        s.append(_read_u32_le(key, i))
    s.append(counter & M32)
    for i in range(0, 12, 4):
        s.append(_read_u32_le(nonce, i))
    w = s[:]
    for _ in range(10):
        _qr(w, 0, 4, 8, 12); _qr(w, 1, 5, 9, 13)
        _qr(w, 2, 6, 10, 14); _qr(w, 3, 7, 11, 15)
        _qr(w, 0, 5, 10, 15); _qr(w, 1, 6, 11, 12)
        _qr(w, 2, 7, 8, 13); _qr(w, 3, 4, 9, 14)
    out = []
    for i in range(16):
        out += _u32_to_le((w[i] + s[i]) & M32)
    return out


def chacha20_xor(key, nonce, counter, data):
    out = []
    n = len(data)
    i = 0
    while i < n:
        ks = _cc_block(key, nonce, counter)
        take = min(64, n - i)
        for j in range(take):
            out.append(data[i + j] ^ ks[j])
        i += 64
        counter += 1
    return out


def bench_chacha20():
    key = [_gen_byte(x) for x in range(32)]
    nonce = [_gen_byte(x) for x in range(12)]
    data = [_gen_byte(x) for x in range(150000)]
    ct = chacha20_xor(key, nonce, 0, data)
    return f"{len(ct)} {ct[12345]}"


# --- aho_corasick (stdlib/aho_corasick.ltl) -------------------------------
def _ac_build(patterns):
    goto = [{}]
    fail = [0]
    output = [[]]
    for pid, p in enumerate(patterns):
        node = 0
        for ch in p:
            if ch not in goto[node]:
                goto.append({}); fail.append(0); output.append([])
                goto[node][ch] = len(goto) - 1
            node = goto[node][ch]
        output[node].append(pid)
    from collections import deque
    dq = deque()
    for ch, nx in goto[0].items():
        dq.append(nx)
    while dq:
        r = dq.popleft()
        for ch, nx in goto[r].items():
            dq.append(nx)
            f = fail[r]
            while f > 0 and ch not in goto[f]:
                f = fail[f]
            if ch in goto[f] and goto[f][ch] != nx:
                fail[nx] = goto[f][ch]
            output[nx] += output[fail[nx]]
    return {"goto": goto, "fail": fail, "output": output}


def _ac_find_all(auto, text):
    hits = []
    node = 0
    for i, ch in enumerate(text):
        while node > 0 and ch not in auto["goto"][node]:
            node = auto["fail"][node]
        if ch in auto["goto"][node]:
            node = auto["goto"][node][ch]
        for pid in auto["output"][node]:
            hits.append((pid, i + 1))
    return hits


def bench_aho_corasick():
    pats = ["the", "quick", "brown", "fox", "jumps", "lazy", "dog",
            "hello", "world", "lateralus"]
    auto = _ac_build(pats)
    text = "the quick brown fox jumps over the lazy dog hello world lateralus "
    big = text * 3000
    hits = _ac_find_all(auto, big)
    return f"{len(big)} {len(hits)}"


# --- radix_sort_u32 (stdlib/radix_sort.ltl) -------------------------------
def _radix_pass(xs, shift):
    counts = [0] * 256
    out = [0] * len(xs)
    for x in xs:
        counts[(x >> shift) & 0xFF] += 1
    s = 0
    for i in range(256):
        c = counts[i]; counts[i] = s; s += c
    for x in xs:
        b = (x >> shift) & 0xFF
        out[counts[b]] = x
        counts[b] += 1
    return out


def radix_sort_u32(xs):
    for sh in (0, 8, 16, 24):
        xs = _radix_pass(xs, sh)
    return xs


def bench_radix_sort():
    xs = [_gen_key(x) for x in range(100000)]
    s = radix_sort_u32(xs)
    return f"{len(s)} {s[0]} {s[99999]}"


STDLIB_BENCHMARKS = {
    "xxhash": bench_xxhash,
    "lz4": bench_lz4,
    "chacha20": bench_chacha20,
    "aho_corasick": bench_aho_corasick,
    "radix_sort": bench_radix_sort,
}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "fib"
    if name in STDLIB_BENCHMARKS:
        print(STDLIB_BENCHMARKS[name]())
    else:
        print(BENCHMARKS[name]())
