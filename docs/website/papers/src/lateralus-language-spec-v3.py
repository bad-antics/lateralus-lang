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
            "more tightly than <code>let</code> and assignment expressions.",
        ]),
    ],
)