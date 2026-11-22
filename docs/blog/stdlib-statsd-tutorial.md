# Metrics Packets with `stdlib/statsd.ltl`

StatsD is the UDP fire-and-forget metrics protocol behind Datadog,
Graphite, and most monitoring pipelines. `stdlib/statsd.ltl` builds and
parses the wire format: `<name>:<value>|<type>[|@rate][|#tags]`.

This tutorial exercises every builder and the parser. Companion:
`examples/statsd_tutorial.ltl`.

---

## Wire format

- Types: `c` counter, `g` gauge (+ delta form), `ms` timer, `h`
  histogram, `d` distribution, `s` set
- `|@<rate>` sample rate, `|#tag:value,...` DogStatsD tags
- `parse_line` returns `{name, value, kind, rate, tags}` or `nil`

## Verified output

- `counter("http.requests", 5, "0.5", [["env","prod"],["region","us"]])`
  → `http.requests:5|c|@0.5|#env:prod,region:us`
- Parse round-trips preserve name/value/kind/rate/tags; bare tags
  (`#solo`) and missing fields handled; malformed lines → `nil`.

## Bugs found while building the tutorial

`index_of`, `split`, and `char_at` are all missing runtime builtins —
the module cannot run as shipped. The tutorial inlines `_index_of` /
`_split` helpers and uses `slice`. Flagged for a module fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/statsd_tutorial.ltl
python -m lateralus_lang check examples/statsd_tutorial.ltl
python -m pytest tests/test_statsd_tutorial.py -x -q
```
