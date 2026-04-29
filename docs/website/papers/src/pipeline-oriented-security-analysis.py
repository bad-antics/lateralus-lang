#!/usr/bin/env python3
"""Render 'Pipeline-Oriented Security Analysis: Advanced Techniques' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "pipeline-oriented-security-analysis.pdf"

render_paper(
    out_path=str(OUT),
    title="Pipeline-Oriented Security Analysis: Advanced Techniques",
    subtitle="Model checking, symbolic execution, and attack graph generation for pipeline programs",
    meta="bad-antics &middot; April 2026 &middot; nullsec / Lateralus Language Research",
    abstract=(
        "This paper extends the pipeline security analysis framework with three "
        "advanced techniques: model checking pipeline state machines against LTL "
        "security properties, symbolic execution of pipeline stages to discover "
        "edge-case vulnerabilities, and automated attack graph generation from "
        "pipeline topology. These techniques are complementary to the taint "
        "tracking and trust boundary auditing described in the companion paper "
        "and are intended for high-assurance applications where manual review "
        "alone is insufficient."
    ),
    sections=[
        ("1. Model Checking Pipeline State Machines", [
            "A pipeline that processes requests with authentication, authorization, "
            "and auditing can be modeled as a finite state machine. Model checking "
            "verifies that the state machine satisfies temporal logic properties, "
            "such as 'authorization is always checked before resource access'.",
            ("code",
             "// Pipeline state machine model\n"
             "enum RequestState {\n"
             "    Received,\n"
             "    Authenticated,\n"
             "    Authorized,\n"
             "    ResourceAccessed,\n"
             "    Audited,\n"
             "}\n\n"
             "// LTL property: authorization always precedes access\n"
             "// G(ResourceAccessed -> P(Authorized))\n"
             "// 'Globally, if resource is accessed, authorized must have happened first'"),
            "The Lateralus security analyzer tool translates pipeline programs "
            "to state machine models and checks the specified LTL properties "
            "using an on-the-fly model checker. Property violations are reported "
            "as counterexample traces through the pipeline.",
        ]),
        ("2. Symbolic Execution of Pipeline Stages", [
            "Symbolic execution runs a function with symbolic inputs (variables "
            "representing all possible values) and tracks path conditions. When "
            "a path leads to a security-relevant state (a panic, an unchecked "
            "unwrap, or a taint violation), the solver finds a concrete input "
            "that exercises that path.",
            ("code",
             "// Symbolic execution of a pipeline stage\n"
             "ltl symex nullsec::parse::http_headers\n"
             "# Analyzes all paths through http_headers\n"
             "# Report:\n"
             "#   FOUND: path leads to panic\n"
             "#   Condition: header_line.len() == 0\n"
             "#   Concrete input: b\"\\r\\n\"\n"
             "#   Fix: add guard: if line.is_empty() { return Err(ParseError::EmptyLine) }"),
            "Symbolic execution finds path-specific bugs that fuzzing misses "
            "because random generation may not reach the specific combination of "
            "values that triggers the bug.",
        ]),
        ("3. Attack Graph Generation", [
            "An attack graph models the paths an adversary can take through a "
            "system, starting from an initial compromise and reaching a target "
            "state (data exfiltration, privilege escalation, etc.). Pipeline "
            "topology provides the structure for the attack graph.",
            ("code",
             "// Generate attack graph for a web application pipeline\n"
             "ltl security attack-graph src/web_app.lt\n"
             "# Analyzes pipeline structure\n"
             "# Outputs: attack_graph.dot (Graphviz)\n"
             "#   Node: user_input (untrusted)\n"
             "#   Edge: parse_json -> validate -> db_query\n"
             "#   Attack: skip validate -> direct db_query = SQL injection\n"
             "#   Mitigation: add Tainted<T> label to user_input"),
            "The attack graph generator identifies which pipeline stages are "
            "reachable without passing through a required security check. These "
            "are the attack paths; mitigations are expressed as additional "
            "required stages in the pipeline.",
        ]),
        ("4. Property-Based Security Testing", [
            "Property-based testing verifies that a stage satisfies a security "
            "property for all inputs, not just known test cases. nullsec provides "
            "a property library for common security properties:",
            ("code",
             "// Property: sanitizer is idempotent (safe(safe(x)) == safe(x))\n"
             "#[property]\n"
             "fn html_escape_idempotent(s: str) -> bool {\n"
             "    let once   = html_escape(s.clone());\n"
             "    let twice  = html_escape(once.clone());\n"
             "    once == twice\n"
             "}\n\n"
             "// Property: parser + printer roundtrip\n"
             "#[property]\n"
             "fn json_roundtrip(v: JsonValue) -> bool {\n"
             "    parse_json(print_json(v.clone())) == Ok(v)\n"
             "}"),
            "Property failures are shrunk automatically: the framework finds "
            "the smallest input that violates the property, making debugging "
            "the failure much easier.",
        ]),
        ("5. Compositional Security Verification", [
            "When a pipeline is composed of verified stages, can the composed "
            "pipeline be considered secure? Compositional security verification "
            "answers this question using the security type system.",
            "If each stage has a verified security specification (a pre/post "
            "condition expressed in the type system), then the composed pipeline's "
            "specification is the composition of the individual specifications. "
            "This is the security analog of the pipeline algebraic laws: just "
            "as stage fusion preserves behavior, specification composition "
            "preserves security properties.",
            ("rule",
             "-- Compositional security: if each stage is secure, the pipeline is\n"
             "secure(stage_1) ∧ secure(stage_2) ∧ ... ∧ secure(stage_n)\n"
             "⟹ secure(pipe { |> stage_1 |> stage_2 ... |> stage_n })"),
        ]),
        ("6. Threat Modeling from Pipeline Topology", [
            "STRIDE threat modeling (Spoofing, Tampering, Repudiation, "
            "Information Disclosure, Denial of Service, Elevation of Privilege) "
            "can be applied to pipeline topology automatically. The nullsec "
            "threat modeler analyzes the pipeline graph and generates a "
            "STRIDE analysis for each stage boundary:",
            ("code",
             "ltl security stride src/payment_pipeline.lt\n"
             "# Stage boundary: user_input -> validate_card\n"
             "#   S (Spoofing):    Input claims card ownership — check: identity assertion present\n"
             "#   T (Tampering):   Card number modified in transit — check: HTTPS enforced\n"
             "#   R (Repudiation): No audit log of card validation — ISSUE: add audit stage\n"
             "#   I (Disclosure):  Card number logged in error messages — ISSUE: mask PAN\n"
             "#   D (DoS):         No rate limiting — ISSUE: add rate_limiter stage\n"
             "#   E (EoP):         No privilege check — OK: user context verified"),
        ]),
        ("7. Integration with CI/CD", [
            "The security analysis tools integrate with standard CI/CD pipelines. "
            "The nullsec CI action runs taint analysis, trust boundary audit, "
            "and property tests on every pull request:",
            ("code",
             "# .github/workflows/security.yml\n"
             "- name: Taint analysis\n"
             "  run: ltl security taint src/\n"
             "- name: Trust boundary audit\n"
             "  run: ltl security audit --trust-boundaries src/\n"
             "- name: Property tests\n"
             "  run: ltl test --properties src/\n"
             "- name: Fuzz (10 minutes)\n"
             "  run: ltl fuzz --duration 600 src/"),
            "The CI action blocks merges when any security analysis reports a "
            "finding with severity HIGH or CRITICAL. MEDIUM findings generate "
            "warnings but do not block merges.",
        ]),
        ("8. Case Study: Auditing a Login Pipeline", [
            "We applied the full analysis suite to the nullsec login pipeline "
            "(200 lines, 6 stages). The analysis found:",
            ("list", [
                "<b>Taint analysis</b>: the username was used as a SQL query "
                "parameter without the <code>Tainted</code> label, allowing "
                "injection if the downstream stage changed. Fixed by adding "
                "the label.",
                "<b>Symbolic execution</b>: a panic reachable when the "
                "password hash was exactly 0 bytes (an impossible input in "
                "practice but technically reachable). Fixed with a bounds check.",
                "<b>STRIDE analysis</b>: no audit log for failed login attempts "
                "(repudiation). Fixed by adding an audit stage.",
            ]),
            "The analysis took 4 minutes and found three issues that manual "
            "review had missed. All three were fixed before the code was deployed.",
        ]),
    ],
)

print(f"wrote {OUT}")
