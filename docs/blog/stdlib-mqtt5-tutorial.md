# MQTT 5.0 Packets with `stdlib/mqtt5.ltl`

MQTT is the lightweight pub/sub protocol of IoT — and version 5 added
a proper property system on top of the classic fixed-header /
variable-header / payload layout. `stdlib/mqtt5.ltl` implements the
wire codec: remaining-length varints, u16-length UTF-8 strings,
property encoders, packet builders, and a frame parser — all as byte
lists, ~220 lines.

This tutorial decodes the byte layout packet by packet. Companion:
`examples/mqtt5_tutorial.ltl`.

---

## The frame shape

```text
fixed header:  packet_type(4b) | flags(4b) | remaining_length(varint)
body:          variable header + payload
```

The first byte packs type in the high nibble and type-specific flags
in the low nibble (`0x32` = PUBLISH, QoS 1). `remaining_length` is an
MQTT-specific base-128 varint — **different from protobuf's**: each
byte contributes `7 bits × 128^position`, little-endian groups, up to
4 bytes (268,435,455 max).

`enc_varint`/`dec_varint` handle it — `128 → 80 01`, `16383 → ff 7f`,
`2097151 → ff ff 7f`. `parse_packet` returns
`{type, flags, remaining, body, consumed}` or `nil` on truncation.

## Strings, binaries, properties

- `enc_utf8` — u16 length + bytes (MQTT strings are **not**
  NUL-terminated and must be valid UTF-8)
- `enc_binary` — same framing for opaque payloads
- Property encoders `prop_u8/u16/u32/utf8/binary/user` emit
  `property_id(varint) + value`; `prop_user` packs a key/value pair
  for user properties (id `0x26`)
- `props_block` prefixes the concatenated property bytes with their
  total length as a varint — pass it a **flat byte list**

## Packet builders

- **`connect(client_id, keepalive, clean_start, username, password,
  props)`** — protocol name `"MQTT"` + level `5`, connect flags
  (clean-start `0x02`, will `0x04/0x08`, password `0x40`, username
  `0x80`), keepalive, properties, then client-id/username/password
  payload
- **`publish(topic, qos, retain, dup, packet_id, props, body)`** —
  flags encode dup(`0x08`) | qos(`0x02`/`0x04`) | retain(`0x01`);
  packet id only present when qos > 0
- **`subscribe(packet_id, filters)`** — filters are
  `[topic_filter, options_byte]` pairs; fixed-header flags must be
  `0x02`
- **`pingreq`/`pingresp`** — two bytes each (`c0 00` / `d0 00`)
- **`disconnect(reason_code)`** — reason byte + empty properties

## Verified output

```text
CONNECT  = 10 2b 0004"MQTT" 05 c2 003c <props> <payload>
PUBLISH  = 32 2a <topic> <pid=42> <props> "21.5"     (QoS1, flags=0x32)
SUBSCRIBE= 82 1c 0007 <props> <filters>             (flags=0x02)
PINGREQ  = c0 00
DISCONNECT= e0 02 00 00
```

`tests/test_mqtt5_tutorial.py` pins every byte string; STEP 7 parses
a ping+publish concatenation back frame-by-frame.

## When to use it

**Use it** for MQTT 5 clients/bridges/gateways — the codec is complete
for the common packets; QoS flows and will messages are application
logic on top.

**Don't expect** the broker, session state, QoS retransmission, or
MQTT 3.1.1 dialect — this is the v5 wire format only. Will-message
flags exist in CONNECT but the module doesn't build will properties.

That is `stdlib/mqtt5.ltl`: bytes in, packets out — the MQTT 5 wire
format, nothing hidden.
