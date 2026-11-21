# QUIC Wire Format with `stdlib/quic.ltl`

QUIC — Quick UDP Internet Connections — replaced TCP+TLS for HTTP/3.
Its packets are binary, self-describing at the frame layer, and built
on one unusual primitive: a variable-length integer that takes 1, 2, 4,
or 8 bytes depending on magnitude. `stdlib/quic.ltl` implements that
wire-format primer — the varint codec, header discrimination, and
long/short header field parsing — in about 135 lines. Cryptographic
packet protection is explicitly out of scope; this is the layer every
QUIC stack sits on top of.

This tutorial covers the varint encoding rules, the first-byte header
discrimination, the long-header field walk, the short-header DCID
problem, and the frame-type tags. Companion:
`examples/quic_tutorial.ltl`.

---

## The variable-length integer (RFC 9000 §16)

QUIC integers are big-endian with the length encoded in the top two
bits of the first byte:

| First-byte prefix | Total bytes | Max value |
|---|---|---|
| `00` | 1 | 63 |
| `01` | 2 | 16,383 |
| `10` | 4 | 1,073,741,823 |
| `11` | 8 | 2^62 − 1 |

The prefix bits are *not* part of the value — `enc_varint(64)` emits
`[0x40, 0x00]`, and `dec_varint` masks them off before accumulating.
Every length-prefixed field in QUIC — token length, packet length,
frame type, stream offset — uses this encoding, so it is the single
most-repeated codec in the protocol.

One implementation note: the tutorial inlines the codec with `>>`
shifts rather than `/` division, because Lateralus `/` produces a
float — the same reason `stdlib/amqp.ltl` encodes its integers with
shifts.

## First-byte header discrimination

Every QUIC packet opens with a first byte whose top bits answer three
questions at once:

- **Bit 7 — header form.** `1` = long header (Initial, 0-RTT,
  Handshake, Retry — everything before keys are established);
  `0` = short header (1-RTT, the steady state).
- **Bit 6 — fixed bit.** Always `1` in QUIC v1; greasing may flip it
  in later versions, which is why the module exposes `fixed_bit`
  instead of assuming it.
- **Bits 5..4 — packet type** (long headers only): 0=Initial,
  1=0-RTT, 2=Handshake, 3=Retry. On short headers these bits are
  repurposed as the spin bit and reserved/key-phase flags.

`header_form`, `fixed_bit`, and `long_packet_type` are pure bit
extractors — the whole discrimination layer is three shifts.

## The long-header field walk

`parse_long_header` walks a byte buffer and returns a map:

```text
{type, version, dcid, scid, token, length, payload_offset}
```

The layout is fixed-order: first byte, 4-byte version, DCID length +
DCID, SCID length + SCID, then — *only for Initial packets* — a
varint-length token, then the varint packet `length`, and finally the
protected payload. `payload_offset` is where the packet-number and
frame bytes begin; everything before it is cleartext header.

The Initial-only token field is the subtle part: 0-RTT, Handshake,
and Retry packets skip it entirely, which is why the parser branches
on `type` rather than assuming a fixed layout.

## The short-header DCID problem

Short headers carry no length fields at all. The DCID length is not
self-describing — it comes from connection state established during
the handshake. `parse_short_header(buf, dcid_len)` therefore takes the
length as an argument and returns `{spin_bit, key_phase, dcid,
payload_offset}`. This mirrors real stacks: you cannot parse a 1-RTT
packet without the connection's negotiated DCID length.

## Frame-type tags

Inside the protected payload, frames are type-tagged bytes. The
module pins the common ones — PADDING `0x00`, PING `0x01`, ACK `0x02`,
CRYPTO `0x06`, STREAM base `0x08`, CONNECTION_CLOSE `0x1C` — and
`stream_frame_tag(off, has_len, fin)` composes the STREAM frame's
low three flag bits (OFF=0x04, LEN=0x02, FIN=0x01) onto the base.

## Running the companion

```text
$ lateralus run examples/quic_tutorial.ltl
=== LATERALUS STDLIB QUIC TUTORIAL ===
STEP 1 varint boundaries (RFC 9000 §16):
  63 -> 1 bytes, roundtrip=True
  64 -> 2 bytes, roundtrip=True
  16383 -> 2 bytes, roundtrip=True
  16384 -> 4 bytes, roundtrip=True
  1073741823 -> 4 bytes, roundtrip=True
  1073741824 -> 8 bytes, roundtrip=True
STEP 2 header discrimination (first byte bits):
  long:  form=1 fixed=1 type=0 (Initial=0)
  short: form=0 fixed=1 spin=0 key_phase=1
STEP 3 parse a long-header Initial packet:
  type=0 version=1 length=50
  dcid=[1, 2, 3, 4, 5, 6, 7, 8] scid=[9, 10] token=[]
  payload_offset=19 (frame bytes start here)
STEP 4 parse a short-header 1-RTT packet:
  spin=0 key_phase=1 dcid=[11, 22, 33, 44, 55, 66, 77, 88]
  payload_offset=9 (PN + protected payload follow)
STEP 5 frame-type tags:
  PADDING=0x00 PING=0x01 ACK=0x02 CRYPTO=0x06 STREAM base=0x08 CONN_CLOSE=0x1C
  stream(off,len,fin)=0x0F stream(fin only)=0x09
PINNED_VECTORS: vi63=1B vi64=2B vi16k=4B vi1g=8B hdr=11000011 type0 spinhdr=01000101 dcid=1..8 payloadoff=19 tag_stream_all=0x0f tag_stream_fin=0x09
```

`tests/test_quic_tutorial.py` pins the varint boundary round-trips,
the hand-built Initial packet parse (`version=1`, `length=50`,
`payload_offset=19`), the short-header DCID slice, and the stream
frame tag composition.

## When to use it

**Use it** to inspect QUIC packets on the wire, to build a QUIC frame
parser or proxy that stops at the cleartext header, or as a compact
worked example of a length-prefixed binary protocol.

**Don't expect** cryptographic packet protection/unprotection, AEAD,
key derivation, connection state machines, or stream reassembly —
`payload_offset` tells you where the protected bytes start; what they
mean is the crypto layer's job.

That is `stdlib/quic.ltl`: four varint widths, three bit-extractor
header predicates, a field-ordered long-header walker, a
state-dependent short-header parser, and the frame-type constants.
