#!/usr/bin/env python3
"""
===========================================================================
LateralusOS — QEMU Test Harness
===========================================================================
Copyright (c) 2025 bad-antics. All rights reserved.

Automated testing of LateralusOS kernel in QEMU with serial output
capture and assertion checking.

Usage:
    python tests/run_qemu_tests.py --kernel build/lateralus.elf
    python tests/run_qemu_tests.py --iso lateralus-os.iso --timeout 30
    python tests/run_qemu_tests.py --kernel build/lateralus.elf --arch arm
"""

import argparse
import subprocess
import sys
import os
import time
import signal
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration: float = 0.0


@dataclass
class TestSuite:
    results: list = field(default_factory=list)
    serial_log: str = ""
    exit_code: int = -1
    timed_out: bool = False

    @property
    def passed(self):
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self):
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self):
        return len(self.results)


# -- QEMU Configuration --------------------------------------------------

QEMU_CONFIGS = {
    "x86_64": {
        "binary": "qemu-system-x86_64",
        "args": [
            "-machine", "q35",
            "-cpu", "qemu64,+rdrand,+aes",
            "-m", "256M",
            "-no-reboot",
            "-no-shutdown",
            "-display", "none",
            "-serial", "stdio",
            "-device", "isa-debug-exit,iobase=0xf4,iosize=0x04",
        ],
    },
    "arm": {
        "binary": "qemu-system-arm",
        "args": [
            "-machine", "lm3s6965evb",
            "-cpu", "cortex-m4",
            "-m", "64M",
            "-nographic",
            "-semihosting",
        ],
    },
    "riscv64": {
        "binary": "qemu-system-riscv64",
        "args": [
            "-machine", "virt",
            "-cpu", "rv64",
            "-m", "128M",
            "-nographic",
            "-bios", "none",
        ],
    },
}


# -- Test Checks ----------------------------------------------------------

BOOT_CHECKS = [
    ("Boot banner",        r"LateralusOS|LATERALUS"),
    ("CPU detection",      r"\[cpu\].*detected|CPUID"),
    ("IDT setup",          r"\[idt\]|\[interrupts\].*ready"),
    ("Memory init",        r"\[memory\].*init|heap.*ready"),
    ("Timer init",         r"\[timer\].*init|PIT.*configured"),
    ("Keyboard init",      r"\[keyboard\].*init|PS/2"),
    ("VGA init",           r"\[vga\].*init|VGA.*ready"),
    ("Syscall table",      r"\[syscall\].*init|syscall.*ready"),
    ("IPC init",           r"\[ipc\].*init|IPC.*ready"),
    ("Scheduler init",     r"\[scheduler\].*init|scheduler.*ready"),
    ("Init started",       r"\[init\].*start|PID 1"),
    ("Crypto service",     r"\[crypto\].*ready|crypto.*start"),
    ("Monitor service",    r"\[monitor\].*start"),
    ("Shell started",      r"\[shell\]|ltlsh|Shell.*ready"),
    ("No kernel panic",    r"(?!.*KERNEL PANIC).*"),
    ("No triple fault",    r"(?!.*TRIPLE FAULT).*"),
]


def run_qemu(kernel_path: str, arch: str, timeout: int,
             iso: Optional[str] = None) -> TestSuite:
    """Run QEMU and capture serial output."""
    suite = TestSuite()

    config = QEMU_CONFIGS.get(arch)
    if not config:
        print(f"Error: Unknown architecture '{arch}'")
        sys.exit(1)

    qemu_bin = config["binary"]
    if not is_available(qemu_bin):
        print(f"Error: {qemu_bin} not found. Install QEMU.")
        sys.exit(1)

    cmd = [qemu_bin] + config["args"]

    if iso:
        cmd.extend(["-cdrom", iso])
    elif arch == "x86_64":
        cmd.extend(["-kernel", kernel_path])
    elif arch == "arm":
        cmd.extend(["-kernel", kernel_path])
    elif arch == "riscv64":
        cmd.extend(["-kernel", kernel_path])

    print(f"[test] Starting QEMU ({arch}): {' '.join(cmd[:5])}...")
    print(f"[test] Timeout: {timeout}s")

    start = time.time()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            suite.serial_log = stdout + stderr
            suite.exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            suite.serial_log = stdout + stderr
            suite.timed_out = True

    except FileNotFoundError:
        print(f"Error: {qemu_bin} not found")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"[test] QEMU exited after {elapsed:.1f}s (code={suite.exit_code})")

    # Run checks against serial output
    for name, pattern in BOOT_CHECKS:
        t0 = time.time()
        if name == "No kernel panic" or name == "No triple fault":
            # Negative check — pattern should NOT match
            bad_pattern = pattern.replace("(?!.*", "").replace(").*", "")
            passed = bad_pattern not in suite.serial_log
        else:
            passed = bool(re.search(pattern, suite.serial_log, re.IGNORECASE))
        dt = time.time() - t0
        suite.results.append(TestResult(name=name, passed=passed, duration=dt))

    return suite


def print_results(suite: TestSuite, verbose: bool = False):
    """Print test results in a formatted table."""
    print()
    print("=" * 60)
    print("  LateralusOS Test Results")
    print("=" * 60)

    for r in suite.results:
        icon = "✓" if r.passed else "✗"
        color = "\033[32m" if r.passed else "\033[31m"
        reset = "\033[0m"
        print(f"  {color}{icon}{reset} {r.name}")

    print("-" * 60)
    print(f"  Passed: {suite.passed}/{suite.total}", end="")
    if suite.failed > 0:
        print(f"  |  \033[31mFailed: {suite.failed}\033[0m", end="")
    if suite.timed_out:
        print(f"  |  \033[33mTimed out\033[0m", end="")
    print()
    print("=" * 60)

    if verbose and suite.serial_log:
        print()
        print("-- Serial Log ------------------------------------------")
        for line in suite.serial_log.split("\n")[:100]:
            print(f"  {line}")
        if suite.serial_log.count("\n") > 100:
            print(f"  ... ({suite.serial_log.count(chr(10)) - 100} more lines)")


def is_available(cmd: str) -> bool:
    """Check if a command is available on PATH."""
    try:
        subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main():
    parser = argparse.ArgumentParser(description="LateralusOS QEMU Test Harness")
    parser.add_argument("--kernel", help="Path to kernel ELF binary")
    parser.add_argument("--iso", help="Path to bootable ISO image")
    parser.add_argument("--arch", default="x86_64",
                        choices=["x86_64", "arm", "riscv64"],
                        help="Target architecture")
    parser.add_argument("--timeout", type=int, default=30,
                        help="QEMU timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show serial log output")
    parser.add_argument("--save-log", help="Save serial log to file")
    args = parser.parse_args()

    if not args.kernel and not args.iso:
        parser.error("Either --kernel or --iso is required")

    kernel = args.kernel or ""
    suite = run_qemu(kernel, args.arch, args.timeout, args.iso)

    print_results(suite, args.verbose)

    if args.save_log:
        with open(args.save_log, "w") as f:
            f.write(suite.serial_log)
        print(f"\n[test] Serial log saved to: {args.save_log}")

    sys.exit(0 if suite.failed == 0 else 1)


if __name__ == "__main__":
    main()
