# Lateralus Cheatsheet

> One page. Every stdlib module grouped by lane. Print it, pin it, ship with it.

---

## Syntax in 30 seconds

```lateralus
// functions, types, mutation
fn add(a: int, b: int) -> int { return a + b }
let x = 10                 // immutable
let mut y = 5              // mutable
y = y + 1

// control flow
if x > 5 { println("big") } else { println("small") }
while y < 10 { y = y + 1 }
for i in range(0, 10) { println(i) }

// pipelines (left → right)
let squared = [1, 2, 3] |> map(fn(x) { x * x }) |> sum()

// async
async fn fetch_all(urls: list) {
    let results = await gather(urls |> map(http_get))
    return results
}

// pattern matching
match result {
    Ok(v)  => println(v),
    Err(e) => println("failed: " + str(e))
}
```

---

## Stdlib by lane

### ◉ Observability

| Module              | What it ships                                          |
|---------------------|--------------------------------------------------------|
| `prometheus`        | text-format emitter + scrape parser                   |
| `influx_line`       | InfluxDB line protocol encode/decode                  |
| `statsd`            | counters, gauges, timers, histograms (DogStatsD tags) |
| `logfmt`            | Heroku/go-kit encoder + quoted-string parser          |
| `opentelemetry`     | OTLP/JSON traces, metrics, logs                       |
| `syslog` / `cef` / `leef` | SIEM wire formats                               |

### ◉ Analytics / Columnar

| Module               | What it ships                                         |
|----------------------|-------------------------------------------------------|
| `parquet`            | PAR1 magic, Thrift compact, data page v1 headers      |
| `arrow_ipc`          | streaming frames, validity bitmaps, UTF-8 buffers     |
| `run_length`         | RLE pairs + Parquet-packed mode                       |
| `dict_encoding`      | order-preserving dict + index-width selector          |
| `frame_of_reference` | classic FOR + Gorilla delta-of-delta                  |
| `roaring`            | Roaring bitmaps (array + bitmap containers)           |
| `bitpack`            | bit-level pack/unpack helpers                         |
| `radix_sort`         | counting / u32 / u64 / i32 / string radix sorts       |

### ◉ Hashes & Codecs

| Module    | What it ships                                              |
|-----------|------------------------------------------------------------|
| `xxhash`  | XXH64 byte-identical to Cyan4973 + FNV-1a-64               |
| `lz4`     | LZ4 block format compress + decompress                     |
| `crc`     | CRC-32 / CRC-8 with configurable polynomial                |
| `compress`| gzip / deflate                                             |
| `base64`  | Base64 / Base32 / hex                                      |

### ◉ Crypto / Secure Channel

| Module      | What it ships                                         |
|-------------|-------------------------------------------------------|
| `blake2s`   | RFC 7693 with full IV + SIGMA tables                  |
| `chacha20`  | RFC 8439 block + streaming XOR                        |
| `poly1305`  | RFC 8439 one-time MAC, constant-time verify           |
| `x25519`    | RFC 7748 Montgomery-ladder DH                         |
| `hkdf`      | RFC 5869 extract + expand + derive_key                |
| `crypto`    | SHA-256, HMAC, AES, Ed25519 pubkey ops                |
| `argon2`    | Argon2id password hashing                             |
| `jwt`       | JWS sign + verify (HS256 / RS256 / EdDSA)             |
| `totp`      | TOTP / HOTP RFC 6238                                  |
| `webauthn`  | WebAuthn ceremony primitives                          |
| `tls`       | TLS record layer                                      |

### ◉ Search / Approximate Matching

| Module          | What it ships                                       |
|-----------------|-----------------------------------------------------|
| `suffix_array`  | prefix-doubling SA + Kasai LCP + binary search      |
| `aho_corasick`  | goto/fail/output automaton, multi-pattern `find_all`|
| `levenshtein`   | Wagner-Fischer + bounded + Damerau                  |
| `simhash`       | 64-bit SimHash + hamming + near-duplicate           |
| `qgram`         | q-gram inverted index + Jaccard + ranked `query`    |
| `trie`          | prefix trie with longest-prefix match               |
| `regex`         | classic regex with capture groups                   |

### ◉ Networking / Protocols

| Module        | What it ships                                         |
|---------------|-------------------------------------------------------|
| `http`        | client + server with streaming                        |
| `dns`         | resolver with A / AAAA / MX / TXT                     |
| `tcp` / `udp` | socket primitives                                     |
| `ip`          | v4 + v6 address parsing / CIDR                        |
| `dhcp`        | client + server                                       |
| `websocket`   | RFC 6455 framing                                      |
| `smtp`        | mail client                                           |

### ◉ Data / Formats

| Module        | What it ships                                         |
|---------------|-------------------------------------------------------|
| `json`        | parse + emit with streaming                           |
| `toml`        | read + write                                          |
| `yaml`        | read + write                                          |
| `csv`         | RFC 4180 with quoting                                 |
| `sqlite`      | embedded SQL driver                                   |
| `xml`         | DOM parser                                            |
| `markdown`    | CommonMark renderer                                   |

### ◉ Concurrency / Runtime

| Module           | What it ships                                      |
|------------------|----------------------------------------------------|
| `async_task`     | futures, `gather`, `timeout`                       |
| `channel`        | MPMC channels + `select`                           |
| `nursery`        | structured concurrency scopes                      |
| `actor`          | actor mailboxes                                    |
| `bloom`          | Bloom filters                                      |
| `consistent_hash`| consistent hashing for shard routing               |
| `rope`           | balanced rope for O(log n) string edits            |

---

## CLI cheatsheet

```sh
lateralus run file.ltl           # tree-walking interpreter
lateralus c file.ltl -o out.c    # transpile to C99
lateralus py file.ltl            # transpile to Python 3
lateralus js file.ltl            # transpile to JavaScript
lateralus wasm file.ltl          # compile to WAT
lateralus check file.ltl         # type-check only
lateralus test file.ltl          # run @test functions
lateralus verify file.ltl        # run @law property tests
lateralus bench file.ltl         # benchmark @bench functions
lateralus fmt file.ltl           # auto-format
lateralus lint file.ltl          # lint
lateralus lsp                    # start LSP server
lateralus dap                    # start debug adapter
lateralus repl                   # interactive REPL
```

---

## Five-line recipes

**Hash a file with xxHash**
```lateralus
import xxhash
let h = xxhash_hash64(read_file_bytes("/etc/passwd"))
println(hex(h))
```

**Compress + encrypt a rollup**
```lateralus
import lz4
import chacha20
let zipped  = lz4_compress(payload)
let sealed  = chacha20_xor(key, nonce, 1, zipped)
```

**Scrape + filter Prometheus**
```lateralus
import prometheus
import aho_corasick
let rules   = aho_corasick_build(["error", "panic"])
let alerts  = prometheus_parse(scrape)
              |> filter(fn(m) { aho_corasick_contains_any(rules, m.name) })
```

**DH handshake**
```lateralus
import x25519
import hkdf
let shared = x25519_scalar_mult(my_sk, peer_pk)
let key    = hkdf_derive_key(salt, shared, bytes_of("session"), 32)
```

**Fuzzy search a corpus**
```lateralus
import qgram
import levenshtein
let idx     = qgram_build_index(docs, 3)
let cands   = qgram_query(idx, query_str, 3)
let best    = cands |> take(5)
              |> map(fn(d) { [d[0], levenshtein_bounded(query_str, docs[d[0]], 50)] })
```

---

## More

- Compare stdlib coverage: <https://lateralus.dev/compare/>
- Read the lane deep-dives: <https://lateralus.dev/blog/>
- Open a bounty: <https://github.com/bad-antics/lateralus-lang/blob/main/BOUNTIES.md>
- Star the repo: <https://github.com/bad-antics/lateralus-lang>
