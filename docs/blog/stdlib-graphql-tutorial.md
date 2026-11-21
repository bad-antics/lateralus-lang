# Building and Parsing GraphQL with `stdlib/graphql.ltl`

GraphQL clients live and die by the query document: operations,
variables, aliases, arguments, and nested selection sets. Pulling in a
full GraphQL toolchain for a typed client is heavy —
`stdlib/graphql.ltl` takes the middle path: a **builder API** that
constructs query ASTs as plain maps, a **renderer** that pretty-prints
them, and a **minimal lexer/parser** for the common query subset.

This tutorial covers both directions. Companion:
`examples/graphql_tutorial.ltl`.

---

## The document model

Everything is a map:

```text
operation: {"operation", "name", "variables": [...], "selections": [...]}
variable:  {"name", "type", "default"}
selection: {"field", "alias", "args": map, "selections": [...]}
```

Plain maps mean you can inspect, transform, or serialize a query with
ordinary Lateralus code — no opaque AST objects.

## Building a query

```text
q = new_query("GetUser")
add_variable(q, "id", "ID!", "")
add_variable(q, "withPosts", "Boolean", "true")
user = field("user")
set_arg(user, "id", "$id")
add_child(user, field("name"))
add_child(user, posts_with_title)
add_child(q, user)
```

- `new_query` / `new_mutation` / `make_op` — operation kinds
- `add_variable` — `$name: Type = default` (empty default = required)
- `field(name)` / `field_as(name, alias)` — selections; alias renders
  as `alias: field`
- `set_arg(f, name, raw)` — argument values are **raw strings**, so you
  control exact rendering (`"$id"`, `"{name: \"Ann\"}"`, `"10"`)
- `add_child(parent, child)` — nests selection sets

## Rendering

`render(op)` produces canonical pretty-printed GraphQL:

```text
query GetUser($id: ID!, $withPosts: Boolean = true) {
  user(id: $id) {
    name
    posts {
      title
    }
  }
}
```

Two-space indentation per depth level, arguments inline, variables in
declaration order. The renderer emits braces via `chr(123)`/`chr(125)`
because `{`/`}` inside string literals trip the Lateralus lexer — the
same workaround the module itself uses.

## The lightweight parser

For reading documents back, the module ships `lex` + `parse`:

- **`lex(text)`** — tokenizes the query subset: punctuation split
  individually, `#` comments stripped, `"..."` strings kept whole,
  commas treated as whitespace (GraphQL's insignificant commas).
- **`parse(text)`** — builds the same map AST: operation kind/name,
  selection sets, aliases (`me: viewer`), and field arguments captured
  as raw token strings (no full value grammar — lists/objects/variables
  inside args stay verbatim).

**Subset limits** (inherited from the module, worth knowing):
variable *definitions* `(...)` after the operation name are not
skipped by `parse`, so parse documents without a variable block or
strip it first; fragment spreads, directives, and full argument value
parsing are out of scope. It's a client-side convenience parser, not a
spec-compliant one.

## Running the companion

```text
STEP 1 builder -> pretty query with 2 variables + nested posts
STEP 2 mutation with alias `upd: updateUser(input: {...})`
STEP 3 lex: 20 tokens for a variable-bearing doc
STEP 4 parse -> op=query name=Q, user -> name leaf
STEP 5 alias=me field=viewer (comment stripped)
```

`tests/test_graphql_tutorial.py` pins the rendered query text, token
count, and parsed AST shape.

## When to use it

**Use it** to generate typed GraphQL documents in client code, to
round-trip simple query documents, or as a readable example of a
recursive-descent parser over a token stream.

**Don't expect** schema validation, fragment support, introspection,
or spec-complete parsing — for those you want a real GraphQL library.
The module's sweet spot is "I know my operations; give me a builder
and a pretty printer."

That is `stdlib/graphql.ltl`: maps in, GraphQL out — build it,
render it, parse the simple cases.
