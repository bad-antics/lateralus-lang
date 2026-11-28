# HTTP status families with `stdlib.http`

`stdlib.http` classifies an existing response map by its `status` field. The
helpers use half-open ranges, so each status belongs to at most one family:

| Helper | Range |
| --- | --- |
| `is_ok` | 200–299 |
| `is_redirect` | 300–399 |
| `is_client_error` | 400–499 |
| `is_server_error` | 500–599 |

The ranges intentionally exclude 199 and 600. A response map can be classified
without making a request, which makes the following example deterministic and
offline:

```lateralus
from stdlib.http import is_ok, is_redirect, is_client_error, is_server_error

let response = {}
response["status"] = 404
assert(is_client_error(response))
```

Run the complete pinned boundary report with:

```sh
python3 -m lateralus_lang run examples/http_status_families.ltl
```

It checks 199/200, 299/300, 399/400, 499/500, and 599/600. Both predicates
remain false for 199 and 600 because neither code is in an HTTP status family
covered by these helpers.
