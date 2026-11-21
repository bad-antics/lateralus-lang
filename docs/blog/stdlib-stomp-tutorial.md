# Message Frames with `stdlib/stomp.ltl`

STOMP — Simple Text Oriented Messaging Protocol — is the wire format
under RabbitMQ's STOMP adapter, ActiveMQ, and a generation of message
brokers. Frames are plain text: a command line, `key:value` headers, a
blank line, a body, and a NUL terminator. `stdlib/stomp.ltl` implements
the 1.2 codec — escaping, encoding, parsing, and builders for the
common commands — in about 180 lines.

This tutorial covers the frame anatomy, header escaping rules, the
parser's heartbeat/incomplete handling, and the frame builders.
Companion: `examples/stomp_tutorial.ltl`.

---

## Frame anatomy

```text
COMMAND\n
header:value\n
header:value\n
\n
body bytes\x00
```

- **Command line** — one uppercase verb (`CONNECT`, `SEND`, `MESSAGE`,
  `ACK`, `BEGIN`...)
- **Headers** — `key:value` per line, terminated by a blank line
- **Body** — arbitrary bytes up to the NUL (`\x00`) terminator

Unlike RESP's length prefixes, STOMP frames self-delimit: the parser
knows the body ends at the first NUL. That makes frames human-readable
on the wire — `telnet` to a STOMP port and you can literally read the
protocol.

## Header escaping (STOMP 1.2)

Header *values* can't contain raw `:`, `\n`, `\r`, or `\` — they'd
break the line format. The 1.2 spec escapes them:

| Raw | Escaped |
|---|---|
| `:` | `\c` |
| `\n` | `\n` (backslash-n) |
| `\r` | `\r` |
| `\` | `\\` |

`escape_header`/`unescape_header` are exact inverses — the tutorial's
`a:b\c<newline>d<CR>e` round-trips cleanly. Note the escape char is
backslash and `\c` means colon (not a generic escape) — a quirk worth
remembering when hand-writing frames.

## Encoding and parsing

`encode_frame(command, headers, body)` builds the wire bytes;
`parse_frame(buf)` returns `{command, headers, body, consumed}` or
`nil`:

- **Heartbeat skipping** — leading `\n`/`\r` runs are ignored, so
  keepalive newlines between frames don't confuse the parser.
- **`consumed`** — bytes eaten including skipped heartbeats' offset
  math; callers can loop `parse_frame` over a buffer.
- **Incomplete → nil** — missing blank line or missing NUL returns
  `nil` rather than throwing, same truncation-safe contract as RESP.

## The frame builders

The module ships constructors for the commands you'll actually send:

```text
connect(host, login, passcode, heartbeat)
send(destination, content_type, body)     -- adds content-length
subscribe(id, destination, ack_mode)
unsubscribe(id) / ack(id, tx) / nack(id, tx)
begin(tx) / commit(tx) / abort(tx)
disconnect(receipt)                        -- receipt requests a RECEIPT frame
```

`send` auto-computes `content-length` — the one header brokers rely on
most. Optional headers are only emitted when non-empty, keeping frames
minimal.

## Running the companion

```text
STEP 1 header escaping:
  esc: a\cb\\c\nd\re
  round-trip equal: True
STEP 2 encode SEND frame:
SEND\ndestination:/queue/orders\ncontent-type:text/plain\ncontent-length:8\n\norder-42<NUL>
STEP 3 encode CONNECT:
CONNECT\naccept-version:1.2\nhost:broker.example.com\nlogin:alice\npasscode:s3cret\nheart-beat:0,0\n\n<NUL>
STEP 4 parse a MESSAGE frame:
  command=MESSAGE body=hello world consumed=99
STEP 5 heartbeat + incomplete:
  after 3 newlines: command=MESSAGE
  missing NUL -> True
STEP 6 transaction frames:
BEGIN\ntransaction:tx-1\n\n<NUL>
COMMIT\ntransaction:tx-1\n\n<NUL>
```

`tests/test_stomp_tutorial.py` pins the escaped header bytes, the
exact frame wire format (visible `\n` + `<NUL>` markers), the parse
result with `consumed=99`, and nil-on-incomplete.

## When to use it

**Use it** to speak STOMP to RabbitMQ/ActiveMQ-style brokers, to
build a STOMP proxy or frame inspector, or as a readable example of a
line-based binary-ish protocol (the NUL-terminated body is the only
binary part).

**Don't expect** STOMP 1.1/1.0 dialect handling, TLS, heart-beat
*negotiation* logic (the codec emits the header; the protocol logic is
yours), or message receipt tracking — `disconnect(receipt)` requests
the frame but correlating `RECEIPT` responses is application code.

That is `stdlib/stomp.ltl`: text frames, four escape rules, a
heartbeat-tolerant parser, and builders for every common verb.
