"""
LATERALUS v3.2 — Ternary Algebraic Structure Laws (10th pillar)

Where `relate` (pillar 9) finds laws between *pairs* of functions,
`triangulate` searches for laws whose witnesses are *triples* of
expressions — the kind of constraint that reveals algebraic structure:

    left-distributive:   f(x, g(y, z)) == g(f(x, y), f(x, z))
    right-distributive:  f(g(x, y), z) == g(f(x, z), f(y, z))
    homomorphism:        g(f(x, y)) == f(g(x), g(y))
                                       ^ h preserves f's structure
    anti-homomorphism:   g(f(x, y)) == f(g(y), g(x))

Together with pillar 9, this is enough to catch the signatures of:
  • monoids (associative + identity, via @law + discover)
  • rings (two ops + distributivity)
  • semirings (both distributive laws hold)
  • group homomorphisms (negate, linear maps, ...)

Each match becomes a single quantified `@law` the rest of the pipeline
can exercise. The inference is pure random sampling, same guard-rails
as every other pillar: safe call wrappers, input-type sampling, a
validity-threshold check to suppress spurious results.
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


@dataclass(frozen=True)
class TernaryRelation:
    kind: str
    # f_arity, g_arity — how each participating fn is shaped
    f_arity: int
    g_arity: int


TERNARY_RELATIONS: List[TernaryRelation] = [
    TernaryRelation("left_distributive",  f_arity=2, g_arity=2),
    TernaryRelation("right_distributive", f_arity=2, g_arity=2),
    TernaryRelation("homomorphism",       f_arity=2, g_arity=1),
    TernaryRelation("anti_homomorphism",  f_arity=2, g_arity=1),
]


@dataclass
class TernaryLaw:
    relation_kind: str
    f_name: str
    g_name: str
    f_arity: int
    g_arity: int
    param_types: List[type]
    trials_passed: int
    lhs_expr: str
    rhs_expr: str

    def law_name(self) -> str:
        return f"{self.f_name}_{self.relation_kind}_{self.g_name}"

    def as_ltl_law(self) -> str:
        # Sample arity uses a (x, y, z) triple for distributivity,
        # (x, y) for homomorphisms.
        if self.relation_kind in ("left_distributive", "right_distributive"):
            params = ", ".join(
                f"{v}: {_ltl_type(self.param_types[0])}"
                for v in ("x", "y", "z")
            )
        else:
            params = ", ".join(
                f"{v}: {_ltl_type(self.param_types[0])}"
                for v in ("x", "y")
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


# ─── Inference loop ────────────────────────────────────────────────────────


def _safe_call(fn: Callable, args: tuple) -> Tuple[bool, Any]:
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return True, fn(*args)
    except BaseException:
        return False, None


def _fns_with_arity(
    ns: Dict[str, Any], user_fns: List[str], arity: int
) -> List[Tuple[str, Callable, List[type]]]:
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


def _check_distrib_left(
    f: Callable, g: Callable,
    t: type, trials: int, rng: random.Random,
) -> Tuple[int, int]:
    """f(x, g(y, z)) == g(f(x, y), f(x, z))"""
    passed = valid = 0
    for _ in range(trials):
        try:
            x = _sample(t, rng); y = _sample(t, rng); z = _sample(t, rng)
        except Exception:
            return 0, 0
        ok, gyz = _safe_call(g, (y, z))
        if not ok: continue
        ok, lhs = _safe_call(f, (x, gyz))
        if not ok: continue
        ok, fxy = _safe_call(f, (x, y))
        if not ok: continue
        ok, fxz = _safe_call(f, (x, z))
        if not ok: continue
        ok, rhs = _safe_call(g, (fxy, fxz))
        if not ok: continue
        valid += 1
        if not _equal(lhs, rhs):
            return 0, 0
        passed += 1
    return passed, valid


def _check_distrib_right(
    f: Callable, g: Callable,
    t: type, trials: int, rng: random.Random,
) -> Tuple[int, int]:
    """f(g(x, y), z) == g(f(x, z), f(y, z))"""
    passed = valid = 0
    for _ in range(trials):
        try:
            x = _sample(t, rng); y = _sample(t, rng); z = _sample(t, rng)
        except Exception:
            return 0, 0
        ok, gxy = _safe_call(g, (x, y))
        if not ok: continue
        ok, lhs = _safe_call(f, (gxy, z))
        if not ok: continue
        ok, fxz = _safe_call(f, (x, z))
        if not ok: continue
        ok, fyz = _safe_call(f, (y, z))
        if not ok: continue
        ok, rhs = _safe_call(g, (fxz, fyz))
        if not ok: continue
        valid += 1
        if not _equal(lhs, rhs):
            return 0, 0
        passed += 1
    return passed, valid


def _check_homomorphism(
    f: Callable, g: Callable,
    t: type, trials: int, rng: random.Random,
) -> Tuple[int, int]:
    """g(f(x, y)) == f(g(x), g(y))   — g is a homomorphism w.r.t. f"""
    passed = valid = 0
    for _ in range(trials):
        try:
            x = _sample(t, rng); y = _sample(t, rng)
        except Exception:
            return 0, 0
        ok, fxy = _safe_call(f, (x, y))
        if not ok: continue
        ok, lhs = _safe_call(g, (fxy,))
        if not ok: continue
        ok, gx = _safe_call(g, (x,))
        if not ok: continue
        ok, gy = _safe_call(g, (y,))
        if not ok: continue
        ok, rhs = _safe_call(f, (gx, gy))
        if not ok: continue
        valid += 1
        if not _equal(lhs, rhs):
            return 0, 0
        passed += 1
    return passed, valid


def _check_antihomomorphism(
    f: Callable, g: Callable,
    t: type, trials: int, rng: random.Random,
) -> Tuple[int, int]:
    """g(f(x, y)) == f(g(y), g(x))"""
    passed = valid = 0
    for _ in range(trials):
        try:
            x = _sample(t, rng); y = _sample(t, rng)
        except Exception:
            return 0, 0
        ok, fxy = _safe_call(f, (x, y))
        if not ok: continue
        ok, lhs = _safe_call(g, (fxy,))
        if not ok: continue
        ok, gx = _safe_call(g, (x,))
        if not ok: continue
        ok, gy = _safe_call(g, (y,))
        if not ok: continue
        ok, rhs = _safe_call(f, (gy, gx))
        if not ok: continue
        valid += 1
        if not _equal(lhs, rhs):
            return 0, 0
        passed += 1
    return passed, valid


def _sufficient(valid: int, trials: int) -> bool:
    return valid >= max(6, trials // 6)


def find_ternary_laws(
    file: str | Path,
    *,
    trials: int = 80,
    seed: int = 42,
) -> List[TernaryLaw]:
    """Compile `file`, exec the transpiled Python, try every ternary
    relation across all valid fn pairs, return the matches."""
    from lateralus_lang.compiler import Compiler, Target
    from lateralus_lang.law_discovery import _extract_user_fns
    from lateralus_lang.law_mutator import _exec_capturing

    path = Path(file)
    src = path.read_text()
    result = Compiler().compile_source(src, target=Target.PYTHON, filename=path.name)
    if not result.ok:
        return []

    user_fns = _extract_user_fns(src)
    ns = _exec_capturing(result.python_src or "", "triangulate")

    binaries = _fns_with_arity(ns, user_fns, arity=2)
    unaries  = _fns_with_arity(ns, user_fns, arity=1)

    found: List[TernaryLaw] = []

    # ----- distributivity: f:2, g:2 (not same fn) -----
    for i, (fn_name, f, f_pts) in enumerate(binaries):
        for j, (gn_name, g, g_pts) in enumerate(binaries):
            if fn_name == gn_name:
                continue
            if f_pts != g_pts or f_pts[0] != f_pts[1]:
                continue
            t = f_pts[0]
            rng = random.Random(seed + i * 131 + j * 17 + 1)
            passed, valid = _check_distrib_left(f, g, t, trials, rng)
            if passed > 0 and _sufficient(valid, trials):
                found.append(TernaryLaw(
                    relation_kind="left_distributive",
                    f_name=fn_name, g_name=gn_name,
                    f_arity=2, g_arity=2,
                    param_types=f_pts,
                    trials_passed=passed,
                    lhs_expr=f"{fn_name}(x, {gn_name}(y, z))",
                    rhs_expr=f"{gn_name}({fn_name}(x, y), {fn_name}(x, z))",
                ))
            rng = random.Random(seed + i * 131 + j * 17 + 2)
            passed, valid = _check_distrib_right(f, g, t, trials, rng)
            if passed > 0 and _sufficient(valid, trials):
                found.append(TernaryLaw(
                    relation_kind="right_distributive",
                    f_name=fn_name, g_name=gn_name,
                    f_arity=2, g_arity=2,
                    param_types=f_pts,
                    trials_passed=passed,
                    lhs_expr=f"{fn_name}({gn_name}(x, y), z)",
                    rhs_expr=f"{gn_name}({fn_name}(x, z), {fn_name}(y, z))",
                ))

    # ----- homomorphism: f:2, g:1 -----
    for i, (fn_name, f, f_pts) in enumerate(binaries):
        if f_pts[0] != f_pts[1]:
            continue
        t = f_pts[0]
        for j, (gn_name, g, g_pts) in enumerate(unaries):
            if g_pts[0] != t:
                continue
            rng = random.Random(seed + i * 191 + j * 23 + 3)
            passed, valid = _check_homomorphism(f, g, t, trials, rng)
            is_hom = passed > 0 and _sufficient(valid, trials)
            rng = random.Random(seed + i * 191 + j * 23 + 4)
            passed_a, valid_a = _check_antihomomorphism(f, g, t, trials, rng)
            is_anti = passed_a > 0 and _sufficient(valid_a, trials)

            if is_hom:
                found.append(TernaryLaw(
                    relation_kind="homomorphism",
                    f_name=fn_name, g_name=gn_name,
                    f_arity=2, g_arity=1,
                    param_types=[t, t],
                    trials_passed=passed,
                    lhs_expr=f"{gn_name}({fn_name}(x, y))",
                    rhs_expr=f"{fn_name}({gn_name}(x), {gn_name}(y))",
                ))
            elif is_anti:
                # Only emit anti if homomorphism didn't fire — for
                # commutative f they coincide and homomorphism is
                # simpler to state.
                found.append(TernaryLaw(
                    relation_kind="anti_homomorphism",
                    f_name=fn_name, g_name=gn_name,
                    f_arity=2, g_arity=1,
                    param_types=[t, t],
                    trials_passed=passed_a,
                    lhs_expr=f"{gn_name}({fn_name}(x, y))",
                    rhs_expr=f"{fn_name}({gn_name}(y), {gn_name}(x))",
                ))

    return found


# ─── File driver ───────────────────────────────────────────────────────────


_APPLY_BANNER = (
    "// ─── lateralus triangulate (auto-generated ternary laws) ─────\n"
    "// Re-running `lateralus triangulate --apply` updates this block in place.\n"
)


def _apply_to_source(path: Path, laws: List[TernaryLaw]) -> None:
    src = path.read_text()
    marker = _APPLY_BANNER.strip().splitlines()[0]
    end_marker = "// ─── end lateralus triangulate ────────────────────────────"

    block = [_APPLY_BANNER]
    for l in laws:
        block.append(l.as_ltl_law())
        block.append("")
    block.append(end_marker)
    new_block = "\n\n".join(block)

    if marker in src:
        before, _, rest = src.partition(marker)
        _, _, after = rest.partition(end_marker)
        new_src = before.rstrip() + "\n\n" + new_block + "\n" + after.lstrip()
    else:
        new_src = src.rstrip() + "\n\n" + new_block + "\n"

    path.write_text(new_src)
    print(f"  → patched {len(laws)} ternary laws into {path.name}")


def triangulate_file(
    file: str | Path,
    *,
    trials: int = 80,
    seed: int = 42,
    output: Optional[str] = None,
    apply: bool = False,
) -> int:
    path = Path(file)
    print(f"\n  Triangulating functions in {path.name}")
    print(f"  {'─' * 60}")

    laws = find_ternary_laws(path, trials=trials, seed=seed)

    if not laws:
        print(f"  No ternary structure laws found  (trials={trials}, seed={seed})")
        return 1

    from collections import Counter
    kind_counts = Counter(l.relation_kind for l in laws)
    print(f"  Trials per relation: {trials}, seed={seed}")
    print(f"  Found: {len(laws)} ternary law(s)")
    for kind, n in sorted(kind_counts.items()):
        print(f"    • {kind:<22} ×{n}")
    print()

    for law in laws:
        print(f"    [{law.relation_kind}]  {law.lhs_expr}")
        print(f"    {' ' * (len(law.relation_kind) + 4)}  ≡  {law.rhs_expr}   "
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
            f"// Auto-generated ternary algebraic laws (lateralus triangulate)\n"
            f"// Source file: {path.name}\n"
            f"// Laws: {len(laws)}\n\n"
        )
        body = "\n\n".join(l.as_ltl_law() for l in laws)
        Path(output).write_text(header + body + "\n")
        print(f"  → wrote {len(laws)} laws to {output}")

    if apply:
        _apply_to_source(path, laws)

    return 0
