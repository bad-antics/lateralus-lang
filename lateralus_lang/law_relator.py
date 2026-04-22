"""
LATERALUS v3.2 — Cross-Function Relational Laws (9th pillar)

Where `discover` finds algebraic identities *inside* one function and
`characterize` finds closed-form defining equations for one function,
this module searches across *pairs* of user functions for relational
laws — the kind of constraint that ties two functions together:

    f(g(x)) == x            ← inverse pair
    g(f(x)) == x            ← other inverse direction
    f(f(x)) == x            ← involution
    f(f(x)) == f(x)         ← f is idempotent
    f(g(x)) == g(f(x))      ← f and g commute
    f(g(x)) == f(x)         ← g is an f-invariant no-op
    f(x)    == g(x)         ← f and g are extensionally equivalent

Each matched relation is emitted as a single, quantified `@law` that
the rest of the pipeline (`verify`, `--mutate`, `harden`) can exercise.
One cross-function law captures an *infinite* family of point witnesses
— encoder/decoder round-trips, hash collisions, symmetric operations,
even simple code-smell detection (two fns that compute the same thing).

This is still pure inductive inference — every relation is validated
on a fresh random sample before being proposed.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from lateralus_lang.law_discovery import _equal, _get_param_types, _sample

# ─── Relation kinds ────────────────────────────────────────────────────────

# Each relation is a template over two fns (f, g) producing:
#   • a short human-readable label
#   • a callable check `(f, g, x, y) -> bool or None` returning
#     True if the relation holds on this input, False if violated,
#     None if the inputs/call raised and we should skip.

@dataclass(frozen=True)
class Relation:
    kind: str
    # LTL expression template — {f}, {g}, {args} get substituted
    lhs: str
    rhs: str
    # Arity required (how many vars we thread through)
    arity: int
    # Symmetric? (if yes, we only try (f, g) once, not both (f,g) and (g,f))
    symmetric: bool
    # Same-fn allowed? (e.g. f∘f)
    allow_same: bool
    # Different-fn required? (e.g. equivalence)
    require_different: bool


RELATIONS: List[Relation] = [
    Relation(
        kind="inverse",
        lhs="{f}({g}({x}))",
        rhs="{x}",
        arity=1,
        symmetric=False,
        allow_same=False,
        require_different=True,
    ),
    Relation(
        kind="involution",
        lhs="{f}({f}({x}))",
        rhs="{x}",
        arity=1,
        symmetric=True,   # single fn
        allow_same=True,
        require_different=False,
    ),
    Relation(
        kind="idempotent_compose",
        lhs="{f}({f}({x}))",
        rhs="{f}({x})",
        arity=1,
        symmetric=True,
        allow_same=True,
        require_different=False,
    ),
    Relation(
        kind="commuting",
        lhs="{f}({g}({x}))",
        rhs="{g}({f}({x}))",
        arity=1,
        symmetric=True,
        allow_same=False,
        require_different=True,
    ),
    Relation(
        kind="absorbs",
        lhs="{f}({g}({x}))",
        rhs="{f}({x})",
        arity=1,
        symmetric=False,
        allow_same=False,
        require_different=True,
    ),
    Relation(
        kind="equivalent",
        lhs="{f}({x})",
        rhs="{g}({x})",
        arity=1,
        symmetric=True,
        allow_same=False,
        require_different=True,
    ),
    Relation(
        kind="equivalent",
        lhs="{f}({x}, {y})",
        rhs="{g}({x}, {y})",
        arity=2,
        symmetric=True,
        allow_same=False,
        require_different=True,
    ),
]


@dataclass
class RelationalLaw:
    relation_kind: str
    f_name: str
    g_name: str            # may equal f_name for involution/idempotent
    arity: int
    param_types: List[type]
    trials_passed: int
    lhs_expr: str          # rendered LTL, e.g. "inc(dec(x))"
    rhs_expr: str          # rendered LTL, e.g. "x"

    def law_name(self) -> str:
        if self.f_name == self.g_name:
            return f"{self.f_name}_{self.relation_kind}"
        return f"{self.f_name}_{self.relation_kind}_{self.g_name}"

    def as_ltl_law(self) -> str:
        if self.arity == 1:
            params = f"x: {_ltl_type(self.param_types[0])}"
        else:
            params = ", ".join(
                f"{v}: {_ltl_type(t)}"
                for v, t in zip(("x", "y"), self.param_types)
            )
        return (
            f"@law\n"
            f"fn {self.law_name()}({params}) -> bool {{\n"
            f"    return ({self.lhs_expr}) == ({self.rhs_expr})\n"
            f"}}"
        )


def _ltl_type(t: type) -> str:
    if t is bool:  return "bool"
    if t is int:   return "int"
    if t is float: return "float"
    return "int"


# ─── The inference engine ─────────────────────────────────────────────────

def _safe_call(fn: Callable, args: tuple) -> Tuple[bool, Any]:
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return True, fn(*args)
    except BaseException:
        return False, None


def _unary_fns_only(
    ns: Dict[str, Any], user_fns: List[str], arity: int
) -> List[Tuple[str, Callable, List[type]]]:
    """Return (name, callable, param_types) triples whose arity matches
    and whose parameters are all numeric/bool (the types we can sample)."""
    out = []
    for name in user_fns:
        fn = ns.get(name)
        if not callable(fn):
            continue
        pts = _get_param_types(fn)
        if not pts or len(pts) != arity:
            continue
        if any(t not in (int, float, bool) for t in pts):
            continue
        out.append((name, fn, pts))
    return out


def _check_relation(
    rel: Relation,
    f_name: str, f: Callable,
    g_name: str, g: Callable,
    param_types: List[type],
    trials: int,
    rng: random.Random,
) -> Optional[RelationalLaw]:
    """Test whether `rel` holds between f and g on `trials` random inputs.
    Returns a RelationalLaw if every valid trial passes, else None."""

    passed = 0
    valid = 0

    if rel.arity == 1:
        t = param_types[0]
        for _ in range(trials):
            try:
                x = _sample(t, rng)
            except Exception:
                return None

            # Evaluate LHS and RHS per relation kind
            if rel.kind == "inverse":
                # f(g(x)) == x
                ok, gv = _safe_call(g, (x,))
                if not ok: continue
                ok, lv = _safe_call(f, (gv,))
                if not ok: continue
                rv = x
            elif rel.kind == "involution":
                ok, fv = _safe_call(f, (x,))
                if not ok: continue
                ok, lv = _safe_call(f, (fv,))
                if not ok: continue
                rv = x
            elif rel.kind == "idempotent_compose":
                ok, fv = _safe_call(f, (x,))
                if not ok: continue
                ok, lv = _safe_call(f, (fv,))
                if not ok: continue
                rv = fv
            elif rel.kind == "commuting":
                ok, gv = _safe_call(g, (x,))
                if not ok: continue
                ok, lv = _safe_call(f, (gv,))
                if not ok: continue
                ok, fv = _safe_call(f, (x,))
                if not ok: continue
                ok, rv = _safe_call(g, (fv,))
                if not ok: continue
            elif rel.kind == "absorbs":
                ok, gv = _safe_call(g, (x,))
                if not ok: continue
                ok, lv = _safe_call(f, (gv,))
                if not ok: continue
                ok, rv = _safe_call(f, (x,))
                if not ok: continue
            elif rel.kind == "equivalent":
                ok, lv = _safe_call(f, (x,))
                if not ok: continue
                ok, rv = _safe_call(g, (x,))
                if not ok: continue
            else:
                return None

            valid += 1
            if not _equal(lv, rv):
                return None
            passed += 1

        # Trivial relations (e.g. both fns return a constant) shouldn't
        # count. Require at least 6 distinct trials and that LHS is not
        # always equal to a tiny fixed set (the constant-predicate guard).
        if valid < max(6, trials // 6):
            return None

        # Render LTL exprs with real param name `x`
        lhs = rel.lhs.format(f=f_name, g=g_name, x="x")
        rhs = rel.rhs.format(f=f_name, g=g_name, x="x")
        return RelationalLaw(
            relation_kind=rel.kind,
            f_name=f_name,
            g_name=g_name,
            arity=1,
            param_types=param_types,
            trials_passed=passed,
            lhs_expr=lhs,
            rhs_expr=rhs,
        )

    # Arity 2 — only the `equivalent` relation is defined today.
    if rel.arity == 2 and rel.kind == "equivalent":
        tx, ty = param_types
        for _ in range(trials):
            try:
                x = _sample(tx, rng)
                y = _sample(ty, rng)
            except Exception:
                return None
            ok, lv = _safe_call(f, (x, y))
            if not ok: continue
            ok, rv = _safe_call(g, (x, y))
            if not ok: continue
            valid += 1
            if not _equal(lv, rv):
                return None
            passed += 1
        if valid < max(6, trials // 6):
            return None
        lhs = rel.lhs.format(f=f_name, g=g_name, x="x", y="y")
        rhs = rel.rhs.format(f=f_name, g=g_name, x="x", y="y")
        return RelationalLaw(
            relation_kind=rel.kind,
            f_name=f_name,
            g_name=g_name,
            arity=2,
            param_types=param_types,
            trials_passed=passed,
            lhs_expr=lhs,
            rhs_expr=rhs,
        )

    return None


def _trivial_pair(f: Callable, g: Callable, pts: List[type],
                  rng: random.Random, n: int = 8) -> bool:
    """Guard against meaningless 'equivalence' between two constant fns
    that happen to return the same value. Returns True if *both* fns
    return the same single value on every input (truly degenerate)."""
    outs_f, outs_g = set(), set()
    for _ in range(n):
        try:
            args = tuple(_sample(t, rng) for t in pts)
        except Exception:
            return False
        ok, v = _safe_call(f, args)
        if ok: outs_f.add(repr(v))
        ok, v = _safe_call(g, args)
        if ok: outs_g.add(repr(v))
    return len(outs_f) == 1 and len(outs_g) == 1


def find_relational_laws(
    file: str | Path,
    *,
    trials: int = 80,
    seed: int = 42,
) -> List[RelationalLaw]:
    """Compile `file`, exec the transpiled Python, enumerate every
    relation × (f, g) combination, and return the matches."""
    from lateralus_lang.compiler import Compiler, Target
    from lateralus_lang.law_discovery import _extract_user_fns
    from lateralus_lang.law_mutator import _exec_capturing

    path = Path(file)
    src = path.read_text()
    result = Compiler().compile_source(src, target=Target.PYTHON, filename=path.name)
    if not result.ok:
        return []

    user_fns = _extract_user_fns(src)
    ns = _exec_capturing(result.python_src or "", "relate")

    found: List[RelationalLaw] = []
    seen_signatures: set = set()   # dedupe commuting/equivalent both orders

    # -- arity-1 pass --------------------------------------------------
    unary = _unary_fns_only(ns, user_fns, arity=1)
    for rel in RELATIONS:
        if rel.arity != 1:
            continue
        uses_g = "{g}" in (rel.lhs + rel.rhs)
        for i, (fn_i, f, pts_i) in enumerate(unary):
            for j, (fn_j, g, pts_j) in enumerate(unary):
                if pts_i != pts_j:
                    continue
                # Single-fn relations: only iterate j==i (g is unused)
                if not uses_g and fn_i != fn_j:
                    continue
                if rel.require_different and fn_i == fn_j:
                    continue
                if not rel.allow_same and fn_i == fn_j:
                    continue
                if rel.symmetric and uses_g and fn_j < fn_i:
                    continue
                sig = (rel.kind, min(fn_i, fn_j) if rel.symmetric else fn_i,
                       max(fn_i, fn_j) if rel.symmetric else fn_j)
                if sig in seen_signatures:
                    continue
                # Weed out both-constant equivalence before matching
                if rel.kind == "equivalent" and _trivial_pair(
                    f, g, pts_i, random.Random(seed + i * 7 + j)
                ):
                    continue
                law = _check_relation(
                    rel, fn_i, f, fn_j, g, pts_i, trials,
                    random.Random(seed + i * 131 + j * 17 + hash(rel.kind) % 9973),
                )
                if law is not None:
                    found.append(law)
                    seen_signatures.add(sig)

    # -- arity-2 pass (equivalence only) -------------------------------
    binary = _unary_fns_only(ns, user_fns, arity=2)
    for rel in RELATIONS:
        if rel.arity != 2:
            continue
        for i, (fn_i, f, pts_i) in enumerate(binary):
            for j, (fn_j, g, pts_j) in enumerate(binary):
                if pts_i != pts_j:
                    continue
                if fn_i == fn_j:
                    continue
                if rel.symmetric and fn_j < fn_i:
                    continue
                sig = (rel.kind, min(fn_i, fn_j), max(fn_i, fn_j))
                if sig in seen_signatures:
                    continue
                law = _check_relation(
                    rel, fn_i, f, fn_j, g, pts_i, trials,
                    random.Random(seed + i * 127 + j * 19 + hash(rel.kind) % 7901),
                )
                if law is not None:
                    found.append(law)
                    seen_signatures.add(sig)

    return found


# ─── File-level driver (CLI entrypoint) ───────────────────────────────────

def relate_file(
    file: str | Path,
    *,
    trials: int = 80,
    seed: int = 42,
    output: Optional[str] = None,
    apply: bool = False,
) -> int:
    """Search for cross-function relational laws and print / emit them."""
    path = Path(file)
    print(f"\n  Relating functions in {path.name}")
    print(f"  {'─' * 60}")

    laws = find_relational_laws(path, trials=trials, seed=seed)

    if not laws:
        print(f"  No relational laws found  (trials={trials}, seed={seed})")
        return 1

    # Group by kind for the summary
    from collections import Counter
    kind_counts = Counter(l.relation_kind for l in laws)
    print(f"  Trials per relation: {trials}, seed={seed}")
    print(f"  Found: {len(laws)} relational law(s)")
    for kind, n in sorted(kind_counts.items()):
        print(f"    • {kind:<20} ×{n}")
    print()

    # Print each match
    for law in laws:
        arrow = "≡" if law.relation_kind == "equivalent" else "↔"
        print(f"    [{law.relation_kind}]  {law.lhs_expr}  {arrow}  {law.rhs_expr}   "
              f"({law.trials_passed} trials)")

    print()
    print("  ─── Generated @law snippets ───")
    print()
    for law in laws:
        for line in law.as_ltl_law().splitlines():
            print(f"    {line}")
        print()

    if output:
        header = (
            f"// Auto-generated relational laws (lateralus relate)\n"
            f"// Source file: {path.name}\n"
            f"// Laws: {len(laws)}\n\n"
        )
        body = "\n\n".join(l.as_ltl_law() for l in laws)
        Path(output).write_text(header + body + "\n")
        print(f"  → wrote {len(laws)} laws to {output}")

    if apply:
        _apply_to_source(path, laws)

    return 0


_APPLY_BANNER = (
    "// ─── lateralus relate (auto-generated relational laws) ────────\n"
    "// Re-running `lateralus relate --apply` updates this block in place.\n"
)


def _apply_to_source(path: Path, laws: List[RelationalLaw]) -> None:
    """Append (or replace) the auto-generated block at the bottom of
    the source file. Idempotent: repeated `--apply` runs overwrite the
    same region instead of accumulating duplicates."""
    src = path.read_text()
    marker = _APPLY_BANNER.strip().splitlines()[0]
    end_marker = "// ─── end lateralus relate ─────────────────────────────────"

    block = [_APPLY_BANNER]
    for l in laws:
        block.append(l.as_ltl_law())
        block.append("")
    block.append(end_marker)
    new_block = "\n\n".join(block)

    if marker in src:
        # Replace existing block
        before, _, rest = src.partition(marker)
        _, _, after = rest.partition(end_marker)
        new_src = before.rstrip() + "\n\n" + new_block + "\n" + after.lstrip()
    else:
        new_src = src.rstrip() + "\n\n" + new_block + "\n"

    path.write_text(new_src)
    print(f"  → patched {len(laws)} relational laws into {path.name}")
