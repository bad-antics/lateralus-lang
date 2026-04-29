#!/usr/bin/env python3
"""Render 'Lateralus OS Architecture Reference' (extended) in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-os-architecture-reference.pdf"

render_paper(
    out_path=str(OUT),
    title="Lateralus OS: Architecture Reference",
    subtitle="Extended reference: boot sequence, trap handling, driver model, and system call table",
    meta="bad-antics &middot; July 2025 &middot; Lateralus Language Research",
    abstract=(
        "This document is an extended reference for Lateralus OS internals. It covers "
        "topics not addressed in the architecture overview: the boot sequence from reset "
        "vector to user shell, trap and interrupt handling, the userspace driver model, "
        "the complete system call table, and the kernel build system. It is intended "
        "as a reference for kernel contributors and driver authors."
    ),
    sections=[
        ("1. Boot Sequence", [
            "On reset, the RISC-V core begins execution at address 0x1000 (SiFive "
            "boot ROM) or at the DRAM base depending on the board. The Lateralus OS "
            "boot sequence has five stages:",
            ("list", [
                "<b>Stage 0 — ROM bootstrap</b>: the board ROM initializes DDR and "
                "loads the first-stage bootloader from flash.",
                "<b>Stage 1 — First-stage bootloader (fsbl)</b>: initializes the "
                "UART, sets up a minimal stack, and loads the kernel ELF from the "
                "storage medium.",
                "<b>Stage 2 — Kernel entry</b>: sets up the machine trap vector, "
                "switches from M-mode to S-mode, and calls <code>kernel_main()</code>.",
                "<b>Stage 3 — Kernel initialization</b>: initializes the physical "
                "memory allocator, the virtual address space, the capability table, "
                "the scheduler, and the IPC subsystem.",
                "<b>Stage 4 — Init process</b>: the kernel spawns the init process "
                "from the initrd, which in turn starts the device driver servers and "
                "the shell.",
            ]),
            ("code",
             "// Kernel entry point (Lateralus source)\n"
             "#[no_mangle]\n"
             "pub fn kernel_main(dtb_ptr: *const u8) {\n"
             "    let dt = DeviceTree::parse(dtb_ptr)?;\n"
             "    mem::init(&dt);\n"
             "    cap::init();\n"
             "    sched::init(&dt);\n"
             "    ipc::init();\n"
             "    drivers::probe(&dt);\n"
             "    init::spawn();\n"
             "    sched::run_forever();\n"
             "}"),
        ]),
        ("2. Trap and Interrupt Handling", [
            "RISC-V traps fall into two categories: synchronous exceptions (page "
            "faults, illegal instructions, system calls via the <code>ecall</code> "
            "instruction) and asynchronous interrupts (timer, external, software).",
            "The kernel sets the machine trap vector to a single entry point "
            "<code>trap_entry</code> written in assembly. It saves all registers "
            "to the thread's trap frame and calls <code>trap_dispatch()</code>:",
            ("code",
             "// Trap dispatch pipeline\n"
             "fn trap_dispatch(frame: &mut TrapFrame) {\n"
             "    let cause = frame.mcause;\n"
             "    match cause.interrupt {\n"
             "        true  => handle_interrupt(cause.code, frame),\n"
             "        false => handle_exception(cause.code, frame),\n"
             "    }\n"
             "}\n\n"
             "fn handle_exception(code: u64, frame: &mut TrapFrame) {\n"
             "    let result = frame\n"
             "        |> classify_exception(code)\n"
             "        |?> check_user_permission\n"
             "        |?> dispatch_to_handler;\n"
             "    match result {\n"
             "        Ok(()) => return,\n"
             "        Err(e) => signal_process(frame.pid, e),\n"
             "    }\n"
             "}"),
        ]),
        ("3. Timer and Clock", [
            "The RISC-V time CSR (<code>mtime</code>) is a monotonically increasing "
            "64-bit counter driven by the platform clock. The kernel programs the "
            "timer comparator (<code>mtimecmp</code>) to fire at the next scheduling "
            "quantum boundary.",
            "The scheduler quantum is 1 ms for interactive threads and 10 ms for "
            "batch threads. Real-time threads specify their own deadline; the "
            "scheduler programs the timer comparator to the earliest deadline "
            "among runnable RT threads.",
            ("code",
             "// Timer interrupt handler\n"
             "fn handle_timer_interrupt() {\n"
             "    let now = time::rdtime();\n"
             "    sched::tick(now);\n"
             "    let next_quantum = sched::next_deadline();\n"
             "    clint::set_mtimecmp(next_quantum);\n"
             "}"),
        ]),
        ("4. Userspace Driver Model", [
            "Lateralus OS follows the L4 tradition of userspace drivers: device "
            "drivers run in userspace processes with capability tokens for their "
            "device MMIO regions and interrupt lines. The kernel routes interrupts "
            "to the registered driver process via an IPC message.",
            ("code",
             "// Driver registration\n"
             "fn register_driver(irq: IrqCap, mmio: MemMapCap) -> Result<DriverHandle, SysError>\n\n"
             "// Interrupt notification to driver (kernel calls this)\n"
             "fn irq_notify(handle: DriverHandle, irq_number: u32)"),
            "A driver is a Lateralus userspace program that registers for one or "
            "more interrupt lines and memory-mapped IO regions, then processes "
            "interrupt notifications in a pipeline:",
            ("code",
             "// Example: network driver main loop\n"
             "loop {\n"
             "    let irq = ipc::recv_irq()?\n"
             "    irq\n"
             "        |>  read_dma_ring\n"
             "        |>  process_received_packets\n"
             "        |>  forward_to_network_stack\n"
             "        |>  acknowledge_irq\n"
             "}"),
        ]),
        ("5. System Call Table", [
            "The complete Lateralus OS system call table (v1.0):",
            ("code",
             "syscall_nr  Name               Signature\n"
             "-------------------------------------------\n"
             "0           sys_exit           (code: i32) -> !\n"
             "1           sys_read           (cap: FileReadCap, buf: *mut u8, len: usize) -> isize\n"
             "2           sys_write          (cap: FileWriteCap, buf: *const u8, len: usize) -> isize\n"
             "3           sys_mem_map        (cap: MemMapCap, sz: usize, fl: u32) -> *mut u8\n"
             "4           sys_mem_unmap      (addr: *mut u8, sz: usize) -> i32\n"
             "5           sys_thread_create  (fn: usize, stack: usize) -> ThreadId\n"
             "6           sys_thread_exit    (code: i32) -> !\n"
             "7           sys_ipc_send       (cap: IpcCap, msg: *const u8, len: usize) -> i32\n"
             "8           sys_ipc_recv       (cap: IpcCap, buf: *mut u8, len: usize) -> isize\n"
             "9           sys_cap_delegate   (cap: AnyCap, to: ThreadId) -> CapId\n"
             "10          sys_cap_revoke     (cap_id: CapId) -> i32\n"
             "11          sys_irq_register   (irq: u32, cap: IpcCap) -> i32\n"
             "12          sys_rdtime         () -> u64"),
        ]),
        ("6. Virtual Memory Layout", [
            "Each process's 64-bit virtual address space is divided into fixed "
            "regions:",
            ("code",
             "0x0000_0000_0000_0000 - 0x0000_FFFF_FFFF_FFFF  User space (128 TiB)\n"
             "  0x0000_0000_1000_0000  Executable and data (text, data, bss)\n"
             "  0x0000_7FFF_E000_0000  Stack (grows down, 8 MiB by default)\n"
             "  0x0000_7FFF_F000_0000  Heap (grows up, mmap region)\n"
             "0xFFFF_0000_0000_0000 - 0xFFFF_FFFF_FFFF_FFFF  Kernel space (64 TiB)\n"
             "  0xFFFF_C000_0000_0000  Kernel text and data\n"
             "  0xFFFF_D000_0000_0000  Direct physical memory map\n"
             "  0xFFFF_E000_0000_0000  Kernel heap (vmalloc region)"),
            "The kernel address space is mapped in every process's page table but "
            "is not accessible from user mode (RISC-V page table PMP entries "
            "enforce this).",
        ]),
        ("7. Build System", [
            "Lateralus OS is built with the Lateralus build tool (<code>ltl build</code>) "
            "using a workspace manifest. The kernel, each driver, and the init "
            "process are separate packages in the workspace.",
            ("code",
             "# Build the OS image for RISC-V QEMU\n"
             "ltl build --target riscv64-linux-gnu --release kernel\n"
             "ltl package os-image --kernel kernel.elf --initrd drivers/\n\n"
             "# Run in QEMU\n"
             "qemu-system-riscv64 -machine virt -bios none \\\n"
             "    -kernel os-image.bin -nographic -m 512M"),
            "The build produces a flat binary image with the kernel ELF and the "
            "initrd (containing driver binaries) concatenated. QEMU loads the "
            "combined image at the DRAM base and begins execution.",
        ]),
        ("8. Testing Infrastructure", [
            "The kernel test suite runs in three environments: QEMU (for full "
            "integration tests), a Lateralus user-mode simulation (for unit "
            "tests of individual subsystems without hardware), and hardware "
            "(nightly on a SiFive HiFive Unmatched board).",
            ("code",
             "# Run kernel unit tests in user-mode simulation\n"
             "ltl test --features=user-mode-sim kernel\n\n"
             "# Run integration tests in QEMU\n"
             "ltl test --target riscv64-linux-gnu --qemu kernel\n\n"
             "# Check for memory safety violations (address sanitizer)\n"
             "ltl build --sanitize=address --target riscv64-linux-gnu kernel"),
            "The user-mode simulation compiles the kernel as a Lateralus program "
            "that replaces hardware operations with in-process simulations. This "
            "allows the full kernel test suite to run on any platform that "
            "supports the Lateralus compiler, including the CI server.",
        ]),
    ],
)

print(f"wrote {OUT}")
