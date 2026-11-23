# Apache Kafka Binary Wire Protocol: Invariants, ZigZag Varints, and Header v2 Codecs in Lateralus

## 1. Introduction & Theoretical Foundations

In high-throughput distributed event streaming architectures, Apache Kafka operates over custom TCP binary wire protocols engineered for minimal serialization overhead, high-bandwidth pipelining, and forward/backward version compatibility. Unlike text-based protocols (such as JSON or REST) or generic RPC frameworks with dynamic reflection overhead, the Kafka protocol relies on compact, strictly typed, big-endian binary frames.

A Kafka connection exchanges discrete request and response messages. Every interaction follows an asynchronous request/response cycle:
1. The client establishes a persistent TCP socket to a broker.
2. The client transmits one or more framed request packets, each tagged with a unique 32-bit `correlation_id`.
3. The broker replies asynchronously with matching `correlation_id` response frames, allowing full bidirectional pipelining over a single connection without head-of-line blocking.

With the advent of KIP-482 (*The Tagged Fields & Flexible Protocol Architecture*), Kafka introduced Header v2 and compact data structures, drastically shrinking metadata bandwidth. Lateralus provides a native implementation of these wire primitives in `stdlib/kafka_wire.ltl`.

---

## 2. Primitive Type System & Serialization Invariants

### Fixed-Width Big-Endian Integers
All standard numeric fields in Kafka are transmitted in network byte order (Big-Endian / Most-Significant Byte first):
- **`INT8`**: 1-byte signed integer $[-128, 127]$.
- **`INT16`**: 2-byte big-endian signed integer $[-32768, 32767]$.
- **`INT32`**: 4-byte big-endian signed integer $[-2^{31}, 2^{31}-1]$.
- **`INT64`**: 8-byte big-endian signed integer $[-2^{63}, 2^{63}-1]$.

Lateralus encodes these primitives through explicit bit-shift sequences, guaranteeing consistent behavior across architectures:
```lateralus
pub fn enc_i16(v: int) -> list {
    return [(v >> 8) & 0xff, v & 0xff]
}

pub fn enc_i32(v: int) -> list {
    return [(v >> 24) & 0xff, (v >> 16) & 0xff,
            (v >> 8)  & 0xff,  v        & 0xff]
}
```

---

### Variable-Length Integers & ZigZag Encoding
Fixed 32-bit or 64-bit integers waste bytes when storing small quantities (such as array lengths, partition counts, or small timestamps). Kafka adopts variable-length integer encoding (LEB128):
- Each byte uses the 7 lowest bits to store data.
- The 8th bit (MSB, `0x80`) serves as a continuation flag: `1` indicates more bytes follow, while `0` terminates the integer.

#### The Negative Integer Problem
Under standard two's complement, small negative numbers like $-1$ (`0xFFFFFFFF`) have leading ones across all bits, requiring 5 bytes for 32-bit integers or 10 bytes for 64-bit integers.

#### ZigZag Mapping Solution
To compress small positive and negative values with equal efficiency, Kafka utilizes **ZigZag encoding** (adapted from Google Protocol Buffers), mapping signed integers onto unsigned integers such that numbers with small absolute magnitudes correspond to small positive values:
$$Z(n) = \begin{cases} 2n & \text{if } n \ge 0 \\ 2|n| - 1 & \text{if } n < 0 \end{cases}$$

| Signed Integer $n$ | ZigZag Encoded $Z(n)$ | Binary $Z(n)$ | Encoded Varint Bytes |
| :---: | :---: | :---: | :---: |
| $0$ | $0$ | `0000 0000` | 1 byte (`0x00`) |
| $-1$ | $1$ | `0000 0001` | 1 byte (`0x01`) |
| $1$ | $2$ | `0000 0010` | 1 byte (`0x02`) |
| $-2$ | $3$ | `0000 0011` | 1 byte (`0x03`) |
| $2$ | $4$ | `0000 0100` | 1 byte (`0x04`) |

Lateralus implements ZigZag encoding and inverse decoding with pure arithmetic:
```lateralus
pub fn zz_encode(n: int) -> int {
    if n >= 0 { return n << 1 }
    return ((0 - n) << 1) - 1
}

pub fn zz_decode(n: int) -> int {
    let low_bit = n & 1
    let half = n >> 1
    if low_bit == 0 { return half }
    return 0 - (half + 1)
}
```

---

### String Formats: Classic vs Compact

1. **`NULLABLE_STRING` (Classic)**:
   - Prepends a 2-byte signed `INT16` length $L$.
   - If $L = -1$, represents `nil` (`[0xff, 0xff]`).
   - If $L \ge 0$, followed by $L$ UTF-8 bytes.
2. **`COMPACT_STRING` (Flexible Version)**:
   - Prepends an unsigned varint with value $L + 1$.
   - Value $0$ represents `nil`.
   - Value $N > 0$ represents a string of length $N - 1$, followed by $N - 1$ UTF-8 bytes.
   - Saves 1 byte on strings under 127 bytes, significantly reducing metadata request footprints.

---

## 3. Frame Envelopes & Header Structures

Every Kafka TCP transmission is wrapped in a 4-byte big-endian framing envelope:
$$\text{Packet} = \text{INT32}(\text{length}) \mathbin{\Vert} \text{Payload}$$

### Request Header v1 (Legacy)
Used by pre-flexible API versions:
$$\text{Header v1} = \text{api\_key} (\text{i16}) \mathbin{\Vert} \text{api\_version} (\text{i16}) \mathbin{\Vert} \text{correlation\_id} (\text{i32}) \mathbin{\Vert} \text{client\_id} (\text{string})$$

### Request Header v2 (Flexible)
Adopted for modern API versions (e.g., Metadata v9+, Produce v9+):
$$\text{Header v2} = \text{Header v1} \mathbin{\Vert} \text{tagged\_fields\_count} (\text{uvarint})$$
In standard requests without custom experimental tags, `tagged_fields_count` is written as `0x00`.

---

## 4. Lateralus `stdlib/kafka_wire.ltl` API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `enc_i8 / enc_i16 / enc_i32 / enc_i64` | `(int) -> list` | Encodes fixed-width big-endian integers into byte arrays. |
| `dec_i8 / dec_i16 / dec_i32 / dec_i64` | `(list, int) -> list` | Decodes integer from buffer at offset, returning `[value, next_offset]`. |
| `enc_varint / dec_varint` | `(int) -> list` | Encodes/decodes signed integers using ZigZag + LEB128 varints. |
| `enc_string / dec_string` | `(str) -> list` | Encodes/decodes classic INT16 length-prefixed strings. |
| `enc_compact_string / dec_compact_string` | `(str) -> list` | Encodes/decodes modern flexible COMPACT_STRING (len+1 varint prefixed). |
| `request_header_v1` | `(int, int, int, str) -> list` | Constructs legacy Request Header v1. |
| `request_header_v2` | `(int, int, int, str) -> list` | Constructs flexible Request Header v2 (terminates with tagged fields `0x00`). |
| `frame_request(body)` | `(list) -> list` | Prepends 4-byte big-endian size prefix to packet body. |
| `parse_response_frame(buf, i)` | `(list, int) -> list` | Extracts length, correlation ID, body bytes, and next offset. |

---

## 5. Practical Implementation & Verification

### Executing the Runnable Example
An end-to-end Kafka protocol framing and response demultiplexing script is provided in `examples/kafka_wire_tutorial.ltl`:
```shell
$ python -m lateralus_lang check examples/kafka_wire_tutorial.ltl
✓ examples/kafka_wire_tutorial.ltl: OK
```

The example demonstrates:
- Composing a Header v2 `API_METADATA` request packet with client identifier `"lateralus-analytics-worker"`.
- Serializing compact topic query arrays.
- Framing the wire payload with 4-byte big-endian length headers.
- Simulating broker responses and validating `correlation_id` matching.
- Demonstrating ZigZag varint space savings.

### Pinned Golden Test Vectors
The companion test suite `tests/stdlib_kafka_wire_tutorial.ltl` verifies:
- Big-endian byte alignment across INT8..INT64.
- Exact ZigZag arithmetic mapping ($0 \to 0, -1 \to 1, 1 \to 2, -2 \to 3$).
- Classic vs compact string round-trip parity and null representation.
- Header v1 and Header v2 structure lengths.
- Response frame extraction and correlation ID parsing.

Validate the test suite with the Lateralus compiler:
```shell
$ python -m lateralus_lang check tests/stdlib_kafka_wire_tutorial.ltl
✓ tests/stdlib_kafka_wire_tutorial.ltl: OK
```
