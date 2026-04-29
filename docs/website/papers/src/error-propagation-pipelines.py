#!/usr/bin/env python3
"""Render 'Error Propagation in Pipeline-Native Languages' in canonical Lateralus style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "error-propagation-pipelines.pdf"

render_paper(
    out_path=str(OUT),
    title="Error Propagation in Pipeline-Native Languages",
    subtitle="Typed short-circuit semantics, error accumulation, and recovery operators",
    meta="bad-antics &middot; January 2024 &middot; Lateralus Language Research",
    abstract=(
        "Error handling is the aspect of pipeline-native languages most frequently "
        "under-specified. Languages that treat the pipe operator as sugar provide no "
        "native mechanism for propagating errors through a pipeline; the programmer must "
        "manually thread Result monads or use exception-based control flow. Lateralus "
        "provides three error operators with distinct semantics: short-circuit propagation "
        "(<code>|?></code>), error accumulation (<code>|!></code>), and recovery "
        "(<code>|~></code>). This paper specifies their typing rules, denotational "
        "semantics, and compilation strategy, and shows that together they cover all "
        "practical error-handling patterns without requiring a separate combinator library."
    ),
    sections=[
        ("1. Why Error Handling Belongs in the Pipeline", [
            "In a traditional expression-oriented language, error handling interrupts "
            "the visual flow of data transformation. A five-step pipeline where each "
            "step can fail requires either nested conditionals, a chain of "
            "<code>.andThen()</code> calls, or exception-based control flow — all of "
            "which obscure the primary data flow.",
            "Lateralus takes the position that error handling is not an interruption of "
            "the pipeline but a property of individual pipeline stages. The operator "
            "connecting two stages communicates how errors are handled at that boundary. "
            "The result is code where the primary path and the error paths are both "
            "visible at a glance.",
            ("h3", "1.1 Three Error Patterns"),
            "Practical code exhibits three distinct error patterns:",
            ("list", [
                "<b>Short-circuit</b>: the first error stops the pipeline. Use case: "
                "request parsing, where there is no meaningful recovery from a malformed "
                "input.",
                "<b>Accumulation</b>: all errors are collected before short-circuiting. "
                "Use case: form validation, where the user wants to see all validation "
                "failures at once.",
                "<b>Recovery</b>: an error triggers a fallback computation. Use case: "
                "cache misses, optional enrichment steps, graceful degradation.",
            ]),
            "Each pattern maps to a distinct operator in Lateralus, keeping the code "
            "intent explicit without requiring a combinator library.",
        ]),
        ("2. Short-Circuit Propagation: |?>", [
            "The <code>|?></code> operator implements monadic bind over "
            "<code>Result&lt;T, E&gt;</code>. When the left-hand side evaluates to "
            "<code>Ok(v)</code>, <code>v</code> is passed to the right-hand stage. "
            "When the left-hand side evaluates to <code>Err(e)</code>, evaluation "
            "of the current pipeline terminates and the pipeline returns "
            "<code>Err(e)</code> immediately.",
            ("rule",
             "Gamma |- x : Result<A, E>    Gamma |- f : A -> Result<B, E>\n"
             "--------------------------------------------------------------\n"
             "              Gamma |- x |?> f : Result<B, E>"),
            "The compiler generates a conditional branch after each <code>|?></code> "
            "stage: if the result tag is <code>Err</code>, jump to the pipeline's "
            "exit block with the error value. If the result tag is <code>Ok</code>, "
            "unwrap the value and pass it to the next stage. A sequence of N "
            "<code>|?></code> stages generates N branch instructions, but a "
            "branch-elimination pass fuses consecutive error branches into a single "
            "early-exit block when the error types are identical.",
            ("code",
             "// Five-stage request handler: all steps can fail\n"
             "let response = request\n"
             "    |?> parse_method\n"
             "    |?> validate_auth_header\n"
             "    |?> deserialize_body\n"
             "    |?> apply_business_rules\n"
             "    |?> serialize_response"),
            "After branch fusion, the compiler generates one error exit point, not five. "
            "The generated code is structurally equivalent to a hand-written if-chain "
            "but is produced automatically from the pipeline form.",
        ]),
        ("3. Error Accumulation: |!>", [
            "The <code>|!></code> operator accumulates errors from all stages before "
            "returning. The input type must be <code>Result&lt;A, E&gt;</code> and "
            "the stage function must return <code>Result&lt;B, E&gt;</code>. If the "
            "input is <code>Err(e)</code>, the stage still executes with the wrapped "
            "value and any new error is appended to the error list. The final result "
            "is either <code>Ok(v)</code> if all stages succeeded or "
            "<code>Err(errors)</code> with the full list of failures.",
            ("rule",
             "Gamma |- x : Result<A, Vec<E>>    Gamma |- f : A -> Result<B, E>\n"
             "-------------------------------------------------------------------\n"
             "              Gamma |- x |!> f : Result<B, Vec<E>>"),
            "Note the asymmetry: the error type of the operator is <code>Vec&lt;E&gt;</code> "
            "(a list of errors), while individual stages return <code>Result&lt;B, E&gt;</code> "
            "(a single error). The accumulation operator lifts each stage's single error "
            "into the growing list.",
            ("code",
             "// Form validation: collect all field errors before returning\n"
             "let validated = form_data\n"
             "    |!> validate_email\n"
             "    |!> validate_phone\n"
             "    |!> validate_address\n"
             "    |!> validate_payment_method\n"
             "// Returns Ok(form) or Err([\"email invalid\", \"phone too short\", ...])"),
            ("h3", "3.1 Handling Dependent Fields"),
            "When later validation steps depend on earlier ones (e.g., the city field "
            "can only be validated if the country field is present), the programmer "
            "switches from <code>|!></code> to <code>|?></code> at the dependency "
            "boundary. The two operators are freely composable:",
            ("code",
             "let result = form\n"
             "    |!> validate_email\n"
             "    |!> validate_phone\n"
             "    |?> require_country    // must succeed before city check\n"
             "    |!> validate_city\n"
             "    |!> validate_postcode"),
        ]),
        ("4. Recovery Operator: |~>", [
            "The <code>|~></code> operator implements error recovery: if the left "
            "side returns <code>Err(e)</code>, the recovery function is called with "
            "<code>e</code> and its result is used as the pipeline value. If the "
            "left side returns <code>Ok(v)</code>, the recovery function is not called.",
            ("rule",
             "Gamma |- x : Result<A, E>    Gamma |- f : E -> Result<A, F>\n"
             "--------------------------------------------------------------\n"
             "              Gamma |- x |~> f : Result<A, F>"),
            "The recovery function maps the old error type <code>E</code> to a new error "
            "type <code>F</code>, which allows error type transformations at recovery "
            "points.",
            ("code",
             "// Cache-aside pattern: try cache, recover by querying DB\n"
             "let data = cache_key\n"
             "    |?> cache::lookup          // Err on miss\n"
             "    |~> db::fetch_and_cache    // called only on miss\n\n"
             "// Graceful degradation: enrich with ML model, recover with rule-based\n"
             "let enriched = record\n"
             "    |?> ml_enricher            // Err if model unavailable\n"
             "    |~> rule_based_enricher    // fallback is always available"),
        ]),
        ("5. Operator Composition and Precedence", [
            "The three error operators compose freely with each other and with the total "
            "operator <code>|></code>. The operator precedence is uniform (left-to-right "
            "evaluation in sequence order), which means the programmer controls error "
            "strategy at each stage boundary explicitly.",
            "A pipeline can switch between accumulation and short-circuit within a single "
            "expression:",
            ("code",
             "let result = input\n"
             "    |?> parse            // short-circuit: no point accumulating parse errors\n"
             "    |!> validate_field_a // accumulate: show all field errors\n"
             "    |!> validate_field_b\n"
             "    |!> validate_field_c\n"
             "    |~> apply_defaults   // recover: fill in defaults if validation partially failed\n"
             "    |>  serialize        // total: cannot fail"),
            ("h3", "5.1 Error Type Unification"),
            "When mixing operators, the error types of consecutive stages must unify or "
            "be explicitly converted. The type checker reports a mismatch at the exact "
            "boundary where types diverge, not at the end of the pipeline, making "
            "error messages actionable.",
        ]),
        ("6. Compilation Strategy", [
            "The compiler represents error-propagating pipelines as a CFG with an "
            "<i>error corridor</i>: a set of basic blocks connected exclusively by "
            "error-tagged branches. The happy path is a straight-line sequence of "
            "blocks; the error corridor collects all the off-ramps.",
            "For <code>|?></code> pipelines, the error corridor has a single merge "
            "point at the pipeline exit. For <code>|!></code> pipelines, the error "
            "corridor carries a <code>Vec&lt;E&gt;</code> accumulator and each stage "
            "appends to it before continuing. For <code>|~></code>, the error corridor "
            "branches into the recovery function rather than the exit.",
            ("code",
             "// Compiler IR sketch for a |?> pipeline\n"
             "bb0:\n"
             "    %r0 = call parse(input)\n"
             "    br %r0.is_ok, bb1, bb_exit_err\n"
             "bb1:\n"
             "    %r1 = call validate_auth(%r0.ok_val)\n"
             "    br %r1.is_ok, bb2, bb_exit_err\n"
             "bb2:\n"
             "    %r2 = call deserialize_body(%r1.ok_val)\n"
             "    br %r2.is_ok, bb3, bb_exit_err\n"
             "bb_exit_err:\n"
             "    // single shared error block — branch fusion result\n"
             "    return Err(current_err)"),
        ]),
        ("7. Comparison with Existing Approaches", [
            "We compare against three existing error-handling styles: Haskell's "
            "<code>do</code>-notation, Rust's <code>?</code> operator, and Java's "
            "checked exceptions. For each, we assess readability (is the data flow "
            "visible?), composability (can error strategies be mixed?), and "
            "performance (does the model impose runtime overhead?).",
            ("code",
             "Style              Data Flow  Composable  Zero-Cost\n"
             "-----------------------------------------------------\n"
             "Haskell do-notation   Medium     Yes         Yes\n"
             "Rust ? operator       Low        No          Yes\n"
             "Java checked exns     Low        No          No\n"
             "Lateralus |?> |!> |~>  High      Yes         Yes"),
            "The 'Data Flow' column reflects the visual left-to-right readability of the "
            "transformation sequence. Lateralus scores highest because the pipeline form "
            "is preserved regardless of which error operators are used; Rust's <code>?</code> "
            "clutters expressions and breaks the pipeline visual when stages return "
            "different <code>Result</code> types.",
        ]),
        ("8. Conclusion", [
            "Error propagation in pipeline-native languages does not require a monadic "
            "library or a separate exception mechanism. Three typed operators — "
            "<code>|?></code> for short-circuit, <code>|!></code> for accumulation, and "
            "<code>|~></code> for recovery — cover the full space of practical error "
            "patterns while remaining composable with each other and with the total "
            "pipeline operator <code>|></code>.",
            "The compilation strategy produces code equivalent to hand-written error "
            "handling with zero abstraction overhead. Future work: extending the "
            "accumulation operator to support partial results (returning both successful "
            "intermediate values and the accumulated error list) and integrating the "
            "recovery operator with the async pipeline for fault-tolerant streaming.",
        ]),
    ],
)

print(f"wrote {OUT}")
