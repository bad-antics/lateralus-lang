#!/usr/bin/env python3
"""Render 'Bare-Metal OS in a High-Level Language' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "bare-metal-os-high-level-language.pdf"

render_paper(
    out_path=str(OUT),
    title="Bare-Metal OS in a High-Level Language",
    subtitle="Why Lateralus is viable for kernel development: ownership, no GC, and zero-cost abstractions",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "Conventional wisdom holds that operating system kernels must be written in C "
        "or assembly: high-level languages impose garbage collection pauses, abstraction "
        "overhead, or runtime dependencies that are incompatible with bare-metal "
        "execution. Lateralus challenges this assumption. Its ownership-based memory "
        "model provides C-level control without GC; its zero-cost abstractions compile "
        "to code equivalent to hand-written C; and its inline assembly support covers "
        "the 5-10% of kernel code that requires direct hardware access. This paper "
        "explains why Lateralus is viable for kernel development and compares it "
        "directly against C, Rust, and Ada/SPARK."
    ),
    sections=[
        ("1. The Kernel Development Requirements", [
            "A language suitable for kernel development must satisfy five requirements:",
            ("list", [
                "<b>No garbage collector</b>: GC pauses are incompatible with "
                "real-time interrupt handling.",
                "<b>No runtime</b>: the language runtime must be absent or "
                "optional; kernels are their own runtimes.",
                "<b>Direct hardware access</b>: memory-mapped I/O, inline "
                "assembly for CSR manipulation, pointer arithmetic.",
                "<b>Predictable performance</b>: no hidden allocations, no "
                "unexpected indirections, no nondeterministic behavior.",
                "<b>Safety guarantees</b>: the language should prevent "
                "common kernel bugs (use-after-free, data races) at compile time.",
            ]),
            "C satisfies 1-4 but not 5. Rust satisfies all five but its "
            "ergonomics for systems programming are sometimes laborious. "
            "Lateralus satisfies all five with higher-level abstractions "
            "than Rust and a syntax designed for pipeline-first code.",
        ]),
        ("2. No Garbage Collector", [
            "Lateralus uses ownership-based memory management: every value has "
            "exactly one owner, and memory is freed when the owner goes out of "
            "scope. There is no GC, no reference counting (unless the programmer "
            "explicitly uses <code>Rc&lt;T&gt;</code>), and no finalization pauses.",
            ("code",
             "// Memory is freed deterministically at scope exit\n"
             "fn process_packet(data: Vec<u8>) -> Result<(), Error> {\n"
             "    let frame = parse_ethernet(&data)?;  // data owned here\n"
             "    let ip_pkt = parse_ip(&frame)?;\n"
             "    route(ip_pkt)?;\n"
             "    // 'data' and 'frame' freed here, deterministically\n"
             "    Ok(())\n"
             "}"),
        ]),
        ("3. No Required Runtime", [
            "Lateralus programs can be compiled with <code>--no-std</code> to "
            "exclude the standard library and produce a bare-metal binary with "
            "no runtime dependencies. Only the core language (arithmetic, ownership, "
            "pattern matching, inline assembly) is available.",
            ("code",
             "// Bare-metal Lateralus kernel entry\n"
             "#![no_std]\n"
             "#![no_main]\n\n"
             "#[no_mangle]\n"
             "pub fn _start() -> ! {\n"
             "    uart::init();\n"
             "    mem::init();\n"
             "    loop { sched::run_once() }\n"
             "}"),
            "The <code>#![no_std]</code> attribute disables the standard library "
            "import. The <code>#![no_main]</code> attribute disables the "
            "default entry point; <code>_start</code> is the ELF entry "
            "defined in the linker script.",
        ]),
        ("4. Hardware Access: Inline Assembly and MMIO", [
            "Approximately 5-10% of kernel code requires direct hardware access. "
            "Lateralus provides two mechanisms: inline assembly for CPU instructions "
            "and typed wrappers for memory-mapped I/O.",
            ("code",
             "// Inline assembly: read the RISC-V time CSR\n"
             "fn rdtime() -> u64 {\n"
             "    let t: u64;\n"
             "    unsafe { asm!(\"csrr {0}, time\", out(reg) t) }\n"
             "    t\n"
             "}\n\n"
             "// MMIO: typed wrapper for a UART register block\n"
             "struct Uart16550 { base: *mut u32 }\n"
             "impl Uart16550 {\n"
             "    fn write_byte(&self, b: u8) {\n"
             "        unsafe { self.base.add(THR_OFFSET).write_volatile(b as u32) }\n"
             "    }\n"
             "}"),
        ]),
        ("5. Zero-Cost Pipeline Abstractions", [
            "Kernel code often has complex control flow: interrupt routing, "
            "syscall dispatch, network stack processing. Lateralus pipelines "
            "express this clearly without overhead:",
            ("code",
             "// Syscall dispatch as a pipeline — compiles to a jump table\n"
             "fn handle_syscall(frame: &TrapFrame) -> SyscallResult {\n"
             "    frame\n"
             "        |>  extract_syscall_number\n"
             "        |>  validate_arguments\n"
             "        |?> dispatch_to_handler\n"
             "        |>  return_to_user\n"
             "}"),
            "The compiler emits a jump table for the dispatch stage when "
            "it can enumerate the cases statically. There is no function "
            "call overhead for the pipeline: all stages are inlined into "
            "the dispatch function.",
        ]),
        ("6. Comparison with C, Rust, and Ada/SPARK", [
            ("code",
             "Property              Lateralus   C      Rust    Ada/SPARK\n"
             "--------------------------------------------------------------\n"
             "No GC                 Yes         Yes    Yes     Yes\n"
             "No required runtime   Yes         Yes    Yes     Yes\n"
             "MMIO support          Yes         Yes    Yes     Yes\n"
             "Inline assembly       Yes         Yes    Yes     Limited\n"
             "Memory safety (CT)    Yes         No     Yes     Partial\n"
             "Data race freedom     Yes         No     Yes     No\n"
             "Formal verification   Planned     No     Partial Yes\n"
             "Pipeline model        Yes         No     No      No"),
            "Lateralus's advantages over C: memory and data-race safety. "
            "Over Rust: the pipeline model reduces boilerplate for data-"
            "flow-heavy kernel code. Over Ada/SPARK: full formal verification "
            "is planned but not yet available; SPARK leads here.",
        ]),
        ("7. Limitations", [
            "Current limitations of Lateralus for kernel development:",
            ("list", [
                "No Lateralus-native AArch64 backend (x86-64 and RISC-V only). "
                "AArch64 support is on the roadmap for v2.0.",
                "No built-in support for ACPI parsing or PCIe enumeration; "
                "these are available via C library bindings through the "
                "polyglot bridge.",
                "The async pipeline model requires a runtime scheduler; for "
                "kernel interrupt handlers (which are not async), only the "
                "total and error variants can be used.",
            ]),
        ]),
        ("8. Conclusion", [
            "Lateralus is viable for kernel development today for RISC-V and "
            "x86-64 targets. The combination of ownership-based memory management, "
            "zero-cost pipeline abstractions, and inline assembly support covers "
            "the full range of kernel programming requirements. Lateralus OS "
            "is proof by construction: a working RISC-V kernel written entirely "
            "in Lateralus.",
        ]),
    ],
)

print(f"wrote {OUT}")
