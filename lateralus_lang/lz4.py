"""
LATERALUS Standard Library — lz4
Python implementation of stdlib/lz4.ltl

Bit-for-bit mirror of the Lateralus LZ4 block format codec (no frame
header). Used as the runtime backing for `import lz4` in transpiled
Lateralus code (see codegen/python.py alias map).

Output is accumulated in a bytearray (O(1) amortised append) instead
of the `out = out + [b]` pattern in the .ltl source, which is O(n)
per byte and makes multi-MB inputs quadratic. The compressed bytes
are identical to the .ltl implementation.

Reference: https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md
"""
from __future__ import annotations

MINMATCH = 4
HASH_BITS = 12
HASH_SIZE = 4096  # 1 << 12
HASH_MASK = 4095
MF_LIMIT = 12  # last match cannot start within 12 of end
LAST_LITS = 5  # last 5 bytes are always literals
MAXD = 65535


def _hash4(buf, i: int) -> int:
    v = buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)
    # Knuth multiplicative hash -> top HASH_BITS bits.
    return ((v * 2654435761) >> (32 - HASH_BITS)) & HASH_MASK


def _emit_var_len(out: bytearray, v: int) -> None:
    while v >= 255:
        out.append(255)
        v = v - 255
    out.append(v)


def compress(src) -> list:
    """Compress a byte list to an LZ4 block (no frame header)."""
    src = bytes(src)
    n = len(src)
    out = bytearray()
    anchor = 0  # start of pending literals
    i = 0
    if n < MF_LIMIT + LAST_LITS:
        # too small -- whole thing as one literal run
        lit_len = n
        if lit_len >= 15:
            out.append(0xF0)
            _emit_var_len(out, lit_len - 15)
        else:
            out.append((lit_len << 4) & 0xFF)
        out.extend(src[:n])
        return list(out)
    # hash table: position of last occurrence for each 4-byte prefix
    htab = [-1] * HASH_SIZE
    end_limit = n - MF_LIMIT - LAST_LITS
    while i <= end_limit:
        hv = _hash4(src, i)
        ref_pos = htab[hv]
        htab[hv] = i
        if (
            ref_pos >= 0
            and i - ref_pos <= MAXD
            and src[ref_pos] == src[i]
            and src[ref_pos + 1] == src[i + 1]
            and src[ref_pos + 2] == src[i + 2]
            and src[ref_pos + 3] == src[i + 3]
        ):
            # match -- extend
            mlen = 4
            while i + mlen < n - LAST_LITS and src[ref_pos + mlen] == src[i + mlen]:
                mlen = mlen + 1
            lit_len = i - anchor
            mlen_t = mlen - MINMATCH
            # token
            t_lit = lit_len if lit_len <= 15 else 15
            t_m = mlen_t if mlen_t <= 15 else 15
            out.append(((t_lit << 4) | t_m) & 0xFF)
            if lit_len >= 15:
                _emit_var_len(out, lit_len - 15)
            # literals
            out.extend(src[anchor : anchor + lit_len])
            # match offset (little-endian)
            off = i - ref_pos
            out.append(off & 0xFF)
            out.append((off >> 8) & 0xFF)
            if mlen_t >= 15:
                _emit_var_len(out, mlen_t - 15)
            i = i + mlen
            anchor = i
        else:
            i = i + 1
    # last literal run (contains the tail)
    lit_len = n - anchor
    if lit_len >= 15:
        out.append(0xF0)
        _emit_var_len(out, lit_len - 15)
    else:
        out.append((lit_len << 4) & 0xFF)
    out.extend(src[anchor : anchor + lit_len])
    return list(out)


def decompress(src) -> list:
    """Decompress an LZ4 block."""
    src = bytes(src)
    n = len(src)
    out = bytearray()
    i = 0
    while i < n:
        tok = src[i]
        i = i + 1
        # -- literal length
        lit_len = (tok >> 4) & 0x0F
        if lit_len == 15:
            while True:
                b = src[i]
                i = i + 1
                lit_len = lit_len + b
                if b != 255:
                    break
        # -- literals
        out.extend(src[i : i + lit_len])
        i = i + lit_len
        if i >= n:
            return list(out)
        # -- match offset
        off = src[i] | (src[i + 1] << 8)
        i = i + 2
        # -- match length
        mlen = tok & 0x0F
        if mlen == 15:
            while True:
                b2 = src[i]
                i = i + 1
                mlen = mlen + b2
                if b2 != 255:
                    break
        mlen = mlen + MINMATCH
        # -- copy from history (byte-wise to support overlap / RLE)
        start = len(out) - off
        for m in range(mlen):
            out.append(out[start + m])
    return list(out)
