# Binary Frames with `stdlib/amqp.ltl`

AMQP 0-9-1 — the protocol under RabbitMQ — is a binary protocol built
from a small set of big-endian primitives wrapped in a uniform frame
envelope. `stdlib/amqp.ltl` implements that wire layer in ~180 lines:
integer and string encoders, a 7-byte frame header, a truncation-safe
parser, handshake method builders, and a one-call `publish_frames`
that emits the three-frame publish sequence.

This tutorial walks the byte layout end to end. Companion:
`examples/amqp_tutorial.ltl`.

---

## Everything is a byte list

The codec represents wire data as `list` of ints (0–255), concatenated
with `+`. Strings travel as `shortstr` (1-byte length + bytes) or
`longstr` (4-byte length + bytes) — the two string types AMQP uses
everywhere.

```text
enc_u8 / u16 / u32 / u64     big-endian, fixed width
dec_u8 / u16 / u32           return [value, next_index] pairs
enc_short_str("amq.direct")  -> [10, 'a','m','q','.','d',...]
enc_long_str                  -> u32 length prefix + bytes
```

## The frame envelope

Every AMQP frame is:

```text
type u8 | channel u16 | payload-size u32 | payload | 0xCE
```

- `type`: 1 = method, 2 = header, 3 = body, 8 = heartbeat, 0 = end
- `channel`: which channel the frame belongs to (0 = connection-level)
- `payload-size`: lets the parser skip without understanding content
- `0xCE`: frame-end octet — not part of the payload

`parse_frame(buf, i)` returns `{type, channel, payload, consumed}` or
`nil` when the buffer is short or the end octet is wrong — the same
truncation-safe contract as the RESP codec.

## Handshake methods

Connection setup is just method frames whose payload starts with
`class-id u16 | method-id u16`. The module ships builders for the
common sequence:

- `connection_start_ok` — client properties table + SASL mechanism +
  response + locale
- `plain_auth` — the `PLAIN` SASL response `\0user\0pass`
- `connection_tune_ok` — channel-max / frame-max / heartbeat
- `connection_open` — vhost + reserved fields

`protocol_header()` emits the literal `AMQP\x00\x00\x09\x01` the
client must send before anything else — version 0-9-1.

## Publishing: three frames, one call

A publish is never one frame — it's a **method** (Basic.Publish with
exchange, routing key, and flags), a **header** (class id, weight,
body size as u64, property flags), then the **body** frame. RabbitMQ
uses the header's body-size to know when the body has fully arrived.

```text
publish_frames(chan, exch, rk, mandatory, immediate, body)
  -> method + header + body  (concatenated byte lists)
```

`mandatory`/`immediate` map to flag bits `0x01`/`0x02` in the method
args.

## Running the companion

```text
STEP 1 protocol header:  hex=414d515000000901
STEP 3 frame envelope:   hex=01000100000005000a0028ffce
                         parse consumed=13, truncated -> True
STEP 4 handshake:        PLAIN auth=006775657374006775657374
STEP 5 publish triple:   total=72 bytes; method/header/body parsed
                         back out frame-by-frame
```

`tests/test_amqp_tutorial.py` pins every byte string — protocol
header, frame envelope, PLAIN auth, tune-ok, and the full publish
triple — so any codec regression fails loudly.

## When to use it

**Use it** to speak AMQP 0-9-1 to RabbitMQ or build a frame-level
proxy/inspector. The byte-list representation makes it easy to unit
test without sockets.

**Don't expect** TLS, connection/channel state machines, consumer
tag bookkeeping, or message property flags beyond the defaults — the
module is the wire codec, not a client. Heartbeat *scheduling* and
reconnection policy are application concerns.

That is `stdlib/amqp.ltl`: primitives in, frames out — parseable,
truncation-safe, and byte-exact.
