# SAML 2.0 Browser SSO with `stdlib/saml.ltl`

SAML — Security Assertion Markup Language — is the XML-based single
sign-on protocol still guarding a large share of enterprise identity.
Where OIDC speaks JSON and JWTs, SAML speaks XML envelopes carried over
plain HTTP: a `SAMLRequest` on the way out, a `SAMLResponse` on the way
back. `stdlib/saml.ltl` implements the *protocol envelope* — request
rendering, the HTTP-Redirect and HTTP-POST bindings, and a deliberately
small response parser — in about 220 lines.

This tutorial walks the full round trip. Companion:
`examples/saml_tutorial.ltl`.

> Scope note: the module does **not** implement XML-DSig. Production
> responses must still be signature-verified by a proper XMLDSig
> library; what this module covers is everything an SP needs to *speak*
> the protocol.

---

## The AuthnRequest envelope

`new_authn_request` collects the SP/IdP coordinates, and
`render_authn_request` serialises them into a `samlp:AuthnRequest`
element:

```text
<samlp:AuthnRequest ... ID="_req-42" Version="2.0"
    IssueInstant="2026-11-21T12:00:00Z"
    Destination="https://idp.example.com/sso"
    AssertionConsumerServiceURL="https://sp.example.com/acs"
    ProtocolBinding="...:HTTP-POST">
  <saml:Issuer>https://sp.example.com</saml:Issuer>
  <samlp:NameIDPolicy Format="...:transient" AllowCreate="true"/>
</samlp:AuthnRequest>
```

Every interpolated value passes through `xml_escape`, so entity
metacharacters in URLs or IDs can't break the document.

## Binding 1: HTTP-Redirect

The Redirect binding ships the request in the URL itself. The XML is
DEFLATE-compressed (optional — callers may pass `nil` for the
identity transform, which test IdPs accept), base64-encoded,
padding-stripped, then percent-encoded as the `SAMLRequest` query
parameter alongside an optional `RelayState`:

```text
https://idp.example.com/sso?SAMLRequest=PHNhbWxwOkF1dGhu...&RelayState=relay-1
```

Because base64's `+`, `/`, and `=` are all outside the RFC 3986
unreserved set, `percent_encode` turns them into `%2B`, `%2F`, `%3D` —
the IdP reverses the chain on receipt.

## Binding 2: HTTP-POST

The POST binding skips compression entirely: base64 of the raw XML goes
into a hidden form field, and the browser auto-submits it. `post_binding`
returns `[encoded_request, form_html]` so callers can render the form
themselves.

## Reading a Response

`saml.ltl` is honest about its limits: `parse_response` is a *shallow*
envelope parser, not an XML parser. It extracts exactly what an SP
needs before signature verification:

- `Response/@ID`, `@InResponseTo`, `@Destination`, `@IssueInstant`
- `StatusCode/@Value` — `is_success` compares it against the
  `urn:oasis:names:tc:SAML:2.0:status:Success` URI
- the `<NameID>` text and the raw `<saml:Assertion>` shell

The tiny scanner underneath (`attr_of`, `between_tags`,
`extract_assertion`, `index_of_from`) handles the `saml:`/`samlp:`/
unprefixed element-name variants and nothing more — a feature, not a
bug: it keeps the trust boundary obvious.

## Running the tutorial

```bash
python -m lateralus_lang run examples/saml_tutorial.ltl
python -m lateralus_lang check examples/saml_tutorial.ltl
python -m pytest tests/test_saml_tutorial.py -x -q
```

The example is self-contained: it inlines the module code with the
standard tutorial shims (`char_at(s,i)` → `s[i]`, a local `index_of`,
`bytes_of(ch)` → `[ord(ch)]` for ASCII inputs, and `>>`/`&` in place of
`/`/`%` because Lateralus `/` yields floats).
