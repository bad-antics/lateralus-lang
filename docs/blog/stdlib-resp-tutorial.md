# Redis Protocol with `stdlib/resp.ltl`

RESP — the Redis Serialization Protocol — is the wire format under every
`redis-cli`, every client library, and every Redis-compatible service
(Valkey, KeyDB, Dragonfly, the AWS ElastiCache protocol). It looks
deceptingly simple: one type tag byte, a CRLF, done. `stdlib/resp.ltl`
implements both directions — encoder and an incremental parser — in
about 200 lines.

This tutorial covers the RESP2/RESP3 type system, command encoding,
and the offset-based decoder that handles nested structures and
truncated buffers. Companion: `examples/resp_tutorial.ltl`.

---

## One tag byte per type

```text
+ simple string     - error          : integer
$ bulk string       * array          _ null (RESP3)
# boolean           , double         ( big number
% map               ~ set
```

RESP2 uses the first five; RESP3 adds the rest. The elegant part: RESP3
is a *superset* — a RESP3 parser reads RESP2 streams natively, which is
why the module shares one `decode` for both versions.

## Encoding: length-prefixed everything

```text
enc_simple_string("OK")   ->  "+OK\r\n"
enc_integer(42)           ->  ":42\r\n"
enc_bulk_string("hello")  ->  "$5\r\nhello\r\n"
enc_command(["SET","foo","bar"])
  ->  "*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
```

Bulk strings carry an explicit byte length — that's what lets them
contain arbitrary binary (including `\r\n` itself) safely. Commands are
always `*N` arrays of bulk strings: the canonical client→server
request, one encoding for every command regardless of arity.

Nulls have *three* spellings across versions: `$-1` (null bulk),
`*-1` (null array), `_` (RESP3 null). The encoder exposes all three —
matching what the peer's protocol version expects matters.

## Decoding: an offset cursor, not a stream

`decode(buf, i)` returns `[value, next_i]` — parse one value starting
at offset `i`, hand back where the next value begins. Recursion handles
nesting: `*` arrays and `%` maps loop `decode` over their elements.

Three design details worth noticing:

1. **Incomplete input returns `[nil, i]`** — never throws, never reads
   past the end. A partial `$10\r\nhe` buffer yields `nil` with the
   cursor intact, so a caller can retry when more bytes arrive. This is
   what makes the codec usable on real sockets.
2. **Negative lengths are nulls** — `$-1`/`*-1` short-circuit before
   the length check.
3. **Simple strings/errors come back as `{kind, value}` maps** — the
   tag is preserved so callers can distinguish `+OK` from an error
   reply that happens to contain the same text.

## RESP2 vs RESP3 in practice

For interop, encode commands as RESP2 (arrays of bulk strings — every
server accepts them) and decode whatever comes back. RESP3-only types
(`_`, `#`, `,`, `(`, `%`, `~`) appear only if you `HELLO 3` first —
the tutorial's decoder handles them anyway since the tag dispatch is
shared.

## Running the companion

```text
STEP 1 scalar encodings:
  simple: +OK\r\n
  error:  -ERR unknown command\r\n
  int:    :42\r\n
  bulk:   $5\r\nhello\r\n
  nulls:  $-1\r\n*-1\r\n_\r\n
  bool:   #t\r\n#f\r\n
  double: ,3.14\r\n
STEP 2 command encoding:
  *3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n
STEP 3-5 decoding:
  +OK -> simple:OK next=5     :42 -> 42 next=5
  $5 hello -> hello next=11   $-1 -> None next=5
  _ -> nil next=3             #t -> True next=4
  *2 array -> [GET, foo]      %1 map -> {'foo': 42}
  ~2 set -> [kind-maps]       truncated -> None next=5
```

`tests/test_resp_tutorial.py` pins encodings byte-for-byte (the `\r\n`
placement is the whole protocol) and decode offsets — `next=` values
prove the cursor lands exactly where the next value starts.

## When to use it

**Use it** to talk to Redis/Valkey/KeyDB/Dragonfly-compatible servers,
to implement a RESP proxy or codec in another language, or to learn
how length-prefixed binary protocols work — RESP is the cleanest
example going.

**Don't expect** RESP3 push messages (`>`) — the module covers the
request/reply types; pub/sub push type isn't in the tag table. And
remember `enc_double` takes a *pre-rendered* string — float formatting
is the caller's problem, a deliberate choice to keep the codec
format-agnostic.

That is `stdlib/resp.ltl`: eleven tags, one cursor, and a parser that
treats truncation as routine rather than exceptional.
