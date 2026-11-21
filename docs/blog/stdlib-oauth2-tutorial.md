# OAuth 2.0 + PKCE with `stdlib/oauth2.ltl`

The OAuth 2.0 authorization-code flow with PKCE is mostly string
plumbing: percent-encode parameters, build a redirect URL, form-encode
token request bodies, and compare the CSRF `state`. All pure
functions — `stdlib/oauth2.ltl` implements them in ~210 lines with
no HTTP or JSON dependencies baked in.

This tutorial walks the whole flow. Companion:
`examples/oauth2_tutorial.ltl`.

---

## Encoding primitives

- **`percent_encode`** — RFC 3986 unreserved set (`A-Z a-z 0-9 - _ .
  ~`) passes through; everything else becomes `%XX` per UTF-8 byte.
  `"a b&c=d"` → `a%20b%26c%3Dd`.
- **`form_encode(pairs)`** — `application/x-www-form-urlencoded`
  bodies: `k=v&k=v`, both sides percent-encoded. Note `keys()` order
  is map order — fine for form bodies where parameter order is
  insignificant.

## PKCE (RFC 7636)

The S256 challenge is `base64url(SHA-256(verifier))` with padding
stripped:

```text
pkce_verifier(entropy)         -> the verifier string itself
pkce_challenge_s256(verifier, sha256_bytes)
                              -> base64url digest, "=" stripped
```

`pkce_challenge_s256` takes the hash as a **function parameter** —
the module stays crypto-agnostic. The companion bridges the builtin
`sha256()` (hex output) through a hex→bytes helper, then a local
base64url encoder.

**Verified against the RFC 7636 Appendix B vector:** verifier
`dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk` produces challenge
`E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM` — exact match.

## The flow

1. **`new_client`** — bundle id/secret/URLs/redirect/scopes.
2. **`authorization_url(client, state, challenge, extra)`** — builds
   `?response_type=code&client_id=…&redirect_uri=…&scope=…&state=…`
   plus `code_challenge`/`code_challenge_method=S256` when a
   challenge is given, and merges `extra` params (e.g. `audience`).
3. **`token_request_body(client, code, verifier)`** — the
   `grant_type=authorization_code` POST body; `client_secret` and
   `code_verifier` are omitted when empty (public clients).
4. **`refresh_request_body` / `revoke_request_body`** — the other
   two grant bodies, with optional `token_type_hint`.
5. **`parse_token_response(json_map)`** — normalizes a parsed JSON
   body into `{access_token, refresh_token, id_token, token_type,
   expires_in, scope}` — **unknown keys are dropped** by design.
6. **`validate_state(expected, got)`** — constant-time compare:
   XOR-accumulate byte differences, length check first. Returns
   false on any mismatch — use it on the callback before trusting
   `state`.

## Verified output

```text
pct("a b&c=d")     = a%20b%26c%3Dd
PKCE challenge     = E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM  (RFC vector)
authorization URL  = …/authorize?response_type=code&…&code_challenge_method=S256
token body         = grant_type=authorization_code&…&code_verifier=dBjft…
state ok/bad       = True / False
```

`tests/test_oauth2_tutorial.py` pins all of it, including the RFC
7636 vector.

## When to use it

**Use it** for any OAuth 2.0 authorization-code client — web, mobile,
CLI — where you handle the HTTP and JSON yourself. The module is the
correctness layer: encoding rules, PKCE math, and CSRF state checks.

**Don't expect** token refresh *scheduling*, JWT validation
(`stdlib/oidc.ltl` covers ID-token verification), discovery-document
fetching, or HTTP transport — those are yours. `client_secret`
belongs in a confidential client only; public clients should pass
`""`.

That is `stdlib/oauth2.ltl`: the RFCs, minus the sockets.
