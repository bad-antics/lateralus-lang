#!/usr/bin/env python3
"""Render 'Lateralus: A Pipeline-Native Language' overview in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-pipeline-native-language.pdf"

render_paper(
    out_path=str(OUT),
    title="Lateralus: A Pipeline-Native Language",
    subtitle="Overview of a systems language built around typed data pipelines as the primary abstraction",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "Lateralus is a statically typed systems programming language that makes "
        "data pipelines a first-class language construct rather than a library "
        "abstraction. This overview introduces Lateralus to readers unfamiliar "
        "with the language: its motivation, its core constructs, its intended "
        "application domains, and how it compares to existing systems languages. "
        "No prior knowledge of Lateralus is assumed."
    ),
    sections=[
        ("1. Motivation", [
            "Most programs are fundamentally pipelines: data flows in, is "
            "transformed through a sequence of stages, and flows out. Yet most "
            "programming languages treat pipelines as a pattern to be implemented "
            "by the programmer — a chain of function calls, a sequence of "
            "method invocations, or a Bash pipe.",
            "Lateralus treats the pipeline as the primary syntactic and semantic "
            "unit. The pipeline operator <code>|></code> is not syntactic sugar "
            "for function application; it is a distinct evaluation form with its "
            "own typing rules, optimization opportunities, and tooling support. "
            "This distinction matters: a language that understands pipelines can "
            "reason about them in ways a language with method chaining cannot.",
        ]),
        ("2. Hello, Lateralus", [
            "A minimal Lateralus program that reads a file, filters its lines, "
            "and prints the matches:",
            ("code",
             "fn main() -> Result<(), IoError> {\n"
             "    std::args().skip(1).first()\n"
             "        |?> fs::read_to_string\n"
             "        |>  str::lines\n"
             "        |>  filter(|line| line.contains(\"error\"))\n"
             "        |>  iter::for_each(println)\n"
             "}"),
            "Each stage after the first receives the output of the previous stage. "
            "The <code>|?></code> operator propagates errors without explicit "
            "<code>match</code> or <code>?</code> syntax — it is the pipeline "
            "equivalent of Rust's <code>?</code> operator.",
        ]),
        ("3. The Four Pipeline Operators", [
            "Lateralus has four pipeline operators, each with distinct semantics:",
            ("code",
             "Operator  Name        Semantics\n"
             "─────────────────────────────────────────────────────\n"
             "|>        Total       Always succeeds; A → B\n"
             "|?>       Fallible    May fail; Result<A,E> → Result<B,E>\n"
             "|>>       Async       Concurrent map; Stream<A> → Stream<B>\n"
             "|>|       Collect     Terminates a stream; Stream<A> → Vec<A>"),
            "The choice of operator is explicit and meaningful: a programmer "
            "reading <code>|?></code> knows the stage may fail and the error "
            "is propagated. A programmer reading <code>|>></code> knows the "
            "operation is concurrent. The operator is documentation.",
        ]),
        ("4. Types and Inference", [
            "Lateralus uses Hindley-Milner type inference. Most programs require "
            "no type annotations; the compiler infers all types from usage. "
            "Annotations are required only at module boundaries (public functions) "
            "and when inference is ambiguous:",
            ("code",
             "-- Inferred: no annotations needed\n"
             "fn double_all(xs: Vec<i32>) -> Vec<i32> {\n"
             "    xs |> map(|x| x * 2)\n"
             "}\n\n"
             "-- Annotation required: return type is a type alias\n"
             "pub fn parse_config(s: &str) -> Result<Config, ConfigError> {\n"
             "    s |> toml::parse |?> Config::from_toml\n"
             "}"),
        ]),
        ("5. Ownership Without Pain", [
            "Lateralus uses ownership-based memory management: no garbage "
            "collector, no manual <code>free</code>. The ownership model is "
            "similar to Rust's but with several ergonomic improvements:",
            ("list", [
                "<b>Move by default in pipelines</b>: pipeline stages automatically "
                "move their input, eliminating the need for explicit <code>.clone()</code> "
                "in most cases.",
                "<b>Implicit borrows for read-only stages</b>: stages that only "
                "read their input receive an implicit immutable borrow rather "
                "than consuming the value.",
                "<b>Borrow inference</b>: the compiler infers borrow kinds in "
                "most cases, requiring explicit <code>&</code> and <code>&mut</code> "
                "only when the borrow kind is ambiguous.",
            ]),
        ]),
        ("6. Application Domains", [
            "Lateralus is designed for three primary domains:",
            ("code",
             "Domain                  Key features used\n"
             "────────────────────────────────────────────────\n"
             "Systems / OS kernel     no_std, ownership, inline asm\n"
             "Security tooling        typed schemas, scope types, pipelines\n"
             "Data processing         async pipelines, streaming, WASM target\n"
             "\nSecondary domains:\n"
             "  Network services      async, TLS, typed protocols\n"
             "  Embedded systems      no_std, RISC-V target, deterministic timing\n"
             "  Language tooling      LSP integration, playground, formatter"),
            "The language does not target mobile, GUI, or game development — "
            "these domains have existing ecosystems (Swift/Kotlin, React/Qt, Unity) "
            "that Lateralus does not aim to displace.",
        ]),
        ("7. Comparison with Similar Languages", [
            "How Lateralus relates to languages it is frequently compared to:",
            ("code",
             "Language   Comparison\n"
             "────────────────────────────────────────────────────────────\n"
             "Rust       Same memory model; Lateralus adds pipeline syntax\n"
             "           and effect types. Rust has larger ecosystem.\n"
             "Elixir     Both pipeline-oriented; Elixir is GC'd and dynamic.\n"
             "           Lateralus is systems-level and statically typed.\n"
             "Haskell    Both have strong type systems; Lateralus is eagerly\n"
             "           evaluated, imperative-first, and explicitly effectful.\n"
             "C          C has no safety or pipelines. Lateralus is C's successor\n"
             "           for applications that need both safety and performance."),
        ]),
        ("8. Current Status and Roadmap", [
            "Lateralus is at version 1.4 (stable). The current status:",
            ("code",
             "v1.4 (current, stable):\n"
             "  ✓ RISC-V and x86-64 backends\n"
             "  ✓ Core type system and inference\n"
             "  ✓ Pipeline operators (|>, |?>, |>>, |>|)\n"
             "  ✓ Ownership and borrows\n"
             "  ✓ Package registry and ltlup toolchain manager\n"
             "  ✓ LSP (ltl-lsp) with pipeline inlay hints\n\n"
             "v2.0 (planned, 2027):\n"
             "  → AArch64 backend\n"
             "  → Effect type system (stable)\n"
             "  → Formal verification framework\n"
             "  → WebAssembly component model support"),
        ]),
    ],
)

print(f"wrote {OUT}")
