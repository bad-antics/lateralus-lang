# {{PROJECT_NAME}}

> A Lateralus project. Generated from the Lateralus seed template.

## Quick start

```bash
pip install lateralus-lang
lateralus run src/main.ltl
```

## Project layout

```
src/          # Lateralus source (.ltl)
tests/        # test modules
.gitattributes  # marks .ltl as Lateralus for GitHub linguist
```

## Development

```bash
lateralus fmt src/            # format
lateralus lint src/           # lint
lateralus test tests/         # run tests
lateralus build src/main.ltl  # produce an executable (via C99 backend)
```

## Learn more

- Language: https://lateralus.dev
- Docs: https://lateralus.dev/docs
- Source: https://github.com/bad-antics/lateralus-lang

## License

MIT — see [LICENSE](LICENSE).
