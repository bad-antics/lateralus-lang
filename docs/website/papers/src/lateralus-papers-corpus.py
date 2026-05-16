#!/usr/bin/env python3
"""
Build the Lateralus Papers Corpus PDF.
Generates a cover/TOC document then merges all Lateralus papers in logical order.
"""
import tempfile
from pathlib import Path
from pypdf import PdfWriter, PdfReader
from _lateralus_template import render_paper

SRC  = Path(__file__).resolve().parent
PDF  = SRC.parent / "pdf"
OUT  = PDF / "lateralus-papers-corpus.pdf"

# Ordered list: (pdf_stem, category, one-line description)
PAPERS = [
    # ── Language Overview ─────────────────────────────────────────────────
    ("lateralus-pipeline-native-language",  "Language Overview",
     "Introduction to Lateralus: pipeline-native systems language"),
    ("lateralus-spec-v1.0",                 "Language Overview",
     "Language specification version 1.0 — initial normative grammar and semantics"),
    ("lateralus-language-spec-v3",          "Language Overview",
     "Full specification v3: grammar, ownership, effect types, module system"),
    ("lateralus-spec-v3.0",                 "Language Overview",
     "Formal edition: operational semantics, type soundness, pipeline calculus"),
    ("data-flow-syntax-survey",             "Language Overview",
     "Survey of pipeline/dataflow syntax across 12 programming languages"),
    ("lateralus-vs-elixir-pipes",           "Language Overview",
     "Head-to-head comparison: Lateralus |> vs Elixir |> on eight metrics"),

    # ── Pipeline Semantics ────────────────────────────────────────────────
    ("pipelines-are-not-sugar",             "Pipeline Semantics",
     "Why |> must be first-class, not syntactic sugar for function application"),
    ("higher-order-pipelines",              "Pipeline Semantics",
     "Pipelines as values: transformers, composition, and higher-order stages"),
    ("error-propagation-pipelines",         "Pipeline Semantics",
     "|?>, |!>, |~> operators: typing rules and error propagation strategies"),
    ("pipeline-semantics-algebraic",        "Pipeline Semantics",
     "14-law equational theory and rewriting system for the pipeline calculus"),
    ("pipelines-as-first-class-semantics",  "Pipeline Semantics",
     "Categorical denotational semantics: CCC, Kleisli categories, profunctors"),
    ("pipeline-calculus",                   "Pipeline Semantics",
     "The lambda_pipe core calculus: syntax, reduction rules, type soundness"),
    ("pipeline-calculus-category-theory",   "Pipeline Semantics",
     "Category-theoretic foundations: Arrows, Hughes composition, free monoids"),
    ("pipeline-native-design-rationale",    "Pipeline Semantics",
     "Design rationale for the pipeline-native model vs alternatives"),

    # ── Type System ───────────────────────────────────────────────────────
    ("structural-typing-without-tax",       "Type System",
     "Row polymorphism and open records without annotation overhead"),
    ("gradual-typing-lateralus-v15",        "Type System",
     "dyn type, consistency relation, and cast semantics for gradual typing"),
    ("type-system-v15-inference",           "Type System",
     "Effect types, lifetime inference, and bidirectional propagation"),
    ("type-inference-hindley-milner-v15",   "Type System",
     "Hindley-Milner inference algorithm extended for pipeline expressions"),
    ("pattern-matching-adts",               "Type System",
     "Algebraic data types, exhaustiveness checking, and guard expressions"),
    ("capability-based-security",           "Type System",
     "Capability types for memory and resource safety at compile time"),
    ("memory-safety-ownership",             "Type System",
     "Ownership model, borrow checker, and lifetime analysis"),

    # ── Compiler & Implementation ─────────────────────────────────────────
    ("zero-to-language",                    "Compiler",
     "Four-stage bootstrapping story and lessons learned"),
    ("bootstrapping-compiler-python",       "Compiler",
     "Stage 0: lexer, parser, and bytecode emitter in 2000 lines of Python"),
    ("from-lexer-to-language",              "Compiler",
     "Full front-end pipeline: lex→parse→resolve→type"),
    ("lexer-design-pipeline-first",         "Compiler",
     "Hand-written DFA, operator disambiguation, and tokenizer design"),
    ("error-messages-as-documentation",     "Compiler",
     "Four principles for compiler error messages as user documentation"),
    ("polyglot-bridge-internals",           "Compiler",
     "C/Python/Rust FFI without wrapper overhead: the polyglot bridge"),
    ("multi-target-compilation",            "Compiler",
     "RISC-V, x86-64, WASM, and C99 backends via shared LIR"),
    ("c-backend-transpiler-design",         "Compiler",
     "C99 transpiler design: mapping Lateralus semantics to portable C"),
    ("lateralus-bytecode-format",           "Compiler",
     "LBC v1 format: 32-bit instructions, NaN-boxing, constant table layout"),
    ("lateralus-bytecode-format-lbc",       "Compiler",
     "LBC deep dive: optimization hints, JIT annotations, debug info"),
    ("lateralus-module-system",             "Compiler",
     "Module system: visibility, packages, workspace manifest, and registry"),
    ("writing-a-repl",                      "Compiler",
     "PCU architecture, incremental type checking, pipeline display in REPL"),
    ("property-testing-compiler-pass",      "Compiler",
     "Property-based testing of compiler passes with generated programs"),

    # ── Standard Library & Ecosystem ─────────────────────────────────────
    ("stdlib-design-philosophy",            "Ecosystem",
     "Pipeline-first APIs, no hidden allocations, minimal surface area"),
    ("developer-ecosystem-engineering",     "Ecosystem",
     "Package registry, ltlup toolchain manager, LSP, and playground"),
    ("lateralus-060-release-notes",         "Ecosystem",
     "Release notes and migration guide for Lateralus 0.6.0"),
    ("lateralus-1.5-release-notes",         "Ecosystem",
     "Release notes and migration guide for Lateralus 1.5"),
    ("lateralus-extensions-distribution",   "Ecosystem",
     "Extension system: VS Code VSIX packaging and signed distribution"),
    ("satellite-ecosystem-engineering",     "Ecosystem",
     "Third-party tool and library ecosystem growth strategies"),
    ("pipeline-native-ecosystem-report",    "Ecosystem",
     "Annual report on the pipeline-native language ecosystem (2026)"),

    # ── Operating Systems ─────────────────────────────────────────────────
    ("bare-metal-os-high-level-language",   "OS & Systems",
     "Why Lateralus is viable for kernel development: ownership + no GC"),
    ("building-bare-metal-os",              "OS & Systems",
     "Step-by-step: linker script → buddy allocator → preemptive scheduler"),
    ("writing-risc-v-os",                   "OS & Systems",
     "Practical guide: startup, traps, memory, and process management"),
    ("lateralus-os-architecture",           "OS & Systems",
     "Microkernel design, capability system, and IPC pipeline"),
    ("lateralus-os-architecture-reference", "OS & Systems",
     "Boot sequence, trap handling, and system call table reference"),
    ("lateralus-os-v12-architecture",       "OS & Systems",
     "Lateralus OS v1.2 architectural changes and performance improvements"),
    ("lateralus-os-gui-framebuffer",        "OS & Systems",
     "Framebuffer graphics layer and GUI compositor for Lateralus OS"),
    ("smp-scheduling-risc-v",               "OS & Systems",
     "SMP scheduler for RISC-V: work stealing, IPI, and core affinity"),
    ("frisc-os-architecture",               "OS & Systems",
     "Educational RISC-V OS in Lateralus: 3300 LOC, full POSIX subset"),
    ("frisc-os-risc-v-education",           "OS & Systems",
     "FRISC OS as a teaching platform for systems programming"),

    # ── Formal Methods ────────────────────────────────────────────────────
    ("mesh-protocol-formal-spec",           "Formal Methods",
     "LTS, TLA+ safety/liveness, X25519+ChaCha20 encryption protocol"),
    ("zero-dependency-crypto-lateralus",    "Formal Methods",
     "SHA-256, X25519, ChaCha20-Poly1305, Ed25519 from scratch in Lateralus"),

    # ── Security & Penetration Testing ────────────────────────────────────
    ("nullsec-linux-security-distro",       "Security",
     "nullsec distro: pipeline tool interface and typed schemas"),
    ("nullsec-kernel-config",               "Security",
     "Kernel hardening config table: security vs capability tradeoffs"),
    ("nullsec-tool-protocol",               "Security",
     "CBOR-based typed inter-tool protocol and schema registry"),
    ("pipeline-native-pentest",             "Security",
     "Full penetration testing lifecycle as a typed Lateralus pipeline"),
    ("building-pentest-distro",             "Security",
     "ISO build system: squashfs assembly, GRUB/systemd-boot, CI release"),
    ("pipeline-security-analysis",          "Security",
     "Taint labels, trust boundary audit, and pipeline fuzzing"),
    ("pipeline-oriented-security-analysis", "Security",
     "Model checking, symbolic execution, and attack graph generation"),
    ("lateralus-pentester-product-overview","Security",
     "Product tiers, features, compliance templates, and integrations"),
    ("lateralus-pentester-architecture",    "Security",
     "Microservices, pipeline executor, evidence store, and audit log"),
    ("lateralus-pentester-v2-whatsnew",     "Security",
     "New features and breaking changes in Lateralus Pentester v2"),

    # ── Energy Systems ────────────────────────────────────────────────────
    ("lateralus-hho-electrolysis-off-grid", "Energy Systems",
     "HHO electrolysis fundamentals and off-grid sizing"),
    ("indefinite-off-grid-hho-fuel-cells",  "Energy Systems",
     "Closed-loop hydrogen generation and fuel cell storage system"),
    ("solar-hho-hybrid-pipeline-energy",    "Energy Systems",
     "Solar + HHO hybrid system with Lateralus pipeline control"),
    ("lateralus-energy-pipeline-protocol",  "Energy Systems",
     "LEPP: typed pipeline protocol for distributed energy components"),
]

# ── Generate cover + TOC via render_paper ─────────────────────────────────

def _toc_sections():
    """Build TOC sections grouped by category."""
    from collections import defaultdict
    by_cat = defaultdict(list)
    for i, (stem, cat, desc) in enumerate(PAPERS, 1):
        by_cat[cat].append(f"<b>{i:02d}.</b> {stem.replace('-', ' ').title()} — {desc}")

    sections = []
    sections.append(("About This Corpus", [
        "This volume collects all 67 research papers, technical specifications, "
        "design documents, and engineering guides produced by the Lateralus Language "
        "Research group through April 2026. Papers span eight thematic areas: "
        "language design, pipeline semantics, type theory, compiler implementation, "
        "operating systems, formal methods, security tooling, and off-grid energy "
        "systems. Each paper is reproduced in full following this introduction.",
        "The corpus is organized by thematic category. Within each category, papers "
        "are ordered from foundational to applied. Cross-references between papers "
        "use the paper number shown in this table of contents. All papers share the "
        "canonical Lateralus paper style: A4, Helvetica body, Courier code blocks.",
        "The Lateralus project is open source (github.com/bad-antics/lateralus-lang) "
        "and all papers are released under CC BY 4.0. The language itself is released "
        "under the MIT license. This corpus may be reproduced freely with attribution.",
    ]))

    for cat, items in by_cat.items():
        sections.append((f"Table of Contents — {cat}", [
            ("list", items),
        ]))

    return sections

with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
    cover_path = tf.name

render_paper(
    out_path=cover_path,
    title="The Lateralus Papers",
    subtitle="Collected Works 2026 — Language, Compiler, OS, Security, and Energy Systems",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research &middot; 67 Papers",
    abstract=(
        "A complete collection of research papers, technical specifications, "
        "engineering guides, and design documents from the Lateralus Language "
        "Research project. Lateralus is a pipeline-native systems programming "
        "language targeting RISC-V, x86-64, and WebAssembly. This corpus covers "
        "the full scope of the project: language design rationale, formal semantics, "
        "compiler implementation, operating system construction, security tooling "
        "(nullsec), and off-grid energy system control. Papers are reproduced in "
        "full in thematic order following the annotated table of contents."
    ),
    sections=_toc_sections(),
)

# ── Merge cover + all individual papers ───────────────────────────────────

writer = PdfWriter()

# Add cover/TOC
cover_reader = PdfReader(cover_path)
for page in cover_reader.pages:
    writer.add_page(page)

# Add each paper in order
missing = []
for stem, cat, desc in PAPERS:
    pdf_path = PDF / f"{stem}.pdf"
    if not pdf_path.exists():
        print(f"  SKIP (missing): {stem}.pdf")
        missing.append(stem)
        continue
    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        writer.add_page(page)
    print(f"  + {stem}.pdf ({len(reader.pages)} pages)")

writer.add_metadata({
    "/Title": "The Lateralus Papers: Collected Works 2026",
    "/Author": "bad-antics",
    "/Subject": "Lateralus Language Research — Complete corpus",
    "/Producer": "",
    "/Creator": "",
})

with open(OUT, "wb") as f:
    writer.write(f)

total = sum(1 for _ in PdfReader(str(OUT)).pages)
print(f"\nwrote {OUT}")
print(f"  total pages : {total}")
print(f"  papers merged: {len(PAPERS) - len(missing)}/{len(PAPERS)}")
if missing:
    print(f"  missing: {missing}")

import os
os.unlink(cover_path)
