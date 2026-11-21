# LZ4 Block Compression with `stdlib/lz4.ltl`

LZ4 is the fastest lossless compressor alive — and its *block* format
is small enough to hold in your head: a token byte splitting literal
length (high nibble) from match length (low nibble), length-extension
bytes at 255, literals, then a 2-byte little-endian match offset.
`stdlib/lz4.ltl` implements both directions in pure Lateralus — a
hash-chain greedy compressor and the canonical decompressor — ~160
lines, no frame format.

This tutorial walks the token format and proves round-trips.
Companion: `examples/lz4_tutorial.ltl`.

---

## The token byte

```text
token:  LLLL MMMM
        LLLL = literal length (15 => read extension bytes)
        MMMM = match length - 4   (15 => read extension bytes)
```

A sequence is: token → literal-length extension (if L=15, add bytes
of 255 until a byte <255) → literal bytes → **2-byte LE offset** →
match-length extension (if M=15) → next token. The stream ends with a
literals-only token (no offset follows when input is exhausted).

## Length extensions

`emit_var_len` writes `v` as a sum of 255-bytes plus a final
remainder — the same trick as MQTT's remaining length but
big-endian-free. Decompression mirrors it: keep adding extension
bytes while they're 255.

## The compressor

A 4096-entry hash table (`LZ4_HASH_SIZE = 1 << 12`) maps a Knuth
hash of each 4-byte window to its last position. At each position:

- hash the 4 bytes, look up `ref_pos`
- verify the 4 bytes actually match (hash collisions happen)
- extend the match forward while bytes agree
- emit pending literals + offset + lengths, jump `mlen` ahead

It's LZ4's "fast" greedy strategy — not optimal parsing, but
exceptionally simple. Minimum match 4, max offset 65535, and the
last 5 bytes always stay literal (LZ4_END conditions).

## The decompressor

Canonical and total: read token, resolve both lengths, copy literals,
read offset, then copy `match_length + 4` bytes **one at a time
from already-emitted output** — which is what makes overlapping
matches (RLE runs like `AAAA…`) work: each copied byte becomes
available for the next.

## Verified results

```text
"hi" (2B)          -> 20 68 69            literals-only token
900B repeated text -> 60B                 15x ratio, round-trip OK
200B pseudo-random -> 202B                ~1.01x (expansion, expected)
300 x 'A'         -> 12B                  overlap match, round-trip OK
```

Every `decompress(compress(x)) == x` across all four cases —
including the pathological all-same-byte input that exercises
overlapping copies.

`tests/test_lz4_tutorial.py` pins the compressed bytes of the
repetitive sample (`f010746865…`) and all round-trip assertions.

## When to use it

**Use it** for fast compression of logs, IPC buffers, or network
payloads where ratio matters less than speed — or as a readable
example of hash-table match finding plus a streaming byte decoder.

**Don't expect** the LZ4 *frame* format (magic `0x184D2204`, block
checksums, content size) — this is block mode only; framing is a
thin wrapper you'd add yourself. Also no dictionary support or the
HC/high-compression variants.

That is `stdlib/lz4.ltl`: tokens, offsets, and overlap — LZ4 in
pure Lateralus.
