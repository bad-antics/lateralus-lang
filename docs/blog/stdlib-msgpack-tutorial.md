# High-Performance Binary Serialization with Lateralus `stdlib/msgpack.ltl`

In high-frequency distributed systems, game backends, telemetry agents, and microservice RPCs, serialization overhead directly impacts latency and network bandwidth. While JSON is human-readable, parsing strings into numerical types consumes CPU cycles, and quotation marks and delimiters introduce significant wire bloat.

**MessagePack** is an efficient binary serialization format that preserves the flexibility of JSON with the speed and footprint of binary protocols. Lateralus ships with a pure standard library implementation in `stdlib/msgpack.ltl`.

---

## 1. Wire Format Architecture & Tag Economy

MessagePack assigns type metadata and length headers directly into single-byte tags whenever possible:

### Fixint (Single-Byte Numbers)
- **Positive Fixint** ($0 \le n \le 127$): Stored as the raw 7-bit byte (`0x00` to `0x7f`). No type prefix is required.
- **Negative Fixint** ($-32 \le n \le -1$): Stored as `0xe0 | (n & 0x1f)`.

### Larger Numbers
When numbers exceed 127, MessagePack dynamically promotes to typed byte widths:
- `uint8` (`0xcc`, followed by 1 byte)
- `uint16` (`0xcd`, followed by 2 big-endian bytes)
- `uint32` (`0xce`, followed by 4 big-endian bytes)

### Fixed Containers
- `fixstr` (`0xa0` | length, up to 31 bytes)
- `fixarray` (`0x90` | count, up to 15 elements)
- `fixmap` (`0x80` | pair_count, up to 15 key-value pairs)

Because common field names, counts, and small integers fit inside single-byte tags, MessagePack payloads routinely achieve **30% to 60% compression** over uncompressed JSON.

---

## 2. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `msgpack_encode` | `(v: any) -> list` | Encodes integers, booleans, strings, lists, or maps into binary byte lists. |
| `msgpack_decode` | `(b: list) -> list` | Decodes the first item from offset 0, returning `[value, next_index]`. |
| `msgpack_decode_at` | `(b: list, i: int) -> list` | Decodes an item starting at offset `i` (for streaming TCP buffers). |

---

## 3. Practical Example: Telemetry Serialization

```lateralus
import msgpack

pub fn main() {
    let payload = {}
    payload["sensor"] = "temp_1"
    payload["active"] = true
    payload["history"] = [20, 22, 21]

    // Encode to binary list of byte integers
    let wire_bytes = msgpack_encode(payload)
    print("Encoded bytes length: " + str(len(wire_bytes)))

    // Decode back into native data structure
    let result = msgpack_decode(wire_bytes)
    let unpacked = result[0]
    let next_offset = result[1]

    print("Restored sensor name: " + unpacked["sensor"])
}
```

---

## 4. Multi-Message Streaming via `decode_at`

Network sockets deliver streams of bytes where multiple packets arrive in a single read. Because `msgpack_decode` returns `[value, next_index]`, parsing multiple concatenated objects in a continuous buffer requires zero memory slicing:

```lateralus
let offset = 0
while offset < len(buffer) {
    let res = msgpack_decode_at(buffer, offset)
    let item = res[0]
    offset = res[1]
    process_message(item)
}
```

---

## 5. Verification & Test Suite

The canonical test vectors in `tests/stdlib_msgpack_tutorial.ltl` verify:
1. Canonical wire tags (`nil=0xc0`, `false=0xc2`, `true=0xc3`, `u16=0xcd`).
2. Single-byte fixint packing and boundary handling.
3. Multi-level nested map and array reconstruction.

Verify locally:
```bash
python -m lateralus_lang check tests/stdlib_msgpack_tutorial.ltl
python -m lateralus_lang check examples/msgpack_tutorial.ltl
```
