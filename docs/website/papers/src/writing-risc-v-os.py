#!/usr/bin/env python3
"""Render 'Writing a RISC-V OS in Lateralus' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "writing-risc-v-os.pdf"

render_paper(
    out_path=str(OUT),
    title="Writing a RISC-V OS in Lateralus",
    subtitle="Practical guide: startup, trap handling, memory, and process management",
    meta="bad-antics &middot; March 2026 &middot; Lateralus Language Research",
    abstract=(
        "This paper is a practical guide to writing an operating system kernel for "
        "RISC-V in Lateralus. We walk through the four core implementation tasks: "
        "the startup sequence (reset vector to first user process), trap handling "
        "(exception and interrupt dispatch), memory management (physical allocator "
        "and page tables), and process management (context switching and scheduling). "
        "Code excerpts are drawn from the FRISC-OS implementation, which serves as "
        "a reference implementation. By the end of this guide, the reader should "
        "have a working kernel that can run a single user process."
    ),
    sections=[
        ("1. Prerequisites and Toolchain", [
            "To follow this guide, you need: the Lateralus compiler (v1.0+), "
            "a RISC-V cross-compilation target (<code>riscv64-linux-gnu</code>), "
            "QEMU for RISC-V (<code>qemu-system-riscv64</code>), and the "
            "<code>riscv64-unknown-elf</code> GNU binutils for linking.",
            ("code",
             "# Install the RISC-V target\n"
             "ltl toolchain add riscv64-linux-gnu\n\n"
             "# Verify\n"
             "ltl build --target riscv64-linux-gnu hello.lt\n"
             "qemu-system-riscv64 -machine virt -nographic -bios none \\\n"
             "    -kernel hello.elf\n"
             "# Output: Hello, RISC-V!"),
            "The <code>-bios none</code> flag skips the OpenSBI firmware and "
            "boots directly to the kernel entry point. This matches what we "
            "want for a bare-metal OS.",
        ]),
        ("2. The Startup Sequence", [
            "At reset, the RISC-V core executes from address 0x80000000 "
            "(QEMU virt machine). Our startup code is a small assembly stub "
            "that sets up the stack and calls <code>kernel_main</code>:",
            ("code",
             "// src/startup.s (linked first)\n"
             ".section .text.start\n"
             ".global _start\n"
             "_start:\n"
             "    la   sp, _stack_top      # set up stack pointer\n"
             "    call kernel_main          # call Lateralus entry point\n"
             "    j    .                   # halt if kernel_main returns"),
            "The linker script places the startup code at 0x80000000 and "
            "the stack at the top of the first 64 KiB of RAM:",
            ("code",
             "// kernel.ld (linker script excerpt)\n"
             "SECTIONS {\n"
             "    . = 0x80000000;\n"
             "    .text.start : { *(.text.start) }\n"
             "    .text       : { *(.text*) }\n"
             "    .data       : { *(.data*) }\n"
             "    .bss        : { *(.bss*) }\n"
             "    _stack_top  = 0x80010000;  /* 64 KiB for initial stack */\n"
             "}"),
        ]),
        ("3. Trap Handling", [
            "Exceptions and interrupts are vectored through the machine trap "
            "handler, set up by writing the handler address to the "
            "<code>mtvec</code> CSR. We set it in Lateralus using inline assembly:",
            ("code",
             "// Set the trap vector\n"
             "#[inline(never)]\n"
             "fn setup_trap_vector() {\n"
             "    unsafe {\n"
             "        asm!(\"la t0, trap_entry; csrw mtvec, t0\")\n"
             "    }\n"
             "}\n\n"
             "// Trap entry: saves registers, calls trap_dispatch\n"
             "#[no_mangle]\n"
             "#[naked]\n"
             "fn trap_entry() {\n"
             "    unsafe {\n"
             "        asm!(\n"
             "            // Save all registers to the current thread's trap frame\n"
             "            \"addi sp, sp, -256\",\n"
             "            \"sd   ra,  0(sp)\",\n"
             "            // ... (all 32 registers)\n"
             "            \"call trap_dispatch\",\n"
             "            \"ld   ra,  0(sp)\",\n"
             "            // ... restore\n"
             "            \"mret\"\n"
             "        )\n"
             "    }\n"
             "}"),
            "The <code>#[naked]</code> attribute tells the compiler to emit "
            "no prologue or epilogue for this function; the assembly is "
            "executed as-is.",
        ]),
        ("4. Physical Memory Allocator", [
            "We implement a page-frame allocator using a free list embedded "
            "in the free pages themselves. Each free 4 KiB page stores a "
            "pointer to the next free page at its base address:",
            ("code",
             "struct PageAllocator {\n"
             "    free_list: *mut u8,  // head of free list\n"
             "    total:     usize,\n"
             "    used:      usize,\n"
             "}\n\n"
             "fn alloc_page(a: &mut PageAllocator) -> Option<*mut u8> {\n"
             "    if a.free_list.is_null() { return None; }\n"
             "    let page = a.free_list;\n"
             "    a.free_list = unsafe { *(page as *const *mut u8) };\n"
             "    a.used += 1;\n"
             "    Some(page)\n"
             "}"),
        ]),
        ("5. Virtual Memory: The Sv39 Page Table", [
            "RISC-V Sv39 uses a three-level radix page table. Each level "
            "indexes 9 bits of the 39-bit virtual address. A page table "
            "entry (PTE) is 8 bytes:",
            ("code",
             "// 64-bit page table entry\n"
             "struct Pte(u64);\n\n"
             "impl Pte {\n"
             "    fn valid(&self)    -> bool { self.0 & 1 != 0 }\n"
             "    fn readable(&self) -> bool { self.0 & 2 != 0 }\n"
             "    fn writable(&self) -> bool { self.0 & 4 != 0 }\n"
             "    fn executable(&self) -> bool { self.0 & 8 != 0 }\n"
             "    fn user(&self)     -> bool { self.0 & 16 != 0 }\n"
             "    fn ppn(&self)      -> u64  { (self.0 >> 10) & 0xFFF_FFFF_FFFF }\n"
             "}\n\n"
             "fn map_page(root: &mut PageTable, va: usize, pa: usize, flags: u64) {\n"
             "    let vpn = [va >> 30, (va >> 21) & 0x1FF, (va >> 12) & 0x1FF];\n"
             "    // Walk three levels, allocating intermediate page tables as needed\n"
             "    // ...\n"
             "}"),
        ]),
        ("6. Context Switching", [
            "Context switching saves the current thread's registers to its "
            "kernel stack and restores the next thread's registers. We use "
            "the callee-saved RISC-V registers (s0-s11, ra, sp):",
            ("code",
             "// Context switch: save current, restore next\n"
             "#[naked]\n"
             "fn context_switch(current: *mut Context, next: *const Context) {\n"
             "    unsafe {\n"
             "        asm!(\n"
             "            // Save callee-saved registers to current context\n"
             "            \"sd ra,  0(a0)\",\n"
             "            \"sd sp,  8(a0)\",\n"
             "            \"sd s0, 16(a0)\",\n"
             "            // ... s1-s11\n"
             "            // Restore next context\n"
             "            \"ld ra,  0(a1)\",\n"
             "            \"ld sp,  8(a1)\",\n"
             "            \"ld s0, 16(a1)\",\n"
             "            // ... s1-s11\n"
             "            \"ret\"\n"
             "        )\n"
             "    }\n"
             "}"),
        ]),
        ("7. A Simple Round-Robin Scheduler", [
            "For a first working kernel, a round-robin scheduler is sufficient. "
            "We maintain a run queue of ready processes and switch to the "
            "next process on each timer interrupt:",
            ("code",
             "let mut run_queue: VecDeque<Process> = VecDeque::new();\n\n"
             "fn schedule() {\n"
             "    let current = run_queue.pop_front().unwrap();\n"
             "    if current.state == ProcessState::Running {\n"
             "        run_queue.push_back(current);\n"
             "    }\n"
             "    let next = run_queue.front_mut().unwrap();\n"
             "    next.state = ProcessState::Running;\n"
             "    context_switch(&mut current.context, &next.context);\n"
             "}"),
        ]),
        ("8. Running a User Process", [
            "To run a user process, we load its binary from the initrd, "
            "create a page table mapping its text and stack, and set up a "
            "trap frame that returns to user mode at the entry point:",
            ("code",
             "fn spawn_user_process(elf: &[u8]) -> Process {\n"
             "    let mut page_table = PageTable::new();\n"
             "    let entry = load_elf_into(&mut page_table, elf);\n"
             "    let stack = alloc_page(&mut ALLOCATOR).unwrap();\n"
             "    map_page(&mut page_table, USER_STACK_VA, stack as usize,\n"
             "             PTE_READ | PTE_WRITE | PTE_USER);\n"
             "    Process {\n"
             "        page_table,\n"
             "        trap_frame: TrapFrame {\n"
             "            pc:   entry,\n"
             "            sp:   USER_STACK_VA + PAGE_SIZE,\n"
             "            mode: MachineMode::User,\n"
             "            ..default()\n"
             "        },\n"
             "        state: ProcessState::Ready,\n"
             "    }\n"
             "}"),
            "With this in place, the kernel can run a simple user-mode "
            "program that makes system calls via <code>ecall</code>. The "
            "ecall trap handler reads <code>a7</code> (system call number) "
            "and dispatches to the appropriate handler.",
        ]),
    ],
)

print(f"wrote {OUT}")
