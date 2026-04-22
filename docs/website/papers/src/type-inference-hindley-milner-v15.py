#!/usr/bin/env python3
"""Render 'Type Inference in Lateralus 1.5' to PDF."""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "type-inference-hindley-milner-v15.pdf"

TITLE = "Type Inference in Lateralus 1.5"
SUBTITLE = "Algorithm W with bidirectional refinements and pipeline-aware unification"
META = "bad-antics &middot; April 2026 &middot; Lateralus Compiler Internals"
ABSTRACT = (
    "Lateralus 1.5 ships a gradual type system built on a variant of Algorithm W with "
    "bidirectional refinements, first-class pipeline types, and principal inference for "
    "generic functions. This paper walks through the implementation as it sits in "
    "<code>lateralus_lang/type_inference.py</code>, covering the core unifier, "
    "let-generalization, the occurs check, the row-polymorphic treatment of records, and "
    "the additions that make pipeline expressions composeable without explicit annotations. "
    "We close with the test strategy that gave us confidence to ship inference on by default "
    "and with the escape hatches we kept for programs that fall outside the inferable fragment."
)

SECTIONS = [
    ("1. Design Goals", [
        "Lateralus positions itself as a gradual language: fully-typed code should feel as precise as ML, while lightly-typed pipelines should require nothing beyond what the programmer would naturally write. The design goals for the 1.5 inference pass were:",
        ("list", [
            "<b>No annotations on local bindings.</b> <code>let x = expr</code> should always infer.",
            "<b>Let-generalization.</b> <code>let id = fn(x) { x }</code> should be usable at multiple types in the same scope.",
            "<b>Principal types.</b> Every inferable program must have a unique most-general type; implementation must return it.",
            "<b>Pipeline composition.</b> <code>xs |&gt; map(f) |&gt; filter(p)</code> must flow types through <code>|&gt;</code> without manual help.",
            "<b>Graceful fallback.</b> When inference reaches the edge of the decidable fragment (recursive records, higher-rank types), the compiler should emit a specific diagnostic rather than a silent <code>any</code>.",
        ]),
    ]),
    ("2. Core Types", [
        "The type language is small:",
        ("code",
         "type Ty =\n"
         "    | TyVar id:int                           # unification variable\n"
         "    | TyCon name:str                         # int, str, float, bool, unit\n"
         "    | TyApp head:str args:list[Ty]           # list[int], map[str,int]\n"
         "    | TyFn params:list[Ty] ret:Ty            # (int, int) -> int\n"
         "    | TyRecord fields:map[str,Ty] row:RowVar # {x:int, y:int | r}\n"
         "    | TyForall vars:list[int] body:Ty        # only at let-binding"),
        "Unification operates on <code>TyVar</code>, <code>TyCon</code>, <code>TyApp</code>, <code>TyFn</code>, and <code>TyRecord</code>. <code>TyForall</code> appears only in type schemes stored in the environment and is instantiated on lookup.",
    ]),
    ("3. The Unifier", [
        "The unifier follows the textbook shape:",
        ("code",
         "fn unify(s: Subst, a: Ty, b: Ty) -> Subst:\n"
         "    a = apply(s, a); b = apply(s, b)\n"
         "    match (a, b):\n"
         "        TyVar(i), TyVar(j) if i == j => s\n"
         "        TyVar(i), t                  => bind(s, i, t)\n"
         "        t, TyVar(i)                  => bind(s, i, t)\n"
         "        TyCon(n), TyCon(m) if n == m => s\n"
         "        TyApp(h1, a1), TyApp(h2, a2) => unify_list(s, h1==h2, a1, a2)\n"
         "        TyFn(p1, r1), TyFn(p2, r2)   => unify_list(unify(s, r1, r2), p1, p2)\n"
         "        TyRecord(f1,r1), TyRecord(f2,r2) => unify_record(s, f1, r1, f2, r2)\n"
         "        _ => fail \"cannot unify {a} with {b}\""),
        "The <code>bind</code> helper performs the occurs check: <code>if i occurs in t: fail</code>. Without this check, self-referential constraints like <code>a ~ list[a]</code> would produce an infinite substitution. In 1.5 we moved the check into the substitution-application path; it runs at bind time rather than at every application, which cut inference time on large pipeline expressions by roughly 30%.",
    ]),
    ("4. Let-Generalization", [
        "On <code>let name = expr in body</code>, the inferred type of <code>expr</code> under substitution <code>s</code> is generalized by abstracting free variables that do not appear free in the substitution-applied environment:",
        ("code",
         "fn generalize(env: Env, s: Subst, t: Ty) -> Scheme:\n"
         "    let env_free = free_vars(apply(s, env))\n"
         "    let quantified = free_vars(apply(s, t)) - env_free\n"
         "    return TyForall(quantified, apply(s, t))"),
        "On lookup, a scheme is instantiated with fresh type variables: <code>TyForall([a, b], a -&gt; b)</code> becomes <code>c -&gt; d</code> for fresh <code>c</code>, <code>d</code>. This is what lets <code>let id = fn(x) {x}; id(1); id(\"hi\")</code> type-check without annotation.",
        "Crucially, generalization only happens at <code>let</code>. Lambda parameters are monomorphic within their body, preserving decidability.",
    ]),
    ("5. Pipeline Inference", [
        "The pipeline operator <code>|&gt;</code> is left-associative and has lower precedence than function application. Lateralus treats <code>x |&gt; f</code> as shorthand for <code>f(x)</code> when <code>f</code> is a reference, and as shorthand for <code>fn_of(f)(x)</code> when <code>f</code> is a partial application like <code>map(g)</code>. Inference must disambiguate without running the program:",
        ("code",
         "fn infer_pipe(env, lhs, rhs):\n"
         "    let t_lhs = infer(env, lhs)\n"
         "    match rhs:\n"
         "        Ident(f):\n"
         "            let t_f = instantiate(lookup(env, f))\n"
         "            let t_ret = fresh_ty()\n"
         "            unify(t_f, TyFn([t_lhs], t_ret))\n"
         "            return t_ret\n"
         "        Call(f, args):\n"
         "            # lhs flows into last argument slot\n"
         "            let t_new = TyFn(map(infer, args) ++ [t_lhs], fresh_ty())\n"
         "            unify(infer(env, f), t_new)\n"
         "            return t_new.ret"),
        "The <code>Call</code> branch is what makes <code>xs |&gt; map(f)</code> work: we treat <code>map(f)</code> as though <code>xs</code> were its final argument, and the unifier threads the element type through without intervention.",
    ]),
    ("6. Records and Row Polymorphism", [
        "Record literals carry an optional row variable: <code>{x: 1, y: 2}</code> has type <code>{x: int, y: int | r}</code> where <code>r</code> is a fresh row variable. Field projection <code>rec.x</code> unifies <code>rec</code> with <code>{x: a | r}</code> and yields <code>a</code>. This gives us duck-typed projection that still enjoys inference:",
        ("code",
         "fn distance(p) -> float:\n"
         "    # p is inferred as {x: float, y: float | r}\n"
         "    return sqrt(p.x * p.x + p.y * p.y)\n"
         "\n"
         "distance({x: 3.0, y: 4.0})               # OK\n"
         "distance({x: 3.0, y: 4.0, z: 5.0})       # also OK, r = {z: float}"),
        "Row unification is strictly more work than ML-style records, but the extra bookkeeping is contained: each <code>TyRecord</code> carries a row variable that is unified independently of its field map.",
    ]),
    ("7. Gradual Fallback", [
        "When an expression is annotated <code>any</code>, inference treats it as a universal-quantified type variable that unifies with anything and propagates as <code>any</code> through the substitution. The result is a type system that is sound on fully-annotated fragments and permissive on any-annotated fragments, with a sharp boundary between the two. Callers of an <code>any</code>-returning function must themselves annotate or accept <code>any</code>, preventing silent drift.",
    ]),
    ("8. Testing", [
        "The inference test suite in <code>tests/test_v15_features.py</code> has three tiers:",
        ("list", [
            "<b>Unit tests for the unifier</b> (~40 cases): unify TyVar with TyCon, TyFn with TyFn, occurs-check failure, row-record unification, etc.",
            "<b>End-to-end inference tests</b> (~120 cases): parse a Lateralus source fragment, run inference, compare the reported type of a named binding against a string expectation. Example: <code>assert_type(\"let x = [1,2,3]\", \"x\", \"list[int]\")</code>.",
            "<b>Diagnostic tests</b> (~25 cases): check that inference failures produce the expected error code and position, not just any failure.",
        ]),
        "The diagnostic tier is what gives us confidence that a production regression will be caught at the same time as a correctness regression. A silent fallback to <code>any</code> is a correctness bug in the tests as well as in the compiler.",
    ]),
    ("9. Future Work", [
        "Three extensions are on the roadmap:",
        ("list", [
            "<b>Higher-rank types</b> for functions that take polymorphic callbacks (<code>fn map_all(f: forall a. a -&gt; a, xs)</code>).",
            "<b>GADTs</b> for parser-combinator-style code where match arms refine type indices.",
            "<b>Effect rows</b> co-existing with the record rows, giving us <code>IO</code>/<code>async</code>/<code>throws</code> tracking at the same site as the field types.",
        ]),
        "Each of these is a principled extension; none require rewriting the core unifier. We expect them over the 1.6 and 1.7 releases respectively.",
    ]),
    ("10. Conclusion", [
        "Lateralus 1.5 delivers an Algorithm W variant tuned for pipeline-heavy code, with row-polymorphic records and a well-defined gradual escape hatch. The implementation fits in under a thousand lines of Python and passes 185 tests covering the inferable fragment, the gradual boundary, and the diagnostic layer. It is the same implementation we rely on in the editor plugins and the <code>lateralus check</code> subcommand, giving us one source of truth for what the language means.",
    ]),
]

if __name__ == "__main__":
    render_paper(OUT, title=TITLE, subtitle=SUBTITLE, meta=META,
                 abstract=ABSTRACT, sections=SECTIONS)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
