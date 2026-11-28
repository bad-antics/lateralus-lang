# Bounty claims

Entries record requests for maintainer review. A requested amount does not
represent an approved award or a completed payment.

## Pending review

| Contributor | Submission | Requested bounty | Status |
| --- | --- | --- | --- |
| @yuchenlan26-cell | [#889: Python backend silently drops stdlib.regex imports](https://github.com/bad-antics/lateralus-lang/issues/889) | $10 recurring minimal bug report | Awaiting maintainer review; no award or payment confirmed |

### #889 reproduction

Tested at `621ae1b8ed2657887abd331766b74e72780c8a69`, on Windows with
CPython 3.14.7. Save this source as `repro.ltl`:

```lateralus
import stdlib.regex as regex
fn main() {
    println(regex.find_first("[a-z]+-[0-9]+", "jobs: sync-104, build-7"))
}
```

- `lateralus check repro.ltl` succeeds.
- `lateralus py repro.ltl -o repro.py` succeeds but emits only a comment
  for the import, leaving `regex` unbound.
- `lateralus run repro.ltl` exits 1 with
  `NameError: name 'regex' is not defined`.
- The `stdlib.math` alias control using `math.sqrt(81)` prints `9.0`.

Expected behavior is either the supported regex result (`sync-104`) or an
explicit compiler diagnostic for an unsupported import. The report concerns
import code generation, separately from the regex source parsing issue #114.

Investigation and this claim record were prepared with Codex assistance.
No compiler fix is included in this claim.
