#!/usr/bin/env python3
"""Render 'Lateralus v0.6.0 Release Notes' in the canonical Lateralus style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-060-release-notes.pdf"

render_paper(
    out_path=str(OUT),
    title="Lateralus v0.6.0 Release Notes",
    subtitle="The Capability Release: effects, borrow checker, faster codegen",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "Lateralus v0.6.0 is the largest release since the self-hosting milestone. It introduces a "
        "first-class <b>capability and effect system</b>, a refined <b>borrow checker</b> with "
        "region-polymorphic inference, an overhauled <b>native backend</b> with a 1.8x median "
        "compile-time improvement, and expanded standard library coverage for cryptography, async "
        "I/O, and structured concurrency. This document summarizes the user-visible changes, "
        "migration guidance for v0.5 codebases, and the design rationale behind the capability "
        "subsystem that now underpins both the compiler and LateralusOS v1.2."
    ),
    sections=[
        ("1. Headline Changes", [
            "Capabilities are now a language-level primitive. A function may declare required capabilities in its signature (for example, <code>fn read_file(p: Path) with Fs.Read -&gt; Result&lt;Bytes&gt;</code>), and the compiler statically enforces that callers hold those capabilities. This closes a long-standing soundness gap between library-level authority and the host operating system.",
            "The borrow checker now performs <b>region-polymorphic inference</b>: most explicit lifetime annotations in v0.5 code can be removed, and a new diagnostic surface explains borrow failures in terms of user-named regions rather than internal tokens.",
            "Codegen: the native backend replaces the legacy tree-walker with a proper SSA IR and linear-scan register allocator. Release-mode binaries are on average 22% smaller and 14% faster on the standard benchmark suite; compile times drop 42% on cold cache.",
            ("list", [
                "New: <code>std.effect</code>, <code>std.capability</code>, <code>std.async.v2</code>, <code>std.crypto.aead</code>.",
                "New: <code>ltlc --emit=mir</code> dumps the mid-level IR used by the new backend.",
                "Removed: deprecated <code>std.legacy_io</code> (use <code>std.io</code>).",
                "Stabilized: <code>std.structured.Scope</code>, <code>std.channel.bounded</code>.",
            ]),
        ]),
        ("2. Capability and Effect System", [
            "The effect system is <i>row-polymorphic</i> and <i>algebraic</i>. An effect row <code>{Fs.Read, Net.Connect | rho}</code> represents a set of required capabilities plus a polymorphic tail. Handlers may discharge effects in the style of Koka or Eff.",
            ("code",
             "fn copy(src: Path, dst: Path) with Fs.Read + Fs.Write -> Result<()> {\n"
             "    let bytes = read_file(src)?\n"
             "    write_file(dst, bytes)\n"
             "}\n\n"
             "with_capabilities([Fs.Read, Fs.Write], || copy(a, b))"),
            "Capabilities are unforgeable values: they cannot be constructed by user code, only granted by the runtime or delegated from an existing capability. This provides the foundation for the sandboxed execution model in LateralusOS v1.2.",
        ]),
        ("3. Borrow Checker Improvements", [
            "The v0.5 checker required explicit lifetime parameters on most APIs that returned references. v0.6.0 introduces <b>region-polymorphic inference</b>, which infers a principal region scheme per function and elaborates user-facing diagnostics in terms of source locations rather than internal variables.",
            "We have benchmarked the inference on every crate in the ecosystem registry (4,312 crates, 1.1M LOC). 87% of user-written lifetime annotations in v0.5 are now redundant and elided by the checker; 3,921 crates compile unchanged with no explicit lifetimes.",
            ("h3", "3.1 New Diagnostics"),
            "Borrow-checking errors now include a <i>narrative</i>: a numbered sequence of events (\"you borrowed <code>x</code> here\", \"you moved <code>x</code> here\", \"you used the borrow here\") with color-coded source spans. This was directly inspired by Rust's NLL diagnostics and user testing showed a 34% reduction in time-to-fix for borrow errors.",
        ]),
        ("4. Backend and Performance", [
            "The native backend was rewritten around an SSA-form mid-level IR (MIR). Passes implemented in v0.6.0: <b>mem2reg</b>, <b>GVN</b>, <b>dead-code elimination</b>, <b>inliner with cost model</b>, <b>loop-invariant code motion</b>, and a <b>linear-scan register allocator</b> targeting x86_64, aarch64, and RISC-V.",
            ("code",
             "$ ltlc --release build\n"
             "   compiled 412 modules in 8.3s  (v0.5.0: 14.2s)\n"
             "   output: target/release/app  (v0.5.0: 6.1MB, v0.6.0: 4.7MB)"),
            "On the standard benchmark suite (SPECLike, the TechEmpower ports, and the compiler's own self-compile), v0.6.0 is 14% faster on the geometric mean and never slower by more than 2% on any single benchmark.",
        ]),
        ("5. Standard Library", [
            ("list", [
                "<code>std.async.v2</code>: structured concurrency with capability-scoped nurseries; cancellation is now cooperative and deterministic.",
                "<code>std.crypto.aead</code>: AES-GCM, ChaCha20-Poly1305, XChaCha20-Poly1305. All constant-time; audited against RFC test vectors.",
                "<code>std.net.quic</code>: experimental QUIC transport (behind <code>--features quic</code>).",
                "<code>std.json</code>: zero-copy parser, 2.1x faster than v0.5.",
            ]),
        ]),
        ("6. Migration from v0.5", [
            "Most v0.5 code compiles under v0.6.0 without modification. The two common break cases are:",
            ("list", [
                "Functions that perform I/O now require an explicit capability in their signature. The migration tool <code>ltlc migrate --add-caps</code> inserts the minimal capability set inferred from the function body.",
                "<code>std.legacy_io</code> has been removed; <code>ltlc migrate --rewrite-io</code> replaces calls with the <code>std.io</code> equivalents.",
            ]),
            "A full migration of the 1.1M-LOC ecosystem registry completed in 34 minutes of CI time, with 99.7% of crates building unchanged after the automated migration.",
        ]),
        ("7. Acknowledgements", [
            "This release reflects contributions from the Lateralus core team and from GRUG affiliates including Miguel Automate, sleepthegod, and domo. The capability-system design drew heavily on prior work in Koka, Links, and seL4.",
        ]),
    ],
)
print("wrote", OUT)
