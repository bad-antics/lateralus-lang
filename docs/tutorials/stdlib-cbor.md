# Concise Binary Object Representation (CBOR) with `stdlib.cbor`

The `stdlib.cbor` module provides high-performance binary object serialization and deserialization conforming strictly to [RFC 8949 (Concise Binary Object Representation)](https://www.rfc-editor.org/rfc/rfc8949.html). CBOR is widely utilized across constrained nodes, Internet of Things (IoT) protocols (such as CoAP), hardware wallets, and WebAuthn authenticators due to its compact binary footprint and extensible type system.

---

## 1. Major Types Architecture

CBOR structures data into 8 major types encoded in the top 3 bits of each initial byte (`mt = byte / 32`):

| Major Type | Name | Purpose | Range / Representation |
| :---: | :--- | :--- | :--- |
| **0** | **Unsigned Integer** | Non-negative integers | `[0 .. 2^64-1]` |
| **1** | **Negative Integer** | Negative values stored as $-1 - n$ | `[-1 .. -2^64]` |
| **2** | **Byte String** | Raw byte payloads | `[bytes]` |
| **3** | **Text String** | Valid UTF-8 string data | `"..."` |
| **4** | **Array** | Ordered sequences of values | `[...]` |
| **5** | **Map** | Key-value pairs | `{ ... }` |
| **6** | **Semantic Tag** | Tags modifying subsequent items | Pass-through |
| **7** | **Simple Values & Floats** | Booleans (`0xf4`/`0xf5`), nil (`0xf6`) | `false`, `true`, `nil` |

---

## 2. Canonical RFC 8949 Pinned Test Vectors

`stdlib.cbor` implements exact canonical shortest-form encoding. The table below lists standard vectors verified against RFC 8949 Appendix A:

| Lateralus Value | CBOR Hex Bytes | Decimal Bytes | Specification Rule |
| :--- | :--- | :--- | :--- |
| **`0`** | `0x00` | `[0]` | Single-byte uint (value < 24) |
| **`1`** | `0x01` | `[1]` | Single-byte uint |
| **`10`** | `0x0a` | `[10]` | Single-byte uint |
| **`23`** | `0x17` | `[23]` | Maximum direct 5-bit integer |
| **`24`** | `0x18 0x18` | `[24, 24]` | 1-byte uint8 prefix (`0x18`) |
| **`100`** | `0x18 0x64` | `[24, 100]` | 1-byte uint8 |
| **`1000`** | `0x19 0x03 0xe8` | `[25, 3, 232]` | 2-byte uint16 prefix (`0x19`) |
| **`-1`** | `0x20` | `[32]` | Negative int: major type 1 with $n = 0$ |
| **`-10`** | `0x29` | `[41]` | Negative int: major type 1 with $n = 9$ |
| **`-100`** | `0x38 0x63` | `[56, 99]` | Negative uint8: $-1 - 99 = -100$ |
| **`false`** | `0xf4` | `[244]` | Simple value 20 |
| **`true`** | `0xf5` | `[245]` | Simple value 21 |
| **`nil`** | `0xf6` | `[246]` | Simple value 22 (null) |
| **`"hello"`** | `0x65 0x68 0x65 0x6c 0x6c 0x6f` | `[101, 104, 101, 108, 108, 111]` | Major type 3 (0x60) + length 5 |
| **`[1, 2, 3]`** | `0x83 0x01 0x02 0x03` | `[131, 1, 2, 3]` | Major type 4 (0x80) + length 3 |
| **`{ a: 1 }`** | `0xa1 0x61 0x61 0x01` | `[161, 97, 97, 1]` | Major type 5 (0xa0) + 1 pair |

---

## 3. Practical Usage & Network Protocol Example

```lateralus
import cbor

fn main() {
    // 1. Construct IoT sensor packet
    let packet = {
        node_id: 1042,
        active: true,
        temp_c: 24,
        metrics: [120, -5, 0]
    }

    // 2. Binary serialization
    let payload = cbor.encode(packet)
    println("Serialized CBOR payload length: " + str(len(payload)))

    // 3. Binary deserialization
    let restored = cbor.decode(payload)
    println("Node ID: " + str(restored["node_id"]))
    println("Status: " + str(restored["active"]))
}
```

---

## 4. Multi-Message Stream Decoding

For continuous wire streams or fragmented buffer reads:

```lateralus
let stream = cbor.encode(10) + cbor.encode("sensor") + cbor.encode(false)

let offset = 0
let messages = []
while offset < len(stream) {
    let pair = cbor.decode_at(stream, offset)
    messages = messages + [pair[0]]
    offset = pair[1]
}
// messages == [10, "sensor", false]
```
