# Hex, Base64 and Percent-Encoding with `stdlib/encoding.ltl`

Every protocol on the internet is built on three tiny codecs: hex, base64,
and percent-encoding. `stdlib/encoding.ltl` implements all three — plus
their decoders — in about 150 lines of Lateralus, with no external
dependencies and semantics you can verify against RFC test vectors by hand.

This tutorial works through each codec, the bit arithmetic underneath, the
edge cases (padding, empty input, the `+`/space quirk), and ends with a
self-contained companion script whose entire output is pinned by pytest.

---

## Hex: the debug format

`hex_encode(bytes)` maps each byte to two lowercase hex digits via a
16-character lookup table; `hex_decode(s)` walks the string two characters
at a time and recombines nibbles with `hi * 16 + lo`.

```text
hex_encode([0, 255, 128])  => "00ff80"
hex_encode("hello" bytes) => "68656c6c6f"
```

Hex is the codec you reach for when humans must read the bytes — checksums,
object IDs, debug dumps. It is *not* compact (2× expansion) and not
encryption (it's a bijection).

The decoder accepts upper- or lowercase (`A–F` and `a–f`) and silently maps
any non-hex character to 0 via `_hex_digit`'s fallthrough — worth knowing:
`hex_decode("zz")` returns `[0]`, not an error. Validate upstream if the
input is untrusted.

## Base64: the transport format

Base64 encodes 3 bytes (24 bits) as 4 characters from a 64-symbol alphabet
(`A–Z a–z 0–9 + /`), padding the final partial group with `=`.

The encoder processes the input in 3-byte chunks and extracts four 6-bit
sextets:

```text
b0 >> 2                          -> sextet 1
((b0 & 3) << 4) | (b1 >> 4)      -> sextet 2
((b1 & 15) << 2) | (b2 >> 6)     -> sextet 3
b2 & 63                          -> sextet 4
```

When the chunk has fewer than 3 bytes, the missing sextets become `=`.
That is why `"hello"` (5 bytes = one full chunk + 2 leftover) encodes to
`aGVsbG8=` — one `=` pad — while `"Hello"` gives `SGVsbG8=`: the capital
`H` (72) sets different top bits, a one-character difference that makes a
handy pin for tests.

The decoder reverses the process, skipping the byte emitted for each `=`
pad. Round-trip property: `base64_decode(base64_encode(x)) == x` for any
byte list.

## Percent-encoding: the URL format

`url_encode` keeps an explicit safe set
(`A–Z a–z 0–9 - _ . ~`, per RFC 3986) and percent-encodes everything else
as `%HH` uppercase hex. `url_decode` reverses `%HH` sequences *and*
translates `+` to space — the HTML form convention that predates RFC 3986.

```text
url_encode("a b&c=d")   => "a%20b%26c%3Dd"
url_encode("100% sure?") => "100%25%20sure%3F"
url_decode("a+b%20c")   => "a b c"
```

Note the asymmetry: `url_encode` emits `%20` for space, never `+` — but
`url_decode` accepts both. If you encode query parameters for a form
endpoint, `%20` is always safe; `+` is only understood by
`application/x-www-form-urlencoded` parsers.

## Edge cases worth pinning

| Input | Output | Why it matters |
|---|---|---|
| `hex_encode([])` | `""` | empty stays empty, no stray digits |
| `base64_encode([0])` | `"AA=="` | two pads for a 1-byte tail |
| `base64_encode([255,255,255])` | `"////"` | all-ones bytes hit the `/` symbol |
| `url_encode("100% sure?")` | `"100%25%20sure%3F"` | `%` itself must be encoded first-order |

## Running the companion script

`examples/encoding_tutorial.ltl` re-implements the same algorithms
self-contained (bit shifts written as `/` and `%` so the script is
backend-agnostic) and prints:

```text
=== LATERALUS STDLIB ENCODING TUTORIAL ===
STEP 1: hex_encode = 68656c6c6f
STEP 2: base64_encode('hello') = aGVsbG8=
STEP 2: base64_encode('Hello') = SGVsbG8=
STEP 3: url_encode('a b&c=d') = a%20b%26c%3Dd
STEP 3: url_decode round-trip = a b&c=d
STEP 4: base64_encode([0]) = 'AA=='
STEP 4: base64_encode([255,255,255]) = '////'
PINNED_VECTORS: hex=68656c6c6f b64=aGVsbG8= b64Hello=SGVsbG8= b64world=aGVsbG8gd29ybGQ= url=a%20b%26c%3Dd
```

`tests/test_encoding_tutorial.py` asserts every line verbatim, so the
pinned vectors double as executable documentation — if the module's
behaviour ever changes, CI tells you exactly which codec moved.

## Choosing a codec

- **hex** — human-readable byte dumps, checksums, IDs.
- **base64** — binary-safe transport inside text protocols (MIME,
  data: URLs, JWT segments). 33% expansion, not encryption.
- **percent-encoding** — URL query strings and path segments only; it is
  not a general-purpose encoding for arbitrary bytes.

That is `stdlib/encoding.ltl` end to end: three codecs, their inverses,
the padding rules, and a runnable script that pins the RFC vectors so you
can verify the module against your own test data.
