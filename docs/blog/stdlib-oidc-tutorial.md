# OpenID Connect with `stdlib/oidc.ltl`

OIDC is OAuth 2.0 plus three things: a discovery document, a signed
`id_token`, and strict claim validation. `stdlib/oidc.ltl` covers all
three — it parses the discovery metadata, builds the OIDC-flavored
authorization URL (with `nonce`), delegates signature checks to
`jwt.ltl`, and validates `iss`/`aud`/`nonce` itself.

This tutorial exercises the whole relying-party flow. Companion:
`examples/oidc_tutorial.ltl`.

---

## Discovery

`parse_discovery(doc)` whitelists the fields a relying party needs —
`issuer`, `authorization_endpoint`, `token_endpoint`,
`jwks_uri`, `end_session_endpoint`, plus supported-scopes lists.
Unknown keys are dropped, so a hostile or sloppy discovery doc can't
smuggle fields into your config.

`client_from_discovery` then binds a client to those endpoints and
**injects `"openid"` at the front of the scope list** if missing —
the one OIDC requirement OAuth alone doesn't have.

## Authorization URL

Same as OAuth 2.0's, plus `nonce` — a replay-protection value echoed
inside the signed `id_token`. The module delegates to the oauth2
builder with `nonce` as an extra param.

## id_token verification

`verify_id_token(token, key, alg, issuer, audience, nonce, now_s)`
returns `[ok, claims_or_error]`:

1. **Signature** — delegated to `jwt_verify_hmac` (HS256/384/512,
   constant-time compare, `alg:none` rejected upstream).
2. **`iss`** — must equal your configured issuer exactly.
3. **`aud`** — accepts string *or* array form (multi-audience tokens).
4. **`nonce`** — checked only when you pass a non-empty expected
   value; empty means "don't check".
5. **`exp`/`nbf`** — checked inside `jwt.ltl` against wall-clock time.

Error strings are specific: `"iss mismatch"`, `"aud mismatch"`,
`"nonce mismatch"`, `"expired"`, `"bad_signature"` — log them
directly.

## at_hash and logout

- **`at_hash_s256(access_token, sha256_bytes)`** — the OIDC Core
  §3.1.3.6 claim binding an access token to the id_token: left
  half of SHA-256, base64url, padding stripped. The companion's
  output `w-EIkXOFVbCf9km_xa1oAA` matches an independent Python
  `hashlib`/`base64` reference byte-for-byte.
- **`end_session_url`** — builds the RP-initiated logout URL with
  `id_token_hint`, optional `post_logout_redirect_uri`, and `state`;
  returns `""` when the discovery doc has no end-session endpoint.

## Verified output

```text
verify ok=True sub=user-1 nonce=nc-42     (real HS256 sign->verify)
wrong nonce -> False nonce mismatch
wrong iss   -> False iss mismatch
expired     -> False expired
+1 byte     -> False bad_signature
at_hash     = w-EIkXOFVbCf9km_xa1oAA     (cross-checked)
```

The companion inlines everything `ltlc run` needs (imports don't
resolve): oauth2 helpers, a compact HS256 JWT sign/verify with a
flat-claims JSON parser, and base64url codecs.

`tests/test_oidc_tutorial.py` pins all of it.

## When to use it

**Use it** for OIDC relying-party code — the discovery→auth→verify
skeleton is the fiddly part; transport and userinfo calls are yours.

**Don't expect** JWKS fetching or RS256/ES256 verification — `verify
id_token` takes a pre-bound verifier for asymmetric algs, and
`at_hash` needs you to supply the `sha256_bytes` hook (the module is
deliberately crypto-agnostic). Discovery is parse-only; you fetch the
document yourself.

That is `stdlib/oidc.ltl`: OAuth 2.0 plus the three things that make
it OpenID.
