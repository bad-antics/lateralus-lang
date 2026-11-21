# Framing Multiline NATS Publishes in Lateralus

The [NATS messaging system](https://nats.io) is renowned for high-throughput, cloud-native microservice communication. The core wire protocol is a minimalist, text-based, zero-overhead stream formatted with ASCII verbs and `\r\n` (CRLF) delimiters.

In this tutorial, we will explore `stdlib/nats.ltl`, the Lateralus Standard Library module for framing client-to-server commands and decoding server-to-client responses. We will focus specifically on how multiline messages and internal CRLF bytes are framed without protocol ambiguity or off-by-one errors.

---

## Anatomy of the NATS `PUB` Frame

Publishing a message in NATS follows this wire syntax:

```text
PUB <subject> [reply-to] <#bytes>\r\n<payload>\r\n
```

The components are:

1. **`PUB`**: ASCII command verb.
2. **`<subject>`**: Target subject string (e.g. `press.status` or `telemetry.sensor`).
3. **`[reply-to]`** *(optional)*: Inbox address where subscribers should send point-to-point responses (request-reply pattern).
4. **`<#bytes>`**: The exact byte length of `<payload>`.
5. **`\r\n`**: Header termination delimiter.
6. **`<payload>`**: The raw message payload bytes.
7. **`\r\n`**: Framing terminator delimiter.

### The Critical CRLF Distinction

A common pitfall when assembling NATS wire frames by hand is confusing **payload delimiters** with **framing delimiters**:

* Any `\r\n` sequence **inside** the payload string counts towards `<#bytes>`. For example, `"ok\r\n42"` has two characters (`ok`) + two CRLF control bytes (`\r\n`) + two characters (`42`) = **6 bytes**.
* The trailing `\r\n` that closes the `PUB` frame is a protocol framing boundary; it is **not** part of the payload and is **not** included in the `<#bytes>` count.
* If a payload itself ends in a CRLF (such as a standard formatted log line `"log line\r\n"`), that trailing CRLF is counted in `<#bytes>` (10 bytes total), and an *additional* framing `\r\n` is appended, producing `\r\n\r\n` on the wire.

---

## The Lateralus Standard Library: `stdlib/nats.ltl`

The standard library module exposes:

```lateralus
pub fn connect(opts_json: str) -> str
pub fn pub_msg(subject: str, reply: str, payload: str) -> str
pub fn sub(subject: str, queue: str, sid: str) -> str
pub fn unsub(sid: str, max: int) -> str
pub fn ping() -> str
pub fn pong() -> str
pub fn parse_message(buf: str) -> map
```

The `pub_msg` implementation calculates payload length automatically:

```lateralus
pub fn pub_msg(subject: str, reply: str, payload: str) -> str {
    let hdr = "PUB " + subject
    if reply != "" { hdr = hdr + " " + reply }
    hdr = hdr + " " + str(len(payload)) + "\r\n"
    return hdr + payload + "\r\n"
}
```

---

## Four Canonical Framing Scenarios

### Scenario 1: Multiline Publish with Reply Subject (Request-Reply)

When implementing request-reply over NATS, the publisher supplies a temporary inbox subject where workers reply:

```lateralus
let frame = pub_msg("press.status", "_INBOX.press", "ok\r\n42")
// Wire representation:
// "PUB press.status _INBOX.press 6\r\nok\r\n42\r\n"
```

Notice:
* `_INBOX.press` is inserted after the subject.
* The length is exactly `6`.

### Scenario 2: Multiline Publish Without Reply (Broadcast)

Publishing without a reply subject omits the inbox argument:

```lateralus
let frame = pub_msg("telemetry.sensor", "", "temp=21.5\r\nhum=45")
// Wire representation:
// "PUB telemetry.sensor 17\r\ntemp=21.5\r\nhum=45\r\n"
```

Notice:
* `"temp=21.5"` (9 bytes) + `\r\n` (2 bytes) + `"hum=45"` (6 bytes) = `17 bytes`.

### Scenario 3: Empty Payload (Pulse / Heartbeat)

Publishing zero-byte triggers or heartbeats:

```lateralus
let frame = pub_msg("heartbeat", "", "")
// Wire representation:
// "PUB heartbeat 0\r\n\r\n"
```

Notice:
* Length is `0`.
* The header `\r\n` immediately precedes the frame trailing `\r\n`.

### Scenario 4: Payload Terminating in CRLF (Log Lines)

When streaming structured logs where lines terminate in `\r\n`:

```lateralus
let frame = pub_msg("logs.app", "", "log line\r\n")
// Wire representation:
// "PUB logs.app 10\r\nlog line\r\n\r\n"
```

Notice:
* `"log line"` (8 bytes) + `\r\n` (2 bytes) = `10 bytes`.
* The trailing frame delimiter results in two consecutive `\r\n` sequences.

---

## Parsing Incoming Server Messages (`MSG`)

Subscribers receive server messages conforming to:
```text
MSG <subject> <sid> [reply-to] <#bytes>\r\n<payload>\r\n
```

Using `stdlib/nats.ltl`:

```lateralus
let raw = "MSG press.status 1 _INBOX.press 6\r\nok\r\n42\r\n"
let msg = parse_message(raw)

// msg["op"]       == "MSG"
// msg["subject"]  == "press.status"
// msg["sid"]      == "1"
// msg["reply"]    == "_INBOX.press"
// msg["payload"]  == "ok\r\n42"
// msg["consumed"] == 43
```

---

## Running the Tutorial

The executable tutorial is located at `examples/nats_tutorial.ltl`. Execute it directly with:

```bash
lateralus run examples/nats_tutorial.ltl
```

Expected output:

```text
=== LATERALUS STDLIB NATS TUTORIAL ===
STEP 1: Multiline PUB with reply inbox (6 payload bytes):
PUB press.status _INBOX.press 6
ok
42

STEP 2: Multiline PUB without reply (17 payload bytes):
PUB telemetry.sensor 17
temp=21.5
hum=45

STEP 3: Empty PUB heartbeat (0 payload bytes):
PUB heartbeat 0


STEP 4: PUB with trailing CRLF in payload (10 payload bytes):
PUB logs.app 10
log line


STEP 5: Parsed incoming server message:
  op=MSG
  subject=press.status
  sid=1
  reply=_INBOX.press
  payload=ok
42
  consumed=43
PINNED_VECTORS: len1=41 len2=44 len3=19 len4=29 op=MSG
```

---

## Conclusion

With `stdlib/nats.ltl`, Lateralus applications can directly communicate with distributed NATS message brokers with microsecond parsing latency, predictable byte accounting, and no third-party native dependencies.
