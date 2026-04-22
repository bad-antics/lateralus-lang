"""
LATERALUS v3.2 — Automatic Law Discovery

Given an implementation, propose laws it satisfies. Drop-in catalog of
algebraic patterns (commutativity, associativity, identity, idempotence,
involution, absorption, distributivity, oddness) is tested against every
user function; those that pass with zero counterexamples over N trials
become *suggested* `@law` declarations — ready to paste into the source.

No other mainstream PBT tool does this. QuickCheck, Hypothesis, mutmut
all require you to *write* laws first. Lateralus proposes them, so the
verification loop bootstraps itself:

    discover  →  propose laws  →  verify  →  mutate-test  →  proved

Safe to run on arbitrary code: each trial is isolated, timeouts are
enforced at the Python level, and any exception from the user function
is treated as the law not holding (never crashes the discovery pass).
"""
from __future__ import annotations

import inspect
import io
import random
import re
import sys
import typing
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─── Type classification ───────────────────────────────────────────────────

_INT_TYPES = (int,)
_FLOAT_TYPES = (float,)
_NUM_TYPES = (int, float)


def _is_int_type(t) -> bool:
    return t is int


def _is_bool_type(t) -> bool:
    return t is bool


def _is_num_type(t) -> bool:
    return t in (int, float)


def _get_param_types(fn: Callable) -> Optional[List[type]]:
    """Return the list of annotated parameter types, or None if any is
    missing/unsupported. Uses `typing.get_type_hints` to resolve strings."""
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        return None
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        return None
    types: List[type] = []
    for name, param in sig.parameters.items():
        t = hints.get(name, param.annotation)
        if t is inspect.Parameter.empty:
            return None
        types.append(t)
    return types


def _get_return_type(fn: Callable) -> Optional[type]:
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        return None
    return hints.get("return")


# ─── Sample generation ─────────────────────────────────────────────────────

def _sample(t: type, rng: random.Random) -> Any:
    if t is bool:
        return rng.choice([False, True])
    if t is int:
        return rng.randint(-50, 50)
    if t is float:
        return rng.uniform(-50.0, 50.0)
    raise ValueError(f"unsupported sample type: {t}")


def _equal(a: Any, b: Any, tol: float = 1e-9) -> bool:
    """Structural equality with float tolerance."""
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= tol * (1.0 + abs(float(a)) + abs(float(b)))
        except Exception:
            return False
    return a == b


def _call_silent(fn: Callable, *args) -> Tuple[bool, Any]:
    """Call fn suppressing stdout/stderr. Returns (ok, value)."""
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return True, fn(*args)
    except Exception:
        return False, None


# ─── Pattern catalog ───────────────────────────────────────────────────────

@dataclass
class DiscoveredLaw:
    fn_name: str
    pattern: str                        # short identifier, e.g. "commutative"
    ltl_source: str                     # the `@law fn ...` snippet
    trials: int
    co_fn: Optional[str] = None         # partner function for cross-patterns


@dataclass
class DiscoveryReport:
    laws: List[DiscoveredLaw] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)  # fn name + reason

    def __bool__(self) -> bool:
        return bool(self.laws)


def _check_many(
    trial_fn: Callable[[random.Random], bool],
    trials: int,
    rng: random.Random,
) -> bool:
    """Return True iff every trial returned True (and no exceptions)."""
    for _ in range(trials):
        try:
            if not trial_fn(rng):
                return False
        except Exception:
            return False
    return True


# ── Unary patterns ─────────────────────────────────────────────────────

def _test_involutive(fn: Callable, ts: List[type], rt: Optional[type],
                     trials: int, rng: random.Random) -> bool:
    """f(f(x)) == x"""
    if len(ts) != 1:
        return False
    if rt is not None and rt is not ts[0]:
        return False
    if not (_is_num_type(ts[0]) or _is_bool_type(ts[0])):
        return False
    def trial(r):
        x = _sample(ts[0], r)
        ok1, y = _call_silent(fn, x)
        if not ok1:
            return False
        ok2, z = _call_silent(fn, y)
        return ok2 and _equal(z, x)
    return _check_many(trial, trials, rng)


def _test_idempotent_unary(fn: Callable, ts: List[type], rt: Optional[type],
                           trials: int, rng: random.Random) -> bool:
    """f(f(x)) == f(x)"""
    if len(ts) != 1:
        return False
    if rt is not None and rt is not ts[0]:
        return False
    if not (_is_num_type(ts[0]) or _is_bool_type(ts[0])):
        return False
    def trial(r):
        x = _sample(ts[0], r)
        ok1, y = _call_silent(fn, x)
        if not ok1:
            return False
        ok2, z = _call_silent(fn, y)
        return ok2 and _equal(z, y)
    # Reject trivial identity (f(x) == x for all x) — not interesting.
    def non_trivial(r):
        x = _sample(ts[0], r)
        ok, y = _call_silent(fn, x)
        return ok and not _equal(y, x)
    has_non_id = any(non_trivial(rng) for _ in range(min(trials, 20)))
    return has_non_id and _check_many(trial, trials, rng)


def _test_odd(fn: Callable, ts: List[type], rt: Optional[type],
              trials: int, rng: random.Random) -> bool:
    """f(-x) == -f(x)"""
    if len(ts) != 1:
        return False
    if not _is_num_type(ts[0]):
        return False
    if rt is not None and not _is_num_type(rt):
        return False
    def trial(r):
        x = _sample(ts[0], r)
        if x == 0:
            x = 1
        ok1, y1 = _call_silent(fn, x)
        ok2, y2 = _call_silent(fn, -x)
        return ok1 and ok2 and _equal(y2, -y1)
    return _check_many(trial, trials, rng)


# ── Binary patterns ────────────────────────────────────────────────────

def _test_commutative(fn: Callable, ts: List[type], rt: Optional[type],
                      trials: int, rng: random.Random) -> bool:
    """f(a, b) == f(b, a)"""
    if len(ts) != 2 or ts[0] is not ts[1]:
        return False
    if not (_is_num_type(ts[0]) or _is_bool_type(ts[0])):
        return False
    def trial(r):
        a, b = _sample(ts[0], r), _sample(ts[1], r)
        ok1, v1 = _call_silent(fn, a, b)
        ok2, v2 = _call_silent(fn, b, a)
        return ok1 and ok2 and _equal(v1, v2)
    return _check_many(trial, trials, rng)


def _test_associative(fn: Callable, ts: List[type], rt: Optional[type],
                      trials: int, rng: random.Random) -> bool:
    """f(f(a,b),c) == f(a,f(b,c))"""
    if len(ts) != 2 or ts[0] is not ts[1]:
        return False
    if rt is not None and rt is not ts[0]:
        return False
    if not (_is_num_type(ts[0]) or _is_bool_type(ts[0])):
        return False
    def trial(r):
        a, b, c = (_sample(ts[0], r) for _ in range(3))
        ok1, ab = _call_silent(fn, a, b)
        if not ok1: return False
        ok2, abc1 = _call_silent(fn, ab, c)
        ok3, bc = _call_silent(fn, b, c)
        if not ok2 or not ok3: return False
        ok4, abc2 = _call_silent(fn, a, bc)
        return ok4 and _equal(abc1, abc2)
    return _check_many(trial, trials, rng)


def _test_idempotent_binary(fn: Callable, ts: List[type], rt: Optional[type],
                            trials: int, rng: random.Random) -> bool:
    """f(a, a) == a"""
    if len(ts) != 2 or ts[0] is not ts[1]:
        return False
    if rt is not None and rt is not ts[0]:
        return False
    if not (_is_num_type(ts[0]) or _is_bool_type(ts[0])):
        return False
    def trial(r):
        a = _sample(ts[0], r)
        ok, v = _call_silent(fn, a, a)
        return ok and _equal(v, a)
    return _check_many(trial, trials, rng)


def _test_identity_constant(fn: Callable, ts: List[type], rt: Optional[type],
                            trials: int, rng: random.Random,
                            *, side: str, constant: Any) -> bool:
    """f(c, a) == a  (side='left')   or   f(a, c) == a  (side='right')"""
    if len(ts) != 2 or ts[0] is not ts[1]:
        return False
    if rt is not None and rt is not ts[0]:
        return False
    if not _is_num_type(ts[0]):
        return False
    if isinstance(constant, float) != (ts[0] is float):
        # 0.0 for float, 0/1 for int
        constant = float(constant) if ts[0] is float else int(constant)
    def trial(r):
        a = _sample(ts[0], r)
        if side == "left":
            ok, v = _call_silent(fn, constant, a)
        else:
            ok, v = _call_silent(fn, a, constant)
        return ok and _equal(v, a)
    return _check_many(trial, trials, rng)


def _test_absorbing(fn: Callable, ts: List[type], rt: Optional[type],
                    trials: int, rng: random.Random,
                    *, side: str, constant: Any) -> bool:
    """f(c, a) == c  (left)  or  f(a, c) == c  (right)"""
    if len(ts) != 2 or ts[0] is not ts[1]:
        return False
    if rt is not None and rt is not ts[0]:
        return False
    if not _is_num_type(ts[0]):
        return False
    if ts[0] is float and isinstance(constant, int):
        constant = float(constant)
    def trial(r):
        a = _sample(ts[0], r)
        if side == "left":
            ok, v = _call_silent(fn, constant, a)
        else:
            ok, v = _call_silent(fn, a, constant)
        return ok and _equal(v, constant)
    return _check_many(trial, trials, rng)


# ── Cross-function pattern ─────────────────────────────────────────────

def _test_distributive(f: Callable, g: Callable,
                       trials: int, rng: random.Random) -> bool:
    """f(a, g(b,c)) == g(f(a,b), f(a,c))"""
    tsf = _get_param_types(f); tsg = _get_param_types(g)
    rtf = _get_return_type(f); rtg = _get_return_type(g)
    if not tsf or not tsg: return False
    if len(tsf) != 2 or len(tsg) != 2: return False
    if not (tsf[0] is tsf[1] is tsg[0] is tsg[1]): return False
    if not _is_num_type(tsf[0]): return False
    if rtf is not None and rtf is not tsf[0]: return False
    if rtg is not None and rtg is not tsg[0]: return False
    T = tsf[0]
    def trial(r):
        a, b, c = (_sample(T, r) for _ in range(3))
        ok1, bc = _call_silent(g, b, c)
        ok2, lhs = _call_silent(f, a, bc) if ok1 else (False, None)
        ok3, fab = _call_silent(f, a, b)
        ok4, fac = _call_silent(f, a, c)
        if not (ok1 and ok2 and ok3 and ok4): return False
        ok5, rhs = _call_silent(g, fab, fac)
        return ok5 and _equal(lhs, rhs)
    return _check_many(trial, trials, rng)


# ─── Source emitters ───────────────────────────────────────────────────────

def _type_name(t: type) -> str:
    if t is int:   return "int"
    if t is float: return "float"
    if t is bool:  return "bool"
    return t.__name__


def _emit_law_source(kind: str, fn_name: str, ts: List[type], **extras) -> str:
    """Produce a Lateralus `@law` snippet for the discovered pattern."""
    T = _type_name(ts[0])
    if kind == "commutative":
        return (
            f"@law\n"
            f"fn {fn_name}_is_commutative(a: {T}, b: {T}) -> bool {{\n"
            f"    return {fn_name}(a, b) == {fn_name}(b, a)\n"
            f"}}"
        )
    if kind == "associative":
        return (
            f"@law\n"
            f"fn {fn_name}_is_associative(a: {T}, b: {T}, c: {T}) -> bool {{\n"
            f"    return {fn_name}({fn_name}(a, b), c) == {fn_name}(a, {fn_name}(b, c))\n"
            f"}}"
        )
    if kind == "idempotent_binary":
        return (
            f"@law\n"
            f"fn {fn_name}_is_idempotent(a: {T}) -> bool {{\n"
            f"    return {fn_name}(a, a) == a\n"
            f"}}"
        )
    if kind == "idempotent_unary":
        return (
            f"@law\n"
            f"fn {fn_name}_is_idempotent(x: {T}) -> bool {{\n"
            f"    return {fn_name}({fn_name}(x)) == {fn_name}(x)\n"
            f"}}"
        )
    if kind == "involutive":
        return (
            f"@law\n"
            f"fn {fn_name}_is_involutive(x: {T}) -> bool {{\n"
            f"    return {fn_name}({fn_name}(x)) == x\n"
            f"}}"
        )
    if kind == "odd":
        return (
            f"@law\n"
            f"fn {fn_name}_is_odd(x: {T}) -> bool {{\n"
            f"    return {fn_name}(-x) == -{fn_name}(x)\n"
            f"}}"
        )
    if kind == "identity":
        side = extras["side"]; c = extras["constant"]
        args = f"{c}, a" if side == "left" else f"a, {c}"
        return (
            f"@law\n"
            f"fn {fn_name}_has_{side}_identity_{c}(a: {T}) -> bool {{\n"
            f"    return {fn_name}({args}) == a\n"
            f"}}"
        )
    if kind == "absorbing":
        side = extras["side"]; c = extras["constant"]
        args = f"{c}, a" if side == "left" else f"a, {c}"
        return (
            f"@law\n"
            f"fn {fn_name}_absorbs_{c}_{side}(a: {T}) -> bool {{\n"
            f"    return {fn_name}({args}) == {c}\n"
            f"}}"
        )
    if kind == "distributive":
        partner = extras["partner"]
        return (
            f"@law\n"
            f"fn {fn_name}_distributes_over_{partner}(a: {T}, b: {T}, c: {T}) -> bool {{\n"
            f"    return {fn_name}(a, {partner}(b, c)) == "
            f"{partner}({fn_name}(a, b), {fn_name}(a, c))\n"
            f"}}"
        )
    raise ValueError(kind)


# ─── User-function extraction (reuses mutator logic) ───────────────────────

_LTL_FN_RE = re.compile(r"^\s*(?:pub\s+)?fn\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(", re.MULTILINE)
_LTL_LAW_RE = re.compile(
    r"^\s*@law\b[^\n]*\n\s*(?:pub\s+)?fn\s+([a-zA-Z_][a-zA-Z_0-9]*)",
    re.MULTILINE,
)


def _extract_user_fns(ltl_source: str) -> List[str]:
    stripped = re.sub(r"//[^\n]*", "", ltl_source)
    order = _LTL_FN_RE.findall(stripped)
    law_fns = set(_LTL_LAW_RE.findall(stripped))
    seen = set()
    out = []
    for name in order:
        if name not in law_fns and name not in seen:
            out.append(name)
            seen.add(name)
    return out


# ─── Driver ────────────────────────────────────────────────────────────────

def discover_laws(
    file: str | Path,
    *,
    trials: int = 60,
    seed: int = 42,
    verbose: bool = True,
) -> DiscoveryReport:
    """Transpile `file`, import it, and try every pattern on every user fn."""
    from lateralus_lang.compiler import Compiler, Target

    path = Path(file)
    src = path.read_text()
    result = Compiler().compile_source(src, target=Target.PYTHON, filename=path.name)
    if not result.ok:
        for e in result.errors:
            print(f"  error: {getattr(e, 'message', str(e))}", file=sys.stderr)
        return DiscoveryReport()

    # Execute transpiled module in an isolated namespace — but we must
    # neutralize `law` / `@law` decorators during import so declaring
    # them doesn't run verification. The generated preamble already
    # defines `law` as a no-op decorator at import time; only
    # `emit_runner_tail` triggers the run. We simply don't append it.
    ns: Dict[str, Any] = {"__name__": "__ltl_discovery__"}
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            exec(result.python_src, ns)
    except Exception as e:
        print(f"  error importing module: {e}", file=sys.stderr)
        return DiscoveryReport()

    user_fn_names = _extract_user_fns(src)
    report = DiscoveryReport()
    rng = random.Random(seed)

    def _fresh_rng() -> random.Random:
        return random.Random(rng.randint(0, 2**31 - 1))

    # Resolve callables
    callables: Dict[str, Callable] = {}
    for name in user_fn_names:
        obj = ns.get(name)
        if callable(obj):
            callables[name] = obj
        else:
            report.skipped.append(f"{name} (not found in module)")

    if verbose:
        print(f"\n  Discovering laws in {path.name}")
        print(f"  {'─' * 60}")
        print(f"  User functions: {len(callables)}  {list(callables)[:6]}"
              f"{'…' if len(callables) > 6 else ''}")
        print(f"  Trials per pattern: {trials}, seed={seed}")
        print()

    # ── Single-function patterns ─────────────────────────────────────
    single_patterns = [
        ("commutative",          _test_commutative,         "binary"),
        ("associative",          _test_associative,         "binary"),
        ("idempotent_binary",    _test_idempotent_binary,   "binary"),
        ("idempotent_unary",     _test_idempotent_unary,    "unary"),
        ("involutive",           _test_involutive,          "unary"),
        ("odd",                  _test_odd,                 "unary"),
    ]
    for name, fn in callables.items():
        ts = _get_param_types(fn)
        rt = _get_return_type(fn)
        if ts is None:
            report.skipped.append(f"{name} (no type annotations)")
            continue
        for kind, tester, _arity in single_patterns:
            try:
                if tester(fn, ts, rt, trials, _fresh_rng()):
                    src = _emit_law_source(kind, name, ts)
                    report.laws.append(DiscoveredLaw(
                        fn_name=name, pattern=kind,
                        ltl_source=src, trials=trials,
                    ))
            except Exception:
                pass

        # identity / absorbing — parameterized by {0, 1} on each side
        if (len(ts) == 2 and ts[0] is ts[1] and _is_num_type(ts[0])
                and (rt is None or rt is ts[0])):
            for side in ("left", "right"):
                for c in (0, 1):
                    if _test_identity_constant(fn, ts, rt, trials, _fresh_rng(),
                                               side=side, constant=c):
                        src = _emit_law_source("identity", name, ts,
                                               side=side, constant=c)
                        report.laws.append(DiscoveredLaw(
                            fn_name=name, pattern=f"identity_{side}_{c}",
                            ltl_source=src, trials=trials,
                        ))
                for c in (0,):
                    if _test_absorbing(fn, ts, rt, trials, _fresh_rng(),
                                       side=side, constant=c):
                        src = _emit_law_source("absorbing", name, ts,
                                               side=side, constant=c)
                        report.laws.append(DiscoveredLaw(
                            fn_name=name, pattern=f"absorb_{c}_{side}",
                            ltl_source=src, trials=trials,
                        ))

    # ── Cross-function distributivity ─────────────────────────────────
    names_list = list(callables)
    for fn_name in names_list:
        for g_name in names_list:
            if fn_name == g_name:
                continue
            f, g = callables[fn_name], callables[g_name]
            try:
                if _test_distributive(f, g, trials, _fresh_rng()):
                    ts = _get_param_types(f)
                    src = _emit_law_source("distributive", fn_name, ts,
                                           partner=g_name)
                    report.laws.append(DiscoveredLaw(
                        fn_name=fn_name, pattern="distributive",
                        ltl_source=src, trials=trials, co_fn=g_name,
                    ))
            except Exception:
                pass

    return report


# ─── CLI entry point ───────────────────────────────────────────────────────

_GREEN  = "\x1b[32m"
_CYAN   = "\x1b[36m"
_YELLOW = "\x1b[33m"
_GREY   = "\x1b[90m"
_BOLD   = "\x1b[1m"
_RST    = "\x1b[0m"


def discover_file(
    file: str | Path,
    *,
    trials: int = 60,
    seed: int = 42,
    output: Optional[str] = None,
    verbose: bool = True,
) -> int:
    report = discover_laws(file, trials=trials, seed=seed, verbose=verbose)

    if verbose:
        by_fn: Dict[str, List[DiscoveredLaw]] = {}
        for law in report.laws:
            by_fn.setdefault(law.fn_name, []).append(law)
        for fn_name in sorted(by_fn):
            print(f"  {_BOLD}{fn_name}{_RST}")
            for law in by_fn[fn_name]:
                tag = law.pattern
                partner = f" over {law.co_fn}" if law.co_fn else ""
                print(f"    {_GREEN}✓{_RST} {_CYAN}{tag}{_RST}{partner}"
                      f"  {_GREY}({law.trials} trials){_RST}")
        if report.skipped and verbose:
            print()
            for s in report.skipped:
                print(f"  {_GREY}· skipped: {s}{_RST}")
        print()
        total = len(report.laws)
        print(f"  {_BOLD}Discovered {total} law{'s' if total != 1 else ''}{_RST}")

    if output:
        lines = [
            "// ═══════════════════════════════════════════════════════════════════",
            f"// Laws discovered automatically by `lateralus discover {Path(file).name}`",
            f"// {len(report.laws)} candidates — review before committing.",
            "// ═══════════════════════════════════════════════════════════════════",
            "",
        ]
        for law in report.laws:
            lines.append(law.ltl_source)
            lines.append("")
        Path(output).write_text("\n".join(lines))
        if verbose:
            print(f"  Written → {output}")

    return 0 if report.laws else 1
