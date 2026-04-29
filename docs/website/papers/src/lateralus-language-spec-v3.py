#!/usr/bin/env python3
"""Render 'Lateralus Language Specification v3' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-language-spec-v3.pdf"

render_paper(
    out_path=str(OUT),
    title="Lateralus Language Specification v3",
    subtitle="Complete grammar, type system, pipeline semantics, and standard library surface",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "This document is the normative specification for Lateralus version 3. "
        "It supersedes the v1 and v2 specifications. Version 3 adds: the effect "
        "type system (§4), async pipelines with structured concurrency (§5), "
        "the formal module system (§8), and the polyglot bridge interface (§9). "
        "The grammar in §2 and the core type system in §3 are unchanged from v2 "
        "except for additions required by the new features. Implementations must "
        "conform to all normative sections; informative sections are labeled [INF]."
    ),
    sections=[
        ("1. Lexical Structure", [
            "Lateralus source files are UTF-8 encoded. The lexical grammar defines "
            "tokens in terms of Unicode categories.",
            ("code",
             "-- Pipeline operators (longest-match rule)\n"
             "PIPE_TOTAL   ::= '|>'\n"
             "PIPE_FALLIBLE ::= '|?>'\n"
             "PIPE_ASYNC   ::= '|>>'\n"
             "PIPE_COLLECT ::= '|>|'\n\n"
             "-- Identifiers\n"
             "IDENT ::= (XID_Start | '_') XID_Continue*\n\n"
             "-- Numeric literals\n"
             "INT   ::= [0-9]+ | '0x' [0-9A-Fa-f]+ | '0b' [01]+\n"
             "FLOAT ::= [0-9]+ '.' [0-9]+ ([eE] [+-]? [0-9]+)?"),
            "Comments: <code>--</code> to end of line (single-line); "
            "<code>---</code> lines are documentation comments attached to the "
            "following declaration. Block comments are not part of the grammar; "
            "multi-line comments must use repeated <code>--</code> lines.",
        ]),
        ("2. Grammar", [
            "Top-level productions:",
            ("code",
             "program     ::= item*\n"
             "item        ::= fn_def | record_def | enum_def | module_def\n"
             "              | use_decl | impl_def | trait_def\n\n"
             "fn_def      ::= doc_comment? 'fn' IDENT generics? params return_type? body\n"
             "pipeline    ::= expr (pipe_op expr)*\n"
             "pipe_op     ::= PIPE_TOTAL | PIPE_FALLIBLE | PIPE_ASYNC | PIPE_COLLECT\n\n"
             "expr        ::= pipeline | match_expr | block | literal | IDENT\n"
             "              | fn_call | field_access | lambda | if_expr"),
            "The pipeline production is left-associative. Operator precedence: "
            "pipeline operators bind more loosely than function application but "
            "more tightly than <code>let</code> and <code>if</code> expressions.",
        ]),
        ("3. Core Type System", [
            "Lateralus uses a Hindley-Milner type system extended with row "
            "polymorphism for records and effect typing (§4). Type inference "
            "is complete for the HM fragment; effect annotations may be required "
            "at function boundaries.",
            ("code",
             "Type τ ::= Int | Float | Bool | Str | Unit\n"
             "         | τ -> τ                    -- function\n"
             "         | Result<τ, τ>              -- fallible\n"
             "         | Async<τ>                  -- async value\n"
             "         | Vec<τ> | Option<τ>        -- containers\n"
             "         | {l: τ, ...| ρ}            -- open record\n"
             "         | α                         -- type variable\n"
             "         | ∀α. τ                     -- polymorphic"),
            "Pipeline operator typing rules (normative):",
            ("code",
             "Γ ⊢ e : A    Γ ⊢ f : A → B\n"
             "─────────────────────────────  [PIPE-TOTAL]\n"
             "Γ ⊢ e |> f : B\n\n"
             "Γ ⊢ e : Result<A,E>    Γ ⊢ f : A → Result<B,E>\n"
             "──────────────────────────────────────────────────  [PIPE-FALLIBLE]\n"
             "Γ ⊢ e |?> f : Result<B,E>"),
        ]),
        ("4. Effect Type System", [
            "Version 3 adds a row-polymorphic effect type system. Effects are "
            "tracked in the return type of functions:",
            ("code",
             "-- Effect rows\n"
             "Effect ε ::= {}          -- pure\n"
             "           | {IO | ε}   -- I/O\n"
             "           | {Exc E | ε} -- exception of type E\n"
             "           | {State S | ε} -- mutable state of type S\n"
             "           | ε          -- row variable\n\n"
             "-- Functions are typed with their effect row\n"
             "fn read_file(path: Str) -> Str ! {IO}\n"
             "fn pure_map<A,B>(f: A->B, xs: Vec<A>) -> Vec<B> ! {}"),
            "Effect polymorphism allows higher-order functions to propagate "
            "effects from their arguments without annotation:",
            ("code",
             "fn map<A,B,ε>(f: A -> B ! ε, xs: Vec<A>) -> Vec<B> ! ε\n"
             "-- ε is inferred from the argument f at call sites"),
        ]),
        ("5. Async Pipelines and Structured Concurrency", [
            "The <code>|>></code> operator applies a function to each element "
            "of a stream concurrently. Structured concurrency guarantees that "
            "all concurrent tasks are joined before the pipeline stage completes:",
            ("code",
             "-- Async pipeline semantics\n"
             "Γ ⊢ e : Stream<A>    Γ ⊢ f : A → Async<B>\n"
             "────────────────────────────────────────────  [PIPE-ASYNC]\n"
             "Γ ⊢ e |>> f : Stream<B>\n\n"
             "-- Collect terminates a stream into a Vec\n"
             "Γ ⊢ e : Stream<A>\n"
             "──────────────────  [PIPE-COLLECT]\n"
             "Γ ⊢ e |>| : Vec<A>"),
            "All tasks spawned by <code>|>></code> are owned by the pipeline "
            "stage's nursery. If any task fails, the nursery cancels all sibling "
            "tasks and propagates the failure. Dangling tasks are impossible.",
        ]),
        ("6. Pattern Matching", [
            "Pattern matching is exhaustive: the compiler rejects a match "
            "expression that does not cover all constructors of the matched type. "
            "Guards are permitted but do not contribute to exhaustiveness:",
            ("code",
             "match value {\n"
             "    Ok(x) if x > 0  => positive(x),\n"
             "    Ok(x)           => non_positive(x),\n"
             "    Err(e)          => handle_error(e),\n"
             "    -- No wildcard needed: Ok and Err exhaust Result<A,E>\n"
             "}"),
            "Structural patterns, tuple patterns, range patterns (<code>1..=10</code>), "
            "and or-patterns (<code>A | B</code>) are all supported. Binding "
            "patterns (<code>x @ pattern</code>) bind the matched value while "
            "also matching its structure.",
        ]),
        ("7. Ownership and Lifetimes", [
            "Lateralus uses a single-owner memory model. Every value has exactly "
            "one owner; ownership is transferred (moved) on assignment and "
            "function call. Borrows are immutable (<code>&T</code>) or mutable "
            "(<code>&mut T</code>); at most one mutable borrow may exist at a time:",
            ("code",
             "fn process(data: Vec<u8>) -> usize {    -- data is moved in\n"
             "    let len = data.len();               -- immutable borrow\n"
             "    transform(&mut data);               -- mutable borrow\n"
             "    len                                 -- data freed here\n"
             "}\n\n"
             "-- Lifetime annotations for struct fields containing borrows\n"
             "record View<'a> { data: &'a [u8] }"),
            "The borrow checker runs after type inference and before code generation. "
            "Its output is a set of lifetime constraints; violations are reported "
            "as errors with suggested fixes.",
        ]),
        ("8. Module System and Packages", [
            "Lateralus has a two-level namespace: modules (within a package) "
            "and packages (in the registry). The module path syntax is "
            "<code>package::module::item</code>:",
            ("code",
             "-- Declare a module\n"
             "module crypto {\n"
             "    pub fn sha256(data: &[u8]) -> [u8; 32] { ... }\n"
             "    -- private by default\n"
             "    fn compress(state: &mut State, block: &[u8]) { ... }\n"
             "}\n\n"
             "-- Use from another module\n"
             "use crypto::sha256;\n"
             "use crypto::{sha256, hmac_sha256};"),
            "Visibility modifiers: <code>pub</code> (public), <code>pub(package)</code> "
            "(visible within the package), and private (default). There is no "
            "<code>pub(super)</code>; packages are the visibility boundary.",
        ]),
        ("9. Polyglot Bridge", [
            "The polyglot bridge allows Lateralus code to call C, Rust, and "
            "Python functions and vice versa. Bindings are declared with "
            "<code>extern</code> blocks:",
            ("code",
             "-- Call a C function\n"
             "extern \"C\" {\n"
             "    fn strlen(s: *const u8) -> usize;\n"
             "    fn malloc(size: usize) -> *mut u8;\n"
             "}\n\n"
             "-- Export a Lateralus function to C\n"
             "#[export_c]\n"
             "pub fn add(a: i32, b: i32) -> i32 { a + b }"),
            "All calls across the bridge are <code>unsafe</code>: the Lateralus "
            "type system cannot verify the safety of foreign code. The bridge "
            "provides automatic type marshalling for primitive types; complex "
            "types require explicit marshalling code.",
        ]),
    ],
)

print(f"wrote {OUT}")
