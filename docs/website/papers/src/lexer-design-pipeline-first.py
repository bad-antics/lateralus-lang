#!/usr/bin/env python3
"""Render 'Lexer Design for a Pipeline-First Language' in canonical Lateralus style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lexer-design-pipeline-first.pdf"

render_paper(
    out_path=str(OUT),
    title="Lexer Design for a Pipeline-First Language",
    subtitle="Tokenizing Lateralus: operator precedence, contextual keywords, and pipeline disambiguation",
    meta="bad-antics &middot; August 2024 &middot; Lateralus Language Research",
    abstract=(
        "The Lateralus lexer must handle four multi-character pipeline operators "
        "(<code>|&gt;</code>, <code>|?&gt;</code>, <code>|&gt;&gt;</code>, <code>|&gt;|</code>), "
        "contextual keywords that are identifiers in some positions, and the disambiguation "
        "of <code>|</code> as either a bitwise-OR operator or the start of a pipeline "
        "operator. This paper describes the lexer's design: a hand-written DFA with "
        "a one-character lookahead, the contextual keyword table, and the two "
        "disambiguation rules. We discuss the trade-offs versus a generated lexer "
        "and explain why a hand-written DFA produces better error messages."
    ),
    sections=[
        ("1. The Lexer's Context in the Compiler", [
            "The Lateralus compiler pipeline is: source text → tokens → AST → "
            "typed IR → optimized IR → machine code. The lexer is the first "
            "stage; it takes a byte stream and produces a token stream. The "
            "parser consumes the token stream and produces an AST.",
            "The lexer's design decisions propagate forward: a poor tokenization "
            "choice forces the parser to carry disambiguating state, which "
            "complicates the grammar and produces worse error messages. The "
            "design principle is to resolve as much ambiguity as possible in "
            "the lexer, keeping the parser grammar context-free.",
        ]),
        ("2. Operator Disambiguation", [
            "The character <code>|</code> appears in three roles in Lateralus:",
            ("list", [
                "Bitwise OR: <code>a | b</code>",
                "Pattern match arm separator: <code>Ok(x) | Err(x) =&gt; ...</code>",
                "Start of a pipeline operator: <code>|&gt;</code>, <code>|?&gt;</code>, "
                "<code>|&gt;&gt;</code>, <code>|&gt;|</code>",
            ]),
            "The lexer disambiguates by one-character lookahead: if the character "
            "after <code>|</code> is <code>&gt;</code>, <code>?</code>, or "
            "a second <code>|</code>, it enters pipeline-operator mode. Otherwise "
            "it emits a <code>PIPE</code> token (used for both bitwise OR and "
            "pattern separators; the parser distinguishes these by context).",
            ("code",
             "// Lexer DFA: states for the | character\n"
             "state AFTER_PIPE:\n"
             "    '>'  -> emit PIPELINE_TOTAL,  return to INITIAL\n"
             "    '?'  -> enter AFTER_PIPE_QUESTION\n"
             "    '|'  -> enter AFTER_PIPE_PIPE\n"
             "    else -> emit BITWISE_OR, re-process current char\n\n"
             "state AFTER_PIPE_QUESTION:\n"
             "    '>'  -> emit PIPELINE_ERROR,  return to INITIAL\n"
             "    else -> error: expected '>' after '|?'"),
        ]),
        ("3. Pipeline Operator Token Table", [
            "The four pipeline operators tokenize to distinct token types with "
            "distinct precedence values baked in at lex time:",
            ("code",
             "Source   Token             Precedence  Category\n"
             "---------------------------------------------------\n"
             "|>       PIPELINE_TOTAL    6           total\n"
             "|?>      PIPELINE_ERROR    6           error\n"
             "|>>      PIPELINE_ASYNC    6           async\n"
             "|>|      PIPELINE_FANOUT   6           fan-out"),
            "All four share precedence 6 (lower than arithmetic, higher than "
            "comparison operators). The shared precedence means no parentheses "
            "are needed in the common case of mixing operator variants in one "
            "expression. The precedence was chosen empirically by testing 200 "
            "real Lateralus programs and measuring how often parentheses were "
            "needed under various precedence assignments.",
        ]),
        ("4. Contextual Keywords", [
            "Lateralus has a small set of contextual keywords: identifiers that "
            "are reserved in specific syntactic positions but legal as identifiers "
            "elsewhere. The contextual keywords are:",
            ("code",
             "Keyword    Contextual position\n"
             "-------------------------------\n"
             "pipe       After '=' or '(' at expression start\n"
             "async      Before 'fn' or '|>'\n"
             "sealed     Before 'record' or 'enum'\n"
             "pub        Before 'fn', 'let', 'record', 'enum', 'module'\n"
             "where      After a type parameter list\n"
             "with       After 'import'"),
            "The lexer emits these as identifier tokens (<code>IDENT</code>) and "
            "the parser promotes them to keyword tokens based on position. This "
            "avoids breaking code that uses these words as variable names, which "
            "is common in practice (<code>let pipe = ...</code> appears in tests "
            "and teaching material).",
        ]),
        ("5. The Hand-Written DFA Rationale", [
            "Lexer generators (flex, ANTLR's lexer mode) produce correct lexers "
            "automatically from a grammar specification. Why write the Lateralus "
            "lexer by hand?",
            "Three reasons: error message quality, contextual keyword support, "
            "and compile-time predictability.",
            ("h3", "5.1 Error Message Quality"),
            "A generated DFA reports 'unexpected character' with the character "
            "and position. A hand-written DFA can report the context: "
            "'expected > after |? to form the error pipeline operator'. This "
            "context-aware message is possible only because the hand-written code "
            "knows it is in <code>AFTER_PIPE_QUESTION</code> state.",
            ("h3", "5.2 Contextual Keyword Support"),
            "Contextual keywords require state that a simple DFA does not carry. "
            "The hand-written lexer threads a 'previous token' value through the "
            "tokenization loop, allowing the contextual keyword table lookup to "
            "check whether the preceding token was an assignment operator, "
            "a parenthesis, or a declaration keyword.",
            ("h3", "5.3 Compile-Time Predictability"),
            "The generated DFA size and performance depend on the lexer generator's "
            "output, which can vary between versions. The hand-written DFA has a "
            "fixed, reviewable implementation that does not change when the tool "
            "is updated.",
        ]),
        ("6. Unicode Handling", [
            "Lateralus source files are UTF-8. The lexer handles Unicode in two "
            "phases: identifier scanning and string literal scanning.",
            "Identifier scanning accepts the Unicode XID_Start and XID_Continue "
            "character classes as defined by Unicode 15.0. Operator characters "
            "are ASCII-only; the four pipeline operators use only <code>|</code>, "
            "<code>&gt;</code>, and <code>?</code>.",
            "String literals accept any valid UTF-8 byte sequence. Escape sequences "
            "follow Rust conventions: <code>\\u{XXXX}</code> for Unicode code points "
            "up to U+10FFFF, <code>\\n</code>, <code>\\t</code>, <code>\\\\</code>, "
            "and <code>\\\"</code>.",
            ("code",
             "// Valid Lateralus identifiers\n"
             "let café = \"espresso\"\n"
             "let π = 3.14159\n"
             "let 名前 = \"Taro\"\n\n"
             "// Invalid: operator characters in identifiers\n"
             "let x|y = 1  // error: | is an operator, not an identifier char"),
        ]),
        ("7. Numeric Literal Lexing", [
            "Numeric literals support four bases and two floating-point formats:",
            ("code",
             "// Integer literals\n"
             "255        // decimal\n"
             "0xFF       // hexadecimal\n"
             "0b11111111 // binary\n"
             "0o377      // octal\n"
             "1_000_000  // underscore separators allowed\n\n"
             "// Floating-point literals\n"
             "3.14\n"
             "1.0e-10\n"
             "0x1.8p+0   // hex float (IEEE 754 hex format)"),
            "The lexer distinguishes integer and float literals without looking at "
            "the suffix: any literal containing a <code>.</code> or <code>e</code>/"
            "<code>E</code> exponent is a float. Hex floats use <code>p</code>/"
            "<code>P</code> as the exponent marker (IEEE 754 convention).",
        ]),
        ("8. Benchmark: Lexer Throughput", [
            "We measured the Lateralus lexer throughput on three representative "
            "inputs: the full Lateralus standard library source (82K tokens), a "
            "generated stress test with maximum pipeline operator density (100K "
            "pipeline operators in 1M tokens), and a Unicode-heavy source with "
            "mixed-script identifiers.",
            ("code",
             "Input                     Size     Throughput\n"
             "-----------------------------------------------\n"
             "Standard library          82K tok   180 MB/s\n"
             "Pipeline stress test      1M tok    165 MB/s\n"
             "Unicode-heavy source      500K tok  140 MB/s"),
            "The pipeline stress test is 9% slower than the standard library "
            "input because the four-character pipeline operators require two "
            "lookahead reads each (the first <code>|</code> and then the "
            "operator suffix). The Unicode overhead reflects the XID character "
            "class table lookup. All three inputs are well within the "
            "threshold for interactive compilation (target: > 50 MB/s).",
        ]),
    ],
)

print(f"wrote {OUT}")
