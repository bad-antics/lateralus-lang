# String Templates with `stdlib/template.ltl`

Emails, HTML fragments, CLI output, API payloads — half of what a program
prints is the same shape with different values punched in. `stdlib/template.ltl`
is Lateralus's answer: a small `<<name>>` substitution engine with defaults,
list rendering, and HTML escaping, in about 180 lines with no dependencies.

This tutorial covers the delimiter syntax, every public function, the edge
cases (unclosed tags, missing vars, escaping order), and ships a runnable
companion (`examples/template_tutorial.ltl`) whose output is pinned by
pytest.

---

## The `<<name>>` syntax

Variables are written `<<name>>` — double angle brackets, optional
whitespace inside tolerated via `trim`:

```text
render("Hello <<name>>!", vars)   -> "Hello world!"
```

The scanner walks the template once. On `<<` it searches forward for the
next `>>`; the slice between them (trimmed) is the variable name. Three
outcomes:

1. **Found and bound** → substitute the value.
2. **Found but unbound** → `render` leaves the literal `<<name>>` in place
   (a feature: templates degrade visibly instead of silently blanking);
   `render_default` substitutes a caller-supplied fallback instead.
3. **No closing `>>`** → the `<` is emitted literally and scanning
   continues — `"unclosed <<oops"` renders unchanged rather than crashing.

## The function surface

| Function | Purpose |
|---|---|
| `render(tmpl, vars)` | substitute bound vars; leave `<<name>>` for missing |
| `render_default(tmpl, vars, d)` | substitute `d` for missing vars |
| `compile(tmpl)` | precompute `{source, vars}` for reuse |
| `render_template(compiled, vars)` | render a compiled template |
| `extract_vars(tmpl)` | list variable names in first-seen order, deduplicated |
| `render_each(tmpl, items, key)` | render once per item, concatenate |
| `render_join(tmpl, items, key, sep)` | same, joined by `sep` |
| `render_numbered(tmpl, items, item_key, idx_key)` | same, with 1-based index bound |
| `escape_html(s)` | `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;` |
| `render_safe(tmpl, vars)` | escape all values, then render |

`extract_vars` is the sleeper feature: run it once at startup to know
exactly which keys a template needs — useful for validating config or
pre-filling a form.

## List rendering

```text
render_join("- <<item>>", ["a","b","c"], "item", ", ")
  -> "- a, - b, - c"

render_numbered("<<i>>. <<item>>", ["apples","pears"], "item", "i")
  -> "1. apples\n2. pears"
```

Each iteration binds a fresh variable scope containing just the item (and
the index for `render_numbered`), so templates stay context-free — no
loop variables leak between iterations.

## Escaping: the order matters

`escape_html` replaces `&` **first**, then `<` and `>`. That ordering is
load-bearing: escaping `<` first would produce `&lt;`, and a later `&` pass
would corrupt it to `&amp;lt;`. The module gets this right, and
`render_safe` applies it to every value before substitution — the correct
pipeline for user-supplied data in HTML contexts.

Note `escape_html` does not escape `"` or `'` — fine for text content,
insufficient for attribute values. If you render `title="<<name>>"`, add
your own quote escaping or sanitize upstream.

## Running the companion script

```text
=== LATERALUS STDLIB TEMPLATE TUTORIAL ===
STEP 1: Hello world!
STEP 2: n=42, missing=<<missing>>
STEP 3: Hello world / earth!
STEP 4: vars in '<<a>> and <<b>> and <<a>>' = [a, b]
STEP 5: unclosed '<<oops' -> unclosed <<oops
STEP 6 join: - a, - b, - c
STEP 7 numbered:
1. apples
2. pears
STEP 8 raw: Title: Mr. <b>Bold</b> & Co
STEP 9 safe: Title: Mr. &lt;b&gt;Bold&lt;/b&gt; &amp; Co
PINNED_VECTORS: hello=Hello world! default=Hello world / earth! vars=a,b join=- a, - b, - c safe=Title: Mr. &lt;b&gt;Bold&lt;/b&gt; &amp; Co
```

`tests/test_template_tutorial.py` pins the whole transcript — including
the two behaviours most likely to surprise: missing vars surviving as
literal `<<name>>`, and `&amp;` appearing *before* `&lt;` in escaped
output (proof the ampersand pass ran first).

## When to use it — and when not to

**Use `stdlib/template.ltl`** for plain-text templating: emails, CLI
reports, simple HTML fragments, notification bodies. The `<<>>` syntax is
unambiguous in prose (unlike `{{ }}` which collides with JS template
literals and Mustache ecosystems).

**Don't use it** for logic-heavy templating — there are no conditionals,
loops, or filters inside templates; do that work in Lateralus code and
bind the results. And don't use `render_safe` as a substitute for a real
HTML sanitizer: it escapes `&<>` only, not quotes or `javascript:` URLs.

That is `stdlib/template.ltl` end to end: one delimiter, eleven public
functions, and a companion script that pins every edge case so you can
verify the module against your own templates.
