# ===========================================================================
# LateralusOS — A Research & Industrial Operating System
# ===========================================================================
#
# Copyright (c) 2025 bad-antics. All rights reserved.
#
# This project is dual-licensed:
#   • Freeware Edition — See LICENSE-FREEWARE.md
#   • Proprietary Master — All rights reserved by bad-antics
#
# Built with the Lateralus programming language (v2.1.0+)
# https://github.com/bad-antics/lateralus-lang
# ===========================================================================

## Architecture

```
                    +-----------------------------------+
                    |        User Applications          |
                    |   (Lateralus programs, agents)    |
                    +-----------------------------------+
                    |       Graphical Desktop (GUI)      |
                    |   animated wallpaper | Alt+Tab     |
                    |   terminal | window animations    |
                    +-----------------------------------+
                    |        System Services Layer       |
                    |   mesh agent | crypto | monitor    |
                    +-----------------------------------+
                    |          LateralusOS Shell         |
                    |    ltlsh -- 17 commands, VFS ops   |
                    +-----------------------------------+
                    |      Kernel Services (Lateralus)   |
                    |   scheduler | IPC | VFS | ramfs    |
                    +-----------------------------------+
                    |      Memory Manager (Lateralus)    |
                    |   page tables | bump alloc         |
                    +-----------------------------------+
                    |   HAL + Drivers                    |
                    |   PIT|PIC|speaker|keyboard|mouse   |
                    +-----------------------------------+
                    |      Bootstrap (C + ASM)           |
                    |   GDT | IDT | paging | entry      |
                    +-----------------------------------+
                    |        Bare Metal Hardware         |
                    +-----------------------------------+
```

## Directory Structure

```
lateralus-os/
+-- boot/            — Multiboot2 bootstrap (ASM + C)
+-- kernel/          — Core kernel in Lateralus
|   +-- main.ltl     — kernel_main entry point
|   +-- memory.ltl   — Physical/virtual memory manager
|   +-- scheduler.ltl— Process/thread scheduler
|   +-- ipc.ltl      — Inter-process communication
|   +-- syscall.ltl  — System call table & dispatcher
|   +-- panic.ltl    — Kernel panic handler
+-- hal/             — Hardware Abstraction Layer
|   +-- cpu.ltl      — CPU feature detection, ring management
|   +-- interrupts.ltl— IDT, IRQ handling
|   +-- timer.ltl    — PIT/APIC timer
|   +-- serial.ltl   — Serial port (debug output)
+-- drivers/         — Device drivers
|   +-- vga.ltl      — VGA text mode display
|   +-- keyboard.ltl — PS/2 keyboard
|   +-- pci.ltl      — PCI bus enumeration
|   +-- disk.ltl     — ATA/AHCI disk driver
|   +-- network.ltl  — NIC driver (RTL8139/virtio-net)
+-- gui/             — Graphical Desktop Environment
|   +-- framebuffer.h/c — Double-buffered framebuffer driver + 8×16 font
|   +-- gui.h/c      — Widget system (windows, menus, icons, buttons, animations)
|   +-- desktop.h/c  — Desktop manager (start menu, icons, sysmon, taskbar)
|   +-- mouse.h/c    — PS/2 mouse driver (IRQ12, 3-byte packets)
|   +-- terminal.h/c — Functional terminal emulator (17 commands, VFS)
|   +-- types.h      — Shared freestanding type definitions
|   +-- bootinfo.h   — Multiboot2 boot info struct
|   +-- app.ltl      — GUI app framework (Lateralus)
|   +-- widgets.ltl  — Widget library (Lateralus)
|   +-- terminal.ltl — Terminal emulator (Lateralus)
|   +-- wallpaper.ltl— Animated wallpaper engine (Lateralus)
|   +-- animation.ltl— Window animation system (Lateralus)
|   +-- shell_gui.ltl— Graphical shell (Lateralus)
+-- fs/              — File systems
|   +-- ramfs.h/c    — In-memory RAM filesystem (64 inodes)
|   +-- vfs.ltl      — Virtual File System layer + RAMFS backend
|   +-- ltlfs.ltl    — Native LateralusFS
|   +-- fat32.ltl    — FAT32 compatibility
+-- drivers/         — Device drivers
|   +-- speaker.h/c  — PC speaker (PIT Channel 2, melody queue)
|   +-- speaker.ltl  — Speaker driver (Lateralus)
|   +-- vga.ltl      — VGA text mode display
|   +-- keyboard.ltl — PS/2 keyboard
|   +-- pci.ltl      — PCI bus enumeration
|   +-- disk.ltl     — ATA/AHCI disk driver
|   +-- network.ltl  — NIC driver (RTL8139/virtio-net)
+-- kernel/          — Core kernel
|   +-- tasks.h/c    — Cooperative task scheduler (16 tasks)
|   +-- main.ltl     — kernel_main entry point
|   +-- memory.ltl   — Physical/virtual memory manager
|   +-- scheduler.ltl— Process/thread scheduler + cooperative tasks
|   +-- ipc.ltl      — Inter-process communication
|   +-- syscall.ltl  — System call table & dispatcher
|   +-- panic.ltl    — Kernel panic handler
|   +-- ltlsh.ltl    — Shell interpreter
|   +-- builtins.ltl — Built-in commands
|   +-- utils/       — Userspace utilities
+-- services/        — System services
|   +-- init.ltl     — Init system (PID 1)
|   +-- mesh_agent.ltl— Mesh network agent
|   +-- crypto_svc.ltl— Cryptographic services
|   +-- monitor.ltl  — System health monitor
+-- editions/        — Build profiles
|   +-- industrial.toml
|   +-- research.toml
|   +-- embedded.toml
|   +-- workstation.toml
+-- tests/           — OS test harness
+-- tools/           — Build tools & image creation
+-- docs/            — OS documentation
+-- Makefile         — Master build system
+-- README.md        — This file
```

## Build Targets

| Edition       | Purpose                        | Footprint | Features                    |
|---------------|--------------------------------|-----------|-----------------------------|
| Industrial    | Factory floor / SCADA          | ~512 KB   | Real-time scheduler, no GUI |
| Research      | Lab instruments / data capture | ~2 MB     | Full kernel, mesh agents    |
| Embedded      | Sensor nodes / IoT             | ~128 KB   | Minimal kernel, no FS       |
| Workstation   | Developer desktop              | ~8 MB     | Full system, shell, network |

## Quick Start

```bash
# Build and launch with GUI desktop (opens QEMU window)
./build_and_boot.sh --gui

# Build ISO only (distributable, boots to GUI by default)
./build_and_boot.sh --iso

# Run automated boot test (headless, text shell)
./build_and_boot.sh --test

# Run with VNC display (for remote/headless servers)
./build_and_boot.sh --vnc    # connect to localhost:5901

# Run in QEMU with serial output (text mode, no display)
./build_and_boot.sh
```

### GUI Keyboard Shortcuts

| Key       | Action                       |
|-----------|------------------------------|
| Ctrl+T    | Open Terminal                |
| Ctrl+A    | Open About                   |
| Ctrl+S    | Open System Monitor          |
| Alt+Tab   | Switch Windows               |
| ESC       | Exit GUI → text shell        |

### Makefile (advanced)

```bash
# Build workstation edition for x86_64
make EDITION=workstation ARCH=x86_64

# Run in QEMU
make run

# Run automated test suite
make test

# Build industrial edition for ARM
make EDITION=industrial ARCH=arm-cortex-m4
```

## Licensing

This project uses dual licensing:

- **Freeware Edition**: Free to use, study, and deploy. No modification or
  redistribution of source code. See [LICENSE-FREEWARE.md](LICENSE-FREEWARE.md).

- **Proprietary Master**: Full source with compiler integration, encryption
  engine, and advanced features. All rights reserved by bad-antics.

The Lateralus compiler and encryption systems remain proprietary to bad-antics
until completed public release.

## Credits

Created by **bad-antics**

Built with the Lateralus programming language — a systems-capable language
with pipelines, pattern matching, algebraic types, and native error handling.
