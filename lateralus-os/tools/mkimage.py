#!/usr/bin/env python3
"""
===========================================================================
LateralusOS — Boot Image Builder
===========================================================================
Copyright (c) 2025 bad-antics. All rights reserved.

Creates bootable ISO images for LateralusOS using GRUB2 as the bootloader.

Usage:
    python mkimage.py --kernel build/lateralus.elf --output lateralus-os.iso
    python mkimage.py --kernel build/lateralus.elf --edition industrial --output ind.iso
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="LateralusOS Boot Image Builder")
    parser.add_argument("--kernel", required=True, help="Path to kernel ELF binary")
    parser.add_argument("--output", default="lateralus-os.iso", help="Output ISO path")
    parser.add_argument("--edition", default="workstation",
                        choices=["industrial", "research", "embedded", "workstation"],
                        help="OS edition to build")
    parser.add_argument("--grub-cfg", default=None, help="Custom GRUB config file")
    parser.add_argument("--watermark", default=None, help="Tester ID for watermarked build")
    parser.add_argument("--sign", action="store_true", help="Sign the image with SHA-256")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if not os.path.exists(args.kernel):
        print(f"Error: Kernel binary not found: {args.kernel}", file=sys.stderr)
        sys.exit(1)

    # Check for required tools
    for tool in ["grub-mkrescue", "xorriso"]:
        if not shutil.which(tool):
            print(f"Error: Required tool '{tool}' not found. Install grub2 and xorriso.",
                  file=sys.stderr)
            sys.exit(1)

    build_iso(args)


def build_iso(args):
    """Build a bootable ISO image."""
    work_dir = Path("_iso_build")
    boot_dir = work_dir / "boot"
    grub_dir = boot_dir / "grub"

    # Clean and create directory structure
    if work_dir.exists():
        shutil.rmtree(work_dir)
    grub_dir.mkdir(parents=True)

    print(f"[mkimage] Building {args.edition} edition ISO...")

    # Copy kernel
    kernel_dest = boot_dir / "lateralus.elf"
    shutil.copy2(args.kernel, kernel_dest)
    kernel_size = os.path.getsize(kernel_dest)
    print(f"[mkimage] Kernel: {kernel_size:,} bytes")

    # Generate or copy GRUB config
    if args.grub_cfg:
        shutil.copy2(args.grub_cfg, grub_dir / "grub.cfg")
    else:
        generate_grub_cfg(grub_dir / "grub.cfg", args.edition)

    # Embed build metadata
    meta = {
        "edition": args.edition,
        "build_time": datetime.utcnow().isoformat(),
        "kernel_size": kernel_size,
        "kernel_sha256": sha256_file(kernel_dest),
        "builder_version": "1.0.0",
    }

    if args.watermark:
        meta["watermark_id"] = args.watermark
        meta["watermark_hash"] = hashlib.sha256(
            f"LATERALUS-WM|{args.watermark}|{meta['build_time']}".encode()
        ).hexdigest()
        print(f"[mkimage] Watermark embedded for tester: {args.watermark}")

    with open(boot_dir / "build.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Build ISO with GRUB
    cmd = [
        "grub-mkrescue",
        "-o", args.output,
        str(work_dir),
    ]

    if not args.verbose:
        cmd.append("--quiet")

    print("[mkimage] Running grub-mkrescue...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: grub-mkrescue failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Sign the image
    if args.sign:
        iso_hash = sha256_file(args.output)
        sig_file = args.output + ".sha256"
        with open(sig_file, "w") as f:
            f.write(f"{iso_hash}  {os.path.basename(args.output)}\n")
        print(f"[mkimage] SHA-256: {iso_hash}")
        print(f"[mkimage] Signature: {sig_file}")

    iso_size = os.path.getsize(args.output)
    print(f"[mkimage] Output: {args.output} ({iso_size:,} bytes)")

    # Cleanup
    shutil.rmtree(work_dir)
    print("[mkimage] Done!")


def generate_grub_cfg(path, edition):
    """Generate a GRUB config tailored to the edition."""
    edition_args = {
        "workstation": "",
        "industrial":  "edition=industrial realtime=1 no_gui=1",
        "research":    "edition=research mesh=1 full_kernel=1",
        "embedded":    "edition=embedded minimal=1",
    }

    extra = edition_args.get(edition, "")

    cfg = f"""set timeout=3
set default=0

menuentry "LateralusOS ({edition.title()} Edition)" {{
    multiboot2 /boot/lateralus.elf {extra}
    boot
}}

menuentry "LateralusOS (Serial Debug)" {{
    multiboot2 /boot/lateralus.elf {extra} serial=on loglevel=debug
    boot
}}

menuentry "Reboot" {{
    reboot
}}
"""
    with open(path, "w") as f:
        f.write(cfg)


def sha256_file(path):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    main()
