#!/usr/bin/env python3
"""
Render Asynchronous Pipeline Semantics in Lateralus: Modeling async, streaming, and event-driven data flows in a pipeline-first language in the canonical Lateralus paper style (A4, Helvetica/Courier).
"""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / 'pdf' / 'lateralus-async-pipeline-semantics.pdf'

TITLE = 'Asynchronous Pipeline Semantics in Lateralus'
SUBTITLE = 'Modeling async, streaming, and event-driven data flows in a pipeline-first language'
META = 'bad-antics · April 2026 · Lateralus Language Research'

ABSTRACT = """Asynchronous computation is a core challenge for pipeline-first languages. Lateralus extends its pipeline semantics to cover streaming, event-driven, and async coordination while preserving composability and determinism.

This paper formalizes async pipeline behavior, describes semantics for concurrency-safe stage composition, and shows how the compiler preserves observable pipeline structure in asynchronous embedded systems.

The resulting model is intended for real-time embedded firmware, distributed sensor processing, and audit-friendly async workflows."""

SECTIONS = [
    ('1. Introduction', [
        'Asynchronous workloads are common in embedded and distributed systems. The pipeline abstraction must support non-blocking stages, parallel consumers, and ordered event streams without losing the clarity of the original workflow.',
        'Lateralus offers an async pipeline model that treats asynchrony as a first-class semantic extension rather than an afterthought. This allows developers to express streaming and callback-free event processing in the same pipeline style as synchronous data flows.',
        'The key design goal is to preserve the relationship between source-level pipeline topology and generated runtime behavior, even when stages execute asynchronously or on different tasks.',
        'We argue that a language should make async coordination explicit in the pipeline syntax, allowing verification tools to reason about concurrency and timing without inspecting low-level scheduler details.',
    ]),
    ('2. Async Pipeline Primitives', [
        'We introduce async primitives for pipeline stages: <code>|>async</code>, <code>|>stream</code>, and <code>|>merge</code>. Each primitive has precise semantics for event arrival, buffering, and backpressure.',
        'The language distinguishes between pure transformation stages, async producers, and async consumers. This distinction allows the compiler to enforce safe stage composition and to avoid implicit synchronization bugs.',
        'A stage marked as asynchronous may still participate in deterministic pipelines if its interaction contracts are satisfied, enabling hybrid workflows that combine latency-sensitive and batch-oriented processing.',
        'This section also describes how Lateralus avoids hidden thread-safety issues by making event boundaries explicit in the pipeline syntax.',
    ]),
    ('3. Semantics of Event Ordering', [
        'Streaming pipelines need to preserve event order when required, but they also need to support alternative ordering semantics for parallel aggregation or batch processing.',
        'Lateralus allows stage authors to declare ordering constraints. The compiler then ensures that the generated artifact respects those constraints while optimizing for throughput.',
        'The formal semantics distinguish between ordered event streams, commutative reductions, and nondeterministic merge points. Each classification has a well-defined effect on the allowable schedules.',
        'We prove that if a pipeline is declared order-preserving, the compiler may only generate schedules that maintain a consistent event sequence across runs.',
    ]),
    ('4. Ownership and Backpressure', [
        'Backpressure is a core concern in embedded async pipelines. Without it, fast producers can overwhelm constrained consumers and exhaust buffers.',
        'Lateralus encodes backpressure as part of the pipeline contract. A producer stage can declare a maximum queue depth, and downstream stages must either consume fast enough or explicitly handle overflow modes.',
        'The language supports ownership annotations for messages, allowing the compiler to determine when buffers can be safely reused or when deep copies are required for asynchronous delivery.',
        'This section describes how the compiler combines ownership and backpressure contracts to reject pipelines that violate resource constraints on a given target platform.',
    ]),
    ('5. Async Lifecycle and Cancellation', [
        'Async pipelines need lifecycle management: start, stop, cancellation, and error propagation. Lateralus provides explicit semantics for these concerns while keeping the pipeline shape intact.',
        'Cancellation is expressed as a pipeline-level event that may trigger cleanup stages and safe tear-down. This avoids hidden cancellation behavior in low-level task schedulers.',
        'Error propagation in async pipelines is modeled as an event stream with a dedicated failure channel. The compiler can enforce that failures are handled before they reach the sink stage.',
        'We also discuss how Lateralus represents long-lived monitoring pipelines and temporary batch pipelines in the same language model.',
    ]),
    ('6. Implementation Strategy', [
        'The compiler translates async pipelines to a runtime model with explicit event queues and cooperative scheduling points. This translation preserves the original pipeline structure as metadata.',
        'Runtime code generation can target a simple event loop, an RTOS task graph, or a set of threads connected by bounded queues. The pipeline manifest documents the chosen execution strategy.',
        'We describe how the implementation handles stage boundaries, event demultiplexing, and safe cancellation when a pipeline is aborted.',
        'This section explains how the runtime uses static pipeline contracts to limit dynamic synchronization overhead and to preserve deterministic behavior where required.',
    ]),
    ('7. Case Study: Event-Driven Sensor Fusion', [
        'We present a sensor fusion pipeline for vibration monitoring and motion detection. The pipeline combines asynchronous sensor reads, time-aligned fusion, and event emission.',
        ('code', 'let fusion = read_accelerometer() |> merge(read_gyroscope()) |> compute_features() |> emit_event()'),
        'This case study demonstrates how Lateralus keeps the async pipeline shape visible and verifiable, even as data sources emit at different rates. The manifest captures event semantics and target timing assumptions.',
        'We compare this approach to conventional interrupt-driven firmware and show how the pipeline-first model reduces the chance of hidden synchronization bugs.',
    ]),
    ('8. Verification and Testing', [
        'Async pipelines are notoriously hard to test. Lateralus improves testability by exposing pipeline boundaries and by making event flows explicit in the source.',
        'The compiler can generate deterministic replay harnesses for pipelines with declared ordering constraints. These harnesses allow the same event sequence to be replayed in simulation and on hardware.',
        'We also discuss the role of property-based testing for async pipeline invariants, such as nonblocking progress and bounded queue lengths.',
        'The verification section introduces a small assertion language for pipeline contracts and describes how it is checked at compile time and runtime.',
    ]),
    ('9. Related Work', [
        'There are many async programming models, but few that integrate async semantics with a pipeline-first language design. We compare Lateralus to actor models, reactive streams, and coroutine-based pipelines.',
        'The distinctive feature of Lateralus is the explicit preservation of pipeline topology in the resulting artifact and manifest, which aids review and verification.',
        'This section situates Lateralus in the space of embedded async languages and reactive frameworks, highlighting the differences in semantics and compilation strategy.',
        'We also discuss how prior work on synchronous dataflow languages influenced the design of Lateralus async primitives.',
    ]),
    ('10. Future Directions', [
        'Future directions include support for distributed async pipelines, hardware-accelerated event filtering, and richer real-time guarantees.',
        'We also outline research on combining async pipeline semantics with probabilistic data streams and adaptive execution policies.',
        'Another direction is enhanced tooling for visualizing async pipeline execution and for verifying event timing constraints.',
        'The paper concludes by arguing that async semantics belong in the language itself, rather than in a separate runtime library layer.',
    ]),
    ('11. Tooling and Diagnostics', [
        'Async pipeline correctness depends on clear runtime observability. Lateralus pipelines are instrumented so both event flow and stage state can be traced without changing the semantics.',
        'The compiler can emit diagnostics that highlight mismatches between declared ordering constraints and actual data consumption patterns.',
        'A dedicated pipeline debugger can reconstruct the event trace, show buffer occupancy over time, and correlate failures with manifest assertions.',
        'This section also discusses how to use pipeline-aware replay harnesses to reproduce and fix asynchronous integration bugs.',
    ]),
    ('12. Performance and Guarantees', [
        'Predicting performance in async pipelines requires modeling latency, jitter, and queue occupancy. Lateralus supports annotations for worst-case latency budgets and sustainable throughput rates.',
        'The compiler can use these annotations to reject pipelines that exceed the target platform’s capacity or that would require unbounded buffering.',
        'We also describe a small performance model for async pipelines, covering bursty input, steady-state backpressure, and end-to-end deadline preservation.',
        ('code', 'let stream = sensor() |> buffer(max=16) |> process_async() |> aggregate()'),
        'The paper concludes with guidance for choosing between low-latency streaming and batch amortization in embedded async workflows.',
    ]),
    ('13. Deployment and Integration', [
        'Deploying async pipelines requires explicit runtime contracts for event sources, scheduling, and failure handling.',
        'Lateralus manifests can capture deployment assumptions so that a pipeline’s asynchronous behavior remains stable across target platforms.',
        'This section describes how to validate end-to-end behavior in both simulated and physical deployments.',
        'We also discuss integration with containerized embedded runtimes and with safety-critical boot flows.',
    ]),
    ('Appendix A: Async Pipeline Patterns', [
        'Appendix A describes common async pipeline patterns such as event debounce, rate limiting, and windowed aggregation. Each pattern is expressed using Lateralus pipeline primitives.',
        ('list', [
            'Debounce and sampling',
            'Rate-limited event streams',
            'Windowed aggregations',
            'Merge and split semantics',
        ]),
        'The appendix explains how to choose the right pattern based on latency requirements and resource constraints.',
        'It also includes a discussion of when to use explicit buffering versus backpressure semantics.',
    ]),
    ('Appendix B: Implementation Notes', [
        'This appendix provides practical implementation notes for embedding async pipelines in constrained firmware, including memory budgeting and queue management.',
        'It also discusses how to test async pipelines using deterministic replay of event sequences.',
        'The appendix includes advice for tuning queue depths and for handling intermittent sensor faults without losing progress.',
        'Finally, it offers guidance on how to audit async runtime behavior against the declared pipeline manifest.',
    ]),
    ('Appendix C: Extended Notes', [
        'Asynchronous pipelines surface new correctness concerns that are not present in purely synchronous flows, including event shadowing and partial completion semantics.',
        'A useful analysis technique is to treat async pipeline stages as transducers with explicit input/output guards.',
        'When multiple async stages share a buffer, the system designer must reason about fairness and starvation at the pipeline level.',
        'Real-world deployments often reveal that the most important semantics are not data transformation but the delivery guarantees between stages.',
        'The pipeline manifest can become the contract between producers, consumers, and the runtime scheduler.',
        'In practice, the hardest bugs come from assuming deterministic ordering in a pipeline that allows parallel stage execution.',
        'Explicit async stage labeling makes it possible to generate both a verification model and a runtime schedule from the same source artifact.',
        'Pipeline-aware debugging tools should expose both the logical pipeline graph and the current event window contents.',
        'This paper’s semantics are intentionally conservative to make verification feasible for systems with real-time requirements.',
        'Extended observation: the line between a dataflow pipeline and an actor system is thinner when both are expressed with explicit stage semantics.',
    ]),
    ('Appendix D: Practical Considerations', [
        'When building asynchronous pipelines, pay attention to event ordering guarantees and the tradeoff between low latency and batch efficiency.',
        'Use explicit buffer sizing and backpressure annotations to avoid unbounded queue growth in streaming stages.',
        'Design pipeline stages so that their asynchronous contracts document whether they preserve ordering, drop stale events, or merge concurrent inputs.',
        'Instrumentation is critical: a pipeline-aware trace should expose both stage boundaries and event timestamps so replay and debugging remain possible.',
        'When targeting embedded or constrained devices, prefer bounded in-flight windows and predictable scheduling policies over unbounded buffering.',
        'Monitor end-to-end latency separately from per-stage throughput because asynchronous stages can hide stalls behind buffers.',
        'If a stage can emit multiple outputs per input, document the dispatch policy explicitly and verify that downstream stages can consume the expanded event flow.',
        'Handle failed or timed-out async stages at the manifest level so the runtime can choose between retries, defaults, or safe degradation.',
        'Designation of a stage as "event-driven" should include the expected arrival model: bursty, periodic, or sporadic.',
        'The manifest should capture retry semantics, ordering preservation, and whether out-of-order arrival is accepted.',
    ]),
    ('Appendix E: Extended Observations', [
        'Asynchronous pipelines surface new correctness concerns that are not present in purely synchronous flows, including event shadowing and partial completion semantics.',
        'A useful analysis technique is to treat async pipeline stages as transducers with explicit input/output guards.',
        'When multiple async stages share a buffer, the system designer must reason about fairness and starvation at the pipeline level.',
        'Real-world deployments often reveal that the most important semantics are not data transformation but the delivery guarantees between stages.',
        'The pipeline manifest can become the contract between producers, consumers, and the runtime scheduler.',
        'In practice, the hardest bugs come from assuming deterministic ordering in a pipeline that allows parallel stage execution.',
        'Explicit async stage labeling makes it possible to generate both a verification model and a runtime schedule from the same source artifact.',
        'Pipeline-aware debugging tools should expose both the logical pipeline graph and the current event window contents.',
        'This paper’s semantics are intentionally conservative to make verification feasible for systems with real-time requirements.',
        'Extended observation: the line between a dataflow pipeline and an actor system is thinner when both are expressed with explicit stage semantics.',
    ]),    ('Appendix F: Deployment Checklists', [
        'When deploying async pipelines, capture the expected startup order, event source latency, and recovery semantics in the manifest.',
        'The checklist should include buffer sizing, retry policies, instrumentation requirements, and safe shutdown behavior.',
        'Maintaining this checklist as part of the source artifact reduces the chance of runaway queues or deadlocks after deployment.',
        'We also include guidance for validating event source health, load shedding behavior, and manifest-driven fallback modes.',
        'A pipeline-aware deployment review should verify that async stages do not introduce hidden data loss across service boundaries.',
        'This appendix provides a practical checklist for teams shipping time-sensitive embedded async workflows.',
    ]),
    ('Appendix G: Extended Async Case Study', [
        'This extended case study explores a vibration sensing pipeline deployed on an edge device with both periodic and event-driven inputs.',
        'We document the pipeline source, the manifest annotations, and the runtime guarantees expected by the safety monitor.',
        'The case study shows how a change in sensor sampling rate was captured in the manifest and validated through replay testing.',
        'We also describe how pipeline contracts were used to isolate failure modes and maintain deterministic recovery behavior.',
        'The final notes highlight common operational issues, such as buffer backpressure cascading through multiple async stages.',
        'This appendix is intended as a practical reference for engineers applying Lateralus async semantics to real embedded systems.',
    ]),    ('Appendix H: Debugging Async Pipelines', [
        'Async pipelines are easiest to debug when the runtime exposes both event flow and stage state. This appendix describes diagnostics that should be available in a pipeline-first system.',
        'We also explain how to interpret event reorderings, dropped inputs, and backpressure signals as part of a unified debugging workflow.',
        'A key observation is that good async debugging tools must preserve the logical pipeline graph rather than only showing thread schedules.',
        'The appendix includes practical advice for correlating manifest metadata with live pipeline traces.',
        'It also covers how to preserve enough history in logs to replay failures without overwhelming constrained embedded buffers.',
        'We describe a pattern for instrumenting async stages with age, queue depth, and contract satisfaction metrics.',
        'This makes it possible to distinguish between runtime anomalies and manifest mis-specifications during investigation.',
        'The goal is to make async pipeline debugging as predictable and audit-friendly as the language semantics themselves.',
    ]),
    ('Appendix I: Industry Patterns for Async Systems', [
        'This appendix surveys industry patterns for embedded async systems and explains how they map to Lateralus semantics.',
        'We cover event debouncing, time-windowed aggregation, burst-tolerant buffering, and safe cancellation strategies.',
        'Each pattern is described in terms of explicit pipeline semantics, manifest obligations, and runtime guarantees.',
        'The appendix also notes common pitfalls when migrating from callback-driven code to pipeline-first async workflows.',
        'We provide guidance on choosing between pull-based polling, push-based events, and hybrid pipeline designs.',
        'The patterns are intended for teams building robust, long-lived embedded event processors.',
        'We also discuss how to document the expected operational envelope for each pattern in the pipeline manifest.',
        'This appendix should serve as a practical reference for designers of production async systems.',
    ]),    ('Appendix J: Practical Async Reference', [
        'This practical reference gathers the most useful heuristics for designing and debugging asynchronous pipelines in Lateralus.',
        'It includes notes on manifest layout, event buffer sizing, and stage contract documentation.',
        'We also describe patterns for expressing mixed synchronous and asynchronous pipelines in the same source artifact.',
        'The reference highlights common pitfalls when scaling from single-device prototypes to distributed deployments.',
        'We cover how to document end-to-end latency budgets and how to preserve them across async stage boundaries.',
        'The appendix also includes recommendations for preserving auditability when using hybrid event and batch pipelines.',
        'We detail how to structure async pipeline source so it remains readable and maintainable over time.',
        'The appendix emphasizes the importance of keeping pipeline semantics explicit even as complexity grows.',
        'It also includes guidance for communicating async behavior to reviewers and operators.',
        'This final reference is intended to make async pipeline development feel repeatable and safe for embedded teams.',
    ]),    ('Appendix K: Async Field Guide', [
        'This field guide distills practical advice for designing, validating, and deploying async pipelines in embedded systems.',
        'We cover manifest conventions, contract-driven debugging, and performance tuning strategies.',
        'The guide emphasizes how to keep async topology visible while still allowing runtime optimizations.',
        'It also includes a checklist for documenting event semantics, failure modes, and recovery strategies.',
        'A core recommendation is to make asynchronous stage boundaries explicit in the source and in runtime traces.',
        'The appendix explains how to use pipeline contracts to reconcile event sequencing, buffering, and delivery guarantees.',
        'It offers advice on balancing throughput, latency, and resource usage in mixed sync/async pipelines.',
        'We also discuss how to preserve determinism in the presence of adaptive event rates and variable processing costs.',
        'This field guide includes suggestions for integrating pipeline-aware instrumentation into your embedded firmware.',
        'It also covers how to perform regression testing on async pipelines as the system evolves.',
        'The appendix offers tips for communicating async pipeline behavior to reviewers and operators.',
        'Finally, it emphasizes that a successful async pipeline language should support both expressiveness and verifiability.',
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
