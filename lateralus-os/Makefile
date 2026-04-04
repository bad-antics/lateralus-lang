# LateralusOS — Build System
# Copyright (c) 2025 bad-antics. All rights reserved.

EDITION    ?= daily_driver
ARCH       ?= x86_64
OUT_DIR    := build/$(ARCH)
ISO_DIR    := $(OUT_DIR)/iso
KERNEL_ELF := $(OUT_DIR)/lateralus.elf
ISO_FILE   := $(OUT_DIR)/lateralus-os-$(EDITION).iso
LTLC       := ltlc
CC         := gcc
AS         := nasm

CFLAGS     := -ffreestanding -nostdlib -O2 -Wall -Wextra -m64 -std=c11 \
              -Iinclude -Iboot
ASFLAGS    := -f elf64
LTLFLAGS   := --target=$(ARCH) --edition=$(EDITION) --os-mode

LTL_SOURCES := \
    kernel/main.ltl \
    kernel/scheduler.ltl \
    kernel/memory.ltl \
    kernel/ipc.ltl \
    kernel/syscall.ltl \
    kernel/panic.ltl \
    kernel/signals.ltl \
    kernel/pipe.ltl \
    kernel/semaphore.ltl \
    hal/cpu.ltl hal/interrupts.ltl hal/serial.ltl hal/timer.ltl \
    drivers/vga.ltl drivers/keyboard.ltl drivers/disk.ltl \
    drivers/network.ltl drivers/pci.ltl drivers/mouse.ltl \
    drivers/sound.ltl drivers/gpu.ltl drivers/nvme.ltl \
    drivers/wifi.ltl drivers/rtc.ltl drivers/usb.ltl \
    net/ip.ltl net/tcp.ltl net/udp.ltl net/dns.ltl \
    net/dhcp.ltl net/tls.ltl net/http.ltl \
    fs/vfs.ltl fs/fat32.ltl fs/ltlfs.ltl \
    fs/ext4.ltl fs/tmpfs.ltl fs/procfs.ltl fs/devfs.ltl \
    gui/animation.ltl gui/app.ltl gui/shell_gui.ltl \
    gui/terminal.ltl gui/wallpaper.ltl gui/widgets.ltl \
    gui/window_manager.ltl gui/compositor.ltl \
    gui/theme_engine.ltl gui/taskbar.ltl \
    gui/desktop.ltl gui/notifications.ltl \
    services/init.ltl services/crypto_svc.ltl \
    services/mesh_agent.ltl services/monitor.ltl \
    services/display.ltl services/audio.ltl \
    services/network_manager.ltl services/power.ltl \
    services/user_manager.ltl services/syslog.ltl \
    services/pkg_manager.ltl \
    shell/ltlsh.ltl shell/builtins.ltl \
    shell/scripting.ltl shell/completion.ltl \
    apps/chat.ltl apps/editor.ltl apps/ltlc.ltl \
    apps/package.ltl apps/browser.ltl apps/file_manager.ltl \
    apps/settings.ltl apps/calculator.ltl apps/calendar.ltl \
    apps/music.ltl apps/video.ltl apps/image_viewer.ltl \
    apps/pdf_reader.ltl apps/screenshot.ltl

C_SOURCES := \
    boot/boot.c \
    kernel/heap.c \
    kernel/ipc.c \
    kernel/sched.c \
    kernel/syscall.c

ASM_SOURCES := boot/entry.asm

C_OBJS  := $(patsubst %.c,  $(OUT_DIR)/%.o, $(C_SOURCES))
ASM_OBJS := $(patsubst %.asm, $(OUT_DIR)/%.o, $(ASM_SOURCES))
LTL_OBJ  := $(OUT_DIR)/lateralus_code.o

.PHONY: all clean iso run run-kvm install-deps

all: $(KERNEL_ELF)

$(OUT_DIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_DIR)/%.o: %.asm
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) $< -o $@

$(LTL_OBJ): $(LTL_SOURCES)
	@mkdir -p $(OUT_DIR)
	$(LTLC) $(LTLFLAGS) --compile-obj -o $@ $(LTL_SOURCES)

$(KERNEL_ELF): $(C_OBJS) $(ASM_OBJS) $(LTL_OBJ)
	$(CC) -nostdlib -T boot/linker.ld -o $@ $^ -lgcc
	@echo "Built: $@"

iso: $(KERNEL_ELF)
	@mkdir -p $(ISO_DIR)/boot/grub
	cp $(KERNEL_ELF) $(ISO_DIR)/boot/lateralus.elf
	echo 'set timeout=3'                            > $(ISO_DIR)/boot/grub/grub.cfg
	echo 'set default=0'                           >> $(ISO_DIR)/boot/grub/grub.cfg
	echo 'menuentry "LateralusOS $(EDITION)" {'    >> $(ISO_DIR)/boot/grub/grub.cfg
	echo '  multiboot2 /boot/lateralus.elf'        >> $(ISO_DIR)/boot/grub/grub.cfg
	echo '  boot'                                  >> $(ISO_DIR)/boot/grub/grub.cfg
	echo '}'                                       >> $(ISO_DIR)/boot/grub/grub.cfg
	grub-mkrescue -o $(ISO_FILE) $(ISO_DIR)
	@echo "ISO: $(ISO_FILE)"

run: iso
	qemu-system-x86_64 \
	  -m 2G \
	  -smp 4 \
	  -cpu host \
	  -cdrom $(ISO_FILE) \
	  -boot d \
	  -vga std \
	  -audiodev pa,id=audio0 \
	  -machine pcspk-audiodev=audio0 \
	  -netdev user,id=net0 -device e1000,netdev=net0 \
	  -usb -device usb-kbd -device usb-mouse \
	  -serial stdio

run-kvm: iso
	qemu-system-x86_64 \
	  -enable-kvm \
	  -m 4G \
	  -smp 8 \
	  -cpu host \
	  -cdrom $(ISO_FILE) \
	  -boot d \
	  -vga virtio \
	  -netdev user,id=net0 -device virtio-net,netdev=net0 \
	  -usb -device usb-kbd -device usb-mouse \
	  -serial stdio

rpi5: $(LTL_OBJ)
	$(CC) $(CFLAGS) -march=armv8.2-a -DTARGET_RPI5 -T boot/linker-rpi5.ld \
	  -o $(OUT_DIR)/lateralus-rpi5.elf $(C_OBJS) $(LTL_OBJ) -lgcc
	@echo "RPi5 image: $(OUT_DIR)/lateralus-rpi5.elf"

clean:
	rm -rf build/

install-deps:
	sudo apt-get install -y nasm gcc grub-pc-bin grub-common xorriso qemu-system-x86

loc:
	@find . -name '*.ltl' | xargs wc -l | tail -1
	@echo "files:" $$(find . -name '*.ltl' | wc -l)
