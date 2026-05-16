#!/usr/bin/env python3
"""
Render Pipeline Verification for Safety-Critical Systems: Using Lateralus pipeline semantics to certify deterministic control and monitoring software in the canonical Lateralus paper style (A4, Helvetica/Courier).
"""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / 'pdf' / 'lateralus-pipeline-verification-safety-critical.pdf'

TITLE = 'Pipeline Verification for Safety-Critical Systems'
SUBTITLE = 'Using Lateralus pipeline semantics to certify deterministic control and monitoring software'
META = 'bad-antics · April 2026 · Lateralus Language Research'

ABSTRACT = """Safety-critical systems require certified software, traceable behavior, and deterministic operation. Lateralus pipeline semantics enable a verification path from source to deployed firmware in safety-sensitive domains.

This paper describes how to encode safety contracts, generate verifiable artifacts, and support audits for pipeline-driven control and monitoring software.

The goal is to make the pipeline itself part of the certification evidence rather than a hidden implementation detail."""

SECTIONS = [
    ('1. Introduction to Safety-Critical Pipelines', [
        'Safety-critical systems are found in avionics, medical devices, industrial controls, and autonomous vehicles. Their software must be certifiable, predictable, and auditable.',
        'Lateralus brings pipeline-first semantics to safety-critical software by making the flow of data and control explicit in the source.',
        'This explicitness simplifies certification because the published artifact corresponds directly to the runtime behavior.',
        'We argue that safety evidence is stronger when the pipeline is visible in the source and when the compiler preserves that visibility in the deployed artifact.',
    ]),
    ('2. Safety Contracts and Stage Invariants', [
        'Each pipeline stage can declare a safety contract that specifies invariants, allowable outputs, and failure modes.',
        'The compiler checks these contracts and ensures that composed stages preserve the overall safety envelope.',
        'Stage invariants may include bounds on output values, timing guarantees, and permitted side effects.',
        'This section formalizes stage invariants and explains how they contribute to system-level safety proofs.',
    ]),
    ('3. Deterministic Control Loops', [
        'Control loops must behave deterministically under the same input conditions. Lateralus models these loops as pipeline cycles with explicit timing and side-effect contracts.',
        'The compiler uses this model to generate artifacts that are amenable to verification and runtime monitoring.',
        'We describe how loop timing is encoded as pipeline contracts that bound the worst-case execution time and the period of each iteration.',
        'This section explains how deterministic pipeline cycles differ from general asynchronous event pipelines in safety-critical contexts.',
    ]),
    ('4. Case Study: Medical Infusion Pump Pipeline', [
        'We describe a pipeline for a medical infusion pump that reads sensor data, computes dosage, monitors safety thresholds, and actuates valves.',
        ('code', 'let control = read_flow() |> compute_dose() |> check_safety() |> dispatch_valve()'),
        'The manifest records the safety contracts, timing assumptions, and allowed failure modes for each stage.',
        'This case study illustrates how Lateralus makes the control pipeline easier to validate and audit.',
    ]),
    ('5. Certification Artifacts and Traceability', [
        'Certification requires traceability from requirements to code to test results. Lateralus pipeline manifests act as a high-level trace artifact that links source semantics to deployed behavior.',
        'The compiler can emit additional trace metadata for each stage, including proof obligations and verification status.',
        'This section explains how those artifacts fit into a safety case and how they support traceability across development and review.',
        'We also discuss how manifest-to-binary binding can be used to validate that the deployed firmware matches the certified source.',
    ]),
    ('6. Runtime Monitoring and Audit Trails', [
        'Safety-critical systems often require runtime telemetry and audit trails. Lateralus preserves the pipeline shape in runtime monitoring so that recorded traces can be aligned with the published manifest.',
        'This alignment makes post-incident analysis more reliable and supports regulatory audits.',
        'We discuss the design of audit-friendly pipeline telemetry and the challenges of capturing sufficient information without violating real-time constraints.',
        'This section also covers how to compress and store runtime trace records for later review in constrained embedded systems.',
    ]),
    ('7. Fault Handling and Redundancy', [
        'Fault handling is a first-class concern in critical control pipelines. Lateralus allows designers to express fallback and redundancy stages explicitly.',
        'The compiler validates that redundant paths do not introduce unsafe races or inconsistent state updates.',
        'We describe common redundancy patterns, such as dual measurement, plausibility checks, and safe disengage stages.',
        'The semantics ensure that redundancy is part of the manifest and not an implicit runtime behavior hidden in low-level code.',
    ]),
    ('8. Related Standards and Compliance', [
        'There are established safety standards such as DO-178C, IEC 61508, and ISO 26262. We discuss how Lateralus pipeline artifacts can complement these standards by providing explicit semantics and verifiable manifests.',
        'The paper argues that pipeline-first source artifacts are a natural fit for compliance workflows because they reduce ambiguity in the certification evidence.',
        'This section compares Lateralus to traditional procedural and model-based approaches used in certified systems.',
        'We show how the manifest can be used as a supplementary evidence artifact in certification packages.',
    ]),
    ('9. Verification Toolchain', [
        'A verification toolchain for Lateralus includes static contract checks, model extraction, and runtime assertion instrumentation.',
        'The compiler can emit a verified pipeline model that is suitable for formal analysis tools and bounded model checking.',
        'We describe how the toolchain links pipeline contracts with test harness generation and hardware-in-the-loop verification.',
        'This section also explains the role of deterministic packaging in maintaining the integrity of certified artifacts.',
    ]),
    ('10. Future Work and Open Challenges', [
        'Future work includes stronger static reasoning about timing, richer side-effect modeling, and integration with proof-carrying code frameworks.',
        'We also identify open challenges in verifying machine-learning inference stages and sensor fusion in safety-critical pipelines.',
        'Another direction is a certification workflow that uses the pipeline manifest to automate portions of the compliance evidence.',
        'The conclusion emphasizes the value of pipeline-visible semantics for making safety-critical firmware easier to certify and maintain.',
    ]),
    ('11. Evidence Packaging and Traceability', [
        'Certified systems need artifacts that connect requirements, source, and binary. Lateralus pipeline manifests serve as a traceable link across that chain.',
        'The compiler can emit metadata that binds pipeline stages to test cases, verification results, and runtime telemetry.',
        'This section also explains how to package pipeline manifests with sealed binaries for evidence-based deployment.',
    ]),
    ('12. Audit Workflow Integration', [
        'Auditors need a clear workflow to review pipeline claims. Lateralus supports manifest-driven review and automated consistency checks.',
        'The section describes how to generate audit-ready reports from the same source that produced the deployed firmware.',
        'We also discuss how to use pipeline contracts as inputs to formal audit tools and how to reconcile runtime traces with certified behavior.',
        ('code', 'let audit = pipeline_manifest() |> verify_contracts() |> generate_report()'),
        'This integration reduces the cost of certification and increases confidence in safety-critical deployments.',
    ]),
    ('13. Runtime Certification Monitoring', [
        'Runtime monitoring can reinforce certification by checking that deployed pipelines continue to meet their declared constraints.',
        'Lateralus telemetry can be aligned with pipeline stages, safety contracts, and deployment metadata so audits remain grounded in observed behavior.',
        'This section explains how to detect drift between the certified manifest and the live system.',
        'It also covers how to trigger safe shutdown or failover when certification assumptions are violated at runtime.',
    ]),
    ('Appendix A: Verification Patterns', [
        'Appendix A presents common verification patterns for pipeline stages, including bounded response, fail-safe defaults, and redundancy checks.',
        ('list', [
            'Bounded response time',
            'Fail-safe defaults',
            'Safe state transitions',
            'Redundant measurement validation',
        ]),
        'The appendix shows how these patterns are encoded as stage contracts and how they support certification evidence.',
        'It also includes notes on applying these patterns in embedded control loops and monitoring pipelines.',
    ]),
    ('Appendix B: Certification Workflow', [
        'This appendix describes a certification workflow for pipeline-driven firmware, from requirements capture to manifest generation, test execution, and artifact archiving.',
        'It also covers the role of deterministic packaging in preserving certified releases.',
        'The appendix includes practical guidance for managing versioned pipeline manifests and audit records across certification cycles.',
        'Finally, it recommends documentation practices that make pipeline-driven evidence easier for auditors to review.',
    ]),
    ('Appendix C: Extended Notes', [
        'Certification often uncovers that the hardest part of verification is not the math, but the communication between engineers, auditors, and operators.',
        'Pipeline-first semantics are useful because they allow the same artifact to serve as code, specification, and partial safety case evidence.',
        'When integrating ML inference, the manifest must document the expected operational envelope and acceptable failure modes.',
        'Deterministic packaging is especially valuable for safety-critical firmware because it reduces the certification attack surface.',
        'It is common for safety cases to treat pipeline boundaries as the natural interface for component-level proofs.',
        'Explicit contract checks in the compiler allow a different class of defects to be found before any hardware is built.',
        'It is important to distinguish between runtime monitoring for safety and runtime enforcement of pipeline contracts.',
        'The pipeline manifest can double as a communication artifact between software engineers and system engineers.',
        'A strong observation is that safety-critical pipelines are easier to maintain when the source language preserves both flow and contracts.',
        'This appendix emphasizes that explicit semantics make verification evidence more robust and repeatable.',
    ]),
    ('Appendix D: Practical Considerations', [
        'Certified systems must manage both the source artifact and the generated binary as linked pieces of evidence.',
        'Use the pipeline manifest to capture assumptions about timing, failure modes, and environment constraints.',
        'Maintain a clear mapping from requirement identifiers to pipeline stages so auditors can trace evidence end to end.',
        'When a stage is marked critical, require a corresponding test case and a verification checklist entry in the manifest.',
        'Instrumentation records should be aligned with pipeline stages rather than low-level functions to make post-incident analysis meaningful.',
        'The manifest should describe how transient faults are handled, including lockstep, watchdog, and safe shutdown paths.',
        'A release package for certified firmware should include both the sealed pipeline manifest and a checksum of the compiled runtime.',
        'Safety-critical deployments benefit from a manifest visualization that highlights stage contracts, redundancy, and fallback behavior.',
        'In safety evidence, avoiding ambiguity is more important than minimizing verbosity: explicit semantics are easier to certify.',
        'The pipeline model helps capture assumptions about sensor validity, input sanitization, and actuator command constraints.',
    ]),
    ('Appendix E: Extended Observations', [
        'Certification often uncovers that the hardest part of verification is not the math, but the communication between engineers, auditors, and operators.',
        'Pipeline-first semantics are useful because they allow the same artifact to serve as code, specification, and partial safety case evidence.',
        'When integrating ML inference, the manifest must document the expected operational envelope and acceptable failure modes.',
        'Deterministic packaging is especially valuable for safety-critical firmware because it reduces the certification attack surface.',
        'It is common for safety cases to treat pipeline boundaries as the natural interface for component-level proofs.',
        'Explicit contract checks in the compiler allow a different class of defects to be found before any hardware is built.',
        'It is important to distinguish between runtime monitoring for safety and runtime enforcement of pipeline contracts.',
        'The pipeline manifest can double as a communication artifact between software engineers and system engineers.',
        'A strong observation is that safety-critical pipelines are easier to maintain when the source language preserves both flow and contracts.',
        'The appendix emphasizes that explicit semantics make verification evidence more robust and repeatable.',
    ]),    ('Appendix F: Certification Preparedness', [
        'Certification preparedness begins with a pipeline manifest that clearly documents requirements, assumptions, and verification deliverables.',
        'This appendix describes the artifacts that should accompany a certified pipeline, including test reports, trace evidence, and failure-mode analyses.',
        'We also explain how to use the manifest to support both static certification checks and runtime assurance evidence.',
        'A preparedness checklist should include manifest integrity, proof artifact mapping, and versioned binary binding.',
        'The compiler can make this easier by emitting a packaged certification payload from the same source pipeline.',
        'This appendix is aimed at teams that need to maintain a consistent evidence trail across certification cycles.',
    ]),
    ('Appendix G: Post-Deployment Audit Patterns', [
        'Post-deployment audits need to compare live telemetry with certified pipeline behavior, and the manifest is the anchor for that comparison.',
        'This appendix presents audit patterns for verifying runtime contract satisfaction and for correlating logs with pipeline stages.',
        'We also discuss how to automate drift detection between the certified manifest and the deployed system.',
        'The appendix notes how to capture evidence of safe degradation and how to make audit reports intelligible to non-software specialists.',
        'These patterns help close the loop between certification and field operations in safety-critical environments.',
        'They also support the ongoing maintenance of certified deployments as requirements and hardware evolve.',
    ]),    ('Appendix H: Continuous Compliance Patterns', [
        'Continuous compliance is about keeping the certified manifest aligned with the running system as changes occur.',
        'This appendix describes patterns for automating compliance checks, trace collection, and manifest drift alerts.',
        'We explain how to bind pipeline updates to review cycles and how to keep certification evidence current during maintenance.',
        'The appendix also covers patterns for safe schema evolution of pipeline manifests and contract definitions.',
        'One pattern is to use manifest diffing and compatibility checking as part of every release pipeline.',
        'We also describe how to generate compliance reports that auditors can review without rerunning the full certification process.',
        'These patterns help organizations preserve safety assurances while still evolving software in a controlled way.',
        'The appendix emphasizes that continuous compliance is a discipline best supported by explicit pipeline semantics.',
    ]),
    ('Appendix I: Integrated Certification Dashboards', [
        'Certification dashboards can make pipeline verification status visible to engineers, auditors, and operators.',
        'This appendix describes what information a dashboard should display, including manifest status, verification outcomes, and runtime telemetry correlations.',
        'We also cover how to map pipeline stages to certification tasks and how to show evidence coverage per stage.',
        'The appendix suggests patterns for dashboard-driven review cycles and for surfacing high-risk changes before deployment.',
        'A good dashboard can shorten audit cycles by making the verification status of each pipeline artifact explicit.',
        'We also discuss how to use dashboards to track post-deployment compliance and drift warnings.',
        'These patterns are useful for teams that need to maintain certified systems over many releases.',
        'The appendix concludes with advice on making certification dashboards understandable to both technical and non-technical stakeholders.',
    ]),    ('Appendix J: Compliance Reference', [
        'This reference appendix collects practical compliance patterns for pipeline-driven safety-critical systems.',
        'It includes guidance on manifest structure, trace evidence, and certification artifacts.',
        'The reference also covers how to maintain compliance across change cycles and how to capture audit-relevant information in the pipeline source.',
        'We describe patterns for organizing documentation, test cases, and runtime traces around pipeline semantics.',
        'The appendix notes how to make certification evidence more usable by both engineers and auditors.',
        'It also includes recommendations for integrating manifest changes with safety case updates.',
        'The reference provides advice on documenting assumptions, failure modes, and runtime monitoring obligations.',
        'We emphasize that the manifest should be the central compliance artifact rather than an incidental output.',
        'This appendix also describes how to handle post-deployment compliance questions with manifest-driven evidence.',
        'The goal is to make certification more systematic and less error-prone for teams using Lateralus semantics.',
    ]),    ('Appendix K: Safety Certification Field Guide', [
        'This field guide collects practical patterns for maintaining certification evidence across a pipeline-driven product lifecycle.',
        'We provide recommendations for organizing safety contracts, manifest artifacts, and runtime trace evidence.',
        'The guide also describes how to keep certification documentation synchronized with code and deployment artifacts.',
        'It includes advice on structuring verification checklists around pipeline stages and contract boundaries.',
        'A key pattern is to treat the manifest as the primary evidence artifact and to derive supporting materials from it.',
        'The appendix explains how to handle incremental changes while preserving previously certified behavior.',
        'It also covers how to manage post-deployment audits with manifest-driven evidence and drift detection.',
        'The field guide provides a practical path for teams to keep safety claims up to date as requirements change.',
        'We describe how to present pipeline semantics clearly to non-technical auditors and regulators.',
        'It also includes guidance on how to document assumptions, limits, and fallback behavior for certified pipelines.',
        'The appendix emphasizes the value of explicit semantics in reducing ambiguity during review.',
        'Finally, it recommends operational practices for maintaining certified systems with minimal rework.',
    ]),
]

if __name__ == '__main__':
    render_paper(
        out_path=OUT,
        title=TITLE,
        subtitle=SUBTITLE,
        meta=META,
        abstract=ABSTRACT,
        sections=SECTIONS,
    )
