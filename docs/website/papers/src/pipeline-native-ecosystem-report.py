#!/usr/bin/env python3
"""Render 'The Pipeline-Native Ecosystem Report 2026' to PDF."""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "pipeline-native-ecosystem-report.pdf"

TITLE = "The Pipeline-Native Ecosystem Report"
SUBTITLE = "State of Lateralus &mdash; April 2026"
META = "bad-antics &middot; April 2026 &middot; Lateralus Language Foundation"
ABSTRACT = (
    "Lateralus's first anniversary finds the project at an inflection point: the compiler is "
    "stable, the toolchain is unified, the operating system is booting, and the public repository "
    "corpus has crossed the 77-project mark on the way to Linguist acceptance. This report sets "
    "out the full 2026 Q1/Q2 state of the project across five axes &mdash; language, runtime, "
    "tooling, OS, and community &mdash; and names the priorities for the next four quarters. "
    "It is intended as the annual-report-style document that new contributors, potential sponsors, "
    "and press contacts can read in fifteen minutes to understand where the project stands."
)

SECTIONS = [
    ("1. The Year in One Paragraph", [
        "Lateralus went from a design sketch in January 2025 to a shipping 1.5 release in April 2026. Along the way it picked up a full compiler (VM plus C and WASM backends), a self-hostable standard library, a complete editor integration (LSP, DAP, VS Code extension), a published paper corpus of 58 documents, a 77-repo public-GitHub footprint, and a companion operating system (LateralusOS) that boots to a graphical desktop on both QEMU and bare metal. Each of these is covered in detail below.",
    ]),
    ("2. Language", [
        "The language specification at 1.5 comprises:",
        ("list", [
            "<b>Expressions</b>: arithmetic, comparison, boolean, string interpolation, ternary, pipe, pipe-assign, spread.",
            "<b>Types</b>: int, float, bool, str, list[T], map[K,V], records with row polymorphism, function types, <code>Option</code>, <code>Result</code>, gradual <code>any</code>.",
            "<b>Declarations</b>: <code>let</code>, <code>let mut</code>, <code>const</code>, <code>fn</code>, <code>struct</code>, <code>enum</code>, <code>trait</code>, <code>impl</code>, <code>type</code> alias.",
            "<b>Control</b>: <code>if/else</code>, <code>match</code> with guards and patterns, <code>for in</code>, <code>while</code>, <code>guard else</code>, <code>where</code>.",
            "<b>Modules</b>: <code>import</code>, <code>from ... import</code>, <code>pub</code>, <code>module</code>.",
            "<b>Concurrency</b>: <code>async</code>/<code>await</code>, channels, <code>measure</code>/<code>probe</code>/<code>emit</code> observability blocks.",
            "<b>FFI</b>: <code>@foreign(\"c\")</code>, <code>@foreign(\"python\")</code>, <code>@foreign(\"wasm\")</code>.",
        ]),
        "The grammar fits in 420 lines of EBNF (see <code>docs/grammar.ebnf</code>) and the type-system-as-implemented fits in ~1100 lines of Python (<code>lateralus_lang/type_inference.py</code>).",
    ]),
    ("3. Runtime and Backends", [
        ("list", [
            "<b>Bytecode VM</b>: ~8,000 lines of Python, 850 tests green. Throughput on a 2021-era laptop: ~4 million instructions per second, ~15 MB/s for string-building workloads.",
            "<b>C backend</b>: emits portable C99 (hosted or freestanding). 10x speedup over the VM on representative benchmarks.",
            "<b>WebAssembly backend</b>: emits WAT/WASM; used by the online playground at <code>playground.lateralus.dev</code>.",
            "<b>Interpreter</b>: tree-walking interpreter, ~25% the speed of the VM, used for REPL and by the LSP for fast feedback on small scripts.",
        ]),
    ]),
    ("4. Tooling", [
        "Tools shipped:",
        ("list", [
            "<code>lateralus build|run|check|fmt|lint|test|repl|lsp|dap|c|wasm|info</code> &mdash; twelve subcommands, each fully implemented.",
            "<b>VS Code extension</b> (<code>vscode-lateralus</code>, 1.5.0) &mdash; syntax, LSP, DAP, commands, snippets. Installed via Marketplace or from local <code>.vsix</code>.",
            "<b>Documentation site</b> &mdash; built from <code>.ltlml</code> files in <code>docs/</code> via <code>scripts/build_docs.py</code>; deployed to <code>lateralus.dev</code>.",
            "<b>Paper corpus</b> &mdash; 58 PDFs at <code>lateralus.dev/papers/</code>, all in the canonical A4/Helvetica Lateralus house style.",
            "<b>Playground</b> &mdash; in-browser compiler+interpreter via WASM.",
        ]),
        "All tools consume the same AST (finally &mdash; that was the major 1.5 unification work). Editor-reported errors are byte-identical to <code>lateralus build</code> errors.",
    ]),
    ("5. LateralusOS", [
        "LateralusOS v0.1 boots on x86_64 (QEMU and physical hardware verified):",
        ("list", [
            "<b>Bootloader</b>: GRUB2 multiboot2; loader fits in 4 KB.",
            "<b>Kernel</b>: C + Lateralus-compiled modules; ~4 MB ELF.",
            "<b>Memory</b>: 4 GB flat-mapped 2 MB-page identity mapping; heap at 2 MB.",
            "<b>Interrupts</b>: IDT installed, PIC remapped, keyboard and mouse IRQs wired.",
            "<b>GUI</b>: 1024x768x32 linear framebuffer, double-buffered, compositor, cursor.",
            "<b>Shell</b>: serial-console parser; planned graphical shell in v0.2.",
        ]),
        "The OS builds reproducibly in under 10 seconds and boots to desktop in under 3 seconds on QEMU. The full build and boot is wrapped in <code>build_and_boot.sh</code> with <code>--iso</code>, <code>--test</code>, and <code>--gui</code> modes.",
    ]),
    ("6. Community", [
        ("list", [
            "<b>Public repos</b>: 77 on GitHub under <code>bad-antics</code> and community authors, all tagged <code>lateralus-lang</code>.",
            "<b>Code-search hits</b>: 1,372 for <code>extension:ltl</code>, 96 for topic <code>ltl</code>.",
            "<b>Contributors</b>: 22 people have filed issues or submitted patches over the 1.4 -&gt; 1.5 window.",
            "<b>Discord/Matrix</b>: active channels with ~150 members, median ~20 messages/day.",
            "<b>Blog</b>: 18 long-form posts at <code>lateralus.dev/blog/</code>, covering language design, implementation, and ecosystem.",
        ]),
    ]),
    ("7. Priorities for 2026 H2", [
        ("h3", "7.1 Language"),
        ("list", [
            "Higher-rank polymorphism (target: 1.6).",
            "Effect system design (target: 1.7).",
            "First-class modules.",
        ]),
        ("h3", "7.2 Tooling"),
        ("list", [
            "Incremental compilation in the language server.",
            "Package manager (<code>lateralus pkg add/publish</code>) with registry at <code>pkg.lateralus.dev</code>.",
            "AOT native-code backend (LLVM).",
        ]),
        ("h3", "7.3 LateralusOS"),
        ("list", [
            "v0.2: windowed shell, input focus, text widget.",
            "v0.3: filesystem (ext2 read, ramdisk write), loadable modules.",
            "v0.4: networking (ARP, IP, UDP, TCP minimal).",
        ]),
        ("h3", "7.4 Ecosystem"),
        ("list", [
            "Reach 200 public repos (Linguist adoption bar).",
            "Submit Linguist pull request Q3 2026.",
            "Launch package registry and first 20 community-published libraries.",
            "Host virtual community conference Q4 2026.",
        ]),
    ]),
    ("8. Funding and Sustainability", [
        "Lateralus remains an independent project with no corporate backer. Development time is volunteer, infrastructure cost is ~$25/month (domain, R2 storage, GitHub Pro). The economics are sustainable at the current pace; a donation path via GitHub Sponsors is live but not a dependency. We have declined two corporate sponsorship offers that were contingent on feature-direction influence; the project's pipeline-first design philosophy is not for sale.",
    ]),
    ("9. Acknowledgements", [
        "Thanks to the entire early-adopter community. Particular thanks to the three contributors who stress-tested the 1.5 gradual-inference branch for two months before merge: their bug reports directly improved the unifier, the diagnostic layer, and the formatter. Additional thanks to the operators who run Lateralus in production at small scale and send back real-world performance data; the C-backend monomorphization work on the 1.6 roadmap is driven entirely by their feedback.",
    ]),
    ("10. Close", [
        "Lateralus is a pipeline-first language with a unified toolchain, a companion kernel, and a growing public corpus. Year one closed with a 1.5 release that is stable, fast, and pleasant to write in. Year two begins with clear priorities: higher-rank types, AOT native compilation, a package registry, and the Linguist submission. We are confident in the trajectory and grateful for the reception the project has received so far. The work continues.",
    ]),
]

if __name__ == "__main__":
    render_paper(OUT, title=TITLE, subtitle=SUBTITLE, meta=META,
                 abstract=ABSTRACT, sections=SECTIONS)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
