#!/usr/bin/env bash
# ===========================================================================
# tools/record_grug_vm.sh — screen-record grugbot420 tests inside QEMU
# ===========================================================================
# Boots LateralusOS in a visible QEMU window, locates that window on the
# X11 display, and records it with ffmpeg (x11grab) to an MP4 file.
# While the VM runs, xdotool types a short grugbot420 test script into the
# guest so the recording captures actual grugbot interaction.
#
# Usage:
#     ./tools/record_grug_vm.sh [seconds]      # default 60s
# Output:
#     build/grug_tests.mp4
# ===========================================================================

set -e
cd "$(dirname "$0")/.."

DURATION="${1:-60}"
BUILD=build
ISO="$BUILD/lateralus-os.iso"
OUT="$BUILD/grug_tests.mp4"
LOG="$BUILD/grug_record.log"

# -- Sanity checks --------------------------------------------------------
for bin in qemu-system-x86_64 ffmpeg xdotool xwininfo; do
    command -v "$bin" >/dev/null 2>&1 || { echo "missing: $bin"; exit 1; }
done
[ -z "$DISPLAY" ] && { echo "no \$DISPLAY — need an X11 session"; exit 1; }

# -- Build ISO if needed --------------------------------------------------
if [ ! -f "$ISO" ]; then
    echo "[record] ISO not found — building…"
    ./build_and_boot.sh --iso
fi

KVM_FLAG=""
[ -w /dev/kvm ] && KVM_FLAG="-enable-kvm -cpu host"

QEMU_NAME="LateralusOS-GrugTest-$$"

echo "[record] booting QEMU  ($QEMU_NAME)"
qemu-system-x86_64 \
    $KVM_FLAG \
    -cdrom "$ISO" \
    -m 256M \
    -vga std \
    -serial file:"$BUILD/serial.log" \
    -no-reboot -no-shutdown \
    -name "$QEMU_NAME" \
    >"$LOG" 2>&1 &
QEMU_PID=$!

# -- Wait for QEMU window -------------------------------------------------
echo "[record] waiting for QEMU window…"
WID=""
for i in $(seq 1 40); do
    WID=$(xdotool search --name "$QEMU_NAME" 2>/dev/null | head -n1 || true)
    [ -n "$WID" ] && break
    sleep 0.25
done
if [ -z "$WID" ]; then
    echo "[record] could not find QEMU window"
    kill $QEMU_PID 2>/dev/null || true
    exit 1
fi

# Give the window a moment to realise its final size, then read geometry
sleep 1
xdotool windowactivate --sync "$WID" || true
GEOM=$(xwininfo -id "$WID")
X=$(echo "$GEOM" | awk '/Absolute upper-left X/ {print $4}')
Y=$(echo "$GEOM" | awk '/Absolute upper-left Y/ {print $4}')
W=$(echo "$GEOM" | awk '/Width:/ {print $2}')
H=$(echo "$GEOM" | awk '/Height:/ {print $2}')
# ffmpeg x11grab wants even dimensions
W=$(( W - W % 2 ))
H=$(( H - H % 2 ))
echo "[record] window $WID geometry: ${W}x${H}+${X}+${Y}"

# -- Let GRUB auto-boot (timeout=0 hidden) before we start recording -----
# Grub still briefly paints its splash for ~1s; skip that too.
GRUB_SKIP="${GRUB_SKIP:-3}"
echo "[record] skipping GRUB phase (${GRUB_SKIP}s) before starting capture…"
sleep "$GRUB_SKIP"

# -- Start ffmpeg screen capture -----------------------------------------
echo "[record] capturing ${DURATION}s → $OUT"
rm -f "$OUT"
ffmpeg -hide_banner -loglevel error -y \
    -video_size "${W}x${H}" \
    -framerate 25 \
    -f x11grab -i "${DISPLAY}+${X},${Y}" \
    -t "$DURATION" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 23 \
    "$OUT" &
FFMPEG_PID=$!

# -- Drive grugbot inside the guest --------------------------------------
# Grug auto-launches in the GUI terminal after kernel + desktop come up.
# Capture starts post-GRUB, so we just wait for the GUI + grug window.
(
    sleep 11      # kernel boot + GUI init + grug window appears
    xdotool windowactivate --sync "$WID" || true

    type_line() {
        xdotool type  --window "$WID" --delay 35 -- "$1"
        xdotool key   --window "$WID" Return
        sleep "${2:-2}"
    }

    # --- intro: greet + show help ---
    type_line "hello grug"                 2
    type_line "/help"                      3

    # --- keyword intelligence ---
    type_line "i have a nasty bug"         2
    type_line "this code is too complex"   2
    type_line "should i refactor or ship?" 3
    type_line "tell me about oop"          2
    type_line "what about perf?"           2
    type_line "is it friday yet"           2

    # --- canned commands ---
    type_line "/wisdom"                    2
    type_line "/joke"                      2
    type_line "/roll"                      2
    type_line "/smoke"                     2
    type_line "/time"                      2

    # --- THE MAIN EVENT: in-VM throughput benchmark (x3) ---
    type_line "/bench"                     8
    type_line "/bench"                     8
    type_line "/bench"                     8

    # --- outro ---
    type_line "/wisdom"                    2
    type_line "later grug"                 2
) &
DRIVER_PID=$!

# -- Wait for ffmpeg, then tear everything down --------------------------
wait $FFMPEG_PID || true
kill $DRIVER_PID 2>/dev/null || true
kill $QEMU_PID   2>/dev/null || true
wait             2>/dev/null || true

if [ -s "$OUT" ]; then
    SIZE=$(du -h "$OUT" | cut -f1)
    echo "[record] ✓ saved $OUT ($SIZE, ${DURATION}s)"
else
    echo "[record] ✗ recording failed — see $LOG"
    exit 1
fi
