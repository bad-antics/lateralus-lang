# CHANGELOG — Lateralus Language

> Created and maintained by **bad-antics**

All notable changes to the Lateralus Language toolchain are documented here.
Follows [Semantic Versioning](https://semver.org/).

---

## [3.5.0-dev] — Unreleased — Spiral Wave 3

> *"the spiral keeps widening — storage & distribution edition"*

Third wave of stdlib expansion.  Five new modules targeting storage
wire formats and distributed-data primitives, all parse-clean,
plus an integrative example and a full test suite.

### Added — stdlib modules

| Module | Purpose |
|---|---|
| `stdlib/resp.ltl`            | Redis Serialization Protocol codec — RESP2 core plus the RESP3 additions (null, boolean, double, big-number, map, set); symmetric `enc_command` / `decode` |
| `stdlib/protobuf.ltl`        | proto3 wire-format codec — varints, zig-zag, tag packing, fixed32/64, length-delimited; encode helpers per scalar, `decode_message` returns a field-keyed map |
| `stdlib/bloom.ltl`           | Bloom filter with double-hashing on FNV-1a/32 × FNV-1a/64, `optimal_params(n, fp_per_1000)`, union / intersect of same-shape filters, `fill_ppt` stat |
| `stdlib/consistent_hash.ltl` | Sorted-ring consistent hashing with configurable virtual-node density, binary-search `lookup`, replica-aware `lookup_n(k, n)`, add / remove |
| `stdlib/merkle.ltl`          | Binary Merkle tree parameterised over any hash function; default hasher uses FNV-1a/64 → hex so tests stay deterministic; inclusion proofs + `verify` + leaf-level `diff_leaves` |

### Added — example

* `examples/spiral_cache_cluster.ltl` — a replicated in-memory cache
  that wires all five Wave 3 modules together: `consistent_hash`
  picks owners, `bloom` gates existence probes, `resp` is the wire
  protocol, `protobuf` frames replication log entries, and `merkle`
  lets replicas reconcile in `O(log n)` exchanged hashes.

### Added — tests

* `tests/stdlib_spiral_wave_3.ltl` — covers:
  * RESP command/integer/bulk/null/nested-array round-trips,
  * protobuf varint and zig-zag round-trips across every size class,
    tag packing for `(field=3, wire=2)`, mixed-field message decode,
    and fixed32 encode/decode,
  * bloom positive/negative lookup, union superset, and
    `optimal_params` scaling,
  * consistent-hash stability, distinctness under `lookup_n`, and
    minimal-movement property when a node is added,
  * Merkle build+verify for 7 leaves, tampered-proof rejection, and
    leaf-diff detection.

### Notes — dialect discoveries

Landing Wave 3 surfaced one more reserved identifier:

* `probe` joins `select, from, where, match, quote` on the
  parse-blocking list.  (Encountered in `stdlib/resp.ltl` during
  duck-typing a value — renamed the local to `p`.)

---

## [3.4.0-dev] — Unreleased — Spiral Wave 2

> *"the spiral keeps widening — networking edition"*

Second wave of stdlib expansion.  Five new networking modules, all
parse-clean under the current front-end, plus one integrative example
and a test suite covering every module's hot path.

### Added — stdlib modules

| Module | Purpose |
|---|---|
| `stdlib/websocket.ltl` | RFC 6455 frame codec, Sec-WebSocket-Accept handshake, masked/unmasked encode, close frames |
| `stdlib/smtp.ltl`      | ESMTP client — EHLO/MAIL/RCPT/DATA/STARTTLS/QUIT, multi-line response parser, dot-stuffing, AUTH LOGIN + AUTH PLAIN |
| `stdlib/graphql.ltl`   | Query document builder (`query`/`mutation`, variables, args, aliases), renderer, and a lightweight lex+parse round-trip |
| `stdlib/ldap.ltl`      | Minimal BER/DER codec + LDAPv3 Bind/Unbind/Search(present) request builders and message framing |
| `stdlib/quic.ltl`      | RFC 9000 §16 variable-length integers, long/short header parsing, frame-type constants, STREAM-frame tag helper |

### Added — example

* `examples/spiral_chat_relay.ltl` — a self-contained chat-relay demo
  wiring **websocket** + **graphql** together with Wave 1's **metrics**
  and **tracing** over an in-memory transport.

### Added — tests

* `tests/stdlib_spiral_wave_2.ltl` — covers:
  * the RFC 6455 §1.3 known-vector for `Sec-WebSocket-Accept`,
  * websocket frame round-trips across the 7-bit, 16-bit and masked
    length encodings,
  * SMTP line parsing (final vs continuation) and dot-stuffing,
  * GraphQL build/render and lex/parse round-trip,
  * LDAP TLV encode/decode for INTEGER and OCTET STRING, plus
    structural checks for Bind and Unbind,
  * QUIC varint round-trips across all four size classes,
  * QUIC header-form / fixed-bit / long-packet-type / STREAM-tag bits.

### Notes — dialect discoveries

Landing Wave 2 surfaced two front-end quirks worth recording for
future waves:

* **Reserved identifiers** — `select`, `from`, `where` and `match`
  cannot be used as function or variable names (in addition to the
  already-known `quote`).  Wave 2's GraphQL module works around this
  by spelling the "select a child into a parent" helper `add_child`.
* **Brace-string lexer quirk** — a string literal whose content begins
  with an unmatched `{` (e.g. `"{"` or `"{\n"`) is interpreted by the
  lexer as the start of an f-string interpolation and silently
  consumes the rest of the source.  Workaround: use `chr(123)` in
  place of a bare `"{"` literal; `"}"` on its own is unaffected.

---

## [3.3.0-dev] — Unreleased — Spiral Wave 1

> *"we are the language that spirals outward"*

First wave of the open-ended stdlib expansion programme.  Ten new modules,
all parse-clean under the current front-end, all written in the restricted
functional dialect used by `semver`, `ini`, `lru` and friends.

### Added — stdlib modules

| Module | Purpose |
|---|---|
| `stdlib/jwt.ltl`     | RFC 7519 JSON Web Tokens (HS256/384/512), constant-time verify, `iat/nbf/exp` issuance |
| `stdlib/totp.ltl`    | RFC 6238 TOTP + RFC 4226 HOTP, ±drift verify, `otpauth://` URI builder |
| `stdlib/argon2.ltl`  | Argon2id password hashing with PHC-format serialisation, `needs_rehash` check, 3 tuning profiles |
| `stdlib/cbor.ltl`    | RFC 8949 Concise Binary Object Representation encode/decode |
| `stdlib/msgpack.ltl` | MessagePack encode/decode (`nil`/bool/int/str/array/map) |
| `stdlib/yaml.ltl`    | YAML 1.2 subset parser (block maps, block seqs, plain scalars) |
| `stdlib/toml.ltl`    | TOML 1.0 parser (tables, arrays-of-tables, scalars) |
| `stdlib/tar.ltl`     | ustar/POSIX tar reader & writer with checksum |
| `stdlib/metrics.ltl` | In-process counters/gauges/histograms + Prometheus text exposition |
| `stdlib/tracing.ltl` | OpenTelemetry-style spans with W3C `traceparent` wire format |

### Added — examples

- `examples/spiral_auth_server.ltl` — integrative demo wiring **argon2**
  (password hashing) + **jwt** (session tokens) + **totp** (2FA) through
  a **metrics** registry and **tracing** spans.  Minimal auth-server
  skeleton showing how the new modules interlock.

### Added — tests

- `tests/stdlib_spiral_wave_1.ltl` — 19 parse-clean test functions
  covering every Wave 1 module: argon2 hash/verify + rehash-check,
  JWT sign/verify + bad-signature rejection, HOTP RFC 4226 known
  vectors, TOTP ±drift window, CBOR & MessagePack round-trips,
  YAML flat-map + comment stripping, TOML tables + arrays-of-tables,
  tar ustar round-trip, Prometheus counter + histogram rendering,
  tracing span lifecycle + W3C traceparent round-trip.
  Run via `pub fn run_all() -> map`.

### Dialect notes discovered during Wave 1

The front-end parser is stricter than many existing stdlib files assume
(52 of the 93 pre-Wave-1 `.ltl` stdlib files do not parse under the
current grammar).  Wave 1 modules target the **verified-clean subset**:

- `nil` not `null`; `not` keyword for negation (also `&&`, `||`)
- Bare builtin calls (`len`, `slice`, `split`, `index_of`, `keys`,
  `contains`, `chr`, `str`, `int`, `bytes_of`, `char_at`, `starts_with`,
  `ends_with`, `trim`, `join`, `sorted`, `try_int`, `parse_int_base`,
  `itoa_base`, `pad_left`) — no method-call `.foo()` syntax
- Maps constructed by `let m = {} ; m["k"] = v` (no inline `{"k":v}`)
- Lists extended by `xs = xs + [item]` (no `.append`)
- **Reserved identifiers** to avoid as variable names:
  `quote` (shadows a parser token), plus the usual keywords
- `for k in keys(m)` for map iteration; `contains(keys(m), k)` for has-key
- Cross-module calls are flat-named (`argon2_hash`, `jwt_sign_hmac`,
  `metrics_inc`) — the module namespace is honoured by `import` but
  call-site syntax remains bare-identifier

### Spiral roadmap

Wave 1 consciously landed ten security/serialisation/observability
primitives.  Future waves will spiral outward into:

- **Wave 2**: networking (`smtp`, `ldap`, `graphql`, `websocket`, `quic`)
- **Wave 3**: data-science (`dataframe`, `parquet`, `arrow`, `sqlite_vfs`)
- **Wave 4**: distributed (`raft`, `gossip`, `vector_clock`, `crdt`)
- **Wave 5**: crypto upgrades (`ed25519`, `x25519`, `age`, `noise_protocol`)

Waves are additive; existing modules are never broken.

---

## [3.2.0-dev] — Unreleased — `@law` Executable Specifications

### � Groundbreaking: Ternary algebraic structure (10th pillar)

> *Discover the algebraic shape hiding inside ordinary code.*

```
$ lateralus triangulate examples/law_triangulate_demo.ltl

  Triangulating functions in law_triangulate_demo.ltl
  ────────────────────────────────────────────────────────────
  Trials per relation: 80, seed=42
  Found: 8 ternary law(s)
    • homomorphism           ×4
    • left_distributive      ×2
    • right_distributive     ×2

    [left_distributive]  times(x, plus(y, z))
                           ≡  plus(times(x, y), times(x, z))
    [right_distributive] times(plus(x, y), z)
                           ≡  plus(times(x, z), times(y, z))
    [homomorphism]       negate(plus(x, y))
                           ≡  plus(negate(x), negate(y))
    [homomorphism]       double(minus(x, y))
                           ≡  minus(double(x), double(y))
    ...
```

Where `relate` tied **pairs** of functions together, `triangulate`
searches over **triples** of expressions to discover the
higher-order algebraic structure that usually has to be *proven
by hand* in a textbook — distributivity and homomorphisms:

| Relation | Law form | Mathematical meaning |
| --- | --- | --- |
| **left_distributive** | `f(x, g(y, z)) == g(f(x, y), f(x, z))` | `f` distributes over `g` from the left (rings, semirings) |
| **right_distributive** | `f(g(x, y), z) == g(f(x, z), f(y, z))` | `f` distributes over `g` from the right |
| **homomorphism** | `g(f(x, y)) == f(g(x), g(y))` | `g` is a structure-preserving map on `f` |
| **anti_homomorphism** | `g(f(x, y)) == f(g(y), g(x))` | `g` reverses structure (e.g. matrix transpose) |

Each match becomes one fully-quantified `@law`:

```lateralus
@law
fn times_left_distributive_plus(x: int, y: int, z: int) -> bool {
    return (times(x, plus(y, z))) == (plus(times(x, y), times(x, z)))
}

@law
fn plus_homomorphism_negate(x: int, y: int) -> bool {
    return (negate(plus(x, y))) == (plus(negate(x), negate(y)))
}
```

**The system literally rediscovered, from user code alone:** the
distributive law of multiplication over addition and subtraction,
and the fact that `negate` and `double` are ℤ-linear maps (group
homomorphisms on `(ℤ, +)`). No axioms were given.

The `--apply` flag patches the source in place under an idempotent
banner — safe to re-run as the codebase evolves:

```
$ lateralus triangulate my_module.ltl --apply
  → patched 8 ternary laws into my_module.ltl
```

**End-to-end validation**: all 8 generated laws from the demo file
pass `verify` at 100 trials each (`8 passed  0 failed`).

### The ten-pillar verification pipeline

| Pillar | Command | What it proves |
| --- | --- | --- |
| 1 | `discover` | Algebraic identities of one fn |
| 2 | `@law` | Declare executable specs in source |
| 3 | `verify` | Random property test with shrinking |
| 4 | ◈ PROVED | Exhaust finite domains |
| 5 | `verify --mutate` | Measure spec completeness |
| 6 | `--propose` | Synthesize witness laws for survivors |
| 7 | `harden` | Iterate 5→6→auto-patch to fixpoint |
| 8 | `characterize` | Find closed-form defining equations |
| 9 | `relate` | Find cross-function relational laws |
| **10** | **`triangulate`** | **Find ternary algebraic structure (distributivity, homomorphisms)** |

*13 new tests. 2055/2055 pytest green. 0 regressions.*

---

### �🔗 Groundbreaking: Cross-function relational laws (9th pillar)

> *Laws can tie functions together, not just characterize them one at a time.*

```
$ lateralus relate examples/law_relate_demo.ltl

  Relating functions in law_relate_demo.ltl
  ────────────────────────────────────────────────────────────
  Trials per relation: 80, seed=42
  Found: 17 relational law(s)
    • absorbs              ×1
    • commuting            ×11
    • equivalent           ×1
    • idempotent_compose   ×1
    • inverse              ×2
    • involution           ×1

    [inverse]    inc(dec(x))         ↔  x
    [inverse]    dec(inc(x))         ↔  x
    [involution] negate(negate(x))   ↔  x
    [idempotent] abs_val(abs_val(x)) ↔  abs_val(x)
    [absorbs]    abs_val(negate(x))  ↔  abs_val(x)
    [equivalent] double(x)           ≡  twice(x)      ← code smell!
    ...
```

Where `discover` finds identities *inside* one function and
`characterize` finds closed-form equations for one function,
`relate` searches across **pairs** of user functions for the richest
laws of all — the ones that tie two functions together:

| Relation | Law form | Example |
| --- | --- | --- |
| **inverse** | `f(g(x)) == x` | encoder/decoder round-trip |
| **involution** | `f(f(x)) == x` | `negate ∘ negate = id` |
| **idempotent ∘** | `f(f(x)) == f(x)` | `abs ∘ abs = abs` |
| **commuting** | `f(g(x)) == g(f(x))` | order-invariant shifts |
| **absorbs** | `f(g(x)) == f(x)` | `abs(−x) = abs(x)` |
| **equivalent** | `f(x) == g(x)` | duplicated definitions (code smell) |

Each match becomes one quantified `@law` that the rest of the
pipeline (`verify`, `--mutate`, `harden`) can exercise:

```lateralus
@law
fn inc_inverse_dec(x: int) -> bool {
    return (inc(dec(x))) == (x)
}

@law
fn abs_val_absorbs_negate(x: int) -> bool {
    return (abs_val(negate(x))) == (abs_val(x))
}

@law
fn double_equivalent_twice(x: int) -> bool {
    return (double(x)) == (twice(x))
}
```

The `--apply` flag patches the source file in place under an
idempotent banner — safe to re-run as the codebase evolves:

```
$ lateralus relate my_module.ltl --apply
  → patched 12 relational laws into my_module.ltl
```

**End-to-end validation**: all 17 generated laws from the demo file
pass `verify` at 100 trials each (`17 passed  0 failed`).

### The nine-pillar verification pipeline

| Pillar | Command | What it proves |
| --- | --- | --- |
| 1 | `discover` | Algebraic identities of one fn |
| 2 | `@law` | Declare executable specs in source |
| 3 | `verify` | Random property test with shrinking |
| 4 | ◈ PROVED | Exhaust finite domains |
| 5 | `verify --mutate` | Measure spec completeness |
| 6 | `--propose` | Synthesize witness laws for survivors |
| 7 | `harden` | Iterate 5→6→auto-patch to fixpoint |
| 8 | `characterize` | Find closed-form defining equations |
| **9** | **`relate`** | **Find cross-function relational laws** |

*16 new tests. 2042/2042 pytest green. 0 regressions.*

---

### 📐 Groundbreaking: Inductive law characterization (8th pillar)

> *Point witnesses are finite. Characterizations are complete.*

```
$ lateralus characterize math.ltl

  Characterizing functions in math.ltl
  ────────────────────────────────────────────────────────────
  User functions: 4  ['abs_val', 'add', 'double', 'is_positive']
  Trials per candidate: 60, seed=42

    abs_val      ≡  x < 0 ? 0 - x : x   (60 trials)
    add          ≡  x + y               (60 trials)
    double       ≡  x + x               (60 trials)
    is_positive  ≡  x > 0               (60 trials)

  Characterized: 4  |  Unmatched: 0
```

Where `discover` found *algebraic identities* ("`f` is commutative"),
`characterize` finds *defining equations* — closed-form expressions
that completely specify a function's behaviour. Each match becomes
a single quantified `@law` that subsumes infinitely many point
witnesses:

```lateralus
@law
fn is_positive_characterized(x: int) -> bool {
    return is_positive(x) == (x > 0)
}
```

### Catalogue

Bool (arity 1): `x > 0`, `x >= 0`, `x < 0`, `x <= 0`, `x == 0`, `x != 0`,
`x % 2 == 0`, `x % 2 != 0`, `true`, `false`.

Bool (arity 2): `x == y`, `x != y`, `x > y`, `x >= y`, `x < y`, `x <= y`.

Numeric (arity 1): `x`, `0 - x`, `x + 1`, `x - 1`, `x * 2`, `x + x`,
`x * x`, `0`, `1`, `x < 0 ? 0 - x : x`, `x > 0 ? x : 0 - x`.

Numeric (arity 2): `x + y`, `x - y`, `y - x`, `x * y`, `x`, `y`.

Trivial constants (`true`, `false`, `0`, `1`) are tried **last** so we
prefer the most informative characterization. The generated `@law`
auto-renames the expression variables (`x`, `y`) to the real parameter
names from the function signature.

Safety: emitted laws are pure primitives (no `abs()` requiring stdlib
imports). Every characterization is *validated* — each candidate must
pass on every sampled input before being emitted.

### The eight-pillar pipeline

| Pillar | Command | What it does |
| --- | --- | --- |
| 1 | `discover` | Propose algebraic identity laws |
| 2 | `@law` | Declare executable specifications in source |
| 3 | `verify` | Random-property test with shrinking |
| 4 | ◈ PROVED | Exhaust finite domains |
| 5 | `verify --mutate` | Measure spec completeness |
| 6 | `--propose` | Synthesize witness laws for survivors |
| 7 | `harden` | Iterate 5→6→auto-patch to fixpoint |
| **8** | **`characterize`** | **Find closed-form defining equations** |

*13 new tests. 2026/2026 pytest green. 0 regressions.*

---

### �🔁 Groundbreaking: Self-hardening laws (7th pillar)

> *One command. Zero manual paste. Your spec hardens itself until it's airtight.*

```
$ lateralus harden weak.ltl

  Hardening weak.ltl
  ────────────────────────────────────────────────────────────
  Target score: 100%,  max iterations: 5

  iter 1: score  66.7%  (4/6 caught, 2 survivors, 1 proposals)
         → applied 1 new witness law(s)
  iter 2: score  83.3%  (5/6 caught, 1 survivors, 0 proposals)
  ⟂ fixpoint: no new witnesses — remaining survivors likely equivalent

  Final score: 83.3%
```

Two new pieces close the loop end-to-end:

**`--apply`** on `verify --mutate --propose` writes the synthesized
witness laws back into the source file, under an idempotent marker
banner (`// ─── BEGIN/END auto-generated witness laws ───`). Re-runs
are byte-exact unchanged when no new witnesses appear. Hand-editing
inside the banner is preserved across regenerations.

**`lateralus harden <file>`** wraps the whole pipeline in a fixpoint
loop: mutate → propose → apply, repeated until mutation score hits
`--target` (default 100%), no new proposals are found (a strong hint
that remaining survivors are *equivalent mutations*), or `--max-iter`
is reached. The tool **does not hang** on equivalent mutations — the
absence of a witness *is* the fixpoint signal.

Flags:
- `--apply` — insert synthesized laws in place (idempotent)
- `--max-iter N` — iteration cap for `harden` (default 5)
- `--target 0.9` — harden to 90% rather than the default 100%

Now the entire spec pipeline is:

| Pillar | Command | What it does |
| --- | --- | --- |
| 1 | `discover` | Propose laws from implementation behaviour |
| 2 | `@law` | Declare executable specifications in source |
| 3 | `verify` | Random-property test with shrinking |
| 4 | ◈ PROVED | Exhaust finite domains (no counterexample possible) |
| 5 | `verify --mutate` | Measure spec completeness by perturbing code |
| 6 | `--propose` | Synthesize the laws the mutations revealed you were missing |
| **7** | **`harden`** | **Iterate 5 → 6 → auto-patch to fixpoint, in one command** |

*7 new tests. 2013/2013 pytest green. 0 regressions.*

---

### 🪡 Groundbreaking: Witness-based law synthesis (6th pillar)

> *Mutation testing found a surviving mutant? Lateralus writes the law that kills it.*

`lateralus verify file.ltl --mutate --propose` closes the mutation
feedback loop. For every surviving mutant, Lateralus:

1. Exec's the **original** and **mutated** transpiled source into
   separate Python namespaces (suppressing stdout/stderr and tolerating
   failed law-runner tails — functions are defined before assertions
   fire).
2. Identifies the user function containing the mutation via a
   line-number → AST function-name map.
3. Samples random inputs (typed via `_get_param_types`) looking for a
   **witness** — a call where `orig(*args) ≠ mut(*args)`.
4. Emits a ready-to-paste `@law` asserting the original's behaviour at
   that witness. Adding that law would kill the mutant.

```
$ lateralus verify weak.ltl --mutate --propose

  Mutation score:  66.7%  [█████████████░░░░░░░]  (weak)
  Caught:         4 / 6
  Survivors:      2

  ─── Proposed laws (1) ───
    // kills mutant in `is_positive`: original→True, mutant→False
    @law
    fn is_positive_witness_20770() -> bool {
        return is_positive(1) == true
    }
```

If a survivor has **no** synthesizable witness, that's a strong hint it
may be a genuinely *equivalent mutation* — the synthesizer's inability
to discriminate is itself diagnostic.

Flags:
- `--propose` — emit witness laws for every survivor
- `--propose-output <file.ltl>` — write them to a ready-to-import file

This completes the verification story no other mainstream language has
assembled end-to-end:

| Pillar | What it does |
| --- | --- |
| `discover` | Propose laws from implementation behaviour |
| `@law` | Declare executable specifications in source |
| `verify` | Random-property test with shrinking |
| ◈ PROVED | Exhaust finite domains (no counterexample possible) |
| `--mutate` | Measure spec completeness by perturbing code |
| **`--propose`** | **Synthesize the laws the mutations revealed you were missing** |

*7 tests added. 2006/2006 pytest green. 0 regressions.*

---

### �🧬 Groundbreaking: Automatic law discovery

> *You wrote the code. Lateralus writes the specs.*

`lateralus discover file.ltl` reads your implementation and **proposes
the laws it actually satisfies**, ready to paste in. It tries every
pattern in a built-in algebraic catalog (commutativity, associativity,
identity, absorbing elements, idempotence, involution, oddness,
cross-function distributivity) against each user function with matched
type signature, and emits compiling `@law` snippets for every pattern
that holds over N random trials.

```
$ lateralus discover kernel.ltl
  Discovering laws in kernel.ltl
  ────────────────────────────────────────────────────────────
  User functions: 6  ['add', 'mul', 'max2', 'negate', 'abs_val', 'square']
  Trials per pattern: 60, seed=42

  add
    ✓ commutative            (60 trials)
    ✓ associative            (60 trials)
    ✓ identity_left_0        (60 trials)
    ✓ identity_right_0       (60 trials)
    ✓ distributive over max2 (60 trials)
  mul
    ✓ commutative            (60 trials)
    ✓ associative            (60 trials)
    ✓ identity_left_1        (60 trials)
    ✓ absorb_0_left          (60 trials)
    ✓ distributive over add  (60 trials)
  negate
    ✓ involutive             (60 trials)
    ✓ odd                    (60 trials)
  abs_val
    ✓ idempotent_unary       (60 trials)
  max2
    ✓ commutative            (60 trials)
    ✓ associative            (60 trials)
    ✓ idempotent_binary      (60 trials)

  Discovered 18 laws
```

Add `-o laws.ltl` to emit the snippets to a file. Concatenating that
file with the original and running `lateralus verify` passes all 18 —
including genuinely non-obvious ones like `add` distributes over
`max2` (the identity `a + max(b,c) = max(a+b, a+c)`).

Why this is new: **no property-based testing tool discovers its own
properties**. QuickCheck, Hypothesis, Jqwik, mutmut all require you to
*write* the invariants first. Lateralus proposes them from a catalog,
lets you review, and hands back compiling source code. The verification
loop now bootstraps itself:

1. **`discover`** — propose laws from implementation behavior ✨ *new*
2. **`@law`** — keep, edit, or reject the proposals
3. **`verify`** — sampled property testing (with shrinking)
4. **◈ `PROVED`** — auto-upgrade to exhaustive proof when domain is finite
5. **`--mutate`** — check the spec set is tight enough to catch bugs

That's **five verification pillars** in one CLI. No other language
in the world ships this combination as first-class built-ins.

Built-in patterns (v3.2 launch set):

| Pattern | Shape | Example |
|---|---|---|
| commutative | `f(a,b) = f(b,a)` | `add`, `mul`, `max2` |
| associative | `f(f(a,b),c) = f(a,f(b,c))` | `add`, `mul` |
| identity left/right {0,1} | `f(c,a) = a` or `f(a,c) = a` | `add`+0, `mul`+1 |
| absorbing left/right {0} | `f(c,a) = c` or `f(a,c) = c` | `mul`+0 |
| idempotent binary | `f(a,a) = a` | `max2`, `min2` |
| idempotent unary | `f(f(x)) = f(x)` | `abs`, `normalize` |
| involutive | `f(f(x)) = x` | `negate`, `reverse` |
| odd | `f(-x) = -f(x)` | `negate`, `sin` |
| distributive | `f(a,g(b,c)) = g(f(a,b),f(a,c))` | `mul` over `add` |

The trivial-identity filter rejects `fn f(x) { return x }` from
triggering `idempotent_unary` (every function satisfies it vacuously).

---

### 🔬 Groundbreaking: Mutation testing driven by laws

> *Your tests verify your code. What verifies your tests?*

`lateralus verify --mutate` closes the loop. It systematically injects
single-site bugs into your implementation (flipping `+`↔`-`, `==`↔`!=`,
`and`↔`or`, `0`↔`1`, boundary shifts on `<`/`<=`, etc.) and checks
whether your existing `@law` suite catches each one. The **mutation
score** = (caught mutations) / (total mutations) is a direct,
quantitative measure of **spec completeness** — not code coverage,
but *invariant coverage*.

```
  Mutation-testing laws in mutation_demo.ltl
  ────────────────────────────────────────────────────────────
  User functions:  5  ['add', 'is_positive', 'max2', 'min2', 'mul']
  Candidate mutants: 6
  Baseline: 100 trials per law, seed=42

  Mutation score:  83.3%  [████████████████░░░░]  (adequate)
  Caught:         5 / 6
  Survivors:      1  (undetected mutations)

  ─── Survivors (laws missing coverage for these) ───
    • line  643  0  →  1           → return (x > 1)
```

The one survivor above is a **real spec gap**: `is_positive(x) = x > 0`
was mutated to `x > 1`, and the existing three laws (on positive, zero,
and negative inputs) all agree on that mutation. No law pins down the
boundary at `x == 1`. The tool tells you *exactly which invariant is
missing*, with file:line precision.

Usage:
- `lateralus verify file.ltl --mutate` — run full mutation campaign
- `--max-mutants N` — cap mutants (fast CI mode)
- `--timeout SEC` — per-mutant timeout (default 10s)
- Returns exit code `0` iff score is 100 %

Why this is new: Rust has `mutagen`, JS has `stryker`, Python has
`mutmut` — but none of them are **fused with property-based specs**.
Traditional mutation testers check unit tests written in an imperative
style; Lateralus checks *declared mathematical invariants*. Combined
with the exhaustive `◈ PROVED` mode, this is the first language where
you can prove a law holds over a finite domain *and* prove your law
set is tight enough to catch arbitrary implementation perturbations —
in one command.

This is the **4th pillar** of the verification story:

1. `@law` — write the spec
2. `verify` — check implementation against spec
3. ◈ `PROVED` — auto-upgrade to exhaustive proof when domain is finite
4. `--mutate` — check the **spec** against injected bugs

---

### 🧪 Groundbreaking: Laws that prove themselves

Property-based testing meets formal verification — no other mainstream
language does this. The `lateralus verify` runner now automatically
upgrades `@law` declarations to three progressively stronger modes:

| Mode | Trigger | Output | Example |
|---|---|---|---|
| ✓ **Sampled** | Default, infinite domain | `(N trials)` | `@law fn reverse_involutive(xs: list[int])` |
| ◈ **PROVED** (exhaustive) | All params finite-domain (`bool`, `@law(bound=N)`) | `(exhaustive: K cases)` | `@law fn de_morgan(p: bool, q: bool)` |
| ≡ **ORACLE** (differential) | `@law(oracle=ref_fn)` | `(N agreements with oracle)` | `@law(oracle=slow_sort) fn quick_sort(xs)` |

**Why this matters:** QuickCheck samples. Hypothesis samples. Lean/Coq
make you write a whole different language. Lateralus **automatically
enumerates** when the input space is finite — the 6 boolean-algebra
laws in our canonical stdlib spec are now **mathematical theorems**,
not statistical confidence. A law with params `(p: bool, q: bool, r: bool)`
gets proved over 2³ = 8 cases; `@law(bound=4) fn mul_distributes(a: int, b: int, c: int)`
gets proved over 9³ = 729 cases. No formal-methods PhD required.

```
◈ PROVED  and_commutative           (exhaustive: 4 cases)
◈ PROVED  de_morgan_and             (exhaustive: 4 cases)
◈ PROVED  mul_distributes_over_add  (exhaustive: 729 cases)
≡         fast_sort_matches_slow    (100 agreements with oracle)

  42 passed  0 failed  0 skipped  [6 proved, 1 oracle]
```

### Language
- **`@law` — first-class executable specifications.** A boolean-returning
  function tagged `@law` is registered by the compiler as a property test.
  Generators are **auto-derived from the declared parameter types** (`int`,
  `float`, `bool`, `str`, `list`, `list[T]`, `map`, `map[K,V]`) — no
  `Arbitrary` instances, no `@given(strategies...)`, no boilerplate.
- **`lateralus verify <file>`** CLI subcommand runs every `@law` in a file
  (default 100 trials each), reports pass/fail, and **shrinks
  counter-examples** to a minimal form when a law fails (halves numeric
  magnitudes, drops list elements, shrinks list-inner values).
- **Decorator kwargs** — `@law(trials=1000)`, `@law(bound=10)`,
  `@law(oracle=reference_fn)`, `@law(exhaustive=true)`. Kwargs propagate
  to `_law_<key>` attrs on the function, surfaced to the runner.
- Flags: `--trials N` for trial count, `--seed S` for reproducibility.

### Why this is novel
Haskell's QuickCheck needs per-type `Arbitrary` typeclass instances.
Python's Hypothesis needs `@given(strategies...)` per parameter. They
both sample. Idris/Lean demand full formal proofs as a separate mode.
Lateralus owns the type system, so the compiler already knows enough
to generate `list[int]` without being told twice *and* detect when the
input space is finite enough to enumerate. **One decorator, three modes,
zero boilerplate.** The specification is the code.

### Runtime
- New `lateralus_lang/law_runner.py` module: generator dispatch, iterative
  shrinker, self-contained harness (with inline fallback when the package
  isn't on `sys.path`).
- Python codegen registers `@law` functions into `_LATERALUS_LAWS` and
  attaches a `._law_spec` attribute carrying the parameter-name/type list
  with generics preserved (`list[int]`, not flattened to `list`).
- **Structural generators for user structs.** `@struct` declarations are
  registered into `_LATERALUS_STRUCTS` with a `_ltl_struct_spec` field
  descriptor; the runner recursively generates instances from the spec,
  so `fn law(p: Point) -> bool` works with no extra config.
- **`assume(pred)` preconditions.** Laws may discard uninteresting trials
  via `assume(b != 0)` / `assume(a >= 0)`. Discarded trials don't count
  against the trial budget but the effective count is reported.
- **`@law(trials=N)` per-law override.** Decorator kwargs land directly on
  the function (`fn._law_trials = N`); high-value laws can run 1000+
  trials without bloating cheap ones.

### Testing
- **Canonical stdlib law file** — [tests/laws/stdlib_laws.ltl](tests/laws/stdlib_laws.ltl)
  ships 42 fundamental invariants across 9 categories (arithmetic,
  integer div/mod, boolean algebra, list structural, string, comparison,
  min/max, gcd/sign/clamp, high-volume smoke). Writing these surfaced
  one real semantic truth: Lateralus `/` is float division, which
  prompted the `idiv`/`imod`/`divmod` builtins below — the feature
  earned its keep on its first serious deployment.
- **pytest CI integration** — [tests/test_stdlib_laws.py](tests/test_stdlib_laws.py)
  shells out to `lateralus verify` under 6 different seeds. Any future
  change that violates a fundamental invariant fails `pytest`.

### Stdlib (closing the loop)
New integer-arithmetic builtins prompted by a `@law` finding:
- **`idiv(a, b)`** — integer floor division (Python `//` semantics). Lateralus
  `/` is float division; `idiv` is the operator you want when both operands
  are integers and you expect `idiv(a,b) * b + imod(a,b) == a` to hold.
- **`imod(a, b)`** — integer modulo (Python `%`).
- **`divmod(a, b)`** — returns `[quotient, remainder]` pair.
- **`gcd(a, b)` / `lcm(a, b)`** — via Python's `math.gcd`/`math.lcm`.
- **`sign(v)`** — returns `-1`, `0`, or `1`.
- **`clamp(v, lo, hi)`** — bounded projection.
- **`is_even(n)` / `is_odd(n)`** — predicates, covered by
  `even_odd_partition` law (exactly one is true for every integer).

### Example
```lateralus
@law
fn addition_commutative(a: int, b: int) -> bool {
    return a + b == b + a
}
```
```
$ lateralus verify examples/laws_demo.ltl --seed 42
  ✓  addition_commutative  (100 trials)
  ...
  16 passed  0 failed  0 skipped
```

---

## [3.1.0] — 2026-04-21 — PyPI Metadata, Distribution & C Backend Perf

### Distribution
- **PyPI v3.1.0 published** — `pip install lateralus-lang` installs the full
  toolchain (compiler, interpreter, LSP, DAP, formatter, linter, package manager)
- **VS Code Marketplace v3.1.0 published** — extension `lateralus.lateralus-lang`
  with syntax highlighting, LSP integration, debugger UI, and 30+ snippets
- **Linguist submission staged** — [docs/linguist/](docs/linguist/) contains 20
  real (compiling) code samples, TextMate grammar repo contents, and the
  `languages.yml` patch ready to submit to github-linguist/linguist

### C Backend
- **Polymorphic `println` / `print` dispatch** — type-inferred at codegen
  so `println(int)`, `println(float)`, `println(bool)` and `println(string)`
  all produce correct C without requiring wrapper helpers in user code
- **Builtin cast functions** — `int(x)`, `float(x)`, `bool(x)`, `str(x)` now
  compile to native C casts or type-dispatched `ltl_*_to_str` calls
- `fib` benchmark: **~60× faster than CPython** (4 ms vs 236 ms)
- `sieve` benchmark: **~30× faster than CPython** (1 ms vs 25 ms), **~300×
  faster than the Lateralus interpreter**
- `mandelbrot` benchmark: **~30× faster than CPython** (3 ms vs 84 ms)
- `nbody` benchmark: **~40× faster than CPython** (0.6 ms vs 36 ms), **~450×
  faster than the Lateralus interpreter**
- Native binaries: 16 KB stripped, `gcc -O2` with `-lm`, no external runtime
- **List literal element population** — `[1, 2, 3]` now emits a GCC
  statement-expression with typed boxing helpers (`ltl_box_int`, etc.) so
  elements actually land in the underlying `ltl_list_t*`
- **List repetition operator** — `[x] * n` lowers to `ltl_list_repeat` runtime
  helper; `[a] + [b]` lowers to `ltl_list_concat`
- **Truthy coercion in conditionals** — `if list[i]` and `while list[i]` auto-
  unbox `ltl_value_t` via `ltl_unbox_bool` when the condition is an untyped value
- **List-element assignment boxing** — `list[i] = expr` now boxes the RHS into
  the correct `ltl_value_t` tag based on inferred source type
- **Function parameter type tracking** — parameter types are now registered
  in the local-type table so inference works throughout the function body
- **Typed C-array lowering for homogeneous numeric list literals** —
  `let xs = [0.0, 4.84, 8.34]` compiles to `double xs[3] = {...};` with
  native indexing. `xs[i] - xs[j]` is now one FP subtract, not two unboxes.
  Tracked in `_list_elem_types` for the whole function scope. This + math-
  builtin return-type inference (`sqrt`, `pow`, `sin`, etc. return `double`)
  unblocked `nbody` at full double precision
- **Full-precision float printing** (`%.17g`) — byte-identical to Lateralus
  interpreter and Node.js output

### Benchmarks
- New `benchmarks/` harness with 4 backends: Lateralus-interp, Lateralus-C99,
  CPython, Node.js — all produce byte-identical output (verified per-run)
- `lateralus-c99` lane pre-builds native binaries, gracefully skips on codegen
  failures rather than faking numbers
- **4/5 benchmarks now native** (fib, sieve, mandelbrot, nbody). The last
  benchmark (`binary_trees`) still goes through the interpreter only —
  blocked on `any`-typed returns mixing primitive sentinels with struct
  variants. Needs a proper dynamic-value-representation design pass in the
  typed codegen path (tracked for v3.2)

### Packaging
- **Fixed package description** — removed stale "proprietary" wording (contradicted MIT license)
- Added **project URLs** for Homepage / Documentation / Papers / Repository / Issues / Changelog
- Expanded PyPI **classifiers**: Development Status (4 - Beta), License (OSI/MIT),
  Intended Audience (Developers + Education), additional Topics (Code Generators, Education),
  and Python 3.13 support
- New keywords: `pipeline`, `type-inference`, `transpiler`
- `__init__.py` docstring rewritten to describe real feature set (HM inference, ADTs,
  multi-target codegen) instead of placeholder "proprietary toolkit" text
- Synced `__version__` with `pyproject.toml` (was drifted at 3.0.0 vs 3.0.1)

### Documentation
- All 58 research PDFs rebuilt to **canonical style**
  (Helvetica + Helvetica-Bold + Courier only, no Oblique)
- Content extraction pipeline (`docs/website/papers/src/_extract_and_render.py`)
  preserves original paragraph structure via block-level PyMuPDF parsing
- Eliminated 20-page padding bug on `lateralus-pipeline-native-language.pdf`
- Page counts synchronized across all index cards (0 mismatches across 58 papers,
  total 4,657 pages)
- New [docs/hn-launch-faq.md](docs/hn-launch-faq.md) — 8-category pre-rehearsed
  Q&A covering perf, type system, concurrency, compilation, tooling, and honest
  design regrets

### Developer Experience
- New [scripts/seed_repo_template/](scripts/seed_repo_template/) — one-command
  bootstrap for new Lateralus projects (`new-lateralus-project.sh <name>`).
  Pre-loaded `.gitattributes` so every derived repo forces `linguist-language=Lateralus`
- 1976/1976 tests passing (3 stale `__version__` assertions bumped 3.0.0 → 3.1.0)

---

## [2.4.0] — 2025-07-19 — Deep Internals, Optimizer & Stdlib Expansion

### CLI
- **4 New Subcommands** (total: 26):
  - `bench` — Run micro-benchmarks on compile/parse pipelines
  - `profile` — Profile compilation with per-phase timing breakdown
  - `disasm` — Disassemble `.ltbc` bytecode files to readable `.ltasm`
  - `clean` — Remove build artifacts, caches, and `__pycache__` directories
- Enhanced `info` subcommand with full v1.5–v2.4 feature list
- REPL flags: `--enhanced/-e`, `--no-color`, `--timing`

### VM
- **Disassembler** (`vm/disassembler.py`, ~300 lines):
  - `disassemble()` — Convert Bytecode objects to human-readable `.ltasm` text
  - `disassemble_instruction()` — Single-instruction decode with operand formatting
  - `instruction_length()` — Calculate byte length from OPCODE_META schemas
  - Two-pass: jump target collection → labeled output generation
  - Round-trip verified: assemble → disassemble produces correct output

### Enhanced REPL
- **3 New Commands** (total: 14 special commands):
  - `:save <file>` — Save REPL session history to a file
  - `:doc <topic>` — Look up documentation for 51 builtins/keywords
  - `:profile` — Profile the next expression with per-phase timing
- 51 builtin documentation entries covering all core functions and keywords

### Optimizer
- **3 New Passes** (total: 10):
  - **Dead branch elimination** — Evaluates constant conditions (`if true`, `if false`,
    `if 1 > 2`) and simplifies unreachable branches
  - **Algebraic simplification** — 20 algebraic identities covering additive, multiplicative,
    bitwise, shift, and boolean patterns (e.g., `x + 0 → x`, `x * 1 → x`, `x & 0 → 0`,
    `x | x → x`, `x ^ x → 0`)
  - **Function inlining analysis** — Scores inline candidates based on body size, call
    frequency, purity (no side effects), parameter count, and recursion; provides
    `should_inline` recommendation

### Stdlib
- **7 New Modules** (total: 59):
  - `heap` — Binary min-heap: push, pop, peek, merge, heap_sort, n_smallest
  - `deque` — Double-ended queue: push/pop front/back, rotation, reverse, contains
  - `trie` — Prefix trie: insert, get, has, has_prefix, keys_with_prefix, longest_prefix
  - `ini` — INI config parser/writer: section support, typed getters (int/bool/float), merge
  - `arena` — Region-based memory allocator: block management, O(1) reset/deallocation
  - `pool` — Object pool: acquire/release, bulk ops, drain/shrink, utilization stats
  - `lru` — LRU cache: get/put with eviction, hit/miss tracking, resize, hit_rate

### Tests
- **207 New Tests** (total: 1,976):
  - 52 DAP server tests (`test_dap_server.py`) — All 15 DAP handlers
  - 47 REPL tests (`test_repl.py`) — Basic and enhanced REPL, 9 test classes
  - 61 VM tests (`test_vm_expanded.py`) — Disassembler, round-trip, string/collection ops,
    bitwise, error handling, assembler edges, bytecode objects
  - 47 optimizer tests (in `test_optimizer.py`) — Dead branches, algebraic identities,
    inline analysis; total optimizer tests: 99

---

## [2.3.0] — 2025-07-18 — Tooling & OS Expansion

### Stdlib
- **6 New Modules** (total: 52):
  - `sort` — Sorting algorithms: quicksort, mergesort, insertion sort, selection sort;
    utilities: `nsmallest()`, `nlargest()`, `binary_search()`, `count_inversions()`,
    `is_sorted()`, `sort_by_key()`
  - `set` — Set operations on deduplicated lists: `add()`, `remove()`, `has()`, `union()`,
    `intersection()`, `difference()`, `symmetric_difference()`, `is_subset()`, `is_superset()`,
    `is_disjoint()`, `equals()`, `power_set()`, `map_set()`, `filter_set()`, `fold()`
  - `ringbuf` — Fixed-size circular buffer: `new()`, `push()`, `pop()`, `peek_front()`,
    `peek_back()`, `to_list()`, `at()`, `map_buf()`, `drain()`
  - `semver` — Semantic Versioning 2.0.0 parsing and comparison: `parse()`, `format()`,
    `compare()`, `bump_major()`, `bump_minor()`, `bump_patch()`, `satisfies_caret()`,
    `satisfies_tilde()`
  - `event` — Pub/sub event emitter: `on()`, `once()`, `off()`, `fire()`, `fire_empty()`,
    `event_names()`, `handler_count()`, `pipe()`, `reset()`
  - `template` — String template engine with `<<name>>` delimiters: `render()`, `compile()`,
    `extract_vars()`, `render_each()`, `render_join()`, `escape_html()`, `render_safe()`

### Linter
- **5 New Rules** (total: 21+):
  - `constant-condition` — Flags `if true`, `if false`, `guard true` (WARNING)
  - `unused-import` — Detects imported modules never referenced in source (WARNING)
  - `deep-nesting` — Warns at 5+ indent levels (INFO for 5-6, WARNING for 7+)
  - `string-concat-in-loop` — Detects `+= "..."` inside for/while loops (INFO)
  - `mutable-default` — Detects `fn(param = [])` or `fn(param = {})` (WARNING)

### Formatter
- **Phase 7**: Trailing comma normalization — automatically adds trailing commas before
  closing `}`, `]`, `)` brackets
- **Phase 8**: Blank line collapse — collapses 3+ consecutive blank lines to max 2

### LSP Server
- **Code Actions** with 4 quick fixes:
  - "Use `let` instead of `var`" → replaces `var` with `let`
  - "Unnecessary semicolon" → removes trailing semicolons
  - "Defined but never used" → prefixes unused variable with underscore
  - "Already imported" → removes duplicate import line
- **Rename Symbol** — Whole-document word-boundary rename via `textDocument/rename`
- **Prepare Rename** — Validates rename is possible, returns range and placeholder
- Updated LSP server version to 2.3.0

### Examples
- `v23_showcase.ltl` — Sorting, sets, ring buffers, semver, events, templates (~350 lines)
- `game_of_life.ltl` — Conway's Game of Life with patterns and simulation (~200 lines)
- `interpreter_demo.ltl` — Full arithmetic expression evaluator: tokenizer, parser, AST,
  interpreter, REPL driver (~310 lines)
- All 37 examples compile successfully (37/37)

### Tests
- 37 new tests in `test_v23_features.py` covering all v2.3.0 features
- **Total: 1,769 tests passing**

### LateralusOS
- **7 New Shell Commands** (total: 55+):
  - `top` — Task monitor with summary, uptime, and per-task state/priority
  - `df` — Filesystem usage (ramfs, procfs, devfs)
  - `id` — Display user/group identity info
  - `seq [start] <end>` — Print number sequences
  - `tr <from> <to>` — Character transliteration
  - `rev <string>` — Reverse a string
  - `factor <n>` — Prime factorization

---

## [2.2.0] — 2026-04-20 — Stdlib Expansion & Linter Intelligence

### Language & Toolchain

- **12 New Stdlib Modules** (total: 49):
  - `fmt` — String formatting with `{}` placeholders, `format()`, `printf()`, `sprintf()`,
    padding (`pad_left`/`pad_right`/`pad_center`), number formatting (`hex`/`bin`/`oct`),
    tabular output (`table()`), `repeat()`, `join()`
  - `encoding` — Hex, Base64, and URL encoding/decoding (`hex_encode`/`hex_decode`,
    `base64_encode`/`base64_decode`, `url_encode`/`url_decode`)
  - `csv` — CSV parsing and generation with quote handling; `parse()`, `parse_dict()`,
    `generate()`, `generate_dict()` with configurable delimiters
  - `logging` — Structured logging with 6 severity levels (TRACE/DEBUG/INFO/WARN/ERROR/FATAL);
    `set_level()`, per-level functions, `log_ctx()` for key-value context, `log_if()`, `log_assert()`
  - `filepath` — Path manipulation: `dirname()`, `basename()`, `extension()`, `stem()`,
    `join_path()`, `normalize()` (resolves `.`/`..`), `is_absolute()`/`is_relative()`,
    `has_extension()`, `with_extension()`
  - `uuid` — UUID v4 generation (`uuid4()`), validation (`is_valid()`), version extraction,
    compact/expand forms, namespace constants (DNS, URL, OID, X500)
  - `hash` — Hash functions: `fnv1a_32()`, `fnv1a_64()`, `djb2()`, `sdbm()`;
    checksums: `checksum8()`, `fletcher16()`, `adler32()`;
    utilities: `combine()` (boost-style), `hash_list()`, `bucket()`
  - `color` — Color construction (`rgb()`, `rgba()`), channel extraction, `to_hex()`;
    manipulation: `lighten()`, `darken()`, `mix()`, `invert()`, `grayscale()`;
    12 named constants + 9 Lateralus theme colors
  - `queue` — Double-ended queue with `push_back`/`push_front`/`pop_front`/`pop_back`,
    `front()`/`back()` peek, `drain()`, `concat()`, `filter_queue()`, `map_queue()`
  - `stack` — LIFO stack with `push()`/`pop()`/`peek()`, `swap_top()`, `dup()`, `drop()`,
    `fold()`, `contains()`, `reversed()`
  - `base64` — RFC 4648 Base64 encoding/decoding: `encode()`/`decode()`,
    URL-safe variants (`encode_url`/`decode_url`), `is_valid()`,
    `encoded_length()`/`decoded_length()`
  - `bitset` — Fixed-size bitset with `set()`/`clear()`/`test()`/`toggle()`,
    set operations: `union()`/`intersection()`/`difference()`/`symmetric_difference()`,
    `is_subset()`, `count()` (popcount), `to_binary_string()`

- **4 New Linter Rules**:
  - `unreachable-code` (WARNING) — Detects dead code after `return`, `break`, `continue` statements
  - `duplicate-import` (WARNING) — Flags modules imported more than once, with suggestion to remove
  - `shadowed-variable` (INFO) — Warns when a variable shadows an earlier definition
  - `todo-comment` (HINT) — Surfaces TODO, FIXME, HACK, and XXX comments in lint output

- **IR: `COND_SELECT` opcode** — Added ternary conditional selection to the IR layer, fixing
  compilation of ternary expressions (`? :`) in modules that pass through semantic analysis

- **42 new tests** covering all new linter rules, stdlib module compilation, import validation,
  and integration testing. Total: **1,734 tests passing**.

### LateralusOS v0.3.0 — Virtual Filesystems, Signals & Shell UX

- **/proc Virtual Filesystem** (`fs/procfs.c`, ~330 lines): Full `/proc` implementation exposing
  live kernel state as 9 readable pseudo-files:
  - `/proc/version` — OS name, version, build info
  - `/proc/uptime` — System uptime in seconds (from tick_count)
  - `/proc/meminfo` — Heap statistics (total, used, free, peak, allocations)
  - `/proc/cpuinfo` — CPU vendor string and feature flags (via CPUID)
  - `/proc/loadavg` — 1-min/5-min/15-min load averages from scheduler
  - `/proc/tasks` — Process table dump (TID, state, priority, name for all 32 slots)
  - `/proc/net` — Network configuration (IP, mask, gateway, DNS, state)
  - `/proc/mounts` — Mounted filesystem list (ramfs, procfs, devfs)
  - `/proc/cmdline` — Boot command line
  Auto-refreshes on `cat /proc/*` to always show current data.

- **/dev Virtual Device Filesystem** (`fs/devfs.c`, ~220 lines): 5 pseudo-device files:
  - `/dev/null` — Always empty (discard sink)
  - `/dev/zero` — Continuous zero stream description
  - `/dev/random` — Pseudo-random hex data (xorshift64 LFSR seeded from tick_count)
  - `/dev/serial` — COM1 serial port info (base 0x3F8, baud 115200)
  - `/dev/fb0` — Framebuffer info (resolution, bpp, address from boot_info)
  Auto-refreshes on `cat /dev/*` for live data.

- **Filesystem Initialization Fix**: Moved `ramfs_init()` from GUI-only path to `kernel_main()`
  text path. All three virtual filesystems (ramfs, procfs, devfs) now initialize in Phase 8b
  of kernel boot, before shell startup.

- **Signal Infrastructure**: Upgraded `cmd_kill()` to support named signals
  (`TERM`, `KILL`, `INT`, `STOP`, `CONT`, `USR1`, `USR2`, `ALARM`) and numeric signal values.
  Syntax: `kill <tid> [TERM|KILL|INT|STOP|CONT|USR1|USR2|ALARM|<number>]` (default: TERM).
  Updated `sys_kill_task` syscall to route through `sched_signal()`.

- **Environment Variable Expansion**: Shell now expands `$VAR` and `${VAR}` references
  in commands before execution. Supports `$?` for last exit code. New `env_get()`,
  `env_unset()`, `env_expand()` internal functions.

- **Alias System**: Full alias support with `alias`, `unalias` commands.
  Default aliases: `ll` → `ls`, `h` → `history`, `cls` → `clear`.
  Supports `alias name=command` and `alias name="multi word command"`.
  Up to 16 aliases with 32-char names and 128-char expansions.

- **Bang History Expansion**: `!N` syntax recalls and re-executes history entry N.

- **`unset` command**: Remove environment variables from the shell.

- **Load Average Tracking**: Exponentially weighted moving average (EMA) load tracking
  in the scheduler. Samples every 5 seconds, tracks 1-min/5-min/15-min averages
  using fixed-point arithmetic (×100). Alpha values: 8%, 2%, 1%.

- **Upgraded `uptime` command**: Now shows days/hours/minutes/seconds, active task count
  from `sched_stats()`, and three load averages in `X.XX X.XX X.XX` format.

- **Tab completion**: Added `alias`, `unalias`, `unset` to shell auto-complete.

---

## [2.1.0] — 2026-04-19 — Kernel Decomposition & Network Stack (continued)

### LateralusOS v0.3.0 — Process Table & TCP Transport

- **Process Table & Scheduler Upgrade**: Extended `SchedTask` struct with `parent_tid`,
  `wait_tid`, `vfs_task_id` fields for proper parent-child process relationships.
  New API: `sched_wait()` (blocks parent, returns child exit code), `sched_reap()`
  (frees dead task stacks via `kfree`, periodic garbage collection every ~1s),
  `sched_get_task()` (const pointer access for ps/monitoring).
  Dead task reaping auto-runs in `sched_tick()` every 1024 ticks.

- **Syscall Upgrades**: Fixed `sys_getpid` to return `sched_current_tid()` (was hardcoded 1).
  Fixed `sys_sleep` to use `sched_sleep()` (was busy-wait `hlt` loop).
  Fixed `sys_yield` to use `sched_yield()` (was single `hlt`).
  Added: `sys_spawn` (SYS_SPAWN=25), `sys_wait` (SYS_WAIT=7), `sys_kill_task` (SYS_KILL=22).
  Now **23 registered syscall handlers**.

- **Shell `spawn` Command**: Spawn background daemon tasks from the shell.
  Available tasks: `heartbeat [secs]` (periodic serial output),
  `counter [n]` (count to n then exit), `netpoll` (network polling daemon).
  Shows task name, TID, and priority on creation.

- **Live `ps` Rewrite**: `ps` command now shows real scheduler data — iterates
  `sched_get_task(0..31)`, displays TID, STATE, PRIO, NAME with color coding
  (green=RUNNING, cyan=READY, yellow=SLEEPING, red=DEAD, gray=BLOCKED).

- **Netpoll Daemon**: Automatically spawned at boot as a high-priority daemon (tid=1).
  Calls `ip_poll()` and `tcp_tick()` at 10 Hz for continuous network + TCP timer service.

- **TCP Transport Layer**: Full TCP/IP implementation in `net/tcp.h` + `net/tcp.c` (~650 lines).
  - RFC 793 state machine: 11 states (CLOSED → LISTEN → SYN_SENT → SYN_RECEIVED →
    ESTABLISHED → FIN_WAIT_1/2 → CLOSE_WAIT → CLOSING → LAST_ACK → TIME_WAIT).
  - 8 concurrent connection slots, 4 KB circular receive buffer per connection.
  - `tcp_connect()` (active open), `tcp_listen()` (passive open), `tcp_send()`,
    `tcp_read()`, `tcp_close()` (graceful FIN sequence).
  - RFC-compliant checksum with pseudo-header, MSS=1460, window size=4096.
  - Retransmit timer (3s, 5 retries), TIME_WAIT cleanup (5s).
  - IP layer dispatches protocol 6 (TCP) to `tcp_recv()` state machine.
  - `tcp` shell command displays active connections with state/color coding.
  - `tcp dump` sends detailed connection table to serial for debugging.

- **Build Pipeline**: 22-step build (was 21). Kernel size: 695,976 bytes.
  Zero warnings, zero errors. OS boots with all subsystems initialized.

---

## [2.1.0] — 2026-04-19 — Kernel Decomposition & Network Stack

### LateralusOS v0.3.0 — Kernel Infrastructure
- **Heap Module Extraction**: Isolated heap allocator from monolithic kernel_stub.c into
  `kernel/heap.h` + `kernel/heap.c`. New API: `kmalloc`, `kcalloc`, `krealloc`, `kfree`,
  `heap_get_stats`, `heap_dump_stats`. Free-list + bump allocation with 16-byte alignment,
  block splitting (MIN_SPLIT=64), and double-free detection (magic=0xDEADBEEF).
- **Virtual File System**: Full VFS layer in `fs/vfs.h` + `fs/vfs.c` (~340 lines).
  32 file descriptors per task, fd types: FILE, CONSOLE, PIPE_READ, PIPE_WRITE, NULL.
  Operations: open (O_CREAT/O_TRUNC/O_APPEND), read, write, close, seek, dup, dup2, pipe.
  Auto-allocates fd 0/1/2 as console for new tasks. `/dev/null` support.
- **Syscall Table Expansion**: 20 registered syscall handlers, VFS-backed sys_read/write/open/close.
  New: `sys_pipe` (SYS_PIPE=20), `sys_dup` (SYS_DUP=21).
- **Shell Pipe & Redirect**: Capture buffer infrastructure hooked into `k_putc`.
  Pipe (`|`) with built-in targets: `grep` (substring filter), `wc` (lines/words/bytes),
  `head -N`, `tail -N`. Redirect: `>` (overwrite), `>>` (append) to ramfs files.
- **IPv4/ARP/UDP/ICMP/DHCP Network Stack**: Full implementation in `net/ip.h` + `net/ip.c`
  (~740 lines). ARP cache (16 entries), IPv4 send with gateway routing, ICMP echo request/reply,
  UDP bind/send/receive (8 port bindings), DHCP client (DISCOVER → OFFER → REQUEST → ACK
  with 5-second timeout). Auto-DHCP during boot with static fallback (10.0.2.15).
- **Upgraded Shell Commands**: `ifconfig` shows IPv4/netmask/gateway/DNS, `ping` uses real
  ICMP echo requests (3 pings, 2s timeout), `arp` uses IP stack's ARP dump.
  New: `dhcp` command for manual DHCP lease renewal.
- **Build pipeline**: 20-step build process (gcc C99 freestanding + nasm elf64).
  Zero warnings, zero errors. OS boots in QEMU with all subsystems initialized.

### Codegen Improvements
- **Block lambda fix**: `fn(x) { expr }` anonymous functions now correctly transpile
  to Python inline lambdas with multi-statement hoisting support.
- **Interface codegen**: ABC-style abstract class generation from interface declarations.
- **Type annotation mapping**: `fn` → `callable`, `map` → `dict` in Python transpiler.
- **Stdlib shims**: `join()`, `sqrt()`, runtime math builtins wired through codegen.
- **C backend fix**: `_temp()` variable collision resolved in C transpiler.

### Showcase
- `v21_showcase.ltl` (401 lines) — enum pattern matching, interface dispatch, pipelines,
  result types, iterators, string processing, matrix operations, state machines.

### Infrastructure
- **32 new tests** in `test_v21_features.py` — block lambda codegen, interface codegen,
  type mapping, pipeline + lambda composition, stdlib shims, showcase compilation.
- **1,670 total tests passing**, 0 failures.
- **30+ example programs**, all compiling successfully.

---

## [2.0.0] — 2026-04-18 — Self-Hosting

### Bootstrap Compiler in Lateralus
- **5 bootstrap modules** written in Lateralus itself, all compiling with the production compiler:
  - `v2_lexer.ltl` (~509 lines) — full tokenizer with keyword lookup, string/number literals, operators
  - `v2_parser.ltl` (~900 lines) — recursive descent parser, 55 node types, 15+ parse functions
  - `v2_codegen.ltl` (~270 lines) — IR code generation from AST
  - `v2_ir_codegen.ltl` (~641 lines) — IR-level optimizations and lowering
  - `v2_python_codegen.ltl` (~500 lines) — Python transpiler with full AST visitor
- Bootstrap parser handles: struct, enum, match, trait, impl, for, while, try/catch,
  lambda, pipe, spread, decorators, async/await, guard, import, type alias
- 6 parser limitations documented and worked around (map literals, `type` keyword,
  while conditions, match delimiters, slice syntax, `emit` keyword)

### Grammar Specification
- `docs/grammar.ebnf` updated from v1.5 to v2.0 (339 → 458 lines).
- 13 new keywords: `select`, `nursery`, `cancel`, `unsafe`, `static`, `extern`, `mut`,
  `macro`, `comptime`, `type`, `trait`.
- 12 new statement productions covering v1.6 structured concurrency, v1.8 metaprogramming,
  v1.9 FFI, and v1.5 traits/type aliases.
- 8 new primary expressions: `cancel_expr`, `channel_expr`, `parallel_expr`, `inline_asm`,
  `macro_invocation`, `addr_of_expr`, `deref_expr`, `alignof_expr`.
- Updated operator precedence table and decorator documentation.

### LateralusOS v0.2.0
- **7 new shell commands** (28 total):
  - `whoami` — prints "root"
  - `hostname` — prints "lateralus"
  - `date` — reads CMOS RTC, displays formatted UTC date/time with BCD conversion
  - `ps` — process listing (kernel, ltlsh, idle)
  - `sysinfo` — bordered system info box with CPU vendor (CPUID), memory, arch
  - `cal` — mini calendar display
  - `write <file> <content>` — write text to ramfs files in /home
- Version strings updated: OS v0.1.0 → v0.2.0, Language v1.5.0 → v2.0.0, ltlsh 0.1.0 → 0.2.0

### Showcase
- `v20_showcase.ltl` (~310 lines) — self-contained mini compiler pipeline written in Lateralus:
  tokenizer (14 keywords), recursive descent parser, dual-target code generator (Python + C),
  compilation pipeline with statistics, built-in verification suite.

### Infrastructure
- **60 new tests** in `test_v20_features.py` across 9 test classes:
  `TestBootstrapCompilation`, `TestV16Parsing`, `TestV18Parsing`, `TestV19Parsing`,
  `TestGrammarSpec`, `TestShowcaseCompilation`, `TestMultiTarget`,
  `TestBootstrapParserCoverage`, `TestLexerKeywords`.
- **1,638 total tests passing**, 0 failures.
- **30 example programs**, all compiling successfully.

---

## [1.9.0] — 2026-04-17 — FFI & Ecosystem

### C FFI Bridge (`lateralus_lang/ffi.py`)
- `load_library(name)` — platform-aware search with `ctypes` (`.so`, `.dylib`, `.dll`).
  Cached library handles with 4-step resolution (direct path, lib prefix, system dirs).
- `FFIFunction` dataclass — lazy binding with auto type coercion between LTL and C types.
  Supports: `int`, `float`, `str`, `bool`, `void`, `size_t`, `uint8`, `int64`, pointer types.
- `FFIRegistry` class — register and call external C functions with type-safe wrappers.
  Methods: `declare_function()`, `declare_struct()`, `call()`, `get_function()`, `get_struct()`.
- `define_ffi_struct(name, fields)` — create ctypes `Structure` subclasses dynamically.
- Memory utilities: `ffi_alloc()`, `ffi_free()`, `ffi_read_string()`, `ffi_write_string()`.
- `get_ffi_builtins()` — returns runtime FFI functions for LTL VM integration.

### JavaScript Target
- `Target.JAVASCRIPT` in compiler Target enum.
- `lateralus js <file> [-o output.js] [--format esm|cjs|iife]` CLI command.
- Full transpilation to JavaScript ES2022+ via `JavaScriptTranspiler`.
- Module format options: ES Modules (default), CommonJS, and IIFE.

### WASM Target
- `Target.WASM` in compiler Target enum.
- `lateralus wasm <file> [-o output.wat]` CLI command.
- Compilation to WebAssembly Text Format (WAT) via `WasmCompiler`.

### Jupyter Kernel
- `LateralusKernel` class with full kernel protocol implementation.
- `do_execute()` — compile LTL source → Python → exec with stdout/stderr capture.
- `do_complete()` — keyword, builtin, and namespace completions.
- `do_inspect()` — symbol inspection and documentation lookup.
- `do_is_complete()` — brace-counting heuristic for multiline input.
- `install_kernel()` — register with Jupyter via `jupyter_client` or manual fallback.
- ipykernel integration via dynamic `IPythonLateralusKernel` subclass.

### C Backend Enhancements
- Added v1.6 async visitors: `_visit_NurseryBlock` (sequential fallback),
  `_visit_AsyncForStmt` (sync for-loop), `_expr_ChannelExpr`, `_expr_CancelExpr`.
- Added v1.7 cfg visitors: `_visit_CfgAttr` (→ `#if defined()`),
  `_expr_CfgExpr` (→ `defined()` ternary).
- Added v1.8 metaprogramming visitors: `_visit_ConstFnDecl` (→ `static inline`),
  `_visit_MacroDecl` (→ `#define`), `_visit_MacroInvocation`,
  `_visit_CompTimeBlock`, `_visit_DeriveAttr`, `_expr_ReflectExpr`,
  `_expr_QuoteExpr`, `_expr_UnquoteExpr`.

### LateralusOS
- **Network Shell Commands**: 4 new commands bring total to 21:
  - `ifconfig` — display eth0 interface info (MAC, link, IO base, IRQ, TX/RX stats)
  - `netstat` — network statistics (packets, bytes, errors)
  - `ping <host>` — ARP broadcast probing with 3-packet send/receive
  - `arp` — display ARP table entries

### Infrastructure
- **50 new tests** in `test_v19_features.py` across 8 test classes:
  `TestTargetEnum`, `TestJavaScript`, `TestWASM`, `TestFFI`, `TestJupyterKernel`,
  `TestCBackendV18`, `TestV19Showcase`, `TestCompileResult`.
- **1,549 total tests passing**, 0 failures.
- **30 example programs**, all compiling successfully.
- New showcase: `v19_showcase.ltl` (180 lines) — Vector2D, Matrix2x2, Shape enum,
  pipeline processing, const fn, FFI buffers, signal processing, Result types.

---

## [1.8.0] — 2026-04-16 — Metaprogramming

### Compile-Time Evaluation
- `const fn` declarations — functions decorated with `@_lru_cache(maxsize=None)` for
  compile-time memoized evaluation. Supports full parameter lists and return types.

### Procedural Macros
- `macro name!(params) { body }` — define procedural macros that expand at compile time.
  Compiled to `_macro_name()` Python functions.
- `name!(args)` invocation syntax — expands to `_macro_name(args)` calls.
  Works in all expression contexts: `let`, `return`, function arguments, etc.

### AST Transformation
- `quote { ... }` — capture AST fragments as data (`{"__ast__": [...]}`).
- `$ident` / `${expr}` — unquote (splicing) within quote blocks.
- `comptime { ... }` — inline compile-time block execution with marker comments.

### Derive System (`@derive`)
- `@derive(Trait1, Trait2, ...)` on `struct` and `enum` declarations.
- **8 built-in derive traits**:
  - `Debug` → `__repr__` method
  - `Display` → `__str__` method
  - `Eq` → `__eq__` method
  - `Hash` → `__hash__` method
  - `Clone` → `clone()` method
  - `Default` → `default()` classmethod
  - `Serialize` → `to_dict()` method
  - `Deserialize` → `from_dict()` classmethod

### Reflection API
- `reflect!(Type)` — compile-time type introspection returning
  `{name, kind, fields, methods}` dict via `_type_info()` runtime helper.
- Supports struct (dataclass) field extraction and enum detection.

### Infrastructure
- **4 new lexer keywords**: `macro`, `comptime`, `derive`, `reflect`
- **8 new AST nodes**: `ConstFnDecl`, `MacroDecl`, `MacroInvocation`,
  `CompTimeBlock`, `DeriveAttr`, `ReflectExpr`, `QuoteExpr`, `UnquoteExpr`
- **56 new tests** in `test_v18_features.py` covering lexer, AST, parser,
  codegen, derive traits, and integration scenarios.

---

## [1.7.0] — 2026-04-15 — Package Manager & Build System

### Package Manager

#### `lateralus.toml` Manifest
- Replaced `lateralus.json` with TOML-based manifest (`lateralus.toml`).
- Lightweight TOML parser bundled (no external dependencies); supports
  strings, integers, floats, booleans, arrays, tables, inline tables,
  multiline arrays, and inline comments.
- Full `ProjectManifest` class with `from_toml()`, `from_json()` (legacy),
  `from_file()`, `to_toml()`, `save()` and round-trip support.

#### Dependency Resolution
- `SemVer` with compound constraints (`>=1.0,<2.0`), caret (`^`), tilde
  (`~`), range, wildcard (`*`), and exact pinning.
- `DepGraph` with topological sort and cycle detection.
- `DependencyResolver` with transitive resolution, local path / git / registry
  source support.
- `LockFile` / `LockEntry` for reproducible builds.

#### Publishing
- `PackageBundle.create()` with SHA-256 integrity hash.
- `lateralus publish` (and `--dry-run`) CLI command.

### Build System

#### Build Profiles
- `BuildProfile` dataclass: `opt_level`, `debug`, `strip`, `lto`, `features`,
  `target`, `extra_flags`.
- Default profiles: `debug` (O0, debug), `release` (O3, strip, lto),
  `bench` (O3, bench feature).
- `lateralus build --profile <name>`.

#### Workspaces
- `Workspace` dataclass with glob-based member resolution and exclude
  patterns, shared dependencies.

### Conditional Compilation

#### `@cfg` Decorator
- `@cfg(target, "python")` — strips decorated `fn`, `struct`, or `enum`
  from codegen when the condition is false.
- Keys: `target`, `os`, `profile`, `feature`, plus custom keys.

#### `cfg!()` Expression
- `cfg!(target, "python")` — compile-time boolean expression.
- Evaluates against `CfgContext` (target, os, profile, features, custom keys).
- Usable in `if`, `let`, and any expression position.

### CLI
- `lateralus init [name] [--template lib|bin|workspace]` — scaffold project.
- `lateralus add <pkg> [--version X] [--git URL] [--dev]` — add dependency.
- `lateralus publish [--dry-run]` — create and verify package bundle.
- Updated `lateralus info` with v1.6 and v1.7 feature lists.

### Testing
- 71 new tests (1,443 total), 28 compiling examples.
- `v17_showcase.ltl` demonstrating @cfg, cfg!(), packages, profiles.

---

## [1.6.0] — 2026-04-01 — Concurrency & Async

### Language — New Constructs

#### Structured Concurrency: `nursery` blocks
- `nursery { spawn task1(); spawn task2() }` — spawns tasks that are
  guaranteed to complete before the nursery exits.
- Named nurseries: `nursery workers { ... }` for clarity.
- Automatic cancellation of sibling tasks on first failure.

#### Channels: `channel<T>(capacity)`
- `let ch = channel<int>(10)` — typed, buffered channel.
- `channel(5)` — untyped channel with capacity.
- `channel<str>()` — unbuffered typed channel.
- Thread-safe `send()`/`recv()` with `try_send()`/`try_recv()` variants.
- `close()`, `is_closed`, `len()`, iterator support.

#### Select Statement
- Multiplexes across channels with recv/send/timeout/default arms:
  ```
  select {
      msg from inbox => { handle(msg) }
      send(outbox, data) => { log("sent") }
      after 1000 => { handle_timeout() }
      _ => { handle_default() }
  }
  ```

#### Async For
- `async for event in stream { process(event) }` — iterate over async
  streams/generators.

#### Cancellation Tokens
- `let token = cancel` — creates a `CancellationToken`.
- `token.cancel(reason)`, `token.is_cancelled`, `token.check()`.
- `token.on_cancel(callback)` — register cleanup handlers.
- `CancelledError` exception on cancelled `.check()`.

#### Parallel Combinators
- `parallel_map(items, fn)` — parallel map across items using thread pool.
- `parallel_filter(items, fn)` — parallel predicate filtering.
- `parallel_reduce(items, fn, init)` — tree-reduce in parallel chunks.

### Compiler

#### AST Nodes (7 new)
- `SelectArm` — kind, channel, binding, value, body.
- `SelectStmt` — list of `SelectArm`.
- `ChannelExpr` — elem_type + capacity.
- `NurseryBlock` — body + optional name.
- `CancelExpr` — creates a cancellation token.
- `AsyncForStmt` — var, iter, body.
- `ParallelExpr` — kind (map/filter/reduce), items, func, init.

#### Lexer
- 3 new keyword tokens: `KW_SELECT`, `KW_NURSERY`, `KW_CANCEL`.

#### Parser
- `_parse_select()` — full select statement with recv/send/timeout/default arms.
- `_parse_nursery()` — nursery blocks with optional name label.
- `_parse_async_for()` — `async for x in stream { ... }`.
- Channel expression: `channel<T>(cap)` with optional generic type.
- Parallel expressions: `parallel_map/filter/reduce(items, fn[, init])`.
- Fixed `from` keyword handling in select recv arms (KW_FROM vs IDENT).

#### Python Codegen
- `visit_SelectStmt` — polling loop with `try_recv`/`try_send`, timeout via
  `time.monotonic()`, default arm.
- `visit_NurseryBlock` — `with _Nursery() as name:` context manager.
- `visit_AsyncForStmt` — `async for var in iter:`.
- `ChannelExpr` → `_Channel(capacity)`.
- `CancelExpr` → `_CancellationToken()`.
- `ParallelExpr` → `_parallel_map/filter/reduce(fn, items[, init])`.

### Async Runtime (`async_runtime.py`)
- `CancellationToken` — thread-safe cancel/check/on_cancel with callbacks.
- `CancelledError` — exception for cancelled operations.
- `Nursery` — structured concurrency using `ThreadPoolExecutor`, auto-cancels
  siblings on failure, context manager interface.
- `select(*channels, timeout)` — polls channels, returns first available value.
- `parallel_reduce(fn, items, initial, workers)` — chunk-based tree reduction.
- Updated `ASYNC_BUILTINS` registry with all new entries.

### Test Suite
- **68 new tests** (1,304 → 1,372):
  - `TestV16Lexer` (6): keyword token recognition.
  - `TestParseSelect` (6): recv/send/timeout/default arms, multi-arm, compilation.
  - `TestParseNursery` (4): basic, named, multi-spawn, compilation.
  - `TestParseChannel` (4): typed buffered/unbuffered, untyped, compilation.
  - `TestParseCancel` (2): cancel expression, compilation.
  - `TestParseAsyncFor` (2): async for parsing and compilation.
  - `TestParseParallel` (6): parallel_map/filter/reduce parse and compile.
  - `TestRuntimeChannel` (6): send/recv, try ops, close, iter, len, threaded.
  - `TestRuntimeCancellation` (5): basic, reason, callback, check raises, idempotent.
  - `TestRuntimeNursery` (4): basic, error propagation, cancel token, results.
  - `TestRuntimeSelect` (3): single channel, multiple, timeout.
  - `TestRuntimeParallel` (6): map, filter, reduce, reduce+initial, empty cases.
  - `TestRuntimeTaskGroup` (3): spawn+wait, wait_first, cancel_all.
  - `TestRuntimeRateLimiter` (2): acquire, refill.
  - `TestV16Integration` (9): async fn, spawn, await, full program, pipeline,
    select+channel, cancel, async for, header version.

### Examples
- `v16_showcase.ltl` (NEW): Demonstrates channels, nursery, select, cancel,
  async for, parallel_map/filter/reduce, and concurrent pipelines.

---

## [1.5.2] — 2026-04-01 — Kernel Concurrency & Backend Coverage

### LateralusOS — Preemptive Scheduler & IPC

#### Preemptive Scheduler (`kernel/sched.h`, `kernel/sched.c`)
- Full preemptive round-robin scheduler with inline-asm context switching.
- 4 priority levels, configurable timeslice (default 10 ticks).
- 32 task slots, each with a 16KB stack.
- `sched_spawn()`, `sched_yield()`, `sched_exit()` for task lifecycle.
- `sched_sleep()` with tick-based wakeup, `sched_block()`/`sched_unblock()`
  for synchronization primitives.
- `sched_list()` serial diagnostic output with task states.
- Wired into `irq0_handler` for timer-driven preemption.

#### IPC Message Queues (`kernel/ipc.h`, `kernel/ipc.c`)
- Ring-buffer message queue system: 16 queues × 32 capacity × 256-byte messages.
- Blocking `ipc_send()`/`ipc_recv()` using scheduler block/unblock.
- Non-blocking `ipc_try_send()`/`ipc_try_recv()` variants.
- Named queue lookup via `ipc_find()`, queue destruction via `ipc_destroy()`.
- `ipc_peek()`, `ipc_pending()`, `ipc_list()` introspection.
- Stats tracking: total sent/received/dropped per queue.

#### Build System
- Build steps: 14 → 16 (added `kernel/sched.o`, `kernel/ipc.o`).
- `kernel_stub.c`: replaced Phase 10/11 stubs with real `ipc_init()` and
  `sched_init()` calls; added `sched_tick()` to timer interrupt handler.
- Kernel size: ~550KB, ISO: 10M.

### Bootstrap
- **`bootstrap/v2_ir_codegen.ltl`** (NEW, ~500 lines): Self-hosted IR code
  generator translating AST to SSA-like IR. Handles 14 expression types,
  7 statement types. `compile_to_ir()` pipeline: Source → Tokens → AST → IR
  → human-readable text. `ir_stats()` provides compiler statistics.

### WASM Backend
- Fixed missing `import re` in `codegen/wasm.py` — was causing `NameError`
  in `expression_to_wat()`.

### Test Suite
- **99 new tests** (1,205 → 1,304):
  - 38 WASM backend tests: `TestWasmType` (8), `TestWatInstructions` (8),
    `TestWasmModule` (8), `TestWasmCompiler` (4), `TestCompileToWasm` (3),
    `TestWatSerialization` (3), `TestWasmIntegration` (4).
  - 61 JS backend tests: `TestJSBuffer` (6), `TestOperatorMapping` (12),
    `TestJSRuntime` (12), `TestJavaScriptTranspiler` (12),
    `TestExpressionTranslation` (7), `TestParamTranslation` (5),
    `TestLineTranslation` (5), `TestJSIntegration` (5).
- All 1,304 tests pass in ~1.9s.

---

## [1.5.1] — 2026-04-01 — Hardening & OS Drivers

### Parser
- **`else if` syntax**: Parser now accepts `else if` as an alias for `elif`,
  enabling both `elif` and `else if` interchangeably in if-chains.
- Added `_peek_next_is()` helper for multi-token lookahead.

### LSP Server v2 Features
- **Document symbols**: `textDocument/documentSymbol` — reports functions,
  structs, enums, traits, constants, and top-level bindings with proper
  SymbolKind values and location ranges.
- **Go to definition**: `textDocument/definition` — finds declarations of
  identifiers by scanning the document for `fn`, `let`, `const`, `struct`,
  `enum`, `trait` definitions.
- **Find references**: `textDocument/references` — word-boundary search for
  all occurrences of an identifier, with option to include/exclude declaration.
- **Signature help**: `textDocument/signatureHelp` — shows function signatures
  and highlights active parameter as user types arguments.
- **Code formatting**: `textDocument/formatting` — integrates the formatter
  module for on-demand code formatting.
- Fixed `doc.source` → `doc.text` bug in formatting handler.

### CLI Extensions
- `lateralus fmt <file>` — format Lateralus source files.
- `lateralus lint <file>` — run linter checks.
- `lateralus lsp` — start the Language Server Protocol server.
- `lateralus dap` — start the Debug Adapter Protocol server.
- `lateralus-dap` entry point added to `pyproject.toml`.

### Formatter
- v1.5 block recognition: `enum`, `struct`, `impl`, `trait`, `pub fn`,
  `pub struct`, `pub enum`, `async fn` now get blank-line spacing.
- Fixed blank-line insertion to trigger before any block declaration when
  preceded by non-empty code (not just after `}`).

### Linter
- Added 12 v1.5 keywords to reserved word set: `enum`, `impl`, `trait`,
  `async`, `await`, `yield`, `spawn`, `chan`, `select`, `Result`, `Option`, `none`.

### C Backend Hardening
- Added 8 missing AST node visitors: `EmitStmt`, `MeasureBlock`,
  `PipelineAssign`, `GuardExpr`, `WhereClause`, `SpreadExpr`, `TryExpr`,
  `ProbeExpr` — all 8 now emit correct C code instead of silent TODO comments.
- Cleaned up fallback messages: `TODO:` → `unsupported:` for clarity.
- JavaScript backend: same cleanup for unknown node handler.

### Standard Library
- **`stdlib/channel.ltl`** (NEW): CSP-style channel primitives for concurrent
  communication. `channel_new`, `channel_send`, `channel_recv`, `try_send`,
  `try_recv`, `channel_close`, `select`, `select_timeout`, `fan_out`,
  `fan_in`, `pipeline`, `drain`, `collect`, `stats`. (34 modules total)

### Test Suite
- **47 new tests** (1,158 → 1,205):
  - 5 parser tests for `else if` syntax.
  - 30 LSP server tests: document symbols (14), definition (7),
    references (4), signature help (5), protocol-level v2 (7).
  - 5 formatter tests for v1.5 block spacing.
- All 1,205 tests pass in ~1.8s.

### IR
- Fixed `IROp.RAISE` → `IROp.THROW` alignment with AST naming convention.

### REPL
- Updated version banner from v1.1.0 → v1.5.0.

### Example Programs
- Fixed all 26 examples to compile cleanly (0 failures).
- Cleaned up syntax issues: `as` casts, `import` statements,
  `fn` lambdas, generic type annotations, map literal patterns.

### LateralusOS — Drivers & Syscalls

#### ATA PIO Disk Driver (`drivers/ata.h`, `drivers/ata.c`)
- Full ATA PIO mode disk driver for the primary IDE controller.
- IDENTIFY command: detects master/slave drives, reads model, serial,
  sector count, and size.
- `ata_read_sectors()`: 28-bit LBA sector reads with polling.
- `ata_write_sectors()`: Sector writes with automatic cache flush.
- `ata_flush()`: Explicit cache flush command.
- Wired into kernel boot sequence as Phase 7 (disk detection).

#### Syscall Dispatch Table (`kernel/syscall.h`, `kernel/syscall.c`)
- Proper syscall dispatch table with 15 functional handlers replacing
  the previous "38 syscalls registered (stub)" message.
- Implemented syscalls: `exit`, `read`, `write`, `open`, `close`,
  `getpid`, `sleep`, `yield`, `brk`, `time`, `disk_read`, `disk_write`,
  `disk_info`, `uptime`, `reboot`.
- `sys_write` to fd 1/2 outputs to serial port.
- `sys_sleep` uses PIT tick counter for millisecond-precision delays.
- `sys_reboot` performs triple-fault reboot.

#### Network Driver (`drivers/net.h`, `drivers/net.c`)
- RTL8139 PCI Ethernet NIC driver with PCI bus scan.
- Hardware init: reset, MAC read, RX/TX buffer allocation, bus mastering.
- `net_send()`: raw Ethernet frame transmission via TX descriptors.
- `net_recv()`: polled packet reception from RX ring buffer.
- `net_link_up()`, `net_mac_str()`, `net_get_info()` status queries.
- Wired into kernel boot sequence as Phase 9 (NIC detection).

#### Syscall Extensions
- Added `SYS_NET_SEND` (38), `SYS_NET_RECV` (39), `SYS_NET_INFO` (40).
- Syscall table: 15 → 18 handlers.

#### Parser Fix
- Fixed incomplete `_parse_guard()`: method now parses the else-block
  and returns a proper `GuardExpr` instead of `None`.
- Added `None`-skip guard in `visit_BlockStmt` (defensive).

#### Build System
- Build steps: 11 → 14 (added `drivers/ata.o`, `drivers/net.o`,
  `kernel/syscall.o`).
- Made `serial_puts()` and `kmalloc()` non-static for cross-module linking.

#### Boot Sequence
- Phase 7: ATA disk detection (reports drive model, size).
- Phase 8: Syscall table initialization (reports handler count).
- Phase 9: Network adapter detection (reports MAC, IRQ).
- Phases 10-11: IPC + Scheduler (stubs, renumbered).

---

## [1.5.0] — 2026-03-31 — ADT Edition

### LSP Server v1.5.0
- **Compiler-powered diagnostics**: `lsp_server.py` now invokes the full
  compiler pipeline (Lex → Parse → Semantic analysis) for real-time
  parse errors, type errors, and semantic warnings in the editor.
- Severity mapping: LTL `FATAL`/`ERROR`/`WARNING`/`INFO`/`HINT` →
  LSP severity levels with suggested-fix annotations.
- **New completions**: v1.5 keywords (`enum`, `impl`, `trait`, `async`,
  `await`, `yield`), types (`Iterator`, `Comparable`, `Hashable`),
  snippets (`enum`, `Result match`, `Option match`, `impl`, `test`).
- Server version bumped 0.1.0 → 1.5.0.

### Gradual Typing (v1.5)
- **`GradualType`** class in `type_system.py`: wraps a known static type
  and permits interop with `any`-typed code without compile-time errors.
  Mismatches are deferred to runtime casts (Siek & Taha 2006).
- `TypeKind.GRADUAL` added to the type kind enum.
- `DYNAMIC` constant (`GradualType(ANY)`) for fully-dynamic boundaries.
- `parse_type_annotation` handles `~T` syntax for gradual types.
- `TypeChecker.check_assignment` skips static checking when either
  side is a `GradualType`.

### VS Code Extension
- **Grammar**: Added `trait` keyword, `none` builtin value, optional type
  pattern (`int?`, `str?`), expanded builtin functions (15 new).
- **Snippets**: Added `fntb` (trait-bound function), `opt` (optional type),
  `ltlc` (C transpile comment), `test` (test function).
- Types list expanded: `Iterator`, `Comparable`, `Hashable`.

### Tutorial v1.5 Refresh
- **Chapter 22**: Result and Option types — `Result<T,E>`, `Option<T>`,
  match-as-expression, `::` scope operator, 8 pattern types.
- **Chapter 23**: Optional types (`int?`), type narrowing, trait bounds
  (`<T: Comparable>`), const generics (`<N: int>`).
- **Chapter 24**: C backend — transpilation, hosted vs freestanding,
  LateralusOS real-kernel example.
- **Chapter 25**: Standard library tour — essential imports, v1.5 modules,
  scientific stack overview.
- Removed outdated "Coming in v1.5" teaser from ending.

### Stale Reference Fixes
- Updated all 9 stdlib headers from v1.2.0/v1.3.0 → v1.5.0.
- Fixed test counts: 1,071 → 1,158 in blog, 1,145 → 1,158 in ROADMAP
  and phase3 blog.
- Fixed stdlib counts: 22 → 28 in onboarding page (3 locations) and
  website blog excerpt.
- Added 6 missing module cards to onboarding: `datetime`, `http`, `iter`,
  `os`, `regex`, `result`.

### Example Programs
- Fixed 8 examples: string-based imports (`import "math"` → `import math`).
- Rewrote `v15_types.ltl`: removed map literals (parser limitation),
  fixed lambda syntax, renamed `measure` → `area` to avoid keyword conflict.

### Health Check
- Updated `scripts/health_check.py`: v1.3.0 → v1.5.0, added 6 new stdlib
  modules, added `compiler` and `lsp_server` to import check, added
  `vscode-lateralus/package.json` and 3 new doc files to file list.
- All 12/12 modules importable, 45/45 files present, HEALTHY.

### Build & Test
- All 1,158 tests passing in ~2.0s.
- All 16 docs build (0 failures).

### Type System Enhancements
- **Optional type syntax**: `int?`, `str?`, `map?` — append `?` to any type
  for compiler-enforced nil checking. Parser now uses `QUESTION` token.
- **Type narrowing**: `TypeNarrower` class for flow-sensitive analysis.
  Narrows optional types in `if x != nil` branches, supports `&&`/`||`/`!`
  composition and `type_of()` checks.
- **Generics with trait bounds**: `fn sort<T: Comparable>(items: list)` —
  bounded generic parameters parsed and stored as `{"name": str, "bound": str}`.
- **Const generics**: `struct Matrix<N: int, M: int>` — value-level generic
  parameters for fixed-size type specifications.
- **FnDecl generics field**: Function declarations now store `generics` list.
- **Test count**: 1,158 tests passing (up from 1,145).

### Standard Library Expansion (22 → 28 modules)
- **`stdlib.os`**: File system, paths, environment, process control.
- **`stdlib.datetime`**: Date/time construction, arithmetic, formatting,
  calendar helpers (leap year, day-of-week, ISO 8601).
- **`stdlib.regex`**: Pattern matching, validation (email, URL, IP),
  extraction, replacement.
- **`stdlib.http`**: HTTP client (GET/POST/PUT/DELETE), JSON helpers,
  URL parsing and encoding.
- **`stdlib.result`**: Result/Option monads with `map`, `and_then`, `or_else`,
  `try_call`, `collect_results`, `partition_results`.
- **`stdlib.iter`**: Lazy iterator combinators — `map`, `filter`, `take`,
  `skip`, `flat_map`, `enumerate`, `zip`, `chain`, `unique`, `chunks`,
  `windows`, `reduce`, `fold`.

### Documentation
- **Cookbook**: Added Chapter 13 (5 recipes for optional types, trait bounds,
  const generics, Result/Option patterns, C backend transpilation).
- **Quick Reference**: Added sections for optional types, trait bounds,
  C backend, and 28 stdlib imports.
- **Blog**: New post "v1.5 Type System: Optional Types, Trait Bounds &
  Type Narrowing".
- **Doc builder fix**: Fixed `render_ltlml()` vs `to_html()` bug in
  `build_docs.py` — all 15 docs now build successfully.
- **Footer version**: Updated doc builder footer from v1.3 to v1.5.

### Roadmap & Feature Flags
- Checked off: optional types, trait bounds, const generics, type narrowing.
- Added feature flags: `optional_types`, `trait_bounds`, `const_generics`,
  `type_narrowing`, `c_backend` — all marked Stable.

### LateralusOS — GUI Phase 3: Interactive Desktop

#### RAM Filesystem (`fs/ramfs.h`, `fs/ramfs.c`)
- **Inode-based in-memory filesystem**: 64 max nodes, 16 children per
  directory, 2 KB max file content.
- Pre-populated directory tree: `/`, `/home`, `/etc`, `/tmp` with default
  files (`hostname`, `motd`, `readme.txt`, `hello.ltl`, `spiral.txt`).
- Full POSIX-like API: `ramfs_create`, `ramfs_mkdir`, `ramfs_write`,
  `ramfs_append`, `ramfs_read`, `ramfs_find`, `ramfs_list`, `ramfs_remove`.
- Path resolution with `..` and `.` support via `ramfs_resolve_path`.
- Integrated into both text-mode shell and GUI terminal.

#### PC Speaker Driver (`drivers/speaker.h`, `drivers/speaker.c`)
- **PIT Channel 2 tone generation**: programs ports 0x42, 0x43, 0x61.
- Non-blocking melody queue (8 notes max) with auto-advance.
- Pre-built sound effects:
  - `speaker_boot_chime`: C5→E5→G5→C6 ascending arpeggio at startup.
  - `speaker_window_open`: A5→D6 two-note chime on window creation.
  - `speaker_keyclick`: 1200 Hz, 3 ms ultra-short feedback.
  - `speaker_error_beep`: A3 warning tone.
  - `speaker_notify`: E6 notification ding.

#### Cooperative Task Scheduler (`kernel/tasks.h`, `kernel/tasks.c`)
- **Lightweight callback scheduler**: 16 max concurrent tasks.
- Round-robin execution with configurable intervals.
- `task_create` (periodic) and `task_create_oneshot` (delayed, auto-remove).
- `tasks_tick()` — call at 1 kHz from PIT ISR.
- `tasks_list()` — human-readable table for terminal `tasks` command.

#### Functional GUI Terminal (`gui/terminal.h`, `gui/terminal.c`)
- **Full interactive terminal emulator** with 200-line scrollback, 80 columns.
- Support for 4 simultaneous terminal instances.
- **17 built-in commands**:
  - `help`, `clear`, `history` — terminal management
  - `ls [dir]`, `cat <file>`, `touch <file>`, `mkdir <dir>`, `rm <f>`,
    `cd <dir>`, `pwd` — VFS file operations
  - `echo <msg>` — print (supports `echo text > file` redirect)
  - `uname`, `uptime`, `free`, `tasks` — system information
  - `neofetch` — ASCII art system info banner
- Command history (16 entries) with Up/Down arrow navigation.
- Cursor blinking (500 ms interval).
- Working directory tracking with `cwd_node` for relative path resolution.
- Terminal windows set `is_terminal` flag for keyboard routing.

#### Alt+Tab Window Switcher
- **Overlay panel** listing all visible windows with highlighted selection.
- `Alt+Tab` cycles forward, `Shift+Alt+Tab` cycles backward.
- Releasing Alt key focuses the selected window (restores if minimized).
- Rendered as centered rounded-rect overlay between menus and cursor.

#### Animated Wallpaper
- **Color-cycling gradient** using integer sine/cosine tables (64 entries).
- **12 twinkling stars** at deterministic pseudo-random positions with
  brightness that fades in and out.
- **5 Fibonacci spiral rings** with rotating dots in Catppuccin accent
  colors (blue, green, yellow, pink, lavender).
- **Pulsing logo**: "LateralusOS" text with oscillating glow color.
- Phase-based animation: `wallpaper_phase` incremented every `gui_tick`.

#### Window Animations
- **Open animation**: 8-frame scale-from-center on window creation.
- **Close animation**: 7-frame shrink-to-center on window close.
- **Minimize animation**: 7-frame slide-to-taskbar on minimize.
- New `Window` fields: `anim_state`, `anim_frame`.

#### Keyboard Enhancements
- **Ctrl key tracking**: scancodes 0x1D/0x9D, generates ASCII control codes.
- **Alt key tracking**: scancodes 0x38/0xB8, enables Alt+Tab.
- **Ctrl+T**: open new terminal.
- **Ctrl+A**: toggle start menu.
- **Ctrl+M**: open system monitor.
- VFS commands (`ls`, `cat`, `touch`, `mkdir`) added to text-mode shell.

#### Lateralus Companion Files
- `gui/terminal.ltl` — full terminal emulator in Lateralus (17 commands).
- `gui/wallpaper.ltl` — animated wallpaper engine with sine tables.
- `gui/animation.ltl` — window animation state machine with easing functions.
- `drivers/speaker.ltl` — PIT Channel 2 speaker driver with melody queue.
- `fs/vfs.ltl` — updated with full RAMFS implementation (~120 new lines).
- `kernel/scheduler.ltl` — updated with cooperative task scheduler section.

#### Build & Metrics
- **11-step build pipeline**: 4 new .c files, 11 total .o files linked.
- Kernel size: **375 KB** (up from 136 KB in Phase 2).
- ISO size: 13 MB.
- 0 compiler warnings.
- Boot test: PASSED (QEMU serial output verified).

### Algebraic Data Types (ADTs)
- `Result::Ok(v)` / `Result::Err(e)` — explicit constructors with `::` syntax.
  Both `Ok` and `Err` now carry `__match_args__` for Python `match/case` destructuring.
- `Option::Some(v)` / `Option::None` — nullable type without null pointers.
  `Some` has `__match_args__`; `None_` is a singleton of `_NoneType`.
- `Option()` helper wraps a Python value: `Some(v)` or `None_`.
- New preamble types: `_LtlOption`, `Some`, `_NoneType`, `None_`.

#### Type Pattern Matching (match as expression)
- `match expr { Pat => value, ... }` — match is now a first-class **expression**
  that returns a value, not only a statement.
- `TypeMatchExpr` AST node with arms of `TypeMatchArm`.
- Full pattern language in match arms:
  - `WildcardPattern` (`_`) — discard
  - `LiteralPattern` (`42`, `"ok"`) — value match
  - `BindingPattern` (`x`) — capture value
  - `TypePattern` (`Point(x, y)`) — struct destructuring
  - `EnumVariantPattern` (`Result::Ok(v)`) — ADT variant destructuring
  - `TuplePattern` (`(a, b)`) — tuple destructuring
  - `ListPattern` (`[h, ...t]`) — head/tail list split
  - `OrPattern` (`"Sat" | "Sun"`) — alternative patterns
- Guard clauses: `Result::Ok(n) if n > 0 => "positive"`.

#### `::` Scope Operator
- New `DOUBLE_COLON` token (`TK.DOUBLE_COLON`) — scoped namespace access.
- Lexer correctly tokenizes `::` as a two-character token, distinct from `:`.
- Used in all ADT constructor and pattern syntax.

#### Hindley-Milner Type Inference (expansion)
- `TypeInferencer.occurs_check(var, typ)` — prevents infinite recursive types.
- `TypeInferencer.unify(t1, t2, context)` — Robinson unification with 10 cases:
  TypeVar binding, List, Map, Tuple, Function, Optional, Union, ANY escape hatch.
- `TypeInferencer.substitute(typ, subst)` — recursive substitution application.
- `TypeInferencer.solve()` — drains constraint queue, returns error list.
- `TypeInferencer.infer_pattern(pattern, subject)` — infers bindings for all
  8 pattern kinds; handles rest bindings in list patterns.

### Improvements

#### Python Transpiler (`codegen/python.py`)
- Added `visit_TypeMatchExpr()` — emits `match/case` (Python 3.10+) or if-chain.
- Added `_render_type_pattern()` — converts pattern nodes to Python pattern strings.
- Added `_type_match_expr_iife()` — wraps match-as-expression in a helper function.
- `ResultExpr` → `Ok(v)` / `Err(e)` in Python output.
- `OptionExpr` → `Some(v)` / `None_` in Python output.
- Preamble version comment updated to `v1.5`.

#### Bug Fixes
- Fixed `_parse_while` method header accidentally deleted during parser refactor.
  Caused `AttributeError: 'Parser' object has no attribute '_parse_while'` in
  all while-loop tests (2 failures, now 0).

#### Deprecation Fixes
- `notebook.py`: `datetime.utcnow()` replaced with `datetime.now(timezone.utc)`
  (eliminated 68 Python 3.12 `DeprecationWarning` instances).

### Version & Metadata
- `pyproject.toml`: `1.4.0` → `1.5.0`
- `__init__.py`: `__version__` → `"1.5.0"`
- `notebook.py` kernel_info version: `"1.3.0"` → `"1.5.0"`
- Compiler preamble comment: `v1.3` → `v1.5`

### New Files
- `examples/v15_showcase.ltl` — comprehensive showcase of all v1.5 features
- `tests/test_v15_features.py` — 60+ tests covering lexer, parser, type system,
  codegen, and end-to-end compilation of all v1.5 constructs

### C99 Backend (`codegen/c.py`)
- **Full C99 transpiler** — translates Lateralus AST to standalone C99 source.
- **Two modes**: `CMode.HOSTED` (links libc, `main()` wrapper) and
  `CMode.FREESTANDING` (bare-metal, `_start()` entry, no libc).
- 45+ AST visitor methods: functions, structs, enums, match, if/while/for/loop,
  Result/Option, type aliases, impl blocks, imports, try/recover, throw,
  foreign blocks, interface vtables, interpolated strings, casts, tuples, maps.
- C-keyword collision avoidance (auto-prefix `ltl_` on reserved names).
- Three-pass emit: forward declarations → struct definitions → implementations.
- Runtime preamble with `ltl_value_t` tagged union, `ltl_str_new()`,
  `ltl_list_new()`, `ltl_heap_reset()`, bump allocator for freestanding.
- `tests/test_c_backend.py` — 74 tests covering all visitors and edge cases.
- CLI: `python -m lateralus_lang c <file.ltl> [-o out.c] [--freestanding]`
  and `ltlc c <file.ltl> [-o out.c] [--freestanding]`.

### LateralusOS
- **38 files scaffolded**: boot, kernel, HAL, drivers, FS, shell, services,
  editions, build tools, licensing, test harness, documentation.
- **First VM boot**: Multiboot2 x86_64 long mode → QEMU boot (13 MB ISO).
- **Interactive shell**: 15 commands (help, clear, uname, uptime, free, echo,
  version, cpuid, ticks, alloc, heap, history, reboot, halt, **gui**).
- VGA text mode driver (80×25), PS/2 keyboard with shift, backspace,
  arrow-key history, PIC + PIT interrupt handling.
- **Bump memory allocator** (`kmalloc`) with linker `_end` symbol.
- Multi-edition build system: workstation, industrial, research, embedded.
- Multi-architecture support: x86_64, ARM Cortex-M4, RISC-V 64.
- Dual licensing: Freeware (free use/study/deploy) and Proprietary (modify/fork).
- **Graphical Desktop Environment**:
  - Framebuffer driver: 1024×768×32bpp linear framebuffer via Multiboot2.
  - Embedded 8×16 bitmap font for pixel-perfect text rendering.
  - Drawing primitives: rectangles, circles, lines, gradients, rounded
    rectangles, alpha blending — all freestanding, no libc.
  - **GUI widget system**: windows with macOS-style traffic light buttons
    (close/minimize/maximize), draggable title bars, content areas.
  - **Desktop environment**: gradient wallpaper, bottom taskbar with clock
    and window tabs, Start button, Catppuccin Mocha color theme.
  - **PS/2 mouse driver**: IRQ12 handler, 3-byte packet decoder, cursor
    rendering, click/drag event dispatch.
  - Lateralus `.ltl` GUI components: `app.ltl` (theme/layout helpers),
    `widgets.ltl` (progress bar, toggle, slider, tab bar, toast),
    `shell_gui.ltl` (terminal emulator widget).
  - `gui` shell command launches graphical desktop; ESC returns to text mode.
  - Kernel size: 122 KB (up from 57 KB with text-only).
- **GUI Phase 2 — Desktop Polish**:
  - **Double-buffering**: all rendering targets an off-screen back buffer;
    `fb_swap()` blits to hardware framebuffer in one pass — eliminates
    screen tearing. Back buffer allocated via `kmalloc` (~3 MB).
  - **Start menu**: popup panel above taskbar with 4 launchable apps
    (Terminal, System Monitor, README, About). Hover highlighting,
    click-to-launch, click-outside-to-dismiss.
  - **Context menu**: right-click anywhere on desktop to open a popup
    with same app launchers. Position-clamped to screen bounds.
  - **Desktop icons**: 4 clickable icons (Terminal, Monitor, About, README)
    on left side of desktop. 48×48 colored squares with glyph and label.
    Hover highlight, selection state.
  - **System Monitor window**: displays CPU, memory, timer, display,
    input info. Uptime and frame count auto-refresh every 2 seconds.
  - **Window resize**: drag handle at bottom-right corner of focused
    windows. Minimum size enforced at 200×150 pixels.
  - **Notification tray**: status area left of the taskbar clock showing
    uptime and approximate FPS, updated every 2 seconds.
  - New keyboard shortcut: Ctrl+M opens System Monitor.
  - Kernel size: 136 KB (up from 122 KB).

### VS Code Extension
- **LSP client** (`extension.js`): spawns `python -m lateralus_lang.lsp_server`,
  JSON-RPC, completions, hover, diagnostics, status bar indicator.
- **6 custom SVG icons**: file icons for `.ltl`, `.ltasm`, `.ltlml`, `.ltlcfg`,
  `.ltbc`, plus `lateralus-logo.svg`.
- **17 new snippets** for v1.5 constructs (Result, Option, match expression,
  pattern matching, ADT enums, pipeline operators).
- Extension version bumped to 1.5.0.

---

## [1.4.0] — Scientific Edition

### New Features

#### Error Handling: Result / Ok / Err / LtlError
- `Ok(value)` and `Err(error)` are first-class result types — no exceptions
  needed for expected failures.
- `Result(v)` wraps a value: returns `Ok(v)` for non-exception values or
  `Err(v)` for exception instances.
- `LtlError` — rich error base class with `.message`, `.code`, `.ctx`,
  `.cause`; methods `.caused_by(e)`, `.with_context(**kw)`, `.format()`.
- `expr?` — Rust-inspired propagation operator: unwraps `Ok` to its inner
  value, or raises `_PropagateSignal` for `Err`/`None`, propagating the
  failure up the call stack automatically.
- `error.caused_by(cause)` — ChainExpr: attach a root cause to any error.
- Full AST nodes: `PropagateExpr`, `ChainExpr`.

#### Mathematical Computing
- **Complex numbers** (preamble): `complex_new`, `re`, `im`, `conj`,
  `magnitude`, `phase`, `polar`, `rect` — all backed by Python `cmath`.
- **Matrix** (preamble): pure-Python `Matrix` class with `+`, `-`, `*`,
  `@`, `.T`; functions `matrix`, `zeros`, `ones`, `eye`, `mat_det`,
  `mat_inv`, `mat_transpose`, `mat_trace`, `mat_norm`, `mat_shape`,
  `mat_row`, `mat_col`, `mat_to_list`, `mat_from_list`.
- **Statistics** (preamble): `mean`, `variance`, `std_dev`, `std_err`,
  `median`, `mode`, `percentile`, `covariance`, `correlation`,
  `normalize`, `zscore`, `histogram`.
- **Numerics** (preamble): `newton` (Newton-Raphson), `bisect`,
  `trapz` (trapezoidal integration), `ndiff` (central differences).
- **min/max** fixed to accept `key=` keyword argument.

#### Cryptography (preamble)
- `sha256`, `sha512`, `md5`, `hmac_sha256`, `b64_encode`, `b64_decode`,
  `uuid4`, `uuid_ns` — backed by Python `hashlib`, `hmac`, `base64`, `uuid`.

#### Standard Library (new modules)
- **`stdlib/complex.ltl`** — `complex`, `real`, `imaginary`, `conjugate`,
  `euler`, `cexp`, `csqrt`, `clog`, `format_complex`, `is_real`.
- **`stdlib/matrix.ltl`** — `mat`, `zero_matrix`, `one_matrix`, `identity`,
  `transpose`, `det`, `inv`, `trace`, `norm`, `shape`, `matmul`, `solve`,
  `mat_map`, `mat_flatten`, `outer`, `dot`, `mat_print`.
- **`stdlib/stats.ltl`** — `avg`, `pop_variance`, `pop_std`, `se_mean`,
  `med`, `most_frequent`, `pct`, `quartiles`, `iqr`, `pearson`, `cov`,
  `min_max`, `standardize`, `hist`, `ss_total`, `rmse`, `mae`,
  `linear_regression`, `predict`, `r_squared`, `outliers`, `sample`.
- **`stdlib/numerics.ltl`** — `newton_root`, `bisection`, `integrate`,
  `derivative`, `second_derivative`, `simpson`, `gradient`, `fixed_point`,
  `euler_ode`, `rk4`, `polyval`, `diff_table`.
- **`stdlib/crypto.ltl`** — `hash_sha256`, `hash_sha512`, `hash_md5`,
  `hmac`, `encode_b64`, `decode_b64`, `random_id`, `named_id`,
  `verify_sha256`, `checksum`, `xor_cipher`, `make_token`, `verify_token`.

#### LTLM Markup Language (`.ltlm`)
- New file format for documentation, blogs, and papers embedded in the
  Lateralus ecosystem.
- Supports: YAML-lite front-matter, headings `# ## ### ####`, **bold**,
  *italic*, `code`, ~~strikethrough~~, links, images, tables, blockquotes,
  bullet/ordered lists, fenced code blocks ` ```lang ` and LTLM semantic
  blocks `:::type ... :::` (note/warning/example/output/math/ltl/info).
- `lateralus_lang/markup/` package: `parser.py` (Document AST) +
  `renderer.py` (HTML with dark-mode CSS layout, ANSI terminal with colors).

#### CLI Additions (`ltlc` / `python -m lateralus_lang`)
- `ltlc test <file>` — discovers and runs all `@test`-decorated functions
  in a `.ltl` file; shows ✓/✗ per function with millisecond timing.
- `ltlc doc <file.ltlm>` — renders an LTLM document; defaults to ANSI
  terminal output; `--html` emits a standalone dark-mode HTML page;
  `-o file` writes output to disk.
- `ltlc info` — prints version, Python backend version, installed stdlib
  modules, and enabled feature flags.

#### Examples
- **`examples/science_demo.ltl`** — complex numbers, matrices, statistics,
  numerical integration, ODE solving, `?` error propagation.
- **`examples/engineering_demo.ltl`** — signal processing, crypto hashing,
  linear-systems solver, measure blocks, pipeline chaining.
- **`examples/v2_bootstrap_preview.ltl`** — a preview of the Lateralus
  self-hosting bootstrap: a partial tokenizer written in Lateralus itself.

#### Documentation
- `docs/spec/language_spec.md` — full language grammar and semantics.
- `docs/spec/stdlib_reference.md` — all stdlib modules documented.
- `docs/blog/` — six launch blog posts in LTLM format.
- `docs/papers/` — three research papers (design, math, polyglot).
- `docs/html/index.html` — dark-mode HTML docs landing page.
- `ROADMAP.md` — versioned advancement schedule through v2.0.

### Test Suite
- **167 tests**, all passing (0 regressions from v1.3.0).

---

## [1.2.0] — Polyglot Edition

### New Features

#### Polyglot Integration (`foreign` blocks + `@foreign` decorator)
- New `foreign "<lang>" { "<source>" }` statement executes source code in an
  external runtime (Julia, Rust, C, Go, R, Zig, Fortran) via
  `lateralus.polyglot`.
- Optional named params: `foreign "julia" (n: limit) { "sqrt(n)" }` passes
  Lateralus values as a JSON object to the foreign runtime.
- New `@foreign("<lang>")` decorator on `fn` declarations:
  ```lateralus
  @foreign("julia")
  fn compute_primes(limit: int) -> list[int] {
      "using Primes; params=JSON3.read(readline()); ..."
  }
  ```
  The function body (single string literal) is sent to the polyglot runtime;
  params are marshalled as JSON; the `result` key of the response is returned.
- `_get_polyglot()` lazy helper emitted into every transpiled Python module.
- `FOREIGN_CALL` IR opcode + `extra` field on `IRInstr` for metadata.

#### Language Improvements
- `fn` declarations now carry a `decorators` field — decorators are attached
  directly to the node they annotate (previously only `struct` and `enum` had
  this).
- `@keyword_decorator` supported: any keyword (e.g. `@foreign`) can appear
  after `@` without requiring it to be an identifier.
- `self` accepted as a parameter name in `fn` parameter lists (`KW_SELF`).
- `struct X implements Y` alternative syntax for interface implementation.
- `interface X extends Y` alternative syntax for interface inheritance.
- Enum record variants: `Circle { radius: float }` brace-style in addition to
  the existing `Circle(radius: float)` paren-style.
- Interface methods can be abstract (no body `{}`): `fn area(self) -> float`
  without a block is now valid inside `interface { }`.
- `from X import Y` declarations are now collected into `Program.imports`
  (previously they landed in `Program.body`).

#### Standard Library
- **`stdlib/io.ltl`** (new) — file I/O: `read_file`, `write_file`,
  `append_file`, `file_exists`, `lines_of`, `split_lines`, `prompt`,
  `read_int`, `read_float`, `print_table`, `basename`, `dirname`,
  `path_join`, `extension`.
- **`stdlib/math.ltl`** (extended) — new functions: `lerp`, `sign`, `ln`,
  `log2`, `log10`, `sin`, `cos`, `tan`, `radians`, `degrees`, `hypot`,
  `isqrt`; new constants: `INF`, `NAN`.

#### Examples
- **`examples/polyglot_demo.ltl`** — demonstrates `@foreign`, inline
  `foreign` blocks, pipeline chaining, struct + impl, and stdlib math.

### Test Suite
- **167 tests** (was 103), all passing.
- New file `tests/test_v12_features.py` — 64 tests covering:
  - Struct (empty, fields, defaults, generics, `implements`, StructLiteral)
  - Enum (simple, named values, paren/brace variants, generics)
  - ImplBlock (method count, `for` interface)
  - InterfaceDecl (empty, methods, `extends`, async methods)
  - TypeAlias
  - Decorators (`@simple`, `@with_args`, `@multiple`, `@fn_decorator`, `@foreign`)
  - `from … import` (single, multiple, braces, alias)
  - `yield` / `spawn` parsing and transpilation
  - `InterpolatedStr` parsing and f-string transpilation
  - Pipeline `|>` chaining transpilation
  - `ForeignBlock` parsing and Python transpilation
  - `@foreign` function decorator transpilation

### IR / VM
- `IROp.FOREIGN_CALL` added.
- `IRInstr.extra: Any` field for opcode-specific metadata.
- `IRInstrBuilder.emit()` and `SemanticAnalyzer._emit()` accept `extra=`.
- `SemanticAnalyzer.visit_ForeignBlock()` emits `FOREIGN_CALL` instructions.

---

## [1.1.0] — Struct / Enum / Generics Edition

### New Language Features
- **Structs**: `struct Name { field: Type = default }` with `@dataclass` transpilation.
- **Enums**: `enum Color { Red, Green = 2, Blue(r: int) }` with Python `Enum` transpilation.
- **Type aliases**: `type Callback = fn(int) -> str`.
- **Impl blocks**: `impl Circle { fn area(self) { … } }` injecting methods into structs.
- **Interfaces**: `interface Shape { fn area(self) -> float }` with ABC transpilation.
- **Decorators**: `@name(args)` syntax on structs, enums, functions.
- **`yield` / `spawn`**: generator and async concurrency primitives.
- **`self`** keyword in method parameter lists.
- **`where`** keyword for generic constraints (parsed, not yet type-checked).
- **`not` / `and` / `or`** as word-form logical operators.
- **`@` / `?`** single-character tokens for decorators and nullable types.

### Tooling
- `ltlc ast <file>` — print the AST as JSON or pretty-printed.
- `ltlc ir <file>` — dump the IR module.
- REPL commands `:ast`, `:ir`, `:ver`.

### Standard Library
- `stdlib/strings.ltl` — 19 string functions.
- `stdlib/collections.ltl` — 24 collection utilities.

### Tests
- 103 tests, all passing.

---

## [1.0.0] — Initial Release

- Lexer, recursive-descent parser, AST.
- IR three-address representation + semantic analysis.
- Python 3.10+ transpiler target.
- Stack-based VM + `.ltasm` assembler.
- REPL, CLI (`ltlc`).
- `stdlib/core.ltl`.
