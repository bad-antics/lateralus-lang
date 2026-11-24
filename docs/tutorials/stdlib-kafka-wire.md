# Mastering Kafka Binary Protocol Serialization with `stdlib.kafka_wire`

The `stdlib.kafka_wire` module provides low-level binary protocol encoders and decoders for Apache Kafka requests and responses. Designed according to the [Kafka Protocol Specification](https://kafka.apache.org/protocol.html), it enables building high-throughput event streaming clients, telemetry forwarders, and network proxies directly in Lateralus without external C or Java bindings.

---

## 1. Fixed-Width Integer Codecs

Kafka encodes primitive numerical types in network byte order (Big-Endian):

| Type | Encoder | Decoder | Range |
| :--- | :--- | :--- | :--- |
| **`INT8`** | `enc_i8(v)` | `dec_i8(buf, offset)` | `-128` to `127` |
| **`INT16`** | `enc_i16(v)` | `dec_i16(buf, offset)` | `-32,768` to `32,767` |
| **`INT32`** | `enc_i32(v)` | `dec_i32(buf, offset)` | `-2,147,483,648` to `2,147,483,647` |
| **`INT64`** | `enc_i64(v)` | `dec_i64(buf, offset)` | 64-bit signed integer |

Decoders return a 2-element tuple: `[decoded_value, next_offset]`.

```lateralus
import kafka_wire

let raw = kafka_wire.enc_i32(4096)
let result = kafka_wire.dec_i32(raw, 0)
let value = result[0]   // 4096
let next_i = result[1]  // 4
```

---

## 2. Compact Serialization: Varints & ZigZag

Flexible protocol versions (KIP-482) leverage unsigned varints and zig-zag encoded varints to minimize wire overhead:

- **`enc_uvarint(v)` / `dec_uvarint(buf, offset)`**: Unsigned variable-length integer (LEB128).
- **`zz_encode(n)` / `zz_decode(n)`**: Maps signed integers to positive domain (`0 -> 0, -1 -> 1, 1 -> 2, -2 -> 3`).
- **`enc_varint(v)` / `dec_varint(buf, offset)`**: Full zig-zag encoded varint.

```lateralus
let encoded = kafka_wire.enc_varint(-15)
let res = kafka_wire.dec_varint(encoded, 0)
// res[0] == -15
```

---

## 3. String & Byte Buffers

Kafka distinguishes between classic and compact (flexible) length prefixes:

- **Classic Strings**: Int16 length prefix (`-1` indicates `nil`).
- **Compact Strings**: Unsigned varint representing `length + 1` (`0` indicates `nil`).

```lateralus
// Classic string
let s_bytes = kafka_wire.enc_string("events.orders")
let s_decoded = kafka_wire.dec_string(s_bytes, 0)[0] // "events.orders"

// Nullable string
let null_bytes = kafka_wire.enc_nullable_string(nil)
let null_val = kafka_wire.dec_string(null_bytes, 0)[0] // nil

// Flexible compact string
let cs_bytes = kafka_wire.enc_compact_string("user-session")
let cs_val = kafka_wire.dec_compact_string(cs_bytes, 0)[0] // "user-session"
```

---

## 4. Request Headers & Message Framing

Every Kafka socket request is framed by a 4-byte big-endian length prefix followed by a versioned request header.

### Header Versions
- **`request_header_v1(api_key, api_version, correlation_id, client_id)`**: Pre-flexible header containing API key, version, tracking ID, and optional client name.
- **`request_header_v2(api_key, api_version, correlation_id, client_id)`**: Flexible header appending tagged field markers (KIP-482).

```lateralus
import kafka_wire

// Build an ApiVersions (key 18) request header
let header = kafka_wire.request_header_v2(
    kafka_wire.api_api_versions(),
    3,              // API version 3
    1001,           // Correlation ID
    "ingest-worker" // Client ID
)

// Frame complete packet with 4-byte payload length
let packet = kafka_wire.frame_request(header)
```

---

## 5. End-to-End Example: Response Frame Parsing

```lateralus
import kafka_wire

fn main() {
    let corr_id = 99
    let response_body = [0, 0, 0, 1] // simulated broker payload
    
    // Simulate broker wire packet: [length: i32][correlation_id: i32][body...]
    let raw_frame = kafka_wire.frame_request(
        kafka_wire.enc_i32(corr_id) + response_body
    )
    
    // Parse received packet
    let parsed = kafka_wire.parse_response_frame(raw_frame, 0)
    let rx_corr = parsed[0]
    let rx_body = parsed[1]
    
    if rx_corr == corr_id {
        println("Successfully matched broker response for correlation " + to_str(rx_corr))
    }
}
```
