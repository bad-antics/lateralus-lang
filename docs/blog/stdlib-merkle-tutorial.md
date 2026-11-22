# Merkle Trees and Inclusion Proofs with `stdlib/merkle.ltl`

A Merkle tree hashes leaves pairwise up to a single root — the data
structure behind git, Certificate Transparency, IPFS, and every
"verify a leaf without downloading the forest" protocol.
`stdlib/merkle.ltl` implements the generic version in about 160
lines: pluggable hashers, RFC 6962-style domain separation, audit
paths, verification, and leaf diffing.

This tutorial builds trees, extracts proofs, and breaks them on
purpose. Companion: `examples/merkle_tutorial.ltl`.

---

## Domain separation

Every hash input is prefixed so leaf and internal-node hashes can
never collide structurally:

- `hash_leaf(h, data)` → `h("L:" + data)`
- `hash_pair(h, l, r)` → `h("N:" + l + "|" + r)`

The default hasher is FNV-1a/64 rendered as 16 hex chars —
deterministic and dependency-free, perfect for tests. Callers needing
production strength wrap SHA-256 and pass it as `hasher` (functions
are first-class in Lateralus, so `build(items, my_sha256_hex)` just
works).

## Build

`build(items, hasher)` returns `{levels, leaves, root}`:

- `levels[0]` = leaf hashes, each upper level pairs adjacent hashes
- an **odd** trailing node is duplicated with itself (`right = left`)
  so every level is well-formed — this is why 3-leaf trees still
  verify
- `root` is `levels`' last element's single entry

## Inclusion proofs

`proof(tree, index)` walks leaf → root collecting
`[sibling_hash, sibling_is_on_the_right]` per level. Verification
re-hashes upward: left siblings prepend (`hash_pair(sibling, running)`),
right siblings append. A proof for the wrong leaf data or the wrong
index fails — the tutorial shows both rejections.

> **Bug found and fixed in the tutorial copy:** the module's
> `proof()` advances with `index = index / 2`, but Lateralus `/`
> yields a float — on any tree taller than one level the next
> iteration's `index ^ 1` raises `TypeError: float ^ int`. The
> inlined copy uses `index >> 1` (identical semantics for indices).
> The stdlib module itself still carries the bug; flagged for a
> future fix PR.

## diff_leaves

`diff_leaves(a, b)` returns the indices whose leaf hashes differ —
a cheap reconciliation primitive for replicas that already share the
root but want to know *which* entries diverged. Unequal-length trees
report the longer side's tail as diffs.

## Running the tutorial

```bash
python -m lateralus_lang run examples/merkle_tutorial.ltl
python -m lateralus_lang check examples/merkle_tutorial.ltl
python -m pytest tests/test_merkle_tutorial.py -x -q
```
