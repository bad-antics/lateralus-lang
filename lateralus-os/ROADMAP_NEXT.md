# LateralusOS Expansion Plan — v0.2 → v1.0

> **Status (April 2026):** v0.1 boots in QEMU/KVM with Multiboot2, pages 4 GB
> identity-mapped, initializes a framebuffer GUI with mouse cursor & desktop
> background, and compiles via `nasm + gcc -ffreestanding`.
>
> **This document is the honest plan** for turning LateralusOS from a
> bootable demo into a usable research OS with real applications. Every
> phase has concrete acceptance criteria, estimated effort, and the files
> or subsystems that need to change.
>
> Companion to [../ROADMAP_NEXT.md](../ROADMAP_NEXT.md) (language roadmap).
> **Rule: the language ships first; the OS follows.**

---

## Where We Are: v0.1 (April 2026)

| Subsystem                  | Status  | Notes |
|----------------------------|---------|-------|
| Multiboot2 bootloader      | ✅ | [lateralus-os/boot/boot.asm](boot/boot.asm) |
| x86_64 long-mode entry     | ✅ | PML4 + PDPT + PD, 4 GB identity map |
| Serial early-debug         | ✅ | COM1 @ 115200 |
| Framebuffer (linear RGB)   | ✅ | VBE mode from GRUB, 32-bpp |
| Physical memory bitmap     | ✅ | [kernel/memory.ltl](kernel/memory.ltl) |
| Heap allocator (bump+free) | ✅ | [kernel/heap.c](kernel/heap.c) |
| GDT + IDT                  | ✅ | bootstrapped in C |
| PIT / PIC timers           | ✅ | 100 Hz tick |
| Cooperative scheduler      | 🟡 | round-robin, 8 tasks, no preemption |
| IPC (mailboxes + pipes)    | 🟡 | API defined, not stress-tested |
| Syscall table              | 🟡 | 23 syscalls, no userspace yet |
| Mouse + keyboard           | ✅ | PS/2 drivers |
| Double-buffered compositor | ✅ | single-window, no clipping yet |
| Wallpaper + cursor         | ✅ | static gradient, 16×16 arrow |
| Shell (`ltlsh`)            | 🟡 | 17 commands, in-kernel only |
| VFS + ramfs                | ✅ | mount/open/read/write/close |
| Persistent FS              | ❌ | — |
| Userspace ring-3 transition | ❌ | — |
| Application packaging       | ❌ | — |

**Honest summary: it boots, it paints pixels, it schedules. It does not run
userspace code yet. The jump from v0.1 → v0.2 is the single biggest step.**

---

## Phase 1 — Ring-3 Userspace (v0.2, target: August 2026)

**Acceptance:** a Lateralus program, compiled via `lateralus c --freestanding
--userspace`, can be copied into the ramfs at build time, `exec`d by the
kernel, run in ring 3, make syscalls, and exit cleanly. Observable proof:
`hello world` from a userspace `.ltl` binary.

**Effort:** ~6 weeks, single developer.

### Tasks
- [ ] **Ring-3 TSS + stack switching** — add a per-task kernel stack,
      IST entry, `sysret`-compatible segment layout
      ([kernel/tasks.c](kernel/tasks.c))
- [ ] **User-mode page tables** — clone kernel PML4, map user stack +
      text/data with `U/S=1`, unmap on task exit
      ([kernel/memory.ltl](kernel/memory.ltl))
- [ ] **Syscall via `syscall`/`sysret`** — MSR setup, register ABI
      (rdi/rsi/rdx/r10/r8/r9), latency budget < 500 ns round-trip
      ([kernel/syscall.c](kernel/syscall.c))
- [ ] **ELF64 loader** — parse program headers, map loadable segments,
      resolve entry point. Static only — no dynamic linking yet.
      (new: `kernel/elf.ltl`)
- [ ] **C-backend `--userspace` flag** — emit position-independent code,
      link against a minimal freestanding libltl that routes I/O through
      syscalls instead of direct framebuffer writes
      ([lateralus_lang/codegen/c.py](../lateralus_lang/codegen/c.py))
- [ ] **Userspace `println` / `read_line`** — stdin/stdout over pipe fds
      handed to the task by the kernel

### Milestone
```
$ cat apps/hello/hello.ltl
fn main() { println("hello from ring 3") }
main()

$ make iso && qemu-system-x86_64 -cdrom build/lateralus-os.iso
[ltlsh]$ hello
hello from ring 3
```

---

## Phase 2 — Persistent Filesystem (v0.3, September 2026)

**Acceptance:** files written in one boot are still present the next boot.
A simple editor can save its state to disk.

**Effort:** ~4 weeks.

### Tasks
- [ ] **AHCI driver (SATA)** — probe PCI config space, initialize ports,
      DMA read/write — new: `drivers/ahci.c`
- [ ] **LTLFS — simple journaling filesystem** — inline inline metadata,
      crash-safe via COW superblock
      (design in [fs/ltlfs.md](fs/ltlfs.md), impl `fs/ltlfs.ltl`)
- [ ] **VFS mount API** — mount LTLFS over root, fall back to ramfs for
      `/tmp`. (`kernel/vfs.ltl`)
- [ ] **`fsync` syscall** — flush buffer cache to disk before signalling
- [ ] **Recovery on mount** — validate superblock checksum, replay journal

### Milestone
```
[ltlsh]$ echo "hello" > /home/a/note.txt
[ltlsh]$ reboot
...
[ltlsh]$ cat /home/a/note.txt
hello
```

---

## Phase 3 — Real GUI Toolkit (v0.4, November 2026)

**Acceptance:** a window manager with proper clipping, multiple concurrent
windows, draggable/resizable chrome, and a toolkit a Lateralus program can
use without touching framebuffer pixels directly.

**Effort:** ~8 weeks.

### Tasks
- [ ] **Damage-region compositor** — rebuild `gui/compositor.ltl` around
      dirty rects; current naive full-redraw hits ~8 FPS at 1024×768
- [ ] **Window list + Z-order** — per-window backing store, composite
      top-down with alpha
- [ ] **Event routing** — mouse click → top-most-window-under-cursor;
      keyboard → focused-window (`gui/window_manager.ltl`)
- [ ] **Toolkit widgets** — Button, Label, TextField, List, Scrollbar,
      MenuBar — each paintable via a `Canvas` handle, no raw pixel access
      (`gui/widgets.ltl` + new `stdlib/ui/`)
- [ ] **Theme engine** — pluggable palette + font (`gui/theme_engine.ltl`
      already stubbed)
- [ ] **Shared-memory framebuffer for userspace** — let a ring-3 app
      composite into its own buffer, kernel promotes to screen

### Milestone
Three overlapping windows: terminal, text editor, system monitor. Drag,
resize, and `Alt+Tab` work. 60 FPS steady on QEMU/KVM.

---

## Phase 4 — Networking (v0.5, January 2027)

**Acceptance:** `curl example.com` from `ltlsh`. ICMP ping replies.

**Effort:** ~6 weeks.

### Tasks
- [ ] **RTL8139 driver** (QEMU default NIC) — PCI probe, ring buffers,
      IRQ handler (`drivers/rtl8139.c`)
- [ ] **TCP/IP stack in Lateralus** — `net/eth.ltl`, `net/arp.ltl`,
      `net/ip.ltl`, `net/tcp.ltl`, `net/udp.ltl`. Use `@law` extensively
      to verify header round-trips, checksum commutativity, window
      arithmetic. **This is where the language pays off** — invariants
      of a protocol stack are exactly what `@law` was designed for.
- [ ] **DHCP client** — acquire IP on boot
- [ ] **DNS resolver** — UDP only, cached
- [ ] **`curl` port** — just enough HTTP 1.1 GET for demos

### Milestone
```
[ltlsh]$ curl http://example.com
<!doctype html>
<html>...
```

---

## Phase 5 — Applications (v0.6 — v0.9, 2027)

Once userspace + FS + GUI + network are real, the OS becomes the platform
for building things. Priority apps (all in Lateralus):

1. **`ltedit`** — modal text editor, saves to LTLFS
2. **`ltfiles`** — two-pane file manager
3. **`ltmon`** — system monitor (CPU, memory, tasks)
4. **`ltpkg`** — package manager fronting `lateralus pkg` tarballs
5. **`ltchat`** — LAN chat over UDP multicast, encrypted with stdlib `crypto`
6. **`ltmusic`** — WAV player via PC speaker + Sound Blaster 16
7. **`ltbrowse`** — very reduced HTML renderer (text + links, no JS)

Each app is a test case for a different subsystem. The ones that are hard
to build reveal missing OS primitives.

---

## Phase 6 — Real Hardware (v1.0, target: end of 2027)

**Acceptance:** boots on a physical ThinkPad T420 from USB.

**Effort:** ~4 weeks after Phase 5.

### Tasks
- [ ] **EFI boot path** — alongside Multiboot2 (many laptops drop BIOS)
- [ ] **PCIe enumeration beyond QEMU defaults**
- [ ] **AHCI on real silicon** (QEMU is forgiving)
- [ ] **Intel HD Audio** (no more PC speaker)
- [ ] **USB HID** for keyboard/mouse (PS/2 is being phased out)
- [ ] **ACPI poweroff + suspend**
- [ ] **Boot-time hardware probe UI** — "we found X, Y, Z; pick one"

### Milestone
Boot LateralusOS from a USB stick on a real laptop. Browse a local
webpage. Play a WAV file. Save a text file across reboots.

This is **v1.0** — the moment LateralusOS stops being a demo.

---

## Cross-Cutting: Language Features that Unlock OS Work

These language-level improvements directly unblock OS subsystems. They
also belong on [../ROADMAP_NEXT.md](../ROADMAP_NEXT.md), but listed here
with their OS-side consumer:

| Language feature         | Unblocks |
|--------------------------|----------|
| `@interrupt` decorator (auto save/restore GPRs, IRET) | IRQ handlers in `.ltl` |
| `volatile` pointer type | MMIO without workarounds |
| Inline assembly blocks (`asm { ... }`) | Context switch, MSR ops |
| Packed structs | Hardware register layouts |
| `@section(".text.init")` placement | Early-boot code |
| `any`-typed mixed returns (v3.2 C backend) | Syscall return values |
| Zero-alloc string formatting | Kernel-side `printk` |

---

## Testing Strategy

- **Per-phase pytest suite** under `lateralus-os/tests/` — already runs
  in CI, boots QEMU with `-device isa-debug-exit`, reads serial log,
  asserts milestones. Extend per phase.
- **`@law` specifications** for kernel invariants — once userspace exists,
  we can run laws like "`malloc(n); free(p)` leaves used-pages unchanged"
  as actual on-target tests via a boot-time law-runner app.
- **Bisectable commits** — every milestone is a single `git bisect run`
  target.

---

## Honest Non-Goals (Through v1.0)

- **Multi-user security** — ring-3 isolates apps from kernel; inter-app
  isolation is v1.5+.
- **POSIX compatibility** — not happening; we have our own, cleaner ABI.
- **SMP** — single-core only through v1.0.
- **Wayland/X compatibility** — LateralusOS has its own compositor; no
  port layer.
- **A C compiler running on LateralusOS** — we cross-compile from Linux.

---

## Dependencies on Language Toolchain

Every OS phase depends on a language capability. The critical path:

```
v3.2 @law  →  v0.2 ring-3 laws (trivial)
v3.3 pkg registry  →  v0.6 ltpkg
v3.4 @interrupt + asm blocks  →  v0.2 IRQ handlers without C shims
v4.0 self-hosting  →  v1.0 LateralusOS built on LateralusOS
```

**The language roadmap drives the OS roadmap.** If the language stalls,
the OS waits. This is the correct order of operations.

---

*Spiral outward. Build something beautiful.*
