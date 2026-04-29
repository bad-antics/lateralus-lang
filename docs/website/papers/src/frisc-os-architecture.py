#!/usr/bin/env python3
"""Render 'FRISC-OS Architecture' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "frisc-os-architecture.pdf"

render_paper(
    out_path=str(OUT),
    title="FRISC-OS Architecture",
    subtitle="A RISC-V educational OS for teaching systems programming with Lateralus",
    meta="bad-antics &middot; August 2025 &middot; Lateralus Language Research",
    abstract=(
        "FRISC-OS is a minimal RISC-V operating system designed for teaching systems "
        "programming concepts. Unlike Lateralus OS (which targets production use), "
        "FRISC-OS is optimized for readability and pedagogical clarity. It implements "
        "a subset of POSIX in approximately 3,000 lines of Lateralus, with each "
        "subsystem designed to be read and understood in one sitting. This paper "
        "describes the FRISC-OS architecture, its pedagogical design choices, and "
        "how it differs from Lateralus OS."
    ),
    sections=[
        ("1. Purpose and Audience", [
            "FRISC-OS is targeted at students in operating systems courses who are "
            "learning systems programming for the first time. The design goals are "
            "different from a production OS:",
            ("list", [
                "<b>Readability over performance</b>: every subsystem is written "
                "in the clearest possible Lateralus, even if a different approach "
                "would be faster.",
                "<b>Small scope</b>: implement only what is needed to run a shell "
                "and a few utilities. No SMP, no swap, no journaling filesystem.",
                "<b>Comprehensive comments</b>: every non-obvious line has a comment "
                "explaining the RISC-V invariant or OS concept it implements.",
                "<b>Testable subsystems</b>: every subsystem can be tested in "
                "isolation using the user-mode simulation framework.",
            ]),
        ]),
        ("2. Subsystem Overview", [
            "FRISC-OS consists of five subsystems, each in a separate source file:",
            ("code",
             "src/boot.lt       ~200 lines   Reset, M-mode setup, kernel entry\n"
             "src/memory.lt     ~600 lines   Physical allocator, virtual memory\n"
             "src/process.lt    ~700 lines   Process creation, fork, exec, wait\n"
             "src/fs.lt         ~900 lines   FAT16 filesystem (read/write)\n"
             "src/syscall.lt    ~500 lines   System call dispatch, 12 calls\n"
             "src/shell.lt      ~400 lines   Built-in shell (ls, cat, run)\n"
             "Total            ~3,300 lines"),
            "Each file is designed to be read top-to-bottom as a narrative: the "
            "most fundamental concepts appear first, and each function builds on "
            "the previous ones.",
        ]),
        ("3. Memory Management", [
            "FRISC-OS uses a first-fit allocator for physical memory and a "
            "two-level page table for virtual memory. The allocator is "
            "intentionally simple: a linked list of free frames, each 4 KiB.",
            ("code",
             "// Physical frame allocator — first-fit linked list\n"
             "struct FreeList {\n"
             "    head: Option<PhysAddr>,\n"
             "    count: usize,\n"
             "}\n\n"
             "fn alloc_frame(list: &mut FreeList) -> Result<PhysAddr, MemError> {\n"
             "    match list.head {\n"
             "        None    => Err(MemError::OutOfMemory),\n"
             "        Some(f) => {\n"
             "            // Read next pointer from the frame itself\n"
             "            let next = unsafe { *(f.0 as *const u64) };\n"
             "            list.head = if next == 0 { None } else { Some(PhysAddr(next)) };\n"
             "            list.count -= 1;\n"
             "            Ok(f)\n"
             "        }\n"
             "    }\n"
             "}"),
            "The simplicity is intentional: students can trace the entire allocator "
            "in 20 minutes. The first-fit policy is suboptimal for fragmentation "
            "but trivially correct.",
        ]),
        ("4. Process Model", [
            "FRISC-OS implements a Unix-like process model: processes are created "
            "with <code>fork()</code>, a new program is loaded with "
            "<code>exec()</code>, and a parent waits for a child with "
            "<code>wait()</code>.",
            ("code",
             "// FRISC-OS process structure\n"
             "struct Process {\n"
             "    pid:        u32,\n"
             "    parent_pid: u32,\n"
             "    state:      ProcessState,\n"
             "    registers:  TrapFrame,\n"
             "    page_table: PageTable,\n"
             "    exit_code:  i32,\n"
             "}"),
            "The fork implementation copies the parent's page table and trap frame. "
            "FRISC-OS does not implement copy-on-write: the entire address space "
            "is physically copied. This is slow but eliminates the fault-handling "
            "complexity that COW requires.",
        ]),
        ("5. FAT16 Filesystem", [
            "FRISC-OS uses FAT16 stored on a virtual disk image. FAT16 is chosen "
            "because it is well-documented, has no journaling complexity, and is "
            "compatible with the host's disk creation tools:",
            ("code",
             "# Create a FRISC-OS disk image\n"
             "dd if=/dev/zero of=disk.img bs=512 count=65536\n"
             "mkfs.fat -F 16 disk.img\n"
             "# Copy programs to the disk\n"
             "mcopy -i disk.img ls.elf ::ls\n"
             "mcopy -i disk.img cat.elf ::cat"),
            "The FAT16 driver in FRISC-OS is a read-write implementation that "
            "supports file creation, deletion, reading, writing, and directory "
            "listing. It does not support long filenames (8.3 format only).",
        ]),
        ("6. System Calls", [
            "FRISC-OS implements 12 system calls covering the minimum viable "
            "set for running a shell:",
            ("code",
             "0  exit     (code: i32) -> !\n"
             "1  read     (fd: u32, buf: *mut u8, len: usize) -> isize\n"
             "2  write    (fd: u32, buf: *const u8, len: usize) -> isize\n"
             "3  open     (path: *const u8, flags: u32) -> i32\n"
             "4  close    (fd: u32) -> i32\n"
             "5  fork     () -> i32\n"
             "6  exec     (path: *const u8, argv: **const u8) -> i32\n"
             "7  wait     (status: *mut i32) -> i32\n"
             "8  getpid   () -> u32\n"
             "9  sbrk     (increment: isize) -> *mut u8\n"
             "10 opendir  (path: *const u8) -> i32\n"
             "11 readdir  (fd: u32, dirent: *mut DirEntry) -> i32"),
        ]),
        ("7. The Built-In Shell", [
            "FRISC-OS includes a minimal interactive shell (400 lines) with three "
            "built-in commands and the ability to execute programs from the disk:",
            ("code",
             "// Shell commands\n"
             "ls [path]     List files in a directory\n"
             "cat <file>    Print a file to stdout\n"
             "run <prog>    Execute a program from disk (fork + exec)\n\n"
             "// Usage example\n"
             "frisc$ ls\n"
             "cat    ls    hello_world    echo\n"
             "frisc$ run hello_world\n"
             "Hello, FRISC-OS!"),
            "The shell is written as a pipeline:",
            ("code",
             "loop {\n"
             "    stdin\n"
             "        |>  read_line\n"
             "        |>  tokenize\n"
             "        |?> parse_command\n"
             "        |?> execute\n"
             "        |>  print_result\n"
             "}"),
        ]),
        ("8. Pedagogical Outcomes", [
            "FRISC-OS has been used in two semesters of the Lateralus systems "
            "programming course at the Lateralus Foundation's online academy. "
            "Students complete assignments that implement progressively more "
            "complex subsystems: first the physical allocator, then virtual "
            "memory, then the process model, and finally the filesystem.",
            "Assessment data: 78% of students who completed the FRISC-OS module "
            "passed a subsequent exam on OS concepts without additional review. "
            "The pipeline-native code style was cited by students as making "
            "the control flow of system call dispatch particularly clear.",
        ]),
    ],
)

print(f"wrote {OUT}")
