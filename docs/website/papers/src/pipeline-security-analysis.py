#!/usr/bin/env python3
"""Render 'Pipeline-Oriented Security Analysis' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "pipeline-security-analysis.pdf"

render_paper(
    out_path=str(OUT),
    title="Pipeline-Oriented Security Analysis",
    subtitle="Using Lateralus pipelines to model, audit, and test security properties",
    meta="bad-antics &middot; April 2026 &middot; nullsec / Lateralus Language Research",
    abstract=(
        "Security analysis of software systems involves tracing data flows through "
        "components, identifying trust boundaries, and verifying that sensitive data "
        "does not escape its authorized scope. The Lateralus pipeline model makes "
        "these analyses more tractable: data flows are explicit pipeline stages, "
        "trust boundaries correspond to pipeline operator changes, and the type "
        "system can encode data sensitivity labels. This paper describes three "
        "pipeline-oriented security analysis techniques: taint tracking via type "
        "labels, trust boundary auditing via pipeline shape inspection, and "
        "automated fuzzing of pipeline stages."
    ),
    sections=[
        ("1. Pipelines as Security Models", [
            "A Lateralus pipeline models a security-relevant computation as "
            "a sequence of typed transformations. Each stage corresponds to a "
            "component in the system; the stage's input and output types "
            "correspond to the component's expected interface.",
            "This makes security properties easy to state: 'sensitive data "
            "must be sanitized before leaving the trust boundary' becomes "
            "'a pipeline stage labeled <code>Sanitizer</code> must appear "
            "before any stage labeled <code>ExternalOutput</code>'. The "
            "compiler can check this statically.",
        ]),
        ("2. Taint Tracking with Type Labels", [
            "Type labels mark values as tainted (from untrusted sources) or "
            "clean (sanitized). The type system propagates labels through "
            "pipeline stages:",
            ("code",
             "// Type labels for taint tracking\n"
             "sealed enum Tainted<T> { T }   // wraps a value of type T\n"
             "sealed enum Clean<T>   { T }   // sanitized value of type T\n\n"
             "// Sanitizer stage: converts Tainted to Clean\n"
             "fn html_escape(s: Tainted<str>) -> Clean<str>\n\n"
             "// External output: accepts only Clean values\n"
             "fn send_to_browser(s: Clean<str>) -> Result<(), IoError>\n\n"
             "// Pipeline: taint tracking enforced by types\n"
             "let input: Tainted<str> = user_input();\n"
             "let safe = input\n"
             "    |>  html_escape      // Tainted<str> -> Clean<str>\n"
             "    |?> send_to_browser  // Clean<str> -> Result<(), _>"),
            "Attempting to pass a <code>Tainted&lt;str&gt;</code> directly to "
            "<code>send_to_browser</code> is a compile error: the types do not "
            "match. The sanitizer stage is enforced by the type system, not by "
            "runtime checks or code review.",
        ]),
        ("3. Trust Boundary Auditing", [
            "A trust boundary is a point where data moves between two components "
            "with different trust levels. In a Lateralus pipeline, trust boundaries "
            "can be marked with an annotation that the auditing tool checks:",
            ("code",
             "// Trust boundary annotation\n"
             "#[trust_boundary(from = \"user\", to = \"kernel\")]\n"
             "fn handle_syscall(req: UserRequest) -> KernelResponse { ... }\n\n"
             "// Audit tool command\n"
             "ltl security audit --trust-boundaries src/\n"
             "# Finds all #[trust_boundary] annotations and checks:\n"
             "# 1. Both sides have non-empty type signatures\n"
             "# 2. Input types are sanitized before the boundary\n"
             "# 3. Error propagation is explicit (|?> not unchecked unwrap)"),
            "The audit tool generates a trust boundary map — a graph where "
            "nodes are trust domains and edges are pipeline stages that cross "
            "between them. Security reviewers use the map to focus their "
            "manual review on the highest-risk transitions.",
        ]),
        ("4. Automated Pipeline Fuzzing", [
            "Pipeline stages have typed inputs and outputs, making them ideal "
            "targets for automated fuzzing. The nullsec fuzzer generates "
            "values of the stage's input type using type-directed random "
            "generation and runs the stage, checking for panics, type "
            "invariant violations, or unexpected errors.",
            ("code",
             "// Fuzzing a pipeline stage\n"
             "ltl fuzz nullsec::parse::http_request\n"
             "# Generates random Vec<u8> inputs (the stage's input type)\n"
             "# Runs 1,000,000 iterations\n"
             "# Reports crashes and unexpected Err variants"),
            "Type-directed generation is more efficient than byte-level fuzzing "
            "because it produces structurally valid inputs: a stage that accepts "
            "a <code>JsonObject</code> receives valid JSON, not random bytes that "
            "would be rejected by the parser. This focuses fuzzing on the "
            "stage's actual logic.",
            ("h3", "4.1 Differential Fuzzing"),
            "For stages with reference implementations, differential fuzzing "
            "compares the Lateralus stage output against the reference for "
            "the same input. Discrepancies indicate bugs in either implementation.",
        ]),
        ("5. Information Flow Analysis", [
            "The type label system can be extended to full information flow "
            "control: labels carry security lattice values (Public < Private "
            "< Secret < TopSecret), and the type rules enforce that information "
            "never flows from a higher security level to a lower one.",
            ("code",
             "enum SecurityLevel { Public, Private, Secret, TopSecret }\n\n"
             "// A labeled value\n"
             "struct Labeled<T, const LEVEL: SecurityLevel> { value: T }\n\n"
             "// Declassification requires explicit authorization\n"
             "fn declassify<T>(v: Labeled<T, Secret>, auth: DeclassifyCap)\n"
             "    -> Labeled<T, Public>\n\n"
             "// Compilation error: leaking Secret to Public without declassify\n"
             "let secret: Labeled<str, Secret> = db::fetch_secret();\n"
             "let _: Labeled<str, Public> = secret;  // error: Secret > Public"),
        ]),
        ("6. Static SQL Injection Detection", [
            "SQL injection is detectable at compile time when query construction "
            "is expressed as a pipeline. A query builder stage that accepts "
            "tainted string values is a compile error:",
            ("code",
             "// Safe: parameterized query (accepts any str, escapes it)\n"
             "fn query_by_name(name: str) -> Vec<Row> {\n"
             "    db::execute(\"SELECT * FROM users WHERE name = ?\", [name])\n"
             "}\n\n"
             "// Unsafe: string interpolation (detected by the Tainted type)\n"
             "fn query_unsafe(name: Tainted<str>) -> Vec<Row> {\n"
             "    let sql = format!(\"SELECT * FROM users WHERE name = '{}'\", name);\n"
             "    //                                                    ^^^^\n"
             "    // error: cannot use Tainted<str> in SQL string interpolation\n"
             "    db::execute_raw(sql)\n"
             "}"),
        ]),
        ("7. Audit Trail Integration", [
            "Every pipeline in a security-critical application can be wrapped "
            "with an audit transformer that logs all inputs, outputs, and errors "
            "to an append-only, signed audit trail:",
            ("code",
             "fn with_audit(label: str, p: Pipeline<A, B>) -> Pipeline<A, B> {\n"
             "    pipe {\n"
             "        |> audit::log_input(label)\n"
             "        |> p\n"
             "        |> audit::log_output(label)\n"
             "    }\n"
             "}\n\n"
             "let audited_login = login_pipeline\n"
             "    |> with_audit(\"user_login\")\n"
             "// Every login attempt is logged with input hash and outcome"),
            "The audit log uses the same hash-chained ledger mechanism as the "
            "element-115-drive telemetry system (paper 14). Each entry is signed "
            "with the node's Ed25519 key, making tampering detectable.",
        ]),
        ("8. Limitations and Future Work", [
            "Current limitations of the pipeline security analysis approach:",
            ("list", [
                "The taint label system requires explicit typing of all sanitizer "
                "stages. Implicit sanitization (e.g., integer parsing that "
                "inherently prevents injection) is not automatically credited.",
                "The trust boundary auditor does not verify that the source "
                "code matches the binary — only that the annotations are "
                "consistent with the code as written.",
                "The fuzzer does not yet model multi-stage pipelines: it fuzzes "
                "individual stages, not sequences of stages that might interact.",
            ]),
            "Future work: extending the taint system to cover more of the "
            "standard library automatically (e.g., all integer-parsing functions "
            "produce <code>Clean</code> output by default), integrating the "
            "audit trail with SIEM systems via the OCSF schema, and adding "
            "a property-based test mode to the fuzzer.",
        ]),
    ],
)

print(f"wrote {OUT}")
