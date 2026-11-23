# RFC 5321 ESMTP Client Protocol Tutorial (`stdlib/smtp`)

The `stdlib/smtp` module provides an ESMTP client protocol driver implementing response parsing, command emission, SASL authentication, and body dot-stuffing conforming to [RFC 5321 (Simple Mail Transfer Protocol)](https://datatracker.ietf.org/doc/html/rfc5321) and [RFC 4954 (SMTP Authentication)](https://datatracker.ietf.org/doc/html/rfc4954).

Network I/O is abstracted via a transport map:
```lateralus
let transport = {
    "send": fn(cmd: str),
    "recv_line": fn() -> str
}
```

---

## 1. Response Line Parsing

SMTP status responses follow the format `<code><separator><text>\r\n`:
- A space separator (`250 OK`) indicates the final reply line (`more = false`).
- A hyphen separator (`250-SIZE 35882577`) indicates a continued multi-line reply (`more = true`).

```lateralus
import stdlib.smtp

let res = parse_line("250-STARTTLS\r\n")
// res[0] == 250 (numeric status code)
// res[1] == "STARTTLS" (response text)
// res[2] == true (more lines follow)
```

`read_response(transport)` transparently consumes multi-line greetings and capabilities, returning the final status code and joined text lines.

---

## 2. Command Emission

Commands are formatted with standard `<CRLF>` line endings:

```lateralus
let ehlo = cmd_ehlo("mail.example.org")        // "EHLO mail.example.org\r\n"
let from = cmd_mail_from("alice@example.org")   // "MAIL FROM:<alice@example.org>\r\n"
let to   = cmd_rcpt_to("bob@example.com")       // "RCPT TO:<bob@example.com>\r\n"
let data = cmd_data()                           // "DATA\r\n"
let quit = cmd_quit()                           // "QUIT\r\n"
```

---

## 3. SASL Authentication

Authentication mechanisms encode credentials into standard base64 strings:
- **`auth_plain(user, password)`**: Emits `AUTH PLAIN <base64(\0user\0password)>\r\n`.
- **`auth_login(user, password)`**: Returns a 3-step sequence: `AUTH LOGIN`, base64-encoded username, and base64-encoded password.

```lateralus
let plain_cmd = auth_plain("user", "pass")
let login_seq = auth_login("user", "pass")
```

---

## 4. Message Body Dot-Stuffing (RFC 5321 §4.5.2)

To prevent lines beginning with a period (`.`) from prematurely terminating the `DATA` phase, `encode_body` prepends an additional period (`..`) and appends the standard terminator `\r\n.\r\n`:

```lateralus
let raw = "Subject: Status\n\n.Important dot line"
let encoded = encode_body(raw)
// Contains "..Important dot line\r\n.\r\n"
```

---

## 5. End-to-End Session Orchestration (`send_mail`)

The `send_mail` function automates the complete mail transaction sequence:
1. Validates server greeting (`220`).
2. Issues `EHLO`.
3. Sets envelope sender (`MAIL FROM`).
4. Iterates through all recipients (`RCPT TO`).
5. Initiates payload transfer (`DATA` &rarr; `354`).
6. Transmits dot-stuffed body and terminator (`250`).
7. Gracefully closes connection (`QUIT`).

```lateralus
let status = send_mail(transport, "sender@example.com", ["recipient@example.com"], "Hello SMTP!")
// status == [true, "ok"]
```

---

## Running the Example & Tests

Run the interactive tutorial example:
```bash
lateralus run examples/smtp_tutorial.ltl
```

Run test suite:
```bash
pytest tests/test_smtp_tutorial.py -v
```
