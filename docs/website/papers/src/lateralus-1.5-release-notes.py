#!/usr/bin/env python3
"""Render 'Lateralus 1.5 Release Notes' to PDF."""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-1.5-release-notes.pdf"

TITLE = "Lateralus 1.5 Release Notes"
SUBTITLE = "Gradual typing, pipelines, and the first self-consistent toolchain"
META = "bad-antics &middot; April 2026 &middot; Lateralus Language Release"
ABSTRACT = (
    "Lateralus 1.5 is the first release in which every user-facing tool &mdash; compiler, "
    "interpreter, formatter, linter, LSP, DAP, and C backend &mdash; operates over a single "
    "canonical AST and a single canonical inference pass. This document records the user-visible "
    "changes, the bug fixes, the breaking changes (one, documented below), and the upgrade path "
    "from 1.4. It is intended to be readable front-to-back by library authors considering the "
    "version bump and as a reference for downstream editor-plugin authors."
)

SECTIONS = [
    ("1. New Language Features", [
        ("h3", "1.1 Gradual type inference on by default"),
        "<code>let</code> bindings no longer require type annotations in the common case; the 1.5 inference pass (Hindley-Milner with bidirectional refinements) handles lists, maps, records, pipelines, and generic functions without intervention. See the companion paper <i>Type Inference in Lateralus 1.5</i> for the algorithmic details.",
        ("h3", "1.2 Pipeline-assign operator"),
        "<code>x |&gt;= f</code> is shorthand for <code>x = x |&gt; f</code>. Especially useful for sequential ETL patterns:",
        ("code",
         "let mut data = load_csv(path)\n"
         "data |&gt;= drop_nulls\n"
         "data |&gt;= normalize_columns\n"
         "data |&gt;= sort_by(\"timestamp\")"),
        ("h3", "1.3 Where clauses"),
        "Return expressions can carry a <code>where</code> block of helper bindings:",
        ("code",
         "fn distance(p, q) -&gt; float:\n"
         "    return sqrt(dx*dx + dy*dy) where:\n"
         "        let dx = p.x - q.x\n"
         "        let dy = p.y - q.y"),
        "Semantically identical to a <code>let</code> chain above the return; aesthetically closer to maths and to SQL.",
        ("h3", "1.4 Measure and probe blocks"),
        "<code>measure \"label\" { ... }</code> times the enclosed block and emits the result to the profiler; <code>probe \"label\" { ... }</code> emits the final expression value to the trace stream. Both compile away under <code>--release</code>.",
        ("h3", "1.5 List comprehensions"),
        "<code>[x * x for x in xs if x &gt; 0]</code> desugars to an iterator pipeline. The compiler optimizes simple cases (single source, no nested generators) to a direct loop.",
        ("h3", "1.6 Spread syntax"),
        "<code>[...a, ...b]</code> flattens lists at construction; <code>{...r, x: 1}</code> extends records, with later keys winning.",
    ]),
    ("2. Standard Library", [
        ("list", [
            "<code>stdlib/strings</code>: added <code>split_n</code>, <code>rsplit</code>, <code>strip_prefix</code>, <code>strip_suffix</code>, <code>replace_all</code>.",
            "<code>stdlib/math</code>: added <code>clamp</code>, <code>lerp</code>, <code>round_to</code> (n-decimal round).",
            "<code>stdlib/io</code>: new module; <code>io.println</code>, <code>io.read_line</code>, <code>io.open</code>, <code>io.walk</code>.",
            "<code>stdlib/time</code>: <code>time.now_ms</code>, <code>time.sleep_ms</code>, <code>time.format</code>.",
            "<code>stdlib/json</code>: <code>json.parse</code>, <code>json.stringify</code> with pretty-print option.",
            "<code>stdlib/testing</code>: a pytest-style harness; the compiler discovers <code>test_*</code> functions and runs them under <code>lateralus test</code>.",
        ]),
    ]),
    ("3. Toolchain", [
        ("h3", "3.1 Unified AST"),
        "Every tool now consumes the same AST that the compiler produces; no more divergence between the linter's parser and the compiler's parser. One practical consequence: a syntax error reported by the linter has the same position and message as the one reported by <code>lateralus build</code>.",
        ("h3", "3.2 Language Server Protocol"),
        "<code>lateralus lsp</code> now supports: hover (types), go-to-definition, find-references, rename-symbol, document-symbols, code-lens, and diagnostics on save. The VS Code extension is updated in the marketplace to match.",
        ("h3", "3.3 Debug Adapter Protocol"),
        "<code>lateralus dap</code> speaks DAP over stdio; breakpoints, stepping, stack traces, and local-variable inspection all work against the VM target. Native-code targets (C backend, bytecode) are not yet debugger-integrated.",
        ("h3", "3.4 C backend"),
        "<code>lateralus c source.ltl -o source.c</code> emits freestanding C99 suitable for embedding in existing projects. <code>--freestanding</code> targets kernel/OS use with no libc dependency. See the companion paper <i>C Backend Transpiler Design</i>.",
        ("h3", "3.5 Formatter"),
        "<code>lateralus fmt</code> is deterministic and idempotent; the file on disk round-trips through parse-format-parse bit-for-bit identical.",
        ("h3", "3.6 Linter"),
        "40 lints shipped in 1.5, covering dead code, shadowing, unused parameters, magic numbers, pipeline anti-patterns, and concurrency hazards. <code>lateralus lint --fix</code> applies the safe ones automatically.",
    ]),
    ("4. Bug Fixes", [
        ("list", [
            "Parser: fix off-by-one column reporting on multi-line string literals (#412).",
            "Inference: the occurs check now fires at bind time rather than at apply time; eliminates a class of pathological slowdowns (#437).",
            "Codegen: pipeline-heavy expressions no longer allocate per-stage closures when the stage is a named function; 2-4x speedup on map/filter pipelines (#451).",
            "VM: integer-literal boxing eliminated on arithmetic paths; measurable on numeric benchmarks (#462).",
            "LSP: hover no longer returns stale types after edit-undo sequences (#478).",
            "Formatter: trailing-comma handling in match arms fixed (#491).",
        ]),
    ]),
    ("5. Breaking Changes", [
        "Exactly one:",
        ("h3", "5.1 let without annotation is no longer an error"),
        "In 1.4, <code>let x = expr</code> without a type annotation was rejected under <code>--strict</code> mode. In 1.5, <code>--strict</code> no longer implies mandatory annotation; inference supplies types silently. Code that relied on the error (for example, CI pipelines that grep for it) should switch to <code>lateralus lint --rule require-annotations</code> which still flags untyped <code>let</code>s under the explicit opt-in.",
        "No other source-level breakage. Binary formats (bytecode, cached ASTs) are version-gated and automatically regenerated on the first run against 1.5.",
    ]),
    ("6. Upgrade Path", [
        ("list", [
            "<b>Python package</b>: <code>pip install --upgrade lateralus-lang</code>.",
            "<b>From source</b>: <code>git pull && make install</code>.",
            "<b>VS Code extension</b>: Marketplace auto-update, or reinstall from <code>.vsix</code> in <code>vscode-lateralus/</code>.",
            "<b>Existing projects</b>: no code changes required for 1.4-compatible code. Run <code>lateralus fmt</code> after upgrade to pick up any minor style adjustments.",
            "<b>Bytecode caches</b>: will be regenerated automatically on first build.",
        ]),
    ]),
    ("7. Benchmarks", [
        "Measured on an M1 MacBook Pro, Python 3.11, best-of-5:",
        ("list", [
            "<code>examples/fibonacci.ltl</code> (VM): 68 ms in 1.4, 52 ms in 1.5 (24% faster).",
            "<code>examples/data_pipeline.ltl</code> (VM): 210 ms in 1.4, 160 ms in 1.5.",
            "<code>examples/crypto_challenges.ltl</code> (VM): 1.1 s in 1.4, 0.85 s in 1.5.",
            "Full test suite (<code>pytest tests/</code>): 12.4 s in 1.4, 11.9 s in 1.5.",
        ]),
        "Most of the gain comes from the closure-elimination fix (#451) and the inference-occurs-check fix (#437); the remainder is minor allocator and lookup-path improvements.",
    ]),
    ("8. What's Not in 1.5", [
        ("list", [
            "<b>Higher-rank types</b>: postponed to 1.6.",
            "<b>Effect system</b>: design in progress, target 1.7.",
            "<b>GADTs</b>: target 1.7.",
            "<b>Native AOT compiler</b>: the C backend covers the near-term need; a dedicated LLVM backend is on the long-range roadmap but not scheduled.",
        ]),
    ]),
    ("9. Acknowledgements", [
        "Thanks to the 22 contributors who filed issues or submitted patches against the 1.4 series. Particular thanks to early adopters who tested the gradual-inference branch for eight weeks before merge and identified three correctness bugs in the row-polymorphism code path. The release would not be shippable without their patience.",
    ]),
    ("10. Next Release", [
        "Lateralus 1.6 is targeted for Q3 2026. Primary themes: higher-rank types, first-class modules, and a stable bytecode format suitable for distribution. Follow <code>CHANGELOG.md</code> on the main repo for in-progress notes.",
    ]),
]

if __name__ == "__main__":
    render_paper(OUT, title=TITLE, subtitle=SUBTITLE, meta=META,
                 abstract=ABSTRACT, sections=SECTIONS)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
