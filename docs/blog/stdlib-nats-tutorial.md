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

## Request-Reply with a Single-Delivery Subscription (`UNSUB`)

A common question is: **what happens when two replies arrive for the same inbox?** NATS `UNSUB` answers this — it cancels a subscription after a maximum number of deliveries.

The sequence for a single-request-single-reply pattern:

1. **`SUB _INBOX.lesson 7`** — subscribe to a temporary inbox, assigning subscription ID `7`.
2. **`UNSUB 7 1`** — cancel subscription `7` after `1` delivery so that only the first reply is accepted.
3. **`PUB lesson.press _INBOX.lesson 6\r\nok\r\n42\r\n`** — publish the two-line reading with the inbox as reply subject.

```lateralus
// Composing the three-command transcript using stdlib/nats.ltl
let subscribe     = sub("_INBOX.lesson", "", "7")
let stop_after_one = unsub("7", 1)
let request       = pub_msg("lesson.press", "_INBOX.lesson", "ok\r\n42")
let transcript    = subscribe + stop_after_one + request

// Pinned wire transcript:
// "SUB _INBOX.lesson 7\r\nUNSUB 7 1\r\nPUB lesson.press _INBOX.lesson 6\r\nok\r\n42\r\n"
assert_eq(transcript,
    "SUB _INBOX.lesson 7\r\nUNSUB 7 1\r\nPUB lesson.press _INBOX.lesson 6\r\nok\r\n42\r\n",
    "one-reply request transcript")
print(transcript)
```

With `UNSUB 7 1` in place, if a responder sends two replies (`ACK` and then `TWO`), the client receives only `ACK`. Removing the `UNSUB` command lets the second message through. This test can be verified offline by checking the encoded transcript, or against a live NATS server using the helper script below.

### Offline Checkout Test

The pinned transcript can be verified without a running broker. The check below uses the **repository's own `stdlib/nats.ltl`** so that any future change to the shipped encoder is caught automatically:

```python
# tests/check_one_reply.py — offline transcript check
import os, subprocess, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_one_reply_transcript():
    """Verify the UNSUB 7 1 request transcript against a pinned byte sequence."""
    module = (REPO_ROOT / "stdlib" / "nats.ltl").read_bytes()
    lesson = b"""
fn main() {
    let subscribe      = sub("_INBOX.lesson", "", "7")
    let stop_after_one = unsub("7", 1)
    let request        = pub_msg("lesson.press", "_INBOX.lesson", "ok\\r\\n42")
    let expected       = "SUB _INBOX.lesson 7\\r\\nUNSUB 7 1\\r\\nPUB lesson.press _INBOX.lesson 6\\r\\nok\\r\\n42\\r\\n"
    let commands       = subscribe + stop_after_one + request
    assert_eq(commands, expected, "one-reply request transcript")
    print(commands)
}
main()
"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        unit = Path(tmp) / "lesson.ltl"
        unit.write_bytes(module + b"\n" + lesson)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        result = subprocess.check_output(
            [sys.executable, "-m", "lateralus_lang", "run", str(unit)],
            env=env, cwd=str(REPO_ROOT)
        )
    expected = (
        b"SUB _INBOX.lesson 7\r\nUNSUB 7 1\r\n"
        b"PUB lesson.press _INBOX.lesson 6\r\nok\r\n42\r\n\n"
    )
    assert result == expected, f"transcript mismatch:\n  got:      {result!r}\n  expected: {expected!r}"
    print("PASS: SUB, UNSUB and PUB match the pinned transcript.")

if __name__ == "__main__":
    test_one_reply_transcript()
```

Run it from the repository root:

```bash
python tests/check_one_reply.py
```

Expected output:
```text
SUB _INBOX.lesson 7
UNSUB 7 1
PUB lesson.press _INBOX.lesson 6
ok
42

PASS: SUB, UNSUB and PUB match the pinned transcript.
```

---

## Running the Full Tutorial

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
STEP 6: Request-Reply with UNSUB 7 1 (single-delivery):
SUB _INBOX.lesson 7
UNSUB 7 1
PUB lesson.press _INBOX.lesson 6
ok
42

PINNED_VECTORS: len1=41 len2=44 len3=19 len4=29 op=MSG transcript_ok=true
```

---

## Conclusion

With `stdlib/nats.ltl`, Lateralus applications can directly communicate with distributed NATS message brokers with microsecond parsing latency, predictable byte accounting, and no third-party native dependencies. The `UNSUB` command provides a clean, protocol-native mechanism for request-reply patterns where exactly one answer is expected.
