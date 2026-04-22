"""
LATERALUS v3.2 — Inductive Law Generalization (8th pillar)

Where `discover` finds algebraic identities ("f is commutative"), this
module finds *defining equations* ("f(x) ≡ x > 0"). A characterization
is a closed-form `@law` that fully specifies a function's behaviour —
strictly stronger than any finite set of point witnesses.

The synthesizer enumerates a curated catalogue of candidate expressions
matching the function's arity and return type, then tests each against
a random sample. If every sampled input agrees, we emit the
characterization. This is pure inductive inference — no symbolic
solver, no SAT query — yet it succeeds on most real spec targets
(predicates, arithmetic combinators, selectors).
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from lateralus_lang.law_discovery import _equal, _get_param_types, _sample

# ─── Candidate expression catalogue ────────────────────────────────────────

# (display name, arity, return "kind" int|bool, callable)
_Candidate = Tuple[str, int, str, Callable[..., Any]]

_CANDIDATES: List[_Candidate] = [
    # 1-arg bool predicates
    ("x > 0",        1, "bool", lambda x: x > 0),
    ("x >= 0",       1, "bool", lambda x: x >= 0),
    ("x < 0",        1, "bool", lambda x: x < 0),
    ("x <= 0",       1, "bool", lambda x: x <= 0),
    ("x == 0",       1, "bool", lambda x: x == 0),
    ("x != 0",       1, "bool", lambda x: x != 0),
    ("true",         1, "bool", lambda x: True),
    ("false",        1, "bool", lambda x: False),
    ("x % 2 == 0",   1, "bool", lambda x: x % 2 == 0),
    ("x % 2 != 0",   1, "bool", lambda x: x % 2 != 0),
    # 1-arg int/float expressions
    ("x",            1, "num",  lambda x: x),
    ("0 - x",        1, "num",  lambda x: -x),
    ("x + 1",        1, "num",  lambda x: x + 1),
    ("x - 1",        1, "num",  lambda x: x - 1),
    ("x * 2",        1, "num",  lambda x: x * 2),
    ("x * x",        1, "num",  lambda x: x * x),
    ("x + x",        1, "num",  lambda x: x + x),
    ("0",            1, "num",  lambda x: 0),
    ("1",            1, "num",  lambda x: 1),
    ("x < 0 ? 0 - x : x", 1, "num", lambda x: -x if x < 0 else x),
    ("x > 0 ? x : 0 - x", 1, "num", lambda x: x if x > 0 else -x),
    # 2-arg bool predicates
    ("x == y",       2, "bool", lambda x, y: x == y),
    ("x != y",       2, "bool", lambda x, y: x != y),
    ("x > y",        2, "bool", lambda x, y: x > y),
    ("x >= y",       2, "bool", lambda x, y: x >= y),
    ("x < y",        2, "bool", lambda x, y: x < y),
    ("x <= y",       2, "bool", lambda x, y: x <= y),
    # 2-arg int/float expressions
    ("x + y",        2, "num",  lambda x, y: x + y),
    ("x - y",        2, "num",  lambda x, y: x - y),
    ("y - x",        2, "num",  lambda x, y: y - x),
    ("x * y",        2, "num",  lambda x, y: x * y),
    ("x",            2, "num",  lambda x, y: x),
    ("y",            2, "num",  lambda x, y: y),
]


@dataclass
class Characterization:
    fn_name: str
    expr: str                  # e.g. "x > 0" or "x + y"
    return_kind: str           # "bool" | "num"
    param_names: List[str]     # actual parameter names from signature
    param_types: List[type]    # resolved types (int/float/bool)
    trials_passed: int

    def as_ltl_law(self) -> str:
        """Emit a quantified `@law` equivalent to this characterization."""
        params = ", ".join(
            f"{n}: {_ltl_type(t)}" for n, t in zip(self.param_names, self.param_types)
        )
        # Rename `x`/`y` in the expression to the real param names
        expr = self.expr
        if len(self.param_names) >= 1 and self.param_names[0] != "x":
            expr = _rename_var(expr, "x", self.param_names[0])
        if len(self.param_names) >= 2 and self.param_names[1] != "y":
            expr = _rename_var(expr, "y", self.param_names[1])
        call = f"{self.fn_name}({', '.join(self.param_names)})"
        # Always parenthesize to be safe with `==` vs `?:`, `||`, etc.
        rhs = f"({expr})"
        return (
            f"@law\n"
            f"fn {self.fn_name}_characterized({params}) -> bool {{\n"
            f"    return {call} == {rhs}\n"
            f"}}"
        )


def _ltl_type(t: type) -> str:
    if t is bool:  return "bool"
    if t is int:   return "int"
    if t is float: return "float"
    return "int"


def _rename_var(expr: str, old: str, new: str) -> str:
    """Token-level rename respecting word boundaries."""
    import re
    return re.sub(rf"\b{re.escape(old)}\b", new, expr)


# ─── The inference loop ────────────────────────────────────────────────────

def _return_kind(fn: Callable, param_types: List[type], rng: random.Random) -> Optional[str]:
    """Probe the fn once to decide whether it returns bool or numeric."""
    for _ in range(8):
        try:
            args = tuple(_sample(t, rng) for t in param_types)
        except Exception:
            return None
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                v = fn(*args)
        except BaseException:
            continue
        if isinstance(v, bool):
            return "bool"
        if isinstance(v, (int, float)):
            return "num"
    return None


def try_characterize(
    fn: Callable,
    *,
    fn_name: Optional[str] = None,
    trials: int = 60,
    seed: int = 42,
) -> Optional[Characterization]:
    """Search the catalogue for an expression that matches `fn` on every
    sampled input. Returns the first match (most specific first)."""
    param_types = _get_param_types(fn)
    if not param_types:
        return None
    # Only handle 1- or 2-arity with numeric/bool params.
    if len(param_types) not in (1, 2):
        return None
    if any(t not in (int, float, bool) for t in param_types):
        return None

    import inspect
    try:
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())
    except (ValueError, TypeError):
        param_names = [f"arg{i}" for i in range(len(param_types))]

    name = fn_name or getattr(fn, "__name__", "fn")
    rng = random.Random(seed)
    ret_kind = _return_kind(fn, param_types, rng)
    if ret_kind is None:
        return None

    # Pre-generate the input sample — every candidate is scored on the
    # *same* inputs so comparisons are fair.
    samples: List[tuple] = []
    probe_rng = random.Random(seed + 1)
    for _ in range(trials):
        try:
            args = tuple(_sample(t, probe_rng) for t in param_types)
        except Exception:
            break
        samples.append(args)
    if not samples:
        return None

    # Collect ground-truth outputs
    truth: List[tuple] = []
    for args in samples:
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                v = fn(*args)
        except BaseException:
            continue
        truth.append((args, v))
    if len(truth) < max(10, trials // 4):
        # Fn crashed too often to characterize reliably
        return None

    arity = len(param_types)
    # Iterate from most-specific to least-specific (longer expressions first
    # match tighter patterns, then shorter ones catch simple selectors).
    # Rank by prefer-nontrivial: `true`/`false`/`0`/`1` last.
    def priority(cand: _Candidate) -> int:
        name_ = cand[0]
        trivial = name_ in ("true", "false", "0", "1")
        return (1 if trivial else 0, len(name_))
    ordered = sorted(_CANDIDATES, key=priority)

    for cname, ar, kind, cfn in ordered:
        if ar != arity:
            continue
        if kind != ret_kind:
            continue
        ok = True
        for args, v in truth:
            try:
                guess = cfn(*args)
            except BaseException:
                ok = False
                break
            if not _equal(guess, v):
                ok = False
                break
        if ok:
            return Characterization(
                fn_name=name,
                expr=cname,
                return_kind=ret_kind,
                param_names=param_names,
                param_types=param_types,
                trials_passed=len(truth),
            )
    return None


# ─── File-level driver ────────────────────────────────────────────────────

def characterize_file(
    file: str | Path,
    *,
    trials: int = 60,
    seed: int = 42,
    output: Optional[str] = None,
) -> int:
    """Compile `file`, execute the transpiled Python in a namespace, and
    try to find a closed-form characterization for each user function.
    Prints (and optionally writes) matching `@law` snippets."""
    from lateralus_lang.compiler import Compiler, Target
    from lateralus_lang.law_mutator import _exec_capturing, _extract_user_fns

    path = Path(file)
    src = path.read_text()
    result = Compiler().compile_source(src, target=Target.PYTHON, filename=path.name)
    if not result.ok:
        import sys
        for e in result.errors:
            print(f"  error: {getattr(e, 'message', str(e))}", file=sys.stderr)
        return 1

    user_fns = _extract_user_fns(src)
    ns = _exec_capturing(result.python_src or "", "characterize")

    print(f"\n  Characterizing functions in {path.name}")
    print(f"  {'─' * 60}")
    print(f"  User functions: {len(user_fns)}  {sorted(user_fns)[:6]}"
          f"{'…' if len(user_fns) > 6 else ''}")
    print(f"  Trials per candidate: {trials}, seed={seed}")
    print()

    emitted: List[Characterization] = []
    skipped = 0
    for fname in sorted(user_fns):
        fn = ns.get(fname)
        if not callable(fn):
            continue
        c = try_characterize(fn, fn_name=fname, trials=trials, seed=seed)
        if c is None:
            skipped += 1
            print(f"    {fname}: (no closed-form match found)")
            continue
        emitted.append(c)
        print(f"    {fname}  ≡  {c.expr}   ({c.trials_passed} trials)")

    print()
    print(f"  Characterized: {len(emitted)}  |  Unmatched: {skipped}")

    if emitted:
        print()
        print("  ─── Generated @law snippets ───")
        print()
        for c in emitted:
            for line in c.as_ltl_law().splitlines():
                print(f"    {line}")
            print()

    if output and emitted:
        header = (
            f"// Auto-generated characterization laws (lateralus characterize)\n"
            f"// Source file: {path.name}\n"
            f"// Characterized: {len(emitted)} function(s)\n\n"
        )
        body = "\n\n".join(c.as_ltl_law() for c in emitted)
        Path(output).write_text(header + body + "\n")
        print(f"  → wrote {len(emitted)} laws to {output}")

    return 0 if emitted else 1
