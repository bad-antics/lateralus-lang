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


# --- stdlib benchmarks (benchmark-ingest) ---
# Same deterministic inputs as benchmarks/src/*.ltl, same expected outputs.
# These are independent Python reference implementations of the same
# algorithms specified by stdlib/{xxhash,lz4,chacha20,aho_corasick,
# radix_sort}.ltl (XXH64, LZ4 block, ChaCha20 RFC 8439, Aho-Corasick,
# LSD radix sort). They must agree byte-for-byte with the .ltl output.

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


# --- XXH64 (xxHash, 64-bit) ---
_M64 = (1 << 64) - 1
_P1 = 11400714785074694791
_P2 = 14029467366897019727
_P3 = 1609587929392839161
_P4 = 9650029242287828579
_P5 = 2870177450012600261


def _u64(x):
    return x & _M64


def _rotl64(v, r):
    v &= _M64
    return ((v << r) | (v >> (64 - r))) & _M64


def _r32(buf, i):
    return buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)


def _r64(buf, i):
    return _r32(buf, i) | (_r32(buf, i + 4) << 32)


def _round64(acc, lane):
    acc = _u64(acc + lane * _P2)
    acc = _rotl64(acc, 31)
    return _u64(acc * _P1)


def _merge(acc, v):
    v = _round64(0, v)
    acc ^= v
    return _u64(acc * _P1 + _P4)


def xxh64(buf, seed=0):
    buf = bytes(buf)
    n = len(buf)
    if n >= 32:
        v1 = _u64(seed + _P1 + _P2)
        v2 = _u64(seed + _P2)
        v3 = _u64(seed)
        v4 = _u64(seed - _P1)
        i = 0
        while i + 32 <= n:
            v1 = _round64(v1, _r64(buf, i))
            v2 = _round64(v2, _r64(buf, i + 8))
            v3 = _round64(v3, _r64(buf, i + 16))
            v4 = _round64(v4, _r64(buf, i + 24))
            i += 32
        h = _u64(_rotl64(v1, 1) + _rotl64(v2, 7) + _rotl64(v3, 12) + _rotl64(v4, 18))
        h = _merge(h, v1)
        h = _merge(h, v2)
        h = _merge(h, v3)
        h = _merge(h, v4)
    else:
        h = _u64(seed + _P5)
    h = _u64(h + n)
    i = n - (n % 32) if n >= 32 else 0
    while i + 8 <= n:
        k = _round64(0, _r64(buf, i))
        h ^= k
        h = _u64(_rotl64(h, 27) * _P1 + _P4)
        i += 8
    if i + 4 <= n:
        h ^= _u64(_r32(buf, i) * _P1)
        h = _u64(_rotl64(h, 23) * _P2 + _P3)
        i += 4
    while i < n:
        h ^= _u64(buf[i] * _P5)
        h = _u64(_rotl64(h, 11) * _P1)
        i += 1
    h ^= h >> 33
    h = _u64(h * _P2)
    h ^= h >> 29
    h = _u64(h * _P3)
    h ^= h >> 32
    return h


# --- LZ4 block codec ---
_LZ_MINMATCH = 4
_LZ_HASH_BITS = 12
_LZ_HASH_SIZE = 4096
_LZ_HASH_MASK = 4095
_LZ_MF_LIMIT = 12
_LZ_LAST_LITS = 5
_LZ_MAXD = 65535


def _lz_hash4(buf, i):
    v = buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)
    return ((v * 2654435761) >> (32 - _LZ_HASH_BITS)) & _LZ_HASH_MASK


def _lz_emit(out, v):
    while v >= 255:
        out.append(255)
        v -= 255
    out.append(v)


def lz4_compress(src):
    src = bytes(src)
    n = len(src)
    out = bytearray()
    anchor = 0
    i = 0
    if n < _LZ_MF_LIMIT + _LZ_LAST_LITS:
        lit_len = n
        if lit_len >= 15:
            out.append(0xF0)
            _lz_emit(out, lit_len - 15)
        else:
            out.append((lit_len << 4) & 0xFF)
        out.extend(src[:n])
        return list(out)
    htab = [-1] * _LZ_HASH_SIZE
    end_limit = n - _LZ_MF_LIMIT - _LZ_LAST_LITS
    while i <= end_limit:
        hv = _lz_hash4(src, i)
        ref_pos = htab[hv]
        htab[hv] = i
        if (ref_pos >= 0 and i - ref_pos <= _LZ_MAXD
                and src[ref_pos] == src[i]
                and src[ref_pos + 1] == src[i + 1]
                and src[ref_pos + 2] == src[i + 2]
                and src[ref_pos + 3] == src[i + 3]):
            mlen = 4
            while i + mlen < n - _LZ_LAST_LITS and src[ref_pos + mlen] == src[i + mlen]:
                mlen += 1
            lit_len = i - anchor
            mlen_t = mlen - _LZ_MINMATCH
            t_lit = lit_len if lit_len <= 15 else 15
            t_m = mlen_t if mlen_t <= 15 else 15
            out.append(((t_lit << 4) | t_m) & 0xFF)
            if lit_len >= 15:
                _lz_emit(out, lit_len - 15)
            out.extend(src[anchor:anchor + lit_len])
            off = i - ref_pos
            out.append(off & 0xFF)
            out.append((off >> 8) & 0xFF)
            if mlen_t >= 15:
                _lz_emit(out, mlen_t - 15)
            i += mlen
            anchor = i
        else:
            i += 1
    lit_len = n - anchor
    if lit_len >= 15:
        out.append(0xF0)
        _lz_emit(out, lit_len - 15)
    else:
        out.append((lit_len << 4) & 0xFF)
    out.extend(src[anchor:anchor + lit_len])
    return list(out)


def lz4_decompress(src):
    src = bytes(src)
    n = len(src)
    out = bytearray()
    i = 0
    while i < n:
        tok = src[i]
        i += 1
        lit_len = (tok >> 4) & 0x0F
        if lit_len == 15:
            while True:
                b = src[i]
                i += 1
                lit_len += b
                if b != 255:
                    break
        out.extend(src[i:i + lit_len])
        i += lit_len
        if i >= n:
            return list(out)
        off = src[i] | (src[i + 1] << 8)
        i += 2
        mlen = tok & 0x0F
        if mlen == 15:
            while True:
                b2 = src[i]
                i += 1
                mlen += b2
                if b2 != 255:
                    break
        mlen += _LZ_MINMATCH
        start = len(out) - off
        for m in range(mlen):
            out.append(out[start + m])
    return list(out)


# --- ChaCha20 (RFC 8439) ---
_CC_MASK = 0xFFFFFFFF


def _cc_u32(x):
    return x & _CC_MASK


def _cc_rotl(v, r):
    v &= _CC_MASK
    return ((v << r) | (v >> (32 - r))) & _CC_MASK


def _cc_r32(buf, i):
    return buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)


def _cc_le(v):
    return [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF]


def _cc_qr(s, a, b, c, d):
    s[a] = _cc_u32(s[a] + s[b])
    s[d] = _cc_rotl(s[d] ^ s[a], 16)
    s[c] = _cc_u32(s[c] + s[d])
    s[b] = _cc_rotl(s[b] ^ s[c], 12)
    s[a] = _cc_u32(s[a] + s[b])
    s[d] = _cc_rotl(s[d] ^ s[a], 8)
    s[c] = _cc_u32(s[c] + s[d])
    s[b] = _cc_rotl(s[b] ^ s[c], 7)


def _cc_block(key, nonce, counter):
    s = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574,
         _cc_r32(key, 0), _cc_r32(key, 4), _cc_r32(key, 8), _cc_r32(key, 12),
         _cc_r32(key, 16), _cc_r32(key, 20), _cc_r32(key, 24), _cc_r32(key, 28),
         counter & _CC_MASK,
         _cc_r32(nonce, 0), _cc_r32(nonce, 4), _cc_r32(nonce, 8)]
    w = list(s)
    for _ in range(10):
        _cc_qr(w, 0, 4, 8, 12)
        _cc_qr(w, 1, 5, 9, 13)
        _cc_qr(w, 2, 6, 10, 14)
        _cc_qr(w, 3, 7, 11, 15)
        _cc_qr(w, 0, 5, 10, 15)
        _cc_qr(w, 1, 6, 11, 12)
        _cc_qr(w, 2, 7, 8, 13)
        _cc_qr(w, 3, 4, 9, 14)
    out = []
    for k in range(16):
        out += _cc_le(_cc_u32(w[k] + s[k]))
    return out


def chacha20_xor(key, nonce, initial_counter, data):
    data = bytes(data)
    out = bytearray()
    n = len(data)
    i = 0
    counter = initial_counter
    while i < n:
        ks = _cc_block(key, nonce, counter)
        take = 64 if n - i >= 64 else n - i
        out.extend(b ^ k for b, k in zip(data[i:i + take], ks))
        i += 64
        counter += 1
    return list(out)


# --- Aho-Corasick ---
def _ac_new_node(auto):
    auto["goto"].append({})
    auto["fail"].append(0)
    auto["output"].append([])
    return len(auto["goto"]) - 1


def ac_build(patterns):
    auto = {"goto": [{}], "fail": [0], "output": [[]], "patterns": patterns}
    for pid, p in enumerate(patterns):
        node = 0
        for ch in p:
            nxt = auto["goto"][node].get(ch)
            if nxt is None:
                nxt = _ac_new_node(auto)
                auto["goto"][node][ch] = nxt
            node = nxt
        auto["output"][node].append(pid)
    queue = []
    for ch, nxt in auto["goto"][0].items():
        auto["fail"][nxt] = 0
        queue.append(nxt)
    head = 0
    while head < len(queue):
        r = queue[head]
        head += 1
        for ch, s in auto["goto"][r].items():
            queue.append(s)
            state = auto["fail"][r]
            while state != 0 and ch not in auto["goto"][state]:
                state = auto["fail"][state]
            auto["fail"][s] = auto["goto"][state].get(ch, 0)
            auto["output"][s] = auto["output"][s] + auto["output"][auto["fail"][s]]
    return auto


def ac_find_all(auto, text):
    hits = []
    state = 0
    for i, ch in enumerate(text):
        while state != 0 and ch not in auto["goto"][state]:
            state = auto["fail"][state]
        state = auto["goto"][state].get(ch, 0)
        for pid in auto["output"][state]:
            hits.append([pid, i + 1])
    return hits


# --- LSD radix sort (base 256) ---
def _counting_sort(arr, k):
    counts = [0] * (k + 1)
    for v in arr:
        counts[v] += 1
    out = [0] * len(arr)
    pos = 0
    for v in range(k + 1):
        for _ in range(counts[v]):
            out[pos] = v
            pos += 1
    return out


def radix_sort_u32(arr):
    cur = list(arr)
    for byte_idx in range(4):
        cur = _radix_scatter(cur, byte_idx)
    return cur


def _radix_scatter(cur, byte_idx):
    counts = [0] * 256
    for v in cur:
        counts[(v >> (byte_idx * 8)) & 0xFF] += 1
    starts = [0] * 256
    acc = 0
    for b in range(256):
        starts[b] = acc
        acc += counts[b]
    out = [0] * len(cur)
    for v in cur:
        b = (v >> (byte_idx * 8)) & 0xFF
        out[starts[b]] = v
        starts[b] += 1
    return out


def bench_xxhash64():
    data = _lcg_bytes(2097152, 777)
    return str(xxh64(data, 0))


def bench_lz4_rt():
    data = _text_chunk(4194304, 12345)
    comp = lz4_compress(data)
    dec = lz4_decompress(comp)
    return f"{len(comp)} {xxh64(comp, 0)} {xxh64(dec, 0)}"


def bench_chacha20():
    data = _lcg_bytes(1048576, 999)
    ct = chacha20_xor(list(range(32)), [0] * 12, 1, data)
    return str(xxh64(ct, 0))


def bench_aho_corasick():
    text = _text_str(1048576, 12345)
    pats = _gen_patterns()
    auto = ac_build(pats)
    hits = ac_find_all(auto, text)
    return (f"{len(hits)} {hits[0][0]} {hits[0][1]} {hits[-1][0]} {hits[-1][1]} "
            f"{sum(h[0] for h in hits)} {sum(h[1] for h in hits)}")


def bench_radix_sort_u32():
    st = 2024
    keys = []
    for _ in range(100000):
        st = (1664525 * st + 1013904223) % (1 << 32)
        keys.append(st)
    srt = radix_sort_u32(keys)
    return (" ".join(str(x) for x in srt[:5]) + " "
            + " ".join(str(x) for x in srt[-5:]) + " " + str(sum(srt)))


BENCHMARKS = {
    "fib": lambda: fib(32),
    "sieve": lambda: sieve(50000),
    "mandelbrot": lambda: mandelbrot(150, 100, 255),
    "nbody": lambda: nbody(5, 5000),
    "binary_trees": lambda: check_tree(make_tree(12)),
    "xxhash64": bench_xxhash64,
    "lz4_rt": bench_lz4_rt,
    "chacha20": bench_chacha20,
    "aho_corasick": bench_aho_corasick,
    "radix_sort_u32": bench_radix_sort_u32,
}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "fib"
    print(BENCHMARKS[name]())
