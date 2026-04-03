# ═══════════════════════════════════════════════════════════════════════════
# LateralusOS — Master Build System
# ═══════════════════════════════════════════════════════════════════════════
# Copyright (c) 2025 bad-antics. All rights reserved.
# ═══════════════════════════════════════════════════════════════════════════

# ── Configuration ─────────────────────────────────────────────────────────

ARCH        ?= x86_64
EDITION     ?= workstation
BUILD_DIR   := build/$(EDITION)-$(ARCH)
ISO_NAME    := lateralus-os-$(EDITION)-$(ARCH).iso

# Lateralus compiler
LTLC        := python -m lateralus_lang
LTLC_CMD    := c
LTLC_FLAGS  := --freestanding

# Cross-compiler (set per architecture)
ifeq ($(ARCH),x86_64)
    CC      := $(shell which x86_64-elf-gcc 2>/dev/null || echo gcc)
    AS      := nasm
    LD      := $(shell which x86_64-elf-ld 2>/dev/null || echo ld)
    ASFLAGS := -f elf64
    CFLAGS  := -ffreestanding -nostdlib -O2 -Wall -Wextra -std=c99 \
               -mno-red-zone -mcmodel=kernel -fno-exceptions -fno-stack-protector
    LDFLAGS := -T tools/linker-$(ARCH).ld -nostdlib
    QEMU    := qemu-system-x86_64
    QEMUFLAGS := -m 256M -serial stdio -no-reboot -no-shutdown
else ifeq ($(ARCH),arm-cortex-m4)
    CC      := arm-none-eabi-gcc
    AS      := arm-none-eabi-as
    LD      := arm-none-eabi-ld
    CFLAGS  := -ffreestanding -nostdlib -O2 -mcpu=cortex-m4 -mthumb \
               -fno-exceptions -fno-stack-protector
    LDFLAGS := -T tools/linker-arm.ld -nostdlib
    QEMU    := qemu-system-arm
    QEMUFLAGS := -M lm3s6965evb -nographic -serial stdio
else ifeq ($(ARCH),riscv64)
    CC      := riscv64-unknown-elf-gcc
    AS      := riscv64-unknown-elf-as
    LD      := riscv64-unknown-elf-ld
    CFLAGS  := -ffreestanding -nostdlib -O2 -march=rv64imac -mabi=lp64 \
               -fno-exceptions -fno-stack-protector
    LDFLAGS := -T tools/linker-riscv.ld -nostdlib
    QEMU    := qemu-system-riscv64
    QEMUFLAGS := -M virt -nographic -bios none
endif

# ── Source discovery ──────────────────────────────────────────────────────

LTL_SRCS    := $(shell find kernel hal drivers fs shell services -name '*.ltl' 2>/dev/null)
C_GENERATED := $(patsubst %.ltl,$(BUILD_DIR)/%.c,$(LTL_SRCS))
OBJS        := $(patsubst %.c,%.o,$(C_GENERATED))

# Boot assembly
BOOT_ASM    := boot/boot.asm
BOOT_OBJ    := $(BUILD_DIR)/boot/boot.o

# Boot C stub
BOOT_C      := boot/boot_stub.c
BOOT_C_OBJ  := $(BUILD_DIR)/boot/boot_stub.o

# ── Edition config ────────────────────────────────────────────────────────

EDITION_CFG := editions/$(EDITION).toml

# ── Targets ───────────────────────────────────────────────────────────────

.PHONY: all clean run test debug iso editions help

all: $(BUILD_DIR)/kernel.elf
	@echo "═══ LateralusOS $(EDITION) ($(ARCH)) built successfully ═══"

help:
	@echo "LateralusOS Build System"
	@echo "────────────────────────"
	@echo "  make                    Build default (workstation/x86_64)"
	@echo "  make EDITION=industrial Build industrial edition"
	@echo "  make EDITION=research   Build research edition"
	@echo "  make EDITION=embedded   Build embedded edition"
	@echo "  make run                Build and run in QEMU"
	@echo "  make test               Run OS test suite"
	@echo "  make iso                Build bootable ISO"
	@echo "  make debug              Run in QEMU with GDB stub"
	@echo "  make clean              Clean build artifacts"

# ── Transpile .ltl → .c ──────────────────────────────────────────────────

$(BUILD_DIR)/%.c: %.ltl $(EDITION_CFG)
	@mkdir -p $(dir $@)
	@echo "  LTLC    $<"
	$(LTLC) $(LTLC_CMD) $< $(LTLC_FLAGS) --arch $(ARCH) -o $@

# ── Compile .c → .o ──────────────────────────────────────────────────────

$(BUILD_DIR)/%.o: $(BUILD_DIR)/%.c
	@mkdir -p $(dir $@)
	@echo "  CC      $<"
	$(CC) $(CFLAGS) -I$(BUILD_DIR) -c $< -o $@

# ── Assemble boot ─────────────────────────────────────────────────────────

$(BOOT_OBJ): $(BOOT_ASM)
	@mkdir -p $(dir $@)
	@echo "  ASM     $<"
	$(AS) $(ASFLAGS) $< -o $@

$(BOOT_C_OBJ): $(BOOT_C)
	@mkdir -p $(dir $@)
	@echo "  CC      $<"
	$(CC) $(CFLAGS) -c $< -o $@

# ── Link kernel ───────────────────────────────────────────────────────────

$(BUILD_DIR)/kernel.elf: $(BOOT_OBJ) $(BOOT_C_OBJ) $(OBJS)
	@echo "  LD      $@"
	$(LD) $(LDFLAGS) $^ -o $@
	@echo "  SIZE    $@"
	@size $@ || true

# ── ISO image (x86_64 only) ──────────────────────────────────────────────

iso: $(BUILD_DIR)/kernel.elf
	@mkdir -p $(BUILD_DIR)/iso/boot/grub
	cp $< $(BUILD_DIR)/iso/boot/kernel.elf
	cp tools/grub.cfg $(BUILD_DIR)/iso/boot/grub/grub.cfg
	grub-mkrescue -o $(BUILD_DIR)/$(ISO_NAME) $(BUILD_DIR)/iso
	@echo "═══ ISO: $(BUILD_DIR)/$(ISO_NAME) ═══"

# ── Run in QEMU ──────────────────────────────────────────────────────────

run: $(BUILD_DIR)/kernel.elf
	$(QEMU) -kernel $< $(QEMUFLAGS)

debug: $(BUILD_DIR)/kernel.elf
	$(QEMU) -kernel $< $(QEMUFLAGS) -s -S &
	@echo "GDB stub listening on localhost:1234"
	@echo "Run: gdb -ex 'target remote :1234' -ex 'symbol-file $<'"

# ── Tests ─────────────────────────────────────────────────────────────────

test:
	@echo "═══ Running LateralusOS test suite ═══"
	cd .. && python -m pytest lateralus-os/tests/ -v --tb=short
	@echo "═══ OS integration tests ═══"
	$(QEMU) -kernel $(BUILD_DIR)/kernel.elf $(QEMUFLAGS) \
		-device isa-debug-exit,iobase=0xf4,iosize=0x04 \
		-append "test_mode=1" || [ $$? -eq 33 ]

# ── Clean ─────────────────────────────────────────────────────────────────

clean:
	rm -rf build/
	@echo "Cleaned."

# ── Edition summary ──────────────────────────────────────────────────────

editions:
	@echo "Available editions:"
	@for f in editions/*.toml; do \
		name=$$(basename $$f .toml); \
		echo "  $$name"; \
	done
