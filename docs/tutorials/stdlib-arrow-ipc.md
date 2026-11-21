# Apache Arrow IPC Stream Framing Tutorial (`stdlib/arrow_ipc`)

The `stdlib/arrow_ipc` module implements columnar memory layouts and message encapsulation conforming to the [Apache Arrow Columnar IPC Stream Specification](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc).

It provides low-level primitive routines to:
1. Construct little-endian validity bitmaps indicating null vs valid elements.
2. Encode primitive integer columnar arrays (`buffer_i32`, `buffer_u8`).
3. Serialize variable-length string columns into contiguous monotonic offsets and UTF-8 payloads (`buffers_utf8`).
4. Encapsulate record batch messages with 8-byte alignment padding and `0xFFFFFFFF` continuation headers.
5. Signal end-of-stream (EOS) markers.

---

## 1. Validity Bitmaps

Arrow uses a bit-packed validity bitmap where each bit indicates whether an entry is valid (`1`) or null (`0`). The bits are stored in little-endian order within each byte:

```lateralus
import stdlib.arrow_ipc

// Element 0: valid, Element 1: null, Element 2: valid, ...
let flags = [true, false, true, true, false, false, true, false, true]
let bmp = validity_bitmap(flags)
// bmp[0] == 77 (0b01001101), bmp[1] == 1 (0b00000001)
// Padded to 8-byte alignment: [77, 1, 0, 0, 0, 0, 0, 0]
```

## 2. Int32 Columnar Buffers

Arrays of 32-bit signed integers are packed into little-endian bytes and aligned to 8-byte boundaries:

```lateralus
let numbers = [10, -20, 300, 4000]
let buf = buffer_i32(numbers)
// Encodes 4-byte little-endian integers with trailing padding
```

## 3. Variable-Length UTF-8 Strings

String arrays are represented by two buffers:
- An offsets buffer containing `N + 1` 32-bit integers defining slices into the data buffer.
- A raw UTF-8 byte data buffer.

```lateralus
let names = ["lateralus", "arrow", "ipc"]
let bufs = buffers_utf8(names)
let offsets = bufs[0]   // [0, 9, 14, 17] (i32 little-endian, padded)
let data = bufs[1]      // UTF-8 payload "lateralusarrowipc" (padded)
```

## 4. Message Framing and End-of-Stream

Each message in an Arrow IPC stream starts with an 8-byte header:
- `0xFFFFFFFF` (4-byte unsigned continuation marker)
- 32-bit metadata length (little-endian)
Followed by the 8-byte aligned metadata payload and 8-byte aligned body buffers.

```lateralus
let metadata = [1, 2, 3, 4]
let body = [10, 20, 30, 40, 50]
let message = frame_message(metadata, body)

let header = parse_frame_header(message, 0)
// header["metadata_len"] == 8 (padded)
// header["header_size"] == 8

// End-of-Stream marker (continuation + 0 length):
let eos = end_of_stream()
let eos_hdr = parse_frame_header(eos, 0)
// eos_hdr["metadata_len"] == 0
```

---

## Runnable Example & Test Suite

Run the full tutorial example:
```bash
lateralus run examples/arrow_ipc_tutorial.ltl
```

Run test suite:
```bash
pytest tests/test_arrow_ipc_tutorial.py -v
```
