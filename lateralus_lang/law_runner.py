"""
LATERALUS v3.2 — Law Runner: first-class executable specifications.

A `@law` in Lateralus is a boolean-returning function that the compiler treats
as a property test. No external test framework, no per-type generator class,
no QuickCheck-style typeclass boilerplate. You write:

    @law
    fn reverse_involutive(xs: list[int]) -> bool {
        return reverse(reverse(xs)) == xs
    }

…and `lateralus verify` generates random inputs matching the declared
parameter types, runs the law N times, and reports pass/fail — plus a
shrunken counter-example if any trial returns False or raises.

This is deliberately simpler than Haskell's QuickCheck. Lateralus owns the
type system, so we can derive generators for every parameter type without
user-written instances. Ergonomics wins over theorem-proving rigor: the goal
is to make *writing specifications* as cheap as writing assertions.
"""

from __future__ import annotations

import io
import random
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

# ─── Input generation ──────────────────────────────────────────────────────

_DEFAULT_STR_ALPHABET = "abcdefghijklmnopqrstuvwxyz 0123456789"


def _gen_value(type_str: str, rng: random.Random, size: int = 10,
                structs: Optional[dict] = None) -> Any:
    """Generate a single random value of the given Lateralus type string.

    Supported types:
      - int, float, bool, str
      - list, list[T], map (recursive in T)
      - any (falls back to int)
      - user-defined struct names registered in `structs`
      - anything else: `_UNSUPPORTED` sentinel (skipped by harness)
    """
    structs = structs or {}
    t = (type_str or "any").strip()
    # Strip trailing ? (nullable) — we always produce a value for simplicity
    if t.endswith("?"):
        t = t[:-1]

    if t == "int":
        return rng.randint(-size * 10, size * 10)
    if t == "float":
        # Bounded floats avoid inf/nan from naive operations in specs
        return rng.uniform(-size * 10.0, size * 10.0)
    if t == "bool":
        return rng.random() < 0.5
    if t == "str":
        n = rng.randint(0, size)
        return "".join(rng.choice(_DEFAULT_STR_ALPHABET) for _ in range(n))
    if t == "any":
        return rng.randint(-size * 10, size * 10)

    # list[T] or list
    if t == "list" or t.startswith("list[") or t.startswith("[") or t.startswith("List"):
        if t == "list":
            inner = "int"
        elif t.startswith("list["):
            inner = t[len("list["):-1]
        elif t.startswith("["):
            inner = t[1:-1]
        else:
            inner = "int"
        n = rng.randint(0, size)
        return [_gen_value(inner, rng, size, structs) for _ in range(n)]

    if t == "map" or t.startswith("map[") or t.startswith("Map"):
        if t.startswith("map["):
            inside = t[len("map["):-1]
            # naive split on first comma at depth 0
            depth = 0
            split = -1
            for i, ch in enumerate(inside):
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                elif ch == "," and depth == 0:
                    split = i
                    break
            if split >= 0:
                key_t = inside[:split].strip()
                val_t = inside[split + 1:].strip()
            else:
                key_t = "str"
                val_t = inside.strip()
        else:
            key_t = "str"
            val_t = "int"
        n = rng.randint(0, size)
        out = {}
        for _ in range(n):
            k = _gen_value(key_t, rng, size, structs)
            # dict keys must be hashable
            if isinstance(k, list):
                k = tuple(k)
            out[k] = _gen_value(val_t, rng, size, structs)
        return out

    # User struct: look up in registry and build from _ltl_struct_spec
    if t in structs:
        cls = structs[t]
        field_spec = getattr(cls, "_ltl_struct_spec", [])
        kwargs = {fname: _gen_value(ftype, rng, size, structs)
                  for fname, ftype in field_spec}
        # If any field produced _UNSUPPORTED, propagate up
        if any(v is _UNSUPPORTED for v in kwargs.values()):
            return _UNSUPPORTED
        try:
            return cls(**kwargs)
        except Exception:
            return _UNSUPPORTED

    # Unknown user type → harness will skip this law
    return _UNSUPPORTED


_UNSUPPORTED = object()


# ─── Shrinking ─────────────────────────────────────────────────────────────

def _shrink(value: Any, type_str: str) -> List[Any]:
    """Produce simpler candidates near `value`. Best-effort, not exhaustive.

    Strategy: halve numeric magnitudes, remove list/map elements, zero out.
    The harness tries each candidate and keeps the simplest that still fails.
    """
    t = (type_str or "any").strip().rstrip("?")
    if isinstance(value, bool):
        return [False] if value else []
    if isinstance(value, int):
        out = []
        if value != 0:
            out.append(0)
        if abs(value) > 1:
            out.append(value // 2)
        if value > 0:
            out.append(value - 1)
        elif value < 0:
            out.append(value + 1)
        return out
    if isinstance(value, float):
        out = []
        if value != 0.0:
            out.append(0.0)
        if abs(value) > 1.0:
            out.append(value / 2)
        out.append(round(value, 2))
        return [c for c in out if c != value]
    if isinstance(value, str):
        if not value:
            return []
        out = ["", value[:1], value[:-1]]
        return [c for c in out if c != value]
    if isinstance(value, list):
        if not value:
            return []
        out: List[Any] = [[]]
        # Drop one element at each position
        for i in range(len(value)):
            out.append(value[:i] + value[i + 1:])
        # Shrink inner elements (infer element type from type_str like "list[int]")
        inner_t = "any"
        if t.startswith("list[") and t.endswith("]"):
            inner_t = t[5:-1].strip()
        elif value:
            v0 = value[0]
            inner_t = ("int" if isinstance(v0, bool) is False and isinstance(v0, int)
                       else "float" if isinstance(v0, float)
                       else "str" if isinstance(v0, str)
                       else "bool" if isinstance(v0, bool)
                       else "any")
        for i in range(len(value)):
            for cand in _shrink(value[i], inner_t):
                shrunk = list(value)
                shrunk[i] = cand
                if shrunk != value:
                    out.append(shrunk)
        return out
    if isinstance(value, dict):
        if not value:
            return []
        out = [dict()]
        keys = list(value.keys())
        for k in keys:
            d = dict(value)
            d.pop(k)
            out.append(d)
        return out
    return []


# ─── Running a single law ──────────────────────────────────────────────────

@dataclass
class LawResult:
    name: str
    passed: bool
    trials: int
    counterexample: Optional[Tuple[Any, ...]] = None
    error: Optional[str] = None
    skipped: bool = False
    reason: Optional[str] = None
    proved: bool = False        # True when the entire input space was exhausted
    oracle: bool = False        # True when this was a differential (oracle) law


# ─── Exhaustive enumeration for finite domains ─────────────────────────────

def _finite_values(type_str: str, bound: int) -> Optional[List[Any]]:
    """Return the exhaustive list of values for a finite-domain type, or None.

    - bool  → [False, True]
    - int   → [-bound, ..., bound] when bound > 0
    - Everything else → None (infinite or unsupported for exhaustive).
    """
    t = (type_str or "").strip().rstrip("?")
    if t == "bool":
        return [False, True]
    if t == "int" and bound > 0:
        return list(range(-bound, bound + 1))
    return None


def _enumerate_inputs(spec: List[Tuple[str, str]], bound: int) -> Optional[List[Tuple[Any, ...]]]:
    """Return the full cartesian product of finite-domain params, or None.

    Returns None if any parameter is not finite-domain or if the total case
    count would exceed a sanity cap (10_000 — keeps proofs tractable).
    """
    domains: List[List[Any]] = []
    total = 1
    MAX_CASES = 10_000
    for _name, t in spec:
        dom = _finite_values(t, bound)
        if dom is None:
            return None
        total *= len(dom)
        if total > MAX_CASES:
            return None
        domains.append(dom)
    import itertools
    return list(itertools.product(*domains))


# ─── Running a single law ──────────────────────────────────────────────────

def _safe_call(fn: Callable, args: Tuple[Any, ...]) -> Tuple[bool, Optional[str]]:
    """Call fn(*args) silencing its stdout/stderr.
    Returns (passed, err). A special err string "_ASSUME_" signals the trial
    was discarded via `assume(...)` and should not count toward failures."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            ret = fn(*args)
        if ret is True:
            return True, None
        if ret is False:
            return False, None
        # Non-bool return — treat as error
        return False, f"law returned non-bool: {type(ret).__name__}"
    except AssertionError as e:
        return False, f"assertion failed: {e}"
    except Exception as e:
        if type(e).__name__ == "_AssumptionFailed":
            return True, "_ASSUME_"
        return False, f"{type(e).__name__}: {e}"


def _shrink_counterexample(
    fn: Callable,
    args: Tuple[Any, ...],
    spec: List[Tuple[str, str]],
    max_steps: int = 100,
) -> Tuple[Any, ...]:
    """Iteratively shrink a failing input. Each step tries per-argument shrinks
    and keeps the first candidate that also fails."""
    current = list(args)
    for _ in range(max_steps):
        improved = False
        for i, (_name, type_str) in enumerate(spec):
            for candidate in _shrink(current[i], type_str):
                trial = list(current)
                trial[i] = candidate
                passed, _err = _safe_call(fn, tuple(trial))
                if not passed:
                    current = trial
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break
    return tuple(current)


def run_law(
    fn: Callable,
    spec: List[Tuple[str, str]],
    trials: int = 100,
    seed: Optional[int] = None,
    structs: Optional[dict] = None,
) -> LawResult:
    """Run a single law.

    Three modes, chosen in priority order:

    1. **Oracle mode** (`@law(oracle=ref_fn)`) — generate random inputs, call
       both `fn` and `ref_fn`, assert their outputs are equal. The law body
       itself is ignored; the decorator defines a differential test.

    2. **Exhaustive mode** — when all parameter types are finite (bool, or
       int with `@law(bound=N)`) the entire cartesian product is enumerated
       and the law is reported as ◈ PROVED rather than ✓ sampled. The total
       case count is capped at 10_000 for tractability.

    3. **Property mode** (default) — generate `trials` random inputs, find
       first failure, shrink it.
    """
    name = getattr(fn, "__name__", "<law>")
    trials = int(getattr(fn, "_law_trials", trials))
    bound = int(getattr(fn, "_law_bound", 0))
    force_exhaustive = bool(getattr(fn, "_law_exhaustive", False))
    oracle = getattr(fn, "_law_oracle", None)
    rng = random.Random(seed)
    structs = structs or {}

    # ── Mode 1: Oracle (differential) ──
    if oracle is not None and callable(oracle):
        for _, t in spec:
            if _gen_value(t, rng, structs=structs) is _UNSUPPORTED:
                return LawResult(
                    name=name, passed=False, trials=0, skipped=True,
                    reason=f"no generator for parameter type {t!r}",
                )
        rng = random.Random(seed)  # reset for reproducibility
        agreements = 0
        for trial_num in range(1, trials + 1):
            args = tuple(_gen_value(t, rng, structs=structs) for _name, t in spec)
            try:
                a = fn(*args)
            except Exception as e:
                if type(e).__name__ == "_AssumptionFailed":
                    continue            # precondition rejected this trial
                return LawResult(
                    name=name, passed=False, trials=trial_num,
                    counterexample=args,
                    error=f"fn raised {type(e).__name__}: {e}", oracle=True,
                )
            try:
                b = oracle(*args)
            except Exception as e:
                if type(e).__name__ == "_AssumptionFailed":
                    continue
                return LawResult(
                    name=name, passed=False, trials=trial_num,
                    counterexample=args,
                    error=f"oracle raised {type(e).__name__}: {e}", oracle=True,
                )
            agreements += 1
            if a != b:
                # Shrink: find smaller input where fn != oracle
                def _pred(*xs):
                    try:
                        return fn(*xs) == oracle(*xs)
                    except Exception:
                        return False
                shrunk = _shrink_counterexample(_pred, args, spec)
                return LawResult(
                    name=name, passed=False, trials=trial_num,
                    counterexample=shrunk,
                    error=f"fn={a!r}  oracle={b!r}", oracle=True,
                )
        return LawResult(name=name, passed=True, trials=agreements, oracle=True)

    # ── Mode 2: Exhaustive (auto-detect or forced) ──
    cases = _enumerate_inputs(spec, bound if bound > 0 else 0)
    if cases is None and force_exhaustive and bound <= 0:
        # Forced exhaustive but no bound — try a reasonable default for ints
        cases = _enumerate_inputs(spec, 16)
    if cases is not None:
        checked = 0
        assume_skipped = 0
        for args in cases:
            passed, err = _safe_call(fn, args)
            if err == "_ASSUME_":
                assume_skipped += 1
                continue
            checked += 1
            if not passed:
                shrunk = _shrink_counterexample(fn, args, spec)
                return LawResult(
                    name=name, passed=False, trials=checked,
                    counterexample=shrunk, error=err,
                )
        return LawResult(name=name, passed=True, trials=checked, proved=True)

    # ── Mode 3: Property (randomised sampling) ──
    for _, t in spec:
        sample = _gen_value(t, rng, structs=structs)
        if sample is _UNSUPPORTED:
            return LawResult(
                name=name,
                passed=False,
                trials=0,
                skipped=True,
                reason=f"no generator for parameter type {t!r}",
            )

    assume_skipped = 0
    effective = 0
    for trial_num in range(1, trials + 1):
        args = tuple(_gen_value(t, rng, structs=structs) for _name, t in spec)
        passed, err = _safe_call(fn, args)
        if err == "_ASSUME_":
            assume_skipped += 1
            continue
        effective += 1
        if not passed:
            shrunk = _shrink_counterexample(fn, args, spec)
            return LawResult(
                name=name,
                passed=False,
                trials=trial_num,
                counterexample=shrunk,
                error=err,
            )
    return LawResult(name=name, passed=True, trials=effective)


# ─── Runtime harness injected by `lateralus verify` ────────────────────────

RUNNER_TAIL = r"""
# ── law runner (injected by `lateralus verify`) ──────────────────────────
import sys as _sys
try:
    from lateralus_lang.law_runner import run_law as _run_law
except ImportError:
    # Fallback: inline a minimal runner if the package isn't on PYTHONPATH
    import random as _r
    def _run_law(fn, spec, trials=100, seed=None):
        class _R:
            def __init__(self, **kw): self.__dict__.update(kw)
        rng = _r.Random(seed)
        def gen(t):
            t = t.rstrip("?")
            if t == "int": return rng.randint(-100, 100)
            if t == "float": return rng.uniform(-100.0, 100.0)
            if t == "bool": return rng.random() < 0.5
            if t == "str":
                n = rng.randint(0, 8)
                return "".join(rng.choice("abcxyz ") for _ in range(n))
            if t == "list" or t.startswith("list["):
                inner = "int" if t == "list" else t[5:-1]
                return [gen(inner) for _ in range(rng.randint(0, 8))]
            return 0
        for i in range(trials):
            args = tuple(gen(t) for _, t in spec)
            try:
                ret = fn(*args)
                if ret is not True:
                    return _R(name=fn.__name__, passed=False, trials=i+1,
                              counterexample=args, error=str(ret), skipped=False, reason=None)
            except Exception as e:
                return _R(name=fn.__name__, passed=False, trials=i+1,
                          counterexample=args, error=f"{type(e).__name__}: {e}", skipped=False, reason=None)
        return _R(name=fn.__name__, passed=True, trials=trials, counterexample=None, error=None, skipped=False, reason=None)

_laws = globals().get("_LATERALUS_LAWS", [])
if not _laws:
    print("  no @law declarations found")
    _sys.exit(0)

_trials = int(_GLOBALS_TRIALS) if "_GLOBALS_TRIALS" in globals() else 100
_seed   = _GLOBALS_SEED if "_GLOBALS_SEED" in globals() else None

_GREEN, _RED, _YEL, _GREY, _BOLD, _RST, _CYAN, _MAG = (
    "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[1m", "\033[0m",
    "\033[96m", "\033[95m",
)

_pass = _fail = _skip = _proved = _oracle = 0
_structs = globals().get("_LATERALUS_STRUCTS", {})
for _fn in _laws:
    _spec = getattr(_fn, "_law_spec", [])
    try:
        _res = _run_law(_fn, _spec, trials=_trials, seed=_seed, structs=_structs)
    except TypeError:
        _res = _run_law(_fn, _spec, trials=_trials, seed=_seed)
    if getattr(_res, "skipped", False):
        print(f"  {_YEL}~{_RST}  {_res.name}  {_GREY}(skipped: {_res.reason}){_RST}")
        _skip += 1
    elif _res.passed:
        if getattr(_res, "proved", False):
            print(f"  {_MAG}◈{_RST} {_BOLD}PROVED{_RST}  {_res.name}  "
                  f"{_GREY}(exhaustive: {_res.trials} cases){_RST}")
            _pass += 1; _proved += 1
        elif getattr(_res, "oracle", False):
            print(f"  {_CYAN}≡{_RST}  {_res.name}  "
                  f"{_GREY}({_res.trials} agreements with oracle){_RST}")
            _pass += 1; _oracle += 1
        else:
            print(f"  {_GREEN}✓{_RST}  {_res.name}  {_GREY}({_res.trials} trials){_RST}")
            _pass += 1
    else:
        _label = "FAILED"
        if getattr(_res, "oracle", False):
            _label = "ORACLE MISMATCH"
        elif getattr(_res, "proved", False):
            _label = "DISPROVED"
        print(f"  {_RED}✗{_RST}  {_res.name}  {_GREY}({_label} on trial {_res.trials}){_RST}")
        if _res.counterexample is not None:
            _pretty = ", ".join(
                f"{_name}={_repr!r}" for (_name, _), _repr in zip(_spec, _res.counterexample)
            ) if _spec else repr(_res.counterexample)
            print(f"     {_BOLD}counter-example{_RST}: {_pretty}")
        if _res.error:
            print(f"     {_GREY}error{_RST}: {_res.error}")
        _fail += 1

print()
_extras = []
if _proved: _extras.append(f"{_MAG}{_proved} proved{_RST}")
if _oracle: _extras.append(f"{_CYAN}{_oracle} oracle{_RST}")
_suffix = f"  {_GREY}[{', '.join(_extras)}]{_RST}" if _extras else ""
print(f"  {_BOLD}{_pass} passed  {_fail} failed  {_skip} skipped{_RST}"
      f"{_suffix}  {_GREY}({_trials} trials per law){_RST}")
_sys.exit(0 if _fail == 0 else 1)
"""


def emit_runner_tail(trials: int = 100, seed: Optional[int] = None) -> str:
    """Return the runner-tail string to append to transpiled Python."""
    preamble = f"_GLOBALS_TRIALS = {int(trials)}\n"
    preamble += f"_GLOBALS_SEED = {repr(seed)}\n"
    return preamble + RUNNER_TAIL


def verify_file(
    file: str | Path,
    trials: int = 100,
    seed: Optional[int] = None,
) -> int:
    """Transpile a .ltl file to Python, append the law runner, execute.
    Returns the process exit code (0 = all laws passed)."""
    import subprocess
    import tempfile

    from lateralus_lang.compiler import Compiler, Target

    path = Path(file)
    source = path.read_text()
    compiler = Compiler()
    result = compiler.compile_source(source, target=Target.PYTHON, filename=path.name)
    if not result.ok:
        for e in result.errors:
            msg = getattr(e, "message", str(e))
            print(f"  error: {msg}", file=sys.stderr)
        return 1

    py_src = (result.python_src or "") + "\n" + emit_runner_tail(trials=trials, seed=seed)
    tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w")
    tmp.write(py_src)
    tmp.close()
    try:
        return subprocess.run([sys.executable, tmp.name]).returncode
    finally:
        Path(tmp.name).unlink(missing_ok=True)
