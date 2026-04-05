#!/usr/bin/env bash
# ===========================================================================
# LateralusOS — Quick Build & Boot Script
# ===========================================================================
# Copyright (c) 2025 bad-antics. All rights reserved.
#
# Usage:
#   ./build_and_boot.sh          # Build + run in QEMU (serial to stdout)
#   ./build_and_boot.sh --gui    # Build + run with visible QEMU GUI window
#   ./build_and_boot.sh --iso    # Build + create ISO only (GUI menu default)
#   ./build_and_boot.sh --test   # Build + run headless test (text shell)
#   ./build_and_boot.sh --vnc    # Build + run with VNC display on :1
# ===========================================================================

set -e
cd "$(dirname "$0")"

BUILD=build
CFLAGS="-ffreestanding -nostdlib -O2 -Wall -std=c99 -mno-red-zone -mgeneral-regs-only -fno-exceptions -fno-stack-protector"
GUI_CFLAGS="$CFLAGS -Wno-unused-function"

echo "==================================================="
echo "  LateralusOS Build System"
echo "==================================================="

mkdir -p "$BUILD/boot" "$BUILD/gui" "$BUILD/fs" "$BUILD/drivers" "$BUILD/kernel"

# -- Assemble -------------------------------------------------------------
echo "[1/25] ASM  boot/boot.asm"
nasm -f elf64 boot/boot.asm -o "$BUILD/boot/boot.o"

# -- Compile boot stubs ---------------------------------------------------
echo "[2/25] CC   boot/boot_stub.c"
gcc $CFLAGS -c boot/boot_stub.c -o "$BUILD/boot/boot_stub.o"

echo "[3/25] CC   boot/kernel_stub.c"
gcc $CFLAGS -Wno-unused-variable -Wno-unused-function \
    -c boot/kernel_stub.c -o "$BUILD/boot/kernel_stub.o"

# -- Compile GUI subsystem -----------------------------------------------
echo "[4/25] CC   gui/framebuffer.c"
gcc $GUI_CFLAGS -c gui/framebuffer.c -o "$BUILD/gui/framebuffer.o"

echo "[5/25] CC   gui/gui.c"
gcc $GUI_CFLAGS -c gui/gui.c -o "$BUILD/gui/gui.o"

echo "[6/25] CC   gui/desktop.c + gui/mouse.c + gui/terminal.c"
gcc $GUI_CFLAGS -c gui/desktop.c -o "$BUILD/gui/desktop.o"
gcc $GUI_CFLAGS -c gui/mouse.c   -o "$BUILD/gui/mouse.o"
gcc $GUI_CFLAGS -c gui/terminal.c -o "$BUILD/gui/terminal.o"

# -- Compile filesystem --------------------------------------------------
echo "[7/25] CC   fs/ramfs.c"
gcc $GUI_CFLAGS -c fs/ramfs.c -o "$BUILD/fs/ramfs.o"

echo "[8/25] CC   fs/vfs.c"
gcc $GUI_CFLAGS -c fs/vfs.c -o "$BUILD/fs/vfs.o"

echo "[9/25] CC   fs/procfs.c"
gcc $GUI_CFLAGS -c fs/procfs.c -o "$BUILD/fs/procfs.o"

echo "[10/25] CC  fs/devfs.c"
gcc $GUI_CFLAGS -c fs/devfs.c -o "$BUILD/fs/devfs.o"

# -- Compile network stack -----------------------------------------------
mkdir -p "$BUILD/net"
echo "[10/25] CC  net/ip.c"
gcc $GUI_CFLAGS -c net/ip.c -o "$BUILD/net/ip.o"
echo "[11/25] CC  net/dns.c"
gcc $GUI_CFLAGS -c net/dns.c -o "$BUILD/net/dns.o"
echo "[12/25] CC  net/tcp.c"
gcc $GUI_CFLAGS -c net/tcp.c -o "$BUILD/net/tcp.o"
echo "[13/25] CC  net/http.c"
gcc $GUI_CFLAGS -c net/http.c -o "$BUILD/net/http.o"

# -- Compile drivers -----------------------------------------------------
echo "[14/25] CC  drivers/speaker.c + drivers/ata.c + drivers/net.c"
gcc $GUI_CFLAGS -c drivers/speaker.c -o "$BUILD/drivers/speaker.o"
gcc $GUI_CFLAGS -c drivers/ata.c     -o "$BUILD/drivers/ata.o"
gcc $GUI_CFLAGS -c drivers/net.c     -o "$BUILD/drivers/net.o"

# -- Compile kernel modules ----------------------------------------------
echo "[15/25] CC  kernel/tasks.c"
gcc $GUI_CFLAGS -c kernel/tasks.c -o "$BUILD/kernel/tasks.o"

echo "[16/25] CC  kernel/sched.c"
gcc $GUI_CFLAGS -c kernel/sched.c -o "$BUILD/kernel/sched.o"

echo "[17/25] CC  kernel/ipc.c"
gcc $GUI_CFLAGS -c kernel/ipc.c -o "$BUILD/kernel/ipc.o"

echo "[18/25] CC  kernel/syscall.c"
gcc $GUI_CFLAGS -c kernel/syscall.c -o "$BUILD/kernel/syscall.o"

echo "[19/25] CC  kernel/heap.c"
gcc $GUI_CFLAGS -c kernel/heap.c -o "$BUILD/kernel/heap.o"

# -- Compile application stubs --------------------------------------------
mkdir -p "$BUILD/apps"
echo "[19b/25] CC apps/apps.c"
gcc $GUI_CFLAGS -Wno-unused-variable -c apps/apps.c -o "$BUILD/apps/apps.o"

# -- Link -----------------------------------------------------------------
echo "[20/25] LD  lateralus.elf"
ld -T tools/linker-boot.ld -nostdlib \
    "$BUILD/boot/boot.o" \
    "$BUILD/boot/boot_stub.o" \
    "$BUILD/boot/kernel_stub.o" \
    "$BUILD/gui/framebuffer.o" \
    "$BUILD/gui/gui.o" \
    "$BUILD/gui/desktop.o" \
    "$BUILD/gui/mouse.o" \
    "$BUILD/gui/terminal.o" \
    "$BUILD/fs/ramfs.o" \
    "$BUILD/fs/vfs.o" \
    "$BUILD/fs/procfs.o" \
    "$BUILD/fs/devfs.o" \
    "$BUILD/net/ip.o" \
    "$BUILD/net/dns.o" \
    "$BUILD/net/tcp.o" \
    "$BUILD/net/http.o" \
    "$BUILD/drivers/speaker.o" \
    "$BUILD/drivers/ata.o" \
    "$BUILD/drivers/net.o" \
    "$BUILD/kernel/tasks.o" \
    "$BUILD/kernel/sched.o" \
    "$BUILD/kernel/ipc.o" \
    "$BUILD/kernel/syscall.o" \
    "$BUILD/kernel/heap.o" \
    "$BUILD/apps/apps.o" \
    -o "$BUILD/lateralus.elf"

SIZE=$(size "$BUILD/lateralus.elf" | tail -1 | awk '{print $4}')
echo "       Kernel size: $SIZE bytes"

# -- ISO ------------------------------------------------------------------
echo "[21/25] ISO lateralus-os.iso"
mkdir -p "$BUILD/iso/boot/grub"
cp "$BUILD/lateralus.elf" "$BUILD/iso/boot/lateralus.elf"

# -- GRUB config — clean, no host theme contamination ---------------------
# grub-mkrescue pulls in the host OS theme/fonts by default.
# We override everything to ensure a pure LateralusOS boot experience.

if [ "${1:-run}" = "--test" ]; then
    # Test mode: boot to text shell (fast, no GUI render overhead)
    cat > "$BUILD/iso/boot/grub/grub.cfg" << 'EOF'
# LateralusOS Boot Configuration (test mode)
set timeout=1
set default=0

# Strip any host theme
set theme=
set color_normal=light-gray/black
set color_highlight=white/blue

menuentry "LateralusOS (Text Shell)" {
    multiboot2 /boot/lateralus.elf
    boot
}
EOF
else
    cat > "$BUILD/iso/boot/grub/grub.cfg" << 'EOF'
# =======================================================
# LateralusOS v0.2.0 — Boot Configuration
# Copyright (c) 2025 bad-antics. All rights reserved.
# =======================================================

# Disable any inherited theme from host system
set theme=
set gfxmode=1024x768x32,auto
set gfxpayload=keep
set timeout=3
set default=0

# LateralusOS color scheme (Catppuccin-inspired)
set menu_color_normal=light-cyan/black
set menu_color_highlight=white/dark-gray
set color_normal=light-gray/black
set color_highlight=white/blue

# Boot splash text
echo ""
echo "  +================================================+"
echo "  |          LateralusOS v0.2.0                   |"
echo "  |      Spiral Out, Keep Going                   |"
echo "  |                                               |"
echo "  |      Copyright (c) 2025 bad-antics            |"
echo "  +================================================+"
echo ""

menuentry "LateralusOS Desktop (GUI)" {
    set gfxpayload=keep
    multiboot2 /boot/lateralus.elf gui=auto
    boot
}
menuentry "LateralusOS (Text Shell)" {
    set gfxpayload=keep
    multiboot2 /boot/lateralus.elf
    boot
}
menuentry "LateralusOS (Serial Debug)" {
    set gfxpayload=keep
    multiboot2 /boot/lateralus.elf serial=on loglevel=debug
    boot
}
EOF
fi

# Remove any host themes/locales that grub-mkrescue might inject
rm -rf "$BUILD/iso/boot/grub/themes" 2>/dev/null
rm -rf "$BUILD/iso/boot/grub/locale" 2>/dev/null
rm -f  "$BUILD/iso/boot/grub/theme.txt" 2>/dev/null

# Build ISO — suppress stderr noise from grub-mkrescue
grub-mkrescue \
    --themes="" \
    --locales="" \
    --fonts="" \
    -o "$BUILD/lateralus-os.iso" "$BUILD/iso" 2>/dev/null

echo "[24/25] ISO: $BUILD/lateralus-os.iso ($(du -h "$BUILD/lateralus-os.iso" | cut -f1))"

echo ""
echo "=== Build complete ==="
echo ""

# -- Run ------------------------------------------------------------------
case "${1:-run}" in
    --iso)
        echo "ISO ready at: $BUILD/lateralus-os.iso"
        ;;
    --test)
        echo "Running boot test (8s timeout)..."
        timeout 8 qemu-system-x86_64 \
            -cdrom "$BUILD/lateralus-os.iso" \
            -m 256M \
            -vga std \
            -serial file:"$BUILD/serial.log" \
            -display none \
            -no-reboot -no-shutdown \
            2>/dev/null || true
        echo ""
        echo "=== Serial Output ==="
        cat "$BUILD/serial.log"
        echo ""
        if grep -q "Boot sequence complete" "$BUILD/serial.log"; then
            echo "✓ BOOT TEST PASSED"
        else
            echo "✗ BOOT TEST FAILED"
            exit 1
        fi
        ;;
    --gui)
        echo "Starting QEMU with GUI desktop (default boots into GUI)..."
        echo "  ESC = exit GUI → text shell"
        echo "  Ctrl+Alt+G = release mouse grab"
        echo "----------------------------------------------------"
        # Use KVM if available for fast MMIO framebuffer writes
        KVM_FLAG=""
        if [ -w /dev/kvm ]; then
            KVM_FLAG="-enable-kvm -cpu host"
        fi
        qemu-system-x86_64 \
            $KVM_FLAG \
            -cdrom "$BUILD/lateralus-os.iso" \
            -m 256M \
            -vga std \
            -serial stdio \
            -no-reboot -no-shutdown \
            -name "LateralusOS v0.2.0"
        ;;
    --vnc)
        echo "Starting QEMU with VNC on :1 (connect to localhost:5901)..."
        qemu-system-x86_64 \
            -cdrom "$BUILD/lateralus-os.iso" \
            -m 256M \
            -vga std \
            -serial file:"$BUILD/serial.log" \
            -display vnc=:1 \
            -no-reboot -no-shutdown \
            -name "LateralusOS v0.2.0"
        ;;
    *)
        echo "Starting QEMU (serial output below, Ctrl-A X to quit)..."
        echo "----------------------------------------------------"
        qemu-system-x86_64 \
            -cdrom "$BUILD/lateralus-os.iso" \
            -m 256M \
            -vga std \
            -serial stdio \
            -display none \
            -no-reboot -no-shutdown
        ;;
esac
