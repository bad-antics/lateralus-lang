#!/usr/bin/env python3
"""Render 'Building a Bare-Metal OS' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "building-bare-metal-os.pdf"

render_paper(
    out_path=str(OUT),
    title="Building a Bare-Metal OS",
    subtitle="Step-by-step construction of Lateralus OS: from linker script to process scheduler",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "This paper is a construction guide for Lateralus OS: a minimal RISC-V "
        "operating system written entirely in Lateralus. It covers the full "
        "build from the linker script through to preemptive multitasking. "
        "Unlike tutorial-style introductions, this paper is structured around "
        "the decisions made during construction — why each component was designed "
        "the way it was, and what the alternatives were."
    ),
    sections=[
        ("1. What We Are Building", [
            "Lateralus OS is a monolithic kernel for RISC-V (RV64GC) that provides:",
            ("list", [
                "Interrupt-driven I/O on the UART, PLIC, and CLINT peripherals.",
                "Physical memory management via a buddy allocator.",
                "Virtual memory using Sv39 page tables.",
                "A preemptive round-robin scheduler.",
                "A minimal system call interface (read, write, fork, exec, exit, wait).",
            ]),
            "The kernel is approximately 8,000 lines of Lateralus. It boots on "
            "QEMU's <code>virt</code> machine and on the SiFive HiFive Unmatched "
            "development board.",
        ]),
        ("2. The Linker Script", [
            "The linker script defines the memory layout of the kernel binary. "
            "RISC-V kernels typically load at a high physical address (0x80200000 "
            "on QEMU's virt machine after OpenSBI loads):",
            ("code",
             "/* lateralus-os.ld */\n"
             "ENTRY(_start)\n"
             "SECTIONS {\n"
             "    . = 0x80200000;\n"
             "    .text   : { *(.text.boot) *(.text .text.*) }\n"
             "    .rodata : { *(.rodata .rodata.*) }\n"
             "    .data   : { *(.data .data.*) }\n"
             "    .bss    : { __bss_start = .; *(.bss .bss.*); __bss_end = . }\n"
             "    . = ALIGN(4096);\n"
             "    __kernel_end = .;\n"
             "}"),
            "The <code>.text.boot</code> section is the assembly entry point "
            "placed first; it initializes the stack and calls the Lateralus "
            "<code>_start</code> function.",
        ]),
        ("3. Boot Sequence", [
            "The kernel boot sequence has five steps:",
            ("code",
             "# Assembly entry (_start.S)\n"
             "1. Zero BSS segment (from __bss_start to __bss_end)\n"
             "2. Set stack pointer (sp = __stack_top)\n"
             "3. Set up trap vector (csrw mtvec, trap_vec)\n"
             "4. Call kmain (j kmain)\n\n"
             "# Lateralus kmain\n"
             "5. uart::init()          → enable UART interrupts\n"
             "6. mem::phys_init()      → initialize buddy allocator\n"
             "7. mem::virt_init()      → set up kernel page tables\n"
             "8. plic::init()          → configure interrupt controller\n"
             "9. sched::init_idle()    → create idle task\n"
             "10. sched::run()         → start scheduler (never returns)"),
        ]),
        ("4. Physical Memory Management", [
            "Physical memory is managed by a buddy allocator. The buddy system "
            "splits and merges power-of-two blocks, providing O(log n) allocation "
            "and deallocation:",
            ("code",
             "// Allocate 2^order contiguous pages\n"
             "fn phys_alloc(order: u8) -> Option<PhysAddr> {\n"
             "    for o in order..=MAX_ORDER {\n"
             "        if let Some(block) = free_lists[o].pop() {\n"
             "            split_down_to(block, o, order);\n"
             "            return Some(block);\n"
             "        }\n"
             "    }\n"
             "    None\n"
             "}"),
            "The allocator manages memory from <code>__kernel_end</code> to the "
            "top of physical RAM (read from the RISC-V Device Tree). Kernel "
            "data structures are allocated from the first 16 MB; everything "
            "above is available for user processes.",
        ]),
        ("5. Virtual Memory: Sv39 Page Tables", [
            "Lateralus OS uses RISC-V Sv39: 39-bit virtual addresses mapped via "
            "three-level page tables (each 4 KB, 512 entries). The kernel is "
            "mapped in the upper half of the address space (VA >= 0xFFFFFFC000000000):",
            ("code",
             "// Map kernel at high virtual address\n"
             "fn map_kernel() {\n"
             "    let root = page_alloc_zeroed();\n"
             "    // Gigapage identity map: VA == PA for kernel range\n"
             "    for gb in (0x80000000..kernel_end).step_by(GB) {\n"
             "        root.entries[high_vpn2(gb)] = PTE::leaf(\n"
             "            PhysAddr(gb), Perm::RWX | Perm::GLOBAL\n"
             "        );\n"
             "    }\n"
             "    csrw!(satp, SATP::sv39(root));\n"
             "    sfence_vma!();\n"
             "}"),
        ]),
        ("6. Trap Handling and the Timer", [
            "All RISC-V exceptions and interrupts go through the trap vector. "
            "The trap handler saves the register file into a <code>TrapFrame</code> "
            "and dispatches by cause code:",
            ("code",
             "fn handle_trap(frame: &mut TrapFrame) {\n"
             "    frame\n"
             "        |>  read_mcause\n"
             "        |>  classify_cause\n"
             "        |?> dispatch_interrupt_or_exception\n"
             "        |>  restore_frame\n"
             "}\n\n"
             "fn dispatch_interrupt_or_exception(cause: Cause) -> Result<(), TrapError> {\n"
             "    match cause {\n"
             "        Cause::TimerInterrupt => sched::tick(),\n"
             "        Cause::ExternalInterrupt => plic::handle(),\n"
             "        Cause::Syscall => syscall::dispatch(frame),\n"
             "        other => panic!(\"unhandled trap: {:?}\", other),\n"
             "    }\n"
             "}"),
        ]),
        ("7. The Preemptive Scheduler", [
            "The scheduler is a round-robin preemptive scheduler. Each timer "
            "tick (1ms) triggers a context switch if the current task's quantum "
            "has expired. Context saving/restoring is done in assembly:",
            ("code",
             "// Scheduler state\n"
             "static TASKS: SpinLock<VecDeque<Task>> = SpinLock::new(VecDeque::new());\n\n"
             "fn tick() {\n"
             "    let mut tasks = TASKS.lock();\n"
             "    let current = tasks.pop_front().unwrap();\n"
             "    tasks.push_back(current.save_context());\n"
             "    let next = tasks.front_mut().unwrap();\n"
             "    next.restore_context();   // resumes in assembly, never returns here\n"
             "}"),
        ]),
        ("8. Lessons and Next Steps", [
            "Building Lateralus OS taught us several things about the language itself:",
            ("list", [
                "The <code>unsafe</code> block requirement for MMIO and CSR access "
                "is valuable — it makes hardware-touching code easy to grep and audit.",
                "The pipeline model is a natural fit for trap dispatch: "
                "each stage is a pure transformation of the trap frame.",
                "The absence of a GC eliminates an entire class of kernel bugs "
                "(GC running at interrupt time) that are common in managed-language kernels.",
                "Formal verification of the page table mapping code is the most "
                "important next step — an incorrect mapping can lead to privilege "
                "escalation that is invisible to testing.",
            ]),
            "Lateralus OS v1.0 is available as open source and serves as the "
            "reference platform for Lateralus kernel development documentation.",
        ]),
    ],
)

print(f"wrote {OUT}")
