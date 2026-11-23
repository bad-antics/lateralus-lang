# SCIM 2.0 Identity Management Protocol Tutorial (`stdlib/scim`)

The `stdlib/scim` module provides an identity management toolkit conforming to [RFC 7643 (SCIM Core Schema)](https://datatracker.ietf.org/doc/html/rfc7643) and [RFC 7644 (SCIM Protocol)](https://datatracker.ietf.org/doc/html/rfc7644).

It provides utilities for:
1. Canonicalising User and Group resources into standard SCIM schema envelopes.
2. Formulating paginated `ListResponse` containers and RFC-compliant `Error` payloads.
3. Building and normalising `PATCH` operation documents (`add`, `remove`, `replace`).
4. Constructing `BulkRequest` operations.
5. Lexing, parsing, and evaluating SCIM filter expressions (`eq`, `ne`, `co`, `sw`, `ew`, `pr`, `and`, `or`).

---

## 1. User & Group Resource Canonicalisation

Resources require standard schema URNs, identifiers, and metadata blocks:

```lateralus
import stdlib.scim

let user = new_user("usr-001", "bjensen@example.com", true)
user = with_name(user, "Barbara", "Jensen", "Ms. Barbara J Jensen, III")
user = with_email(user, "bjensen@example.com", "work", true)

let group = new_group("grp-001", "Administrators", ["usr-001"])
```

Schema URN constants include:
- `schema_user()`: `"urn:ietf:params:scim:schemas:core:2.0:User"`
- `schema_group()`: `"urn:ietf:params:scim:schemas:core:2.0:Group"`
- `schema_list_response()`: `"urn:ietf:params:scim:api:messages:2.0:ListResponse"`
- `schema_patch_op()`: `"urn:ietf:params:scim:api:messages:2.0:PatchOp"`
- `schema_bulk_request()`: `"urn:ietf:params:scim:api:messages:2.0:BulkRequest"`
- `schema_error()`: `"urn:ietf:params:scim:api:messages:2.0:Error"`

---

## 2. Paginated Responses & Error Handling

```lateralus
// 1-based indexing for SCIM ListResponse pagination
let res = list_response([user], 1, 20, 100)
// res["totalResults"] == 100
// res["startIndex"] == 1
// res["itemsPerPage"] == 20

// Error envelope with optional scimType
let err = error(409, "uniqueness", "User already exists with given email")
```

---

## 3. PATCH and Bulk Request Documents

### PATCH Normalisation
`parse_patch(doc)` normalises the JSON operations into clean `[op, path, value]` triples:

```lateralus
let op1 = patch_op("replace", "active", false)
let op2 = patch_op("add", "emails", {"value": "new@example.com"})
let op3 = patch_op("remove", "title", nil)

let doc = patch_document([op1, op2, op3])
let ops = parse_patch(doc)
// ops[0] == ["replace", "active", false]
```

### Bulk Requests
```lateralus
let op = bulk_operation("POST", "/Users", "bulk-1", user)
let bulk = bulk_request(10, [op]) // failOnErrors = 10
```

---

## 4. Filter Language (RFC 7644 §3.4.2.2)

The filter parser converts expressions into a nested AST and evaluates them against resource maps:

| Operator | Meaning | Example |
|---|---|---|
| `eq` | Equal (case-insensitive) | `userName eq "bjensen"` |
| `ne` | Not equal | `active ne true` |
| `co` | Contains substring | `name.formatted co "Jensen"` |
| `sw` | Starts with | `userName sw "b"` |
| `ew` | Ends with | `emails.value ew ".com"` |
| `pr` | Present (attribute has value) | `title pr` |
| `and` / `or` | Logical conjunction/disjunction | `active eq true and (department sw "Eng" or title pr)` |

```lateralus
let ast = parse_filter("name.givenName sw Barb and active eq true")
let is_match = eval_filter(ast, user)
// is_match == true
```

---

## Running the Example & Tests

Run the interactive tutorial example:
```bash
lateralus run examples/scim_tutorial.ltl
```

Run test suite:
```bash
pytest tests/test_scim_tutorial.py -v
```
