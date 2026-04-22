# Changelog

All notable changes to the Lateralus TextMate grammar are documented
here. The grammar is versioned independently of the main compiler
(`bad-antics/lateralus-lang`) so that editors and Linguist can pin a
stable revision.

## 1.0.0 — 2026-04-22

Initial public release, extracted from
`bad-antics/lateralus-lang/vscode-lateralus/syntaxes/lateralus.tmLanguage.json`
at the tag of the `v3.1.0` compiler release.

### Grammar coverage

- Keywords: `fn`, `let`, `mut`, `match`, `if`, `else`, `while`, `for`,
  `in`, `return`, `import`, `module`, `pub`, `struct`, `enum`, `impl`,
  `trait`, `where`, `type`, `const`, `async`, `await`, `spawn`,
  `guard`, `yield`, `break`, `continue`, `defer`, `as`
- Builtin types: `int`, `float`, `bool`, `str`, `char`, `any`, `list`,
  `map`, `tuple`, `Option`, `Result`, `unit`
- Pipeline operator `|>` and method-chain `.`
- Algebraic data-type variants (uppercase-leading identifiers in match
  arms)
- Attribute decorators (`@memo`, `@doc(...)`, `@foreign(...)`, `@law`,
  `@bench`, `@deprecated`)
- String interpolation (`"hello {name}"`) and raw strings (`r"..."`)
- Char literals, numeric suffixes (`_i32`, `_f64`, `_u8`)
- Nested block comments (`/* ... /* ... */ ... */`)
- Line comments (`//`)
- Operators and assignment operators
- Function definitions and closures
- Generics and trait bounds

### Stability guarantee

The TextMate `scopeName` is fixed at `source.ltl` and will not change
in any future 1.x release.
