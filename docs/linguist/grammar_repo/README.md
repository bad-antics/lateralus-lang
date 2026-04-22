# Lateralus TextMate Grammar

Official TextMate grammar for the [Lateralus](https://lateralus.dev)
programming language.

This repository is vendored by `github-linguist/linguist` under
`vendor/grammars/lateralus-grammar` to power GitHub's syntax
highlighting and language classification for `.ltl` files.

It is also consumed directly by the [Lateralus VS Code
extension](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang)
and by any other editor that supports TextMate grammars (Atom, Sublime
Text, TextMate itself, Zed, Helix, etc.).

## Contents

| File | Purpose |
|------|---------|
| `lateralus.tmLanguage.json` | TextMate grammar (scope `source.ltl`) |
| `language-configuration.json` | Bracket/comment metadata for editors |
| `LICENSE` | MIT |

## Scope

`source.ltl`

## File extension

`.ltl` (primary). Related extensions `.ltasm`, `.ltlm`, `.ltlml`,
`.ltlcfg`, `.ltlnb` are documented in the main language repository but
are not covered by this grammar; each has its own grammar in the
upstream VS Code extension package.

## Upstream

The authoritative source is
[bad-antics/lateralus-lang](https://github.com/bad-antics/lateralus-lang)
under `vscode-lateralus/syntaxes/lateralus.tmLanguage.json`. This
repository simply republishes that grammar on a stable public URL
suitable for Linguist submoduling.

## License

MIT — see [LICENSE](./LICENSE).
