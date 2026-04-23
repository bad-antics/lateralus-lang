#!/usr/bin/env bash
# Launch LateralusOS in QEMU from a desktop shortcut. Logs to build/gui.log.
set -e
cd "$(dirname "$(readlink -f "$0")")/.."
mkdir -p build
exec ./build_and_boot.sh --gui 2>&1 | tee build/gui.log
