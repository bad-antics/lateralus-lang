# Extracting Job IDs with `stdlib/regex.ltl`

Build systems, CI pipelines, and deployment monitors frequently emit log lines containing structured job identifiers such as `sync-104` or `build-7`. The `stdlib/regex.ltl` module provides fast pattern matching and substring extraction without external dependencies.

The companion runnable example is [`examples/regex_log_extraction.ltl`](../../examples/regex_log_extraction.ltl).

## Pattern matching and extraction

Importing the module exposes `find_first`, `find_all`, `match`, and `is_match`:

```lateralus
import stdlib.regex as regex

let line = "jobs: sync-104, build-7, ignored"
let first_id = regex.find_first("[a-z]+-[0-9]+", line)     // "sync-104"
let all_ids = regex.find_all("[a-z]+-[0-9]+", line)        // ["sync-104", "build-7"]
let has_jobs = regex.is_match("[a-z]+-[0-9]+", line)      // true
```

### `find_first(pattern, text)`
Finds the first substring matching `pattern`. If a match is found, returns the exact matched slice from `start` to `end`. If no match occurs, it returns an empty string `""` without raising exceptions.

### `find_all(pattern, text)`
Iterates across all non-overlapping matches of `pattern` in `text` and returns them as a standard `list` of strings in encounter order. For log lines with no matching identifiers (such as `"jobs: none"`), `find_all` returns an empty list `[]`.

### `is_match(pattern, text)`
Returns a boolean indicating whether the pattern occurs anywhere within the text.

## Test Vectors

The companion runner verifies the following pinned vectors:

| Input Log Line | Pattern | `find_first` | `find_all` | `is_match` |
| :--- | :--- | :--- | :--- | :--- |
| `"jobs: sync-104, build-7, ignored"` | `[a-z]+-[0-9]+` | `"sync-104"` | `["sync-104", "build-7"]` | `true` |
| `"jobs: none"` | `[a-z]+-[0-9]+` | `""` | `[]` | `false` |

## Running the Tutorial

To run and typecheck the companion tutorial:

```bash
python -m lateralus_lang run examples/regex_log_extraction.ltl
python -m lateralus_lang check examples/regex_log_extraction.ltl
pytest tests/test_regex_tutorial.py -v
```
