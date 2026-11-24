# MessagePack Serialization and Deserialization with `stdlib.msgpack`

The `stdlib.msgpack` module provides binary object serialization and deserialization conforming to the [MessagePack specification](https://msgpack.org). MessagePack delivers compact binary encoding for structured data (integers, strings, booleans, nil, lists, and maps), achieving significantly smaller payload sizes and faster parsing overhead than equivalent JSON text representations.

---

## 1. Core Primitives

The module exposes two primary functions:

```lateralus
pub fn encode(v) -> list
pub fn decode(b: list) -> list
```

- **`encode(v)`**: Serializes any supported Lateralus primitive or composite data structure into a byte array (represented as a list of integers `0` through `255`).
- **`decode(b)`**: Deserializes a MessagePack byte stream into its original Lateralus representation. Returns a tuple `[value, next_index]`, allowing sequential extraction of multiple serialized frames from a continuous buffer.

---

## 2. Canonical Type Mappings and Pinned Vectors

`stdlib.msgpack` encodes types using canonical MessagePack prefix tags:

| Lateralus Type | Condition / Value Range | MessagePack Tag / Format | Canonical Encoded Bytes |
| :--- | :--- | :--- | :--- |
| **`nil`** | `nil` | `0xc0` (nil format) | `[0xc0]` |
| **`bool`** | `false` | `0xc2` (false format) | `[0xc2]` |
| **`bool`** | `true` | `0xc3` (true format) | `[0xc3]` |
| **`int`** (positive fixint) | `0 <= n < 128` | `0x00 - 0x7f` | `42` → `[0x2a]` |
| **`int`** (negative fixint) | `-32 <= n < 0` | `0xe0 - 0xff` | `-10` → `[0xf6]` |
| **`int`** (uint8) | `128 <= n < 256` | `0xcc [val]` | `200` → `[0xcc, 200]` |
| **`int`** (uint16) | `256 <= n < 65536` | `0xcd [msb, lsb]` | `1000` → `[0xcd, 3, 232]` |
| **`str`** (fixstr) | `len < 32` | `0xa0 | len` + ASCII/UTF-8 | `"hello"` → `[0xa5, 104, 101, 108, 108, 111]` |
| **`list`** (fixarray) | `len < 16` | `0x90 | len` + items | `[1, 2, 3]` → `[0x93, 1, 2, 3]` |
| **`map`** (fixmap) | `len < 16` | `0x80 | len` + key/val pairs | `{ a: 1 }` → `[0x81, 0xa1, 97, 1]` |

---

## 3. Practical Example: Network Telemetry Frame

```lateralus
import msgpack

fn main() {
    // Construct a structured telemetry packet
    let payload = {
        sensor: "accelerometer",
        status: true,
        readings: [10, -5, 42]
    }

    // Binary serialization
    let wire_bytes = msgpack.encode(payload)
    println("Serialized bytes length: " + str(len(wire_bytes)))

    // Binary deserialization
    let unpacked = msgpack.decode(wire_bytes)
    let message = unpacked[0]
    let next_offset = unpacked[1]

    println("Deserialized sensor: " + message["sensor"])
    println("Deserialized status: " + str(message["status"]))
}
```

---

## 4. Multi-Frame Stream Decoding

When reading concatenated binary frames from a socket or message queue, `decode_at` enables zero-copy offset progression:

```lateralus
let buffer = msgpack.encode(1) + msgpack.encode(2) + msgpack.encode(3)

let offset = 0
let results = []
while offset < len(buffer) {
    let pair = msgpack.decode_at(buffer, offset)
    results = results + [pair[0]]
    offset = pair[1]
}
// results == [1, 2, 3]
```
