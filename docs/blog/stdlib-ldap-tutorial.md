# BER on the Wire with `stdlib/ldap.ltl`

LDAP is BER (Basic Encoding Rules) end to end: every value is a
`tag | length | value` triple, strings are octet strings, integers are
two's-complement, and messages are `SEQUENCE { messageID, protocolOp }`
envelopes. `stdlib/ldap.ltl` implements the encoder/decoder primitives
plus the three message builders you'll actually use — BindRequest,
UnbindRequest, and a present-filter SearchRequest — in ~160 lines.

This tutorial walks the byte format with verified hex. Companion:
`examples/ldap_tutorial.ltl`.

---

## TLV primitives

```text
enc_tlv(tag, value)  -> [tag] + enc_len(len(value)) + value
decode_tlv(buf, i)   -> [tag, value_bytes, next_index]
```

`decode_tlv` handles both short-form lengths (`< 0x80`) and long-form
(`0x81`/`0x82`/`0x83` = 1/2/3 length octets) — the parser side is
fully general.

**Encoder caveat (upstream bug):** `enc_len`'s `0x82`/`0x83` branches
use `n / 256` — float division under the Python backend — so lengths
≥ 256 crash with `TypeError: unsupported operand type(s) for &`.
Verified live: `enc_len(300)` dies in generated Python. The companion
uses `int(n / 256)` as a workaround and documents the fix. Practically,
LDAP messages under 64 KiB only need the `0x81` form anyway, which
works fine — but attribute lists or long DNs can cross 256 bytes, so
this is a real bug worth a follow-up PR.

## Scalar encoders

- `enc_integer(v)` — minimal big-endian two's-complement; prepends
  `0x00` when the high bit is set so 128 encodes as `02020080`
  (positive), not negative.
- `enc_octet_string(s)` — `04 len bytes`
- `enc_boolean(b)` — `01 01 ff` for true, `...00` for false
- `enc_enumerated(v)` — same as INTEGER but tag `0x0a` (LDAP uses
  ENUMERATED for scope/deref)

## Message envelopes

LDAP messages are always:

```text
SEQUENCE { messageID INTEGER, protocolOp <APPLICATION tag> {...} }
```

The `APPLICATION n, constructed` tags are raw bytes: BindRequest =
`0x60`, SearchRequest = `0x63`, UnbindRequest = `0x42` with empty body.

- **`bind_request(id, version, dn, password)`** — version 3, simple
  auth as `[0x80] len password` (context tag 0, primitive)
- **`search_present(id, base_dn, scope, attr, attrs)`** — a
  `(attr=*)` presence filter (`0x87` = context [7]), scope as
  ENUMERATED, limits zeroed, attribute list as a SEQUENCE of
  octet strings
- **`parse_message(buf)`** — splits the envelope and returns
  `{message_id, op_tag, op_body}` for response handling

## Verified output

```text
enc_integer(128)   = 02020080        (sign-pad byte)
enc_octet_string   = 0402636e        ("cn")
BindRequest        = 3027 0201 01 60 22 ...  (41 bytes, op_tag 0x60)
SearchRequest      = 3040 0201 07 63 3b ...  (66 bytes, op_tag 0x63)
UnbindRequest      = 3005 0201 09 42 00
```

`tests/test_ldap_tutorial.py` pins every hex string byte-for-byte.

## When to use it

**Use it** to build LDAP simple-bind/search clients, to inspect BER in
other protocols (SNMP, X.509 share the TLV core), or as a compact
example of definite-length DER encoding.

**Don't expect** SASL binds, controls, referrals, StartTLS, or full
LDAP filter syntax — the module covers the presence filter only.
SASL and TLS layers are application concerns.

That is `stdlib/ldap.ltl`: tag-length-value all the way down — encode
a bind, send a search, parse the envelope back.
