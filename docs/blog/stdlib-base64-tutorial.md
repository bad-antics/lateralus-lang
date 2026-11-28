# Base64 in Lateralus

`stdlib/base64.ltl` implements RFC 4648 Base64 for text values. The module keeps the API small: encode and decode, URL-safe variants, validation, and length helpers.

## The fixed vector

A useful smoke test is the RFC 4648 ASCII vector for `hello`:

```lateralus
let encoded = b64_encode("hello")
assert encoded == "aGVsbG8="
assert b64_decode(encoded) == "hello"
```

The expected string is pinned in `tests/stdlib_base64_tutorial.ltl`, so a compiler change cannot silently alter the wire format.

## Round trips

Use a round trip when the original text must be recovered exactly:

```lateralus
let original = "Lateralus base64"
let encoded = b64_encode(original)
let decoded = b64_decode(encoded)
assert decoded == original
```

For the extended module API, `encode_url` replaces `+` with `-` and `/` with `_`. `decode_url` reverses those substitutions before decoding. This is useful in URLs and filenames where the standard alphabet has special meaning.

## Validation and sizing

`is_valid` checks that the input uses the Base64 alphabet and a multiple-of-four length. `encoded_length` returns the padded output size for an input byte count. `decoded_length` accounts for one or two trailing `=` characters.

```lateralus
// The extended module exposes these helpers as is_valid,
// encoded_length, and decoded_length.
let encoded = b64_encode("hello")
assert encoded == "aGVsbG8="
```

The runnable example in `examples/base64_tutorial.ltl` uses the compiler's built-in `b64_encode` and `b64_decode` shims, which are the same RFC 4648 behavior exposed by the standard-library module.

## Verify it

```text
python -m lateralus_lang check tests/stdlib_base64_tutorial.ltl
python -m lateralus_lang run examples/base64_tutorial.ltl
```
