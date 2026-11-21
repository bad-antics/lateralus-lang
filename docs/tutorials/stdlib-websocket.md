# RFC 6455 WebSocket Codec Tutorial (`stdlib/websocket`)

The `stdlib/websocket` module provides a pure-Lateralus codec implementing the frame framing, payload masking, status code negotiation, and opening handshake verification mandated by [RFC 6455 (The WebSocket Protocol)](https://datatracker.ietf.org/doc/html/rfc6455).

---

## 1. Frame Architecture and Opcodes

WebSocket frames consist of a 1-byte header indicating fragment status (`FIN`) and opcode, a payload length descriptor (1 to 9 bytes), an optional 4-byte masking key, and the raw payload:

| Opcode | Constant | Description |
|---|---|---|
| `0x0` | `op_continuation()` | Fragmented message continuation |
| `0x1` | `op_text()` | UTF-8 encoded text payload |
| `0x2` | `op_binary()` | Arbitrary binary data payload |
| `0x8` | `op_close()` | Connection close handshake |
| `0x9` | `op_ping()` | Heartbeat ping frame |
| `0xA` | `op_pong()` | Heartbeat pong frame |

---

## 2. Server-to-Client Frame Encoding

Server-to-client frames are unmasked:

```lateralus
import stdlib.websocket

let text = "Hello, client!"
let payload = bytes_of(text)

// Encode unmasked text frame (fin = 1, opcode = op_text())
let frame = encode_frame(1, op_text(), payload)
let decoded = decode_frame(frame)

// decoded["fin"] == 1
// decoded["opcode"] == 1
// decoded["payload"] == payload
```

---

## 3. Extended Length Tiers

RFC 6455 accommodates variable payloads through three length tiers:
1. **$\le$ 125 bytes**: Encoded directly into 7 bits of the second header byte.
2. **126 to 65,535 bytes**: Indicator `126` followed by a 16-bit unsigned big-endian integer (`n >> 8`, `n & 255`).
3. **$\ge$ 65,536 bytes**: Indicator `127` followed by a 64-bit unsigned big-endian integer.

```lateralus
// Medium frame with extended 16-bit header
let payload = [65; 300] // 300 bytes
let frame = encode_frame(1, op_binary(), payload)
// Header contains [0x82, 126, 1, 44] (300 == 0x012C)
```

---

## 4. Client-to-Server Masking

All frames transmitted from client to server must be masked using a pseudo-random 4-byte masking key. The payload is transformed byte-by-byte via:

$$j = i \pmod 4, \quad \text{transformed}[i] = \text{payload}[i] \oplus \text{mask}[j]$$

```lateralus
let mask = [0x12, 0x34, 0x56, 0x78]
let frame = encode_masked(1, op_text(), payload, mask)
let decoded = decode_frame(frame)
// decode_frame automatically detects the mask bit and unmasks payload
```

---

## 5. Close Frames and Handshake Verification

### Close Handshake
Close frames (`0x8`) contain a 2-byte big-endian status code (e.g. `1000` for Normal Closure, `1001` for Going Away) followed by an optional human-readable UTF-8 reason string:

```lateralus
let frame = close_frame(1000, "Normal Closure")
let decoded = decode_frame(frame)
let code = (decoded["payload"][0] << 8) | decoded["payload"][1]
```

### Sec-WebSocket-Accept Handshake
During the HTTP Upgrade opening handshake, the server must compute `Sec-WebSocket-Accept` from the client's `Sec-WebSocket-Key` by appending the canonical GUID `"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"`, hashing with SHA-1, and base64-encoding the digest:

```lateralus
let key = "dGhlIHNhbXBsZSBub25jZQ=="
let accept = compute_accept(key)
// accept == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=" (RFC 6455 §1.3 test vector)
```

---

## Running the Example & Tests

Run the interactive tutorial example:
```bash
lateralus run examples/websocket_tutorial.ltl
```

Run test suite:
```bash
pytest tests/test_websocket_tutorial.py -v
```
