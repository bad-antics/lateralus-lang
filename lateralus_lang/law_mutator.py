"""
LATERALUS v3.2 — Law-driven Mutation Testing

Measures the *quality* of `@law` specifications by systematically mutating
the transpiled Python source and checking whether the existing laws detect
each mutation. A law is only as strong as the mutations it catches.

Mutation score = (mutations caught by at least one law) / (total mutations).

A score of 1.0 means every syntactic perturbation of the implementation
violates at least one declared invariant — evidence that the spec is tight.
A low score means laws are probably missing or too weak.

No other mainstream language ships mutation testing driven by executable
specifications. Rust has `mutagen`, JS has `stryker`, but neither is
paired with first-class property declarations. Lateralus fuses them.
"""
from __future__ import annotations

import ast
import io
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# ─── Mutation operators ────────────────────────────────────────────────────

# (description, regex, replacement) — applied one at a time to python source.
# Regex uses \b-anchored tokens so we don't mutate substrings of identifiers.
_MUTATIONS: List[Tuple[str, str, str]] = [
    # Arithmetic operator swaps
    ("+  →  -",  r"(?<![=+\-*/<>!])\s\+\s(?![=+])",       " - "),
    ("-  →  +",  r"(?<![=+\-*/<>!])\s-\s(?![=])",          " + "),
    ("*  →  /",  r"(?<![=*/])\*(?![=*])",                  "/"),
    ("/  →  *",  r"(?<![=/])/(?![=/])",                    "*"),
    ("//  →  *", r"(?<![=])//(?![=])",                     "*"),
    # Comparison flips
    ("==  →  !=", r"==",                                   "!="),
    ("!=  →  ==", r"!=",                                   "=="),
    ("<  →  >",   r"(?<![<=])\s<\s(?![=])",                " > "),
    (">  →  <",   r"(?<![>=])\s>\s(?![=])",                " < "),
    ("<=  →  >", r"<=",                                    ">"),
    (">=  →  <", r">=",                                    "<"),
    # Boolean flips
    ("and  →  or",  r"\band\b",                            "or"),
    ("or  →  and",  r"\bor\b",                             "and"),
    ("True  →  False",  r"\bTrue\b",                       "False"),
    ("False  →  True",  r"\bFalse\b",                      "True"),
    ("not x  →  x",  r"\bnot\s+",                          ""),
    # Constant perturbations
    ("0  →  1",  r"(?<![\w.])\b0\b(?![\w.])",              "1"),
    ("1  →  0",  r"(?<![\w.])\b1\b(?![\w.])",              "0"),
]


# ─── Mutant model ──────────────────────────────────────────────────────────

@dataclass
class Mutant:
    """One single-site mutation: swap exactly one occurrence of `pattern`
    at `match_index` with `replacement` in the source."""
    rule_name: str
    pattern: str
    replacement: str
    match_index: int          # which match of pattern to replace
    line_no: int              # 1-based line number in the source
    line_snippet: str         # the line after mutation, for reporting
    containing_fn: Optional[str] = None   # user fn name enclosing this line


@dataclass
class ProposedLaw:
    """A synthesized @law that would kill a surviving mutant."""
    fn_name: str
    witness_args: Tuple          # the discriminating input
    expected: object             # orig_fn(*witness_args)
    mutant_yields: object        # mut_fn(*witness_args)
    ltl_source: str              # ready-to-paste @law snippet


@dataclass
class MutationReport:
    total: int = 0
    caught: int = 0
    survivors: List[Mutant] = field(default_factory=list)
    equivalents: List[Mutant] = field(default_factory=list)  # caused no-op
    proposals: List[ProposedLaw] = field(default_factory=list)

    @property
    def score(self) -> float:
        testable = self.total - len(self.equivalents)
        return (self.caught / testable) if testable else 1.0


# ─── Source-line scope helpers ─────────────────────────────────────────────

# Don't mutate the law runner, generator, or registry — only the user's
# implementation code. We detect runner lines by a marker comment.
_RUNNER_MARKER = "# ── law runner (injected by `lateralus verify`) ──"
# Lines inside these function bodies are laws themselves — don't mutate them,
# because a mutated law is meaningless (laws define what's true).
_LAW_FUNCS_RE = re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(", re.MULTILINE)


def _find_protected_spans(source: str, user_fns: Optional[set] = None) -> List[Tuple[int, int]]:
    """Return [(start_line, end_line), ...] spans to protect from mutation.

    If `user_fns` is given, the *inverse* policy is used: we protect EVERY
    line except the bodies of functions whose names appear in `user_fns`
    and which are NOT decorated with `@law`. This cleanly restricts
    mutation to user-authored implementation code when running through
    the compiler (which prepends a large stdlib preamble).

    Otherwise, falls back to protecting the runner tail and @law bodies.
    """
    lines = source.splitlines()
    total = len(lines)
    spans: List[Tuple[int, int]] = []

    # 1. Runner tail
    for i, ln in enumerate(lines, 1):
        if _RUNNER_MARKER in ln:
            spans.append((i, total))
            break

    # 2. Parse AST once
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return spans

    if user_fns is not None:
        # Invert: build set of unprotected spans (user fn bodies), then
        # protect everything else.
        unprotected: List[Tuple[int, int]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name not in user_fns:
                continue
            # Skip @law-decorated functions (they're the spec, not the impl)
            is_law = False
            for dec in node.decorator_list:
                n = dec.func.id if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) \
                    else (dec.id if isinstance(dec, ast.Name) else None)
                if n == "law":
                    is_law = True
                    break
            if is_law:
                continue
            # Protect decorators/signature line; allow body lines only
            body_start = node.body[0].lineno if node.body else node.lineno
            body_end = node.end_lineno or node.lineno
            unprotected.append((body_start, body_end))
        # Convert unprotected → protected complement
        unprotected.sort()
        cursor = 1
        for s, e in unprotected:
            if cursor < s:
                spans.append((cursor, s - 1))
            cursor = e + 1
        if cursor <= total:
            spans.append((cursor, total))
        return spans

    # 3. Legacy path: protect @law bodies
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            name = dec.id if isinstance(dec, ast.Name) else (
                dec.func.id if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) else None
            )
            if name == "law":
                start = min(d.lineno for d in node.decorator_list)
                end = node.end_lineno or node.lineno
                spans.append((start, end))
                break
    return spans


def _is_protected(line_no: int, spans: List[Tuple[int, int]]) -> bool:
    return any(s <= line_no <= e for s, e in spans)


def _build_line_to_fn_map(source: str, user_fns: set) -> dict:
    """Map each line number inside a user fn body → that fn's name."""
    out = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in user_fns:
            continue
        start = node.body[0].lineno if node.body else node.lineno
        end = node.end_lineno or node.lineno
        for ln in range(start, end + 1):
            out[ln] = node.name
    return out


# ─── Mutation generation ───────────────────────────────────────────────────

def generate_mutants(source: str, user_fns: Optional[set] = None) -> List[Mutant]:
    """Produce the full list of candidate mutants for the given source.

    If `user_fns` is provided, only lines inside the bodies of those
    (non-`@law`-decorated) functions are eligible for mutation."""
    spans = _find_protected_spans(source, user_fns=user_fns)
    line_to_fn = _build_line_to_fn_map(source, user_fns or set())
    mutants: List[Mutant] = []
    for rule_name, pattern, repl in _MUTATIONS:
        for match_idx, m in enumerate(re.finditer(pattern, source)):
            line_no = source.count("\n", 0, m.start()) + 1
            if _is_protected(line_no, spans):
                continue
            mutated = source[:m.start()] + repl + source[m.end():]
            mutated_line = mutated.splitlines()[line_no - 1]
            mutants.append(Mutant(
                rule_name=rule_name,
                pattern=pattern,
                replacement=repl,
                match_index=match_idx,
                line_no=line_no,
                line_snippet=mutated_line.strip()[:90],
                containing_fn=line_to_fn.get(line_no),
            ))
    return mutants


def apply_mutant(source: str, mutant: Mutant, user_fns: Optional[set] = None) -> str:
    """Return the source with exactly `mutant` applied."""
    spans = _find_protected_spans(source, user_fns=user_fns)
    for idx, m in enumerate(re.finditer(mutant.pattern, source)):
        if idx != mutant.match_index:
            continue
        line_no = source.count("\n", 0, m.start()) + 1
        if _is_protected(line_no, spans):
            return source  # protected — no-op
        return source[:m.start()] + mutant.replacement + source[m.end():]
    return source


# ─── Runner: does a mutated program still pass its laws? ──────────────────

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _run_python(source: str, timeout: float = 10.0) -> Tuple[int, str]:
    """Write source to a tempfile and run it with the current interpreter.
    Returns (exit_code, stdout). A non-zero exit (or timeout, or syntax error)
    means the mutant was *caught* by at least one law."""
    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write(source)
        tmp.close()
        try:
            proc = subprocess.run(
                [sys.executable, tmp.name],
                capture_output=True, text=True, timeout=timeout,
            )
            return proc.returncode, _ANSI_RE.sub("", proc.stdout)
        except subprocess.TimeoutExpired:
            return 1, "<timeout>"
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    except Exception as e:
        return 1, f"<error: {e}>"


# ─── Witness-based law proposal ────────────────────────────────────────────

def _py_to_ltl_literal(v) -> str:
    """Render a Python value as a Lateralus literal for emitted @law source."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return repr(v)
    if isinstance(v, float):
        # `repr(1.0)` → '1.0' — already valid ltl float literal
        return repr(v)
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    # Lists / dicts: best-effort, falls through to Python repr
    return repr(v)


def _exec_capturing(source: str, name: str) -> dict:
    """Exec `source` into a fresh namespace, swallowing stdout/stderr AND
    any top-level exception (e.g. a failed `assert` in the runner tail).
    Function defs are evaluated before the tail executes, so they remain
    in the namespace even if a later law assertion raises."""
    ns: dict = {"__name__": f"<{name}>"}
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            exec(compile(source, f"<{name}>", "exec"), ns)
    except BaseException:
        pass
    return ns


def synthesize_proposals(
    source_with_runner: str,
    survivors: List[Mutant],
    user_fns: set,
    *,
    trials: int = 200,
    seed: int = 42,
) -> List[ProposedLaw]:
    """For each surviving mutant, search for a *witness input* — a call
    argument tuple on which the original function and the mutated function
    return different values — and emit a ready-to-paste `@law` asserting the
    original's behaviour at that witness. Adding that law would then catch
    the mutant."""
    try:
        from lateralus_lang.law_discovery import _get_param_types, _sample
    except Exception:
        return []
    import random

    ns_orig = _exec_capturing(source_with_runner, "original")
    rng = random.Random(seed)
    proposals: List[ProposedLaw] = []
    seen_keys: set = set()

    for mut in survivors:
        fn_name = mut.containing_fn
        if not fn_name:
            continue
        orig_fn = ns_orig.get(fn_name)
        if not callable(orig_fn):
            continue

        mutated_src = apply_mutant(source_with_runner, mut, user_fns=user_fns)
        if mutated_src == source_with_runner:
            continue
        ns_mut = _exec_capturing(mutated_src, "mutant")
        mut_fn = ns_mut.get(fn_name)
        if not callable(mut_fn):
            continue

        # Resolve parameter types. Fall back to ints if annotations missing.
        try:
            param_types = _get_param_types(orig_fn)
        except Exception:
            param_types = None
        if not param_types:
            try:
                arity = orig_fn.__code__.co_argcount
            except Exception:
                arity = 1
            param_types = [int] * max(arity, 1)

        witness = None
        expected = None
        mutant_yields = None
        for _ in range(trials):
            try:
                args = tuple(_sample(t, rng) for t in param_types)
            except Exception:
                break
            try:
                o = orig_fn(*args)
            except BaseException:
                continue
            try:
                m = mut_fn(*args)
            except BaseException:
                # Mutant crashes where original didn't → that's already a
                # discriminator. Any input the original handles will kill it.
                witness, expected, mutant_yields = args, o, "<crash>"
                break
            if o != m:
                witness, expected, mutant_yields = args, o, m
                break

        if witness is None:
            continue
        key = (fn_name, witness)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        args_lit = ", ".join(_py_to_ltl_literal(a) for a in witness)
        expected_lit = _py_to_ltl_literal(expected)
        tag = abs(hash(key)) % 100000
        ltl_src = (
            f"@law\n"
            f"fn {fn_name}_witness_{tag:05d}() -> bool {{\n"
            f"    return {fn_name}({args_lit}) == {expected_lit}\n"
            f"}}"
        )
        proposals.append(ProposedLaw(
            fn_name=fn_name,
            witness_args=witness,
            expected=expected,
            mutant_yields=mutant_yields,
            ltl_source=ltl_src,
        ))
    return proposals


# ─── In-place source patching ─────────────────────────────────────────────

_APPLY_BANNER_START = "// ─── BEGIN auto-generated witness laws ───"
_APPLY_BANNER_END   = "// ─── END auto-generated witness laws ───"


def apply_proposals_to_source(
    ltl_file: Path,
    proposals: List[ProposedLaw],
) -> Tuple[int, int]:
    """Append each proposal's `@law` snippet to the .ltl source file under
    a marker banner. Idempotent: snippets already inside the banner block
    are not duplicated.

    Returns (newly_added, already_present).
    """
    if not proposals:
        return 0, 0
    ltl_file = Path(ltl_file)
    text = ltl_file.read_text()

    # Extract what's already in the banner block (if any)
    existing_block = ""
    if _APPLY_BANNER_START in text and _APPLY_BANNER_END in text:
        s = text.index(_APPLY_BANNER_START)
        e = text.index(_APPLY_BANNER_END) + len(_APPLY_BANNER_END)
        existing_block = text[s:e]
        text = text[:s].rstrip() + text[e:]

    # De-duplicate by fn-name witness signature (fn(args) == expected)
    sig_re = re.compile(r"return\s+([a-zA-Z_][a-zA-Z_0-9]*\([^\)]*\)\s*==\s*[^\n]+)")
    # Split existing banner into individual `@law ... }` blocks (drop preamble comments)
    existing_snippets: List[str] = []
    if existing_block:
        inner = existing_block[len(_APPLY_BANNER_START):-len(_APPLY_BANNER_END)]
        # Find every @law block (greedy until matching `}`)
        existing_snippets = re.findall(
            r"@law\s*\n\s*(?:pub\s+)?fn\s+[a-zA-Z_][a-zA-Z_0-9]*\s*\([^)]*\)\s*->\s*bool\s*\{[^}]*\}",
            inner,
        )
    seen = set()
    for snip in existing_snippets:
        for sig in sig_re.findall(snip):
            seen.add(sig)

    new_snippets: List[str] = []
    for p in proposals:
        sigs = sig_re.findall(p.ltl_source)
        sig = sigs[0] if sigs else p.ltl_source
        if sig in seen:
            continue
        seen.add(sig)
        new_snippets.append(p.ltl_source)

    already = len(proposals) - len(new_snippets)

    # Re-assemble: prior @law snippets + new ones, all under a fresh banner.
    all_bodies = existing_snippets + new_snippets

    banner = (
        f"\n\n{_APPLY_BANNER_START}\n"
        f"// Inserted by `lateralus verify --mutate --propose --apply`.\n"
        f"// Edit or reorganize freely — regeneration is idempotent.\n\n"
        + "\n\n".join(all_bodies)
        + f"\n{_APPLY_BANNER_END}\n"
    )

    ltl_file.write_text(text.rstrip() + banner)
    return len(new_snippets), already


def run_mutation_campaign(
    source_with_runner: str,
    mutants: List[Mutant],
    *,
    user_fns: Optional[set] = None,
    progress: Optional[Callable[[int, int, Mutant, bool], None]] = None,
    timeout: float = 10.0,
    propose: bool = False,
    propose_trials: int = 200,
    propose_seed: int = 42,
) -> MutationReport:
    """Run every mutant through the full law suite. A mutant is `caught`
    iff the mutated program exits non-zero (at least one law failed)."""
    report = MutationReport(total=len(mutants))

    base_code, _ = _run_python(source_with_runner, timeout=timeout)
    if base_code != 0:
        raise RuntimeError(
            "baseline law run failed — fix existing laws before mutating"
        )

    for i, mut in enumerate(mutants, 1):
        mutated_src = apply_mutant(source_with_runner, mut, user_fns=user_fns)
        if mutated_src == source_with_runner:
            report.equivalents.append(mut)
            if progress: progress(i, len(mutants), mut, True)
            continue
        code, _out = _run_python(mutated_src, timeout=timeout)
        caught = code != 0
        if caught:
            report.caught += 1
        else:
            report.survivors.append(mut)
        if progress:
            progress(i, len(mutants), mut, caught)

    if propose and report.survivors:
        report.proposals = synthesize_proposals(
            source_with_runner,
            report.survivors,
            user_fns or set(),
            trials=propose_trials,
            seed=propose_seed,
        )
    return report


# ─── Entry-point used by `lateralus verify --mutate` ───────────────────────

_LTL_FN_RE = re.compile(r"^\s*(?:pub\s+)?fn\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(", re.MULTILINE)
_LTL_LAW_RE = re.compile(
    r"^\s*@law\b[^\n]*\n\s*(?:pub\s+)?fn\s+([a-zA-Z_][a-zA-Z_0-9]*)",
    re.MULTILINE,
)


def _extract_user_fns(ltl_source: str) -> set:
    """Return names of user-defined `fn` declarations, minus those that are
    `@law`-decorated. Comments (`//`) are stripped first to avoid false hits."""
    stripped = re.sub(r"//[^\n]*", "", ltl_source)
    all_fns = set(_LTL_FN_RE.findall(stripped))
    law_fns = set(_LTL_LAW_RE.findall(stripped))
    return all_fns - law_fns


def mutation_test_file(
    file: str | Path,
    *,
    trials: int = 50,
    seed: Optional[int] = 42,
    timeout: float = 10.0,
    max_mutants: Optional[int] = None,
    verbose: bool = True,
    propose: bool = False,
    propose_output: Optional[Path] = None,
    apply: bool = False,
) -> int:
    """Compile `file`, attach the law runner, produce mutants, execute.

    Returns 0 iff mutation score == 1.0 (every mutant caught). Otherwise
    returns 1 and prints surviving-mutant details so the user knows which
    invariants are under-specified.
    """
    from lateralus_lang.compiler import Compiler, Target
    from lateralus_lang.law_runner import emit_runner_tail

    path = Path(file)
    src = path.read_text()
    result = Compiler().compile_source(src, target=Target.PYTHON, filename=path.name)
    if not result.ok:
        for e in result.errors:
            print(f"  error: {getattr(e, 'message', str(e))}", file=sys.stderr)
        return 1
    user_fns = _extract_user_fns(src)
    py_src = (result.python_src or "") + "\n" + emit_runner_tail(
        trials=trials, seed=seed
    )

    mutants = generate_mutants(py_src, user_fns=user_fns)
    if max_mutants is not None:
        mutants = mutants[:max_mutants]

    if verbose:
        print(f"\n  Mutation-testing laws in {path.name}")
        print(f"  {'─' * 60}")
        print(f"  User functions:  {len(user_fns)}  {sorted(user_fns)[:6]}{'…' if len(user_fns) > 6 else ''}")
        print(f"  Candidate mutants: {len(mutants)}")
        print(f"  Baseline: {trials} trials per law, seed={seed}")
        print()

    if not mutants:
        print("  (no mutants generated — no user functions found, or all protected)")
        return 0

    def _progress(i: int, total: int, mut: Mutant, caught_or_equiv: bool):
        if verbose:
            dot = "." if caught_or_equiv else "✗"
            end = "\n" if i % 50 == 0 or i == total else ""
            print(dot, end=end, flush=True)

    report = run_mutation_campaign(
        py_src, mutants, user_fns=user_fns, progress=_progress, timeout=timeout,
        propose=propose, propose_seed=seed or 42,
    )

    print("\n")
    testable = report.total - len(report.equivalents)
    score = report.score * 100.0
    status = "strong" if score >= 90 else ("adequate" if score >= 70 else "weak")
    bar_filled = int(score / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    print(f"  Mutation score: {score:5.1f}%  [{bar}]  ({status})")
    print(f"  Caught:         {report.caught} / {testable}")
    if report.equivalents:
        print(f"  Equivalent:     {len(report.equivalents)}  (no-op mutations)")
    if report.survivors:
        print(f"  Survivors:      {len(report.survivors)}  (undetected mutations)")
        print()
        print("  ─── Survivors (laws missing coverage for these) ───")
        for mut in report.survivors[:15]:
            print(f"    • line {mut.line_no:4d}  {mut.rule_name:16s}  → {mut.line_snippet}")
        if len(report.survivors) > 15:
            print(f"    … and {len(report.survivors) - 15} more")

    if propose and report.proposals:
        print()
        print(f"  ─── Proposed laws ({len(report.proposals)}) ───")
        print("  Paste any of these into your source to kill the matching survivor:")
        print()
        for prop in report.proposals[:10]:
            got_repr = prop.mutant_yields if prop.mutant_yields == "<crash>" else repr(prop.mutant_yields)
            print(f"    // kills mutant in `{prop.fn_name}`: "
                  f"original→{prop.expected!r}, mutant→{got_repr}")
            for line in prop.ltl_source.splitlines():
                print(f"    {line}")
            print()
        if len(report.proposals) > 10:
            print(f"    … and {len(report.proposals) - 10} more")
        if propose_output is not None:
            propose_output = Path(propose_output)
            header = (
                "// Auto-generated witness laws (lateralus verify --mutate --propose)\n"
                f"// Source file: {path.name}\n"
                f"// Proposals: {len(report.proposals)}\n\n"
            )
            body = "\n\n".join(p.ltl_source for p in report.proposals)
            propose_output.write_text(header + body + "\n")
            print(f"  → wrote {len(report.proposals)} proposals to {propose_output}")
        if apply:
            added, already = apply_proposals_to_source(path, report.proposals)
            print(f"  → inserted {added} new witness law(s) into {path.name}"
                  + (f" ({already} already present)" if already else ""))
        if len(report.proposals) < len(report.survivors):
            gap = len(report.survivors) - len(report.proposals)
            print()
            print(f"  ({gap} survivor(s) without witnesses — likely equivalent mutations,")
            print("   or involve inputs this synthesizer can't sample yet)")
    elif propose and not report.proposals and report.survivors:
        print()
        print("  (no witnesses found — survivors may be equivalent mutations,")
        print("   or involve non-numeric inputs or side effects)")

    return 0 if not report.survivors else 1


# ─── Self-hardening: iterate --mutate --propose --apply to fixpoint ──────

def harden_file(
    file: str | Path,
    *,
    trials: int = 50,
    seed: Optional[int] = 42,
    timeout: float = 10.0,
    max_iter: int = 5,
    target_score: float = 1.0,
    verbose: bool = True,
) -> int:
    """Iteratively mutation-test → propose → apply until mutation score
    reaches `target_score` (default 100%), no new proposals are generated
    (fixpoint), or `max_iter` iterations elapse.

    Returns 0 iff target score was reached, else 1.
    """
    from lateralus_lang.compiler import Compiler, Target
    from lateralus_lang.law_runner import emit_runner_tail

    path = Path(file)
    last_score = 0.0
    reached = False

    print(f"\n  Hardening {path.name}")
    print(f"  {'─' * 60}")
    print(f"  Target score: {target_score*100:.0f}%,  max iterations: {max_iter}")
    print()

    for it in range(1, max_iter + 1):
        src = path.read_text()
        result = Compiler().compile_source(
            src, target=Target.PYTHON, filename=path.name
        )
        if not result.ok:
            for e in result.errors:
                print(f"  error: {getattr(e, 'message', str(e))}", file=sys.stderr)
            return 1
        user_fns = _extract_user_fns(src)
        py_src = (result.python_src or "") + "\n" + emit_runner_tail(
            trials=trials, seed=seed
        )
        mutants = generate_mutants(py_src, user_fns=user_fns)

        report = run_mutation_campaign(
            py_src, mutants, user_fns=user_fns, progress=None, timeout=timeout,
            propose=True, propose_seed=(seed or 42) + it,
        )
        testable = report.total - len(report.equivalents)
        score = report.score
        last_score = score

        print(f"  iter {it}: score {score*100:5.1f}%  "
              f"({report.caught}/{testable} caught, "
              f"{len(report.survivors)} survivors, "
              f"{len(report.proposals)} proposals)")

        if score >= target_score:
            reached = True
            print(f"  ✓ reached target score at iteration {it}")
            break
        if not report.proposals:
            print("  ⟂ fixpoint: no new witnesses — remaining survivors likely equivalent")
            break

        added, already = apply_proposals_to_source(path, report.proposals)
        if added == 0:
            print(f"  ⟂ fixpoint: all {already} proposals already present")
            break
        print(f"         → applied {added} new witness law(s)")

    print()
    print(f"  Final score: {last_score*100:.1f}%"
          + ("  ✓" if reached else "  (did not reach target)"))
    return 0 if reached else 1
