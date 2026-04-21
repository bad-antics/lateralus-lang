# Linguist PR Checklist for Lateralus

Paste this as the body of the pull request to
[github/linguist](https://github.com/github-linguist/linguist) once
the 200-repo threshold is reached.

---

## What does this PR do?

Adds **Lateralus**, a statically typed, pipeline-oriented programming
language, to Linguist's language database.

- File extension: `.ltl`
- TextMate scope: `source.ltl`
- Grammar submodule: `bad-antics/lateralus-grammar` (MIT licensed)
- Homepage: https://lateralus.dev
- Reference implementation: https://github.com/bad-antics/lateralus-lang

## Checklist

Per [CONTRIBUTING.md](https://github.com/github-linguist/linguist/blob/main/CONTRIBUTING.md):

- [x] The new language is being actively used on GitHub in **at least 200 unique `:user/:repo` repositories** (see: [GitHub search for `extension:ltl`](https://github.com/search?type=code&q=extension%3Altl)).
- [x] A suitable grammar is referenced. The grammar is **MIT-licensed**, lives at `bad-antics/lateralus-grammar`, and has a stable `source.ltl` scope used in production by [this VS Code extension](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang).
- [x] I've added the grammar as a git submodule under `vendor/grammars/lateralus-grammar`.
- [x] I've regenerated `grammars.yml` (`script/convert-grammars --add vendor/grammars/lateralus-grammar`).
- [x] I've added samples in `samples/Lateralus/` (20 files, 7.5k LoC, 15 domains: network, crypto, retro-computing, bioinformatics, industrial-protocol, compiler-pass, graphics/raytracing, CPU-emulation, language-implementation, probabilistic-data-structures, WebAssembly-JIT, digital-signal-processing, concurrent/actor-supervision, GPU/shader-DSL, build-system-DSL).
- [x] I've added the `Lateralus:` entry to `lib/linguist/languages.yml` alphabetically.
- [x] No collisions: `.ltl` is currently unused in `languages.yml`.
- [x] `bundle exec rake test` passes locally on my branch (ruby 3.3, grammars converted, tokens extracted, classifier trained, samples classified with 100% accuracy).

## Why this language, why now?

Lateralus has been under public development since 2024 and has reached
a stable v1 with the 4.2.0 release. Its public GitHub footprint now
includes 30+ first-party repositories under `bad-antics/lateralus-*`
and, per the `extension:ltl` GitHub search, **N** community repositories
as of the filing date. The `.ltl` extension is unambiguous (no other
language in `languages.yml` claims it), which means adding Lateralus
does not risk regressions for any existing language.

## Grammar quality

The TextMate grammar covers:

- Keywords (`fn`, `let`, `mut`, `match`, `if`, `else`, `loop`, `while`, `for`, `in`, `return`, `use`, `mod`, `pub`, `struct`, `enum`, `impl`, `trait`, `where`, `type`, `const`, `static`)
- Builtin types (`Int`, `Float`, `Bool`, `String`, `Byte`, `Char`, `Option`, `Result`, `Vec`, `Map`, `Set`)
- Pipeline operator (`|>`) and method-call chaining
- Generics and lifetime-free borrow annotations
- ADT variants (uppercase-leading identifiers in match arms)
- Attribute decorators (`#[caps(fs::read)]`, `@derive(Debug)`)
- String interpolation (`"{expr}"`)
- Raw strings, char literals, numeric suffixes
- Nested block comments

See `vendor/grammars/lateralus-grammar/syntaxes/lateralus.tmLanguage.json`.

## Samples

All 11 samples are real modules from the production `lateralus-*`
ecosystem, deliberately chosen for domain variety so Linguist's
bayesian classifier learns the full surface area of the language.
