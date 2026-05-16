#!/usr/bin/env python3
"""
Render Hardware-Accelerated Pipelines in Lateralus: Offloading pipeline stages to accelerators while preserving pipeline semantics and determinism in the canonical Lateralus paper style (A4, Helvetica/Courier).
"""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / 'pdf' / 'lateralus-hardware-accelerated-pipelines.pdf'

TITLE = 'Hardware-Accelerated Pipelines in Lateralus'
SUBTITLE = 'Offloading pipeline stages to accelerators while preserving pipeline semantics and determinism'
META = 'bad-antics · April 2026 · Lateralus Language Research'

ABSTRACT = """Hardware acceleration is an important dimension of embedded pipeline execution. Lateralus supports hardware-accelerated stages while keeping the pipeline semantics explicit and the end-to-end artifact deterministic.

This paper describes accelerator-aware pipeline annotations, stage offload contracts, and compiler-generated hybrid execution plans for CPUs and dedicated hardware.

The result is a pipeline language that can express both software and hardware stage placements without losing auditability."""

SECTIONS = [
    ('1. Introduction', [
        'Embedded pipelines often include compute-heavy stages such as FFTs, neural filters, or image preprocessing. Offloading these stages to hardware accelerators improves performance but can obscure the pipeline semantics.',
        'Lateralus makes hardware acceleration explicit in the source, allowing developers to annotate stages as accelerator candidates while preserving the overall pipeline shape.',
        'This transparency enables both performance and auditability in accelerator-enabled systems.',
        'We introduce compiler support for hybrid execution plans that combine CPU code with accelerator kernels in a deterministic manifest.',
    ]),
    ('2. Accelerator Stage Contracts', [
        'An accelerator stage contract specifies the hardware capabilities required, the input and output formats, and the determinism guarantees.',
        'The compiler uses these contracts to match stages to available accelerators and to verify that the chosen offload plan preserves end-to-end semantics.',
        'Contracts also capture performance constraints such as throughput, latency, and memory alignment requirements.',
        'We define the contract language and the validation rules for accelerator compatibility.',
    ]),
    ('3. Hybrid Execution Plans', [
        'Hardware-accelerated pipelines are often hybrid: some stages run on the CPU, others on accelerators, and data moves between them.',
        'Lateralus generates hybrid execution plans that include explicit transfer points and compatibility checks. These plans are also reflected in the sealed manifest.',
        'The manifest ensures that the pipeline remains reviewable even when execution is split across heterogeneous units.',
        'We describe how the compiler schedules transfers and avoids hidden data copies by making stage boundaries explicit.',
    ]),
    ('4. Case Study: FPGA-Accelerated Signal Processing', [
        'We present a signal processing pipeline that offloads FFT and correlation stages to an FPGA while keeping pre-/post-processing on the CPU.',
        ('code', 'let signal = read_adc() |> normalize() |> fft_accel() |> correlate_accel(template) |> threshold()'),
        'The case study shows how the pipeline manifest captures both the CPU and accelerator stages, as well as the data transfer contracts.',
        'This example also highlights the importance of matching data formats and timing expectations between CPU and accelerator domains.',
    ]),
    ('5. Backend Support for Accelerator Kernels', [
        'The Lateralus compiler includes backend support for generating accelerator-specific kernels and glue code. It also emits metadata that records the accelerator mapping for each stage.',
        'The compiler can reject pipelines when the required accelerator features are unavailable or when the hardware contract is violated.',
        'This prevents accidental deployment of unsupported hybrid pipelines.',
        'We describe how the backend emits code for both the CPU and the accelerator, preserving the pipeline shape in the generated artifacts.',
    ]),
    ('6. Data Movement and Buffer Management', [
        'Data movement is central to hardware-accelerated pipelines. Lateralus exposes transfer points and buffer semantics so that performance-critical data flows are visible in the source.',
        'The language supports explicit buffer ownership and staging annotations, enabling the compiler to minimize copies and avoid aliasing bugs.',
        'We also discuss how the runtime can allocate accelerator buffers with deterministic lifetime semantics.',
        'This section explains how data movement is verified against the pipeline manifest to ensure compatibility with the target accelerator memory model.',
    ]),
    ('7. Determinism Across Heterogeneous Stages', [
        'Determinism is challenging when parts of the pipeline run on different hardware. Lateralus addresses this by requiring that accelerator stages declare deterministic behavior and stable input formats.',
        'The manifest includes a hardware fingerprint that must match the target at deployment time, ensuring that the accelerator configuration is consistent with the published pipeline.',
        'This supports reproducible results across devices with the same accelerator capabilities.',
        'We also discuss fallback strategies for targets where an accelerator is unavailable or misconfigured.',
    ]),
    ('8. Safety and Verification', [
        'Hardware acceleration introduces additional safety concerns, such as buffer alignment, data format compatibility, and side-channel behavior.',
        'Lateralus verifies that accelerator stages preserve data invariants and that any offload does not violate stage contracts.',
        'This section discusses the verification model and how it interacts with existing pipeline semantics.',
        'We present a static check that ensures accelerated stages cannot observe or corrupt memory outside their declared buffers.',
    ]),
    ('9. Related Work', [
        'There are existing DSLs for accelerator kernels, but they rarely integrate with a pipeline-first source language. We compare Lateralus to these approaches and highlight the benefits of pipeline-visible acceleration.',
        'The key distinction is that Lateralus preserves the pipeline shape as a reviewable artifact, even when some stages execute on specialized hardware.',
        'We also compare to hardware-aware languages that expose low-level device intrinsics but not pipeline semantics.',
        'This section shows why a pipeline-first model is better suited for audit-friendly hardware acceleration in embedded systems.',
    ]),
    ('10. Future Directions', [
        'Future work includes automated accelerator selection, adaptive offload planning, and tight integration with FPGA tooling.',
        'We also describe research directions for verifying timing constraints and for supporting hardware-software co-design within the pipeline language.',
        'Another direction is a runtime visualization tool that shows the hybrid execution plan and accelerator usage.',
        'The conclusion emphasizes that accelerator support should augment the pipeline semantics without compromising determinism or reviewability.',
    ]),
    ('11. Performance Modeling and Metrics', [
        'Hardware-accelerated pipelines require explicit performance models to make sure offload placement improves the end-to-end behavior.',
        'Lateralus captures throughput, latency, and buffer cost in the pipeline manifest so that acceleration decisions remain reviewable.',
        'The compiler can use these metrics to choose between CPU execution, FPGA kernels, and specialized DSP accelerators.',
        'This section also discusses how to validate performance assumptions with profiling and hardware-in-the-loop testing.',
    ]),
    ('12. FPGA and ASIC Integration', [
        'FPGA and ASIC targets have unique constraints that must be expressed in the pipeline language. Lateralus supports declarative accelerator contracts for these domains.',
        'The manifest records interface widths, clock-domain crossing semantics, and supported numeric ranges for accelerator kernels.',
        'We present a deployment approach where the compiler emits both software host code and accelerator configuration artifacts from the same source pipeline.',
        ('code', 'let fpga_filter = adc() |> reshape(32,128) |> fft_accel() |> downsample()'),
        'This section also describes how to keep FPGA and ASIC stage semantics aligned with the source pipeline during iterative development.',
    ]),
    ('13. Operational and Compliance Support', [
        'Operational support for accelerator-enabled pipelines includes compatibility validation, hardware fingerprinting, and fallback planning.',
        'Lateralus manifests can capture which accelerator revisions are allowed and how to fall back if a target device is missing a feature.',
        'This section describes how hardware contracts interact with deployment tooling and how to preserve cross-device determinism.',
        'We also discuss safety concerns around accelerator thermal management and how explicit manifest metadata aids compliance.',
    ]),
    ('Appendix A: Accelerator Pipeline Recipes', [
        'This appendix provides recipes for mapping common pipeline patterns to accelerator-friendly designs, including convolution, FFT, and matrix multiply.',
        ('list', [
            'Convolution and filtering',
            'FFT and spectral analysis',
            'Matrix multiply and linear algebra',
            'Data reformatting patterns',
        ]),
        'It also explains how to express these recipes in Lateralus and how the compiler converts them into hybrid plans.',
        'The appendix includes guidance on when to prefer hardware acceleration versus CPU-only execution.',
    ]),
    ('Appendix B: Deployment Guidance', [
        'This appendix describes deployment guidance for hardware-accelerated Lateralus pipelines, including compatibility checks, firmware packaging, and target validation.',
        'It also covers fallback strategies when the accelerator is unavailable at runtime.',
        'The appendix gives practical advice for maintaining hardware-software consistency across versions and for preserving audit artifacts.',
        'Finally, it discusses how to handle accelerator configuration changes without invalidating sealed pipeline manifests.',
    ]),
    ('Appendix C: Extended Notes', [
        'Hardware-accelerated pipelines require careful documentation of data formats and transfer boundaries to avoid silent errors.',
        'A manifest-driven design makes it possible to validate hardware contracts before the pipeline is deployed.',
        'In many systems the dominant latency cost is not the kernel itself, but the data movement between the CPU and accelerator.',
        'Explicit accelerator contracts also make it easier to migrate a pipeline between FPGA, GPU, and ASIC targets.',
        'The paper emphasizes that auditability is not optional when special-purpose hardware is part of the computation graph.',
        'Compiler diagnostics should highlight mismatches between stage capability requirements and the available hardware.',
    ]),
    ('Appendix D: Practical Considerations', [
        'Hardware-accelerated pipeline design must account for data alignment and memory layout as first-class concerns.',
        'When a stage is offloaded, the manifest should describe the accelerator’s supported precision, vector width, and endian conventions.',
        'Cache coherence and DMA scheduling are often the dominant cost in hybrid CPU/accelerator pipelines, so keep transfers explicit.',
        'Prefer explicit accelerator buffer ownership semantics rather than implicit shared memory to avoid invisible aliasing bugs.',
        'A good rule is to expose accelerator kernel preconditions in the pipeline source so the compiler can reject unsupported mappings early.',
        'Mixed-precision and quantized accelerators should be modeled with capability contracts that describe numeric ranges and saturation behavior.',
        'Power, thermal, and availability constraints belong in the manifest when runtime placement is not fixed at compile time.',
        'Use hardware fingerprints in the sealed artifact to prevent deploying a pipeline on mismatched accelerator revisions.',
        'Design accelerated pipeline stages to include graceful fallback paths for targets that lack the required accelerator features.',
        'For auditability, preserve the distinction between CPU-only and accelerator-backed stage implementations in the published artifact.',
    ]),
    ('Appendix E: Extended Observations', [
        'Hardware acceleration can improve performance dramatically, but it only remains useful when the pipeline semantics are still reviewable and deterministic.',
        'Observing the computation at accelerator boundaries is essential for diagnosing issues like silent data format mismatches.',
        'An accelerator-aware pipeline language places the responsibility for data movement planning on the compiler rather than on handwritten glue code.',
        'Sealing the pipeline manifest against hardware parameters turns deployment drift into a detectable verification failure.',
        'In heterogeneous pipelines, the most common failure mode is not a bad algorithm, but a mis-specified transfer contract.',
        'The appendix emphasizes that hardware acceleration should extend the pipeline model, not replace it with low-level device code.',
        'Designing for accelerator reuse means choosing stage granularity carefully so individual kernels remain portable across targets.',
        'Real hardware pipelines often require a separate validation pass for buffer lifetime and interconnect timing.',
        'The manifest-driven approach gives operators a way to inspect the effective hardware mapping before execution.',
        'A final observation: accelerator support is most valuable when it is expressed in the same declarative pipeline language used for the rest of the system.',
    ]),    ('Appendix F: Integration Checklist', [
        'Hardware pipeline integration should begin with a manifest-level compatibility checklist that covers data formats, clock domains, and memory layout.',
        'The checklist should also capture accelerator availability, fallback paths, and allowed precision modes.',
        'Including this checklist in the pipeline artifact improves both deployment safety and auditability.',
        'We describe how the compiler can generate validator stubs from the manifest to catch mismatches before deployment.',
        'The appendix includes practical recommendations for recording accelerator revisions and runtime hardware fingerprints.',
        'It also highlights the importance of verifying that all stage contracts remain consistent across accelerator and CPU paths.',
    ]),
    ('Appendix G: Validation Patterns', [
        'This appendix describes validation patterns for hardware-accelerated pipelines, including data integrity checks and transfer contract verification.',
        'We explain how to use pipeline manifests to enforce alignment, endian, and precision constraints at stage boundaries.',
        'The patterns also cover runtime validation of accelerator readiness, buffer ownership, and deterministic handoff semantics.',
        'A good validation pattern makes both the hardware and software execution graph reviewable to operators.',
        'We include a note on profiling accelerated pipelines and on reconciling observed throughput with manifest assumptions.',
        'These validation patterns are designed to reduce silent failures and to keep pipeline semantics visible in heterogeneous systems.',
    ]),    ('Appendix H: Hardware Compatibility Patterns', [
        'Compatibility patterns are important for pipelines that target multiple accelerator backends and revision families.',
        'This appendix describes how to encode compatibility modes, supported feature sets, and fallback behaviors in the manifest.',
        'We also cover patterns for graceful degradation when an accelerator is partially available or when a pipeline must run in CPU-only mode.',
        'The manifest can capture both mandatory and optional accelerator capabilities to support tiered deployment targets.',
        'A good compatibility pattern makes upgrade and rollback decisions safer by keeping hardware assumptions explicit.',
        'We also describe how to validate that data formats and memory alignments remain compatible across accelerator revisions.',
        'These patterns reduce the risk of silent failures when pipelines move between devices with similar but not identical hardware.',
        'The appendix closes with guidance on maintaining compatibility documentation as the hardware landscape evolves.',
    ]),
    ('Appendix I: Long-Lived Pipeline Maintenance', [
        'Long-lived hardware-accelerated pipelines require maintenance plans for firmware updates, accelerator firmware revisions, and performance drift.',
        'This appendix describes maintenance patterns that preserve pipeline semantics while allowing safe evolution over time.',
        'We cover manifest versioning, hardware fingerprinting, and compatibility testing procedures.',
        'The appendix also explains how to manage hybrid pipelines when the available accelerator set changes over a product lifecycle.',
        'A central idea is to keep pipeline and hardware contracts aligned so operators can safely update both software and accelerator binaries.',
        'We also discuss how to handle deprecating accelerator features while preserving older pipeline artifacts for reference.',
        'These maintenance patterns are especially useful for products deployed in the field with long support windows.',
        'The appendix helps teams treat hardware-accelerated pipelines as maintainable artifacts rather than one-off performance hacks.',
    ]),    ('Appendix J: Accelerator Deployment Reference', [
        'This appendix serves as a practical reference for deploying hardware-accelerated pipelines in real systems.',
        'It includes guidance on accelerator compatibility, manifest-driven deployment, and fallback path design.',
        'We also cover the role of hardware fingerprints and runtime validation checks in maintaining deployment integrity.',
        'The reference includes tips for managing different accelerator revisions and for protecting against silent data mismatches.',
        'We describe how to keep the pipeline shape visible while optimizing compute-heavy stages on specialized hardware.',
        'The appendix also emphasizes the importance of testing the end-to-end hybrid execution plan, not just the accelerator kernels.',
        'We provide advice for documenting the operational assumptions behind each accelerator mapping.',
        'The reference notes how to align hardware contracts with the pipeline manifest to simplify reviews.',
        'It also includes patterns for handling partial accelerator availability and graceful degradation.',
        'This appendix is intended to help engineering teams treat acceleration as an intentional, verifiable part of the pipeline.',
    ]),    ('Appendix K: Accelerator Field Guide', [
        'This field guide provides practical guidance for integrating accelerators into pipeline-first systems.',
        'It covers manifest-driven hardware selection, fallback planning, and compatibility validation.',
        'We explain how to structure accelerator stage annotations so they remain reviewable and maintainable.',
        'The guide also includes advice on documenting accelerator assumptions and hardware footprint limitations.',
        'A key recommendation is to keep data movement explicit and to avoid hidden copies between CPU and accelerator domains.',
        'The appendix describes how to verify accelerator contracts and to detect silent data mismatches early.',
        'We offer strategies for profiling hybrid pipelines and for translating those measurements back into manifest expectations.',
        'The field guide also covers the role of hardware fingerprinting and how to keep accelerator mappings reproducible.',
        'It includes advice for managing accelerator revisions and for safe migration between targets.',
        'The appendix provides patterns for balancing specialization with portability in pipeline designs.',
        'It also emphasizes the need for clear operational guidance when deploying accelerator-backed firmware.',
        'Finally, the guide argues that accelerator support should prolong the pipeline’s semantics rather than obscure them.',
    ]),    ('Appendix L: Accelerator Lifecycle Guide', [
        'This guide covers the lifecycle of accelerator-backed pipeline stages from development through maintenance.',
        'It explains how to coordinate hardware revisions, firmware updates, and pipeline manifest evolution.',
        'The guide includes patterns for regression testing accelerator paths after each hardware change.',
        'We also describe how to keep performance expectations aligned with actual accelerator behavior over time.',
        'A key recommendation is to version accelerator contracts separately from the pipeline source.',
        'This makes it possible to detect when a new accelerator model violates an existing pipeline guarantee.',
        'The appendix also covers how to manage fallback modes when an accelerator becomes unavailable.',
        'It includes advice for maintaining observability and diagnostics across CPU/accelerator boundaries.',
        'We discuss how to preserve auditability when accelerator mappings change between deployments.',
        'The guide also summarizes safe rollback procedures for hardware-assisted pipelines.',
        'It recommends keeping a small set of stable accelerator configurations for critical systems.',
        'Finally, the appendix emphasizes that pipeline semantics should remain the reference even as hardware changes.',
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
