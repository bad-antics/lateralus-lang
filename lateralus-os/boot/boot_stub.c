/* =======================================================================
 * LateralusOS — C Bootstrap Stub (Enhanced v0.2.0)
 * =======================================================================
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 *
 * This thin C layer bridges the ASM bootloader and the Lateralus kernel.
 * It performs minimal hardware init that must happen before the Lateralus
 * runtime is ready:
 *   1. Parse multiboot2 info structure (with full validation)
 *   2. Initialize serial port for debug output
 *   3. Clear screen
 *   4. Validate framebuffer parameters before kernel handoff
 *   5. Call kernel_main() (generated from kernel/main.ltl)
 * ======================================================================= */

#include "../gui/types.h"

/* -- Port I/O ----------------------------------------------------------- */

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

/* -- Serial Port (COM1 = 0x3F8) ---------------------------------------- */

#define COM1 0x3F8

static void serial_init(void) {
    outb(COM1 + 1, 0x00);  /* Disable interrupts              */
    outb(COM1 + 3, 0x80);  /* Enable DLAB (baud rate divisor)  */
    outb(COM1 + 0, 0x03);  /* 38400 baud (lo byte)             */
    outb(COM1 + 1, 0x00);  /*             (hi byte)            */
    outb(COM1 + 3, 0x03);  /* 8 bits, no parity, one stop bit  */
    outb(COM1 + 2, 0xC7);  /* Enable FIFO, 14-byte threshold   */
    outb(COM1 + 4, 0x0B);  /* IRQs enabled, RTS/DSR set        */
}

static void serial_putc(char c) {
    while (!(inb(COM1 + 5) & 0x20));  /* Wait for transmit ready */
    outb(COM1, (uint8_t)c);
}

static void serial_puts(const char *s) {
    while (*s) serial_putc(*s++);
}

/* -- VGA Text Mode ------------------------------------------------------ */

static volatile uint16_t *const VGA = (volatile uint16_t*)0xB8000;
#define VGA_WIDTH  80
#define VGA_HEIGHT 25

static int vga_x = 0, vga_y = 0;
static uint8_t vga_color = 0x0F;  /* white on black */

static void vga_clear(void) {
    for (int i = 0; i < VGA_WIDTH * VGA_HEIGHT; i++)
        VGA[i] = (uint16_t)' ' | ((uint16_t)vga_color << 8);
    vga_x = 0;
    vga_y = 0;
}

static void vga_scroll(void) {
    /* Scroll up one line */
    for (int y = 0; y < VGA_HEIGHT - 1; y++)
        for (int x = 0; x < VGA_WIDTH; x++)
            VGA[y * VGA_WIDTH + x] = VGA[(y + 1) * VGA_WIDTH + x];
    /* Clear last line */
    for (int x = 0; x < VGA_WIDTH; x++)
        VGA[(VGA_HEIGHT - 1) * VGA_WIDTH + x] = (uint16_t)' ' | ((uint16_t)vga_color << 8);
    vga_y = VGA_HEIGHT - 1;
}

static void vga_putc(char c) {
    if (c == '\n') {
        vga_x = 0;
        vga_y++;
    } else if (c == '\r') {
        vga_x = 0;
    } else if (c == '\t') {
        vga_x = (vga_x + 8) & ~7;
    } else {
        VGA[vga_y * VGA_WIDTH + vga_x] = (uint16_t)c | ((uint16_t)vga_color << 8);
        vga_x++;
    }
    if (vga_x >= VGA_WIDTH) { vga_x = 0; vga_y++; }
    if (vga_y >= VGA_HEIGHT) vga_scroll();
}

static void vga_puts(const char *s) {
    while (*s) vga_putc(*s++);
}

/* -- Boot banner -------------------------------------------------------- */

static void print_banner(void) {
    vga_color = 0x0D;  /* light magenta */
    vga_puts("  _         _                 _           ___  ____  \n");
    vga_puts(" | |   __ _| |_ ___ _ _ __ _ | |_  _ ___ / _ \\/ ___| \n");
    vga_puts(" | |__/ _` |  _/ -_) '_/ _` || | || (_-<| | | \\___ \\ \n");
    vga_puts(" |____\\__,_|\\__\\___|_| \\__,_||_|\\_,_/__/ \\___/|____/ \n");
    vga_color = 0x07;  /* light grey */
    vga_puts("\n");
    vga_puts(" LateralusOS v0.2.0 — Created by bad-antics\n");
    vga_puts(" Built with the Lateralus programming language\n");
    vga_puts(" ----------------------------------------------------\n\n");
    vga_color = 0x0F;  /* white */
}

/* -- Multiboot2 info parsing ------------------------------------------- */

#include "../gui/bootinfo.h"

BootInfo boot_info;   /* globally visible — kernel_stub.c reads this */

static void parse_multiboot(uint32_t magic, uint32_t mb_info_addr) {
    /* Basic multiboot2 parsing — extract memory info */
    boot_info.total_memory_kb = 0;
    boot_info.available_memory_kb = 0;
    boot_info.framebuffer_addr = 0;
    boot_info.fb_width = 0;
    boot_info.fb_height = 0;
    boot_info.fb_pitch = 0;
    boot_info.fb_bpp = 0;
    boot_info.fb_available = 0;
    boot_info.boot_cmd[0] = '\0';

    if (magic != 0x36D76289) {
        serial_puts("[BOOT] Warning: Invalid multiboot2 magic\n");
        return;
    }

    /* Walk multiboot2 tags */
    uint8_t *ptr = (uint8_t*)(uint64_t)mb_info_addr;
    uint32_t total_size = *(uint32_t*)ptr;
    ptr += 8;  /* Skip total_size and reserved */

    while ((uint64_t)(ptr - (uint8_t*)(uint64_t)mb_info_addr) < total_size) {
        uint32_t tag_type = *(uint32_t*)ptr;
        uint32_t tag_size = *(uint32_t*)(ptr + 4);

        if (tag_type == 0) break;  /* End tag */

        switch (tag_type) {
            case 4: /* Basic memory info */
                boot_info.total_memory_kb =
                    (uint64_t)(*(uint32_t*)(ptr + 8)) +
                    (uint64_t)(*(uint32_t*)(ptr + 12)) * 1024;
                break;
            case 1: /* Boot command line */
                {
                    const char *cmd = (const char*)(ptr + 8);
                    int len = 0;
                    while (cmd[len] && len < 255) {
                        boot_info.boot_cmd[len] = cmd[len];
                        len++;
                    }
                    boot_info.boot_cmd[len] = '\0';
                }
                break;
            case 8: /* Framebuffer info */
                {
                    boot_info.framebuffer_addr = *(uint64_t*)(ptr + 8);
                    boot_info.fb_pitch  = *(uint32_t*)(ptr + 16);
                    boot_info.fb_width  = *(uint32_t*)(ptr + 20);
                    boot_info.fb_height = *(uint32_t*)(ptr + 24);
                    boot_info.fb_bpp    = *(uint8_t*)(ptr + 28);
                    boot_info.fb_available = 1;
                    serial_puts("[BOOT] Framebuffer detected: ");
                    /* Print width x height */
                    char fbuf[24];
                    uint64_t w = boot_info.fb_width;
                    int fp = 0;
                    if (w == 0) fbuf[fp++] = '0';
                    else {
                        char rev[12]; int rp = 0;
                        while (w > 0) { rev[rp++] = '0' + (w % 10); w /= 10; }
                        while (rp > 0) fbuf[fp++] = rev[--rp];
                    }
                    fbuf[fp++] = 'x';
                    w = boot_info.fb_height;
                    if (w == 0) fbuf[fp++] = '0';
                    else {
                        char rev[12]; int rp = 0;
                        while (w > 0) { rev[rp++] = '0' + (w % 10); w /= 10; }
                        while (rp > 0) fbuf[fp++] = rev[--rp];
                    }
                    fbuf[fp] = '\0';
                    serial_puts(fbuf);
                    serial_puts("\n");
                    /* Print framebuffer physical address */
                    serial_puts("[BOOT] fb_addr=0x");
                    {
                        uint64_t a = boot_info.framebuffer_addr;
                        char hex[17];
                        int i;
                        for (i = 15; i >= 0; i--) {
                            int d = a & 0xF;
                            hex[i] = d < 10 ? '0' + d : 'a' + d - 10;
                            a >>= 4;
                        }
                        hex[16] = '\0';
                        serial_puts(hex);
                    }
                    serial_puts("\n");
                }
                break;
        }

        /* Advance to next tag (8-byte aligned) */
        ptr += (tag_size + 7) & ~7;
    }
}

/* -- External: Lateralus kernel entry ----------------------------------- */

extern void kernel_main(void);

/* -- Boot init — called from boot.asm ----------------------------------- */

void boot_init(uint32_t magic, uint32_t mb_info_addr) {
    /* 1. Serial output for debug */
    serial_init();
    serial_puts("\n[BOOT] LateralusOS bootstrap starting...\n");

    /* 2. Clear VGA screen */
    vga_clear();

    /* 3. Parse multiboot info */
    parse_multiboot(magic, mb_info_addr);
    serial_puts("[BOOT] Multiboot info parsed\n");
    serial_puts("[BOOT] boot_cmd=[");
    serial_puts(boot_info.boot_cmd);
    serial_puts("]\n");
    if (boot_info.fb_available) {
        serial_puts("[BOOT] fb_available=YES\n");
    } else {
        serial_puts("[BOOT] fb_available=NO\n");
    }

    /* 4. Print boot banner */
    print_banner();

    /* 5. Report memory */
    vga_puts("[boot] Memory: ");
    /* Simple integer printing without printf */
    {
        uint64_t mb = boot_info.total_memory_kb / 1024;
        char buf[20];
        int pos = 0;
        if (mb == 0) { buf[pos++] = '0'; }
        else {
            uint64_t tmp = mb;
            char rev[20];
            int rpos = 0;
            while (tmp > 0) { rev[rpos++] = '0' + (tmp % 10); tmp /= 10; }
            while (rpos > 0) buf[pos++] = rev[--rpos];
        }
        buf[pos] = '\0';
        vga_puts(buf);
    }
    vga_puts(" MB detected\n");

    /* 6. Validate framebuffer before kernel handoff */
    if (boot_info.fb_available) {
        serial_puts("[BOOT] Validating framebuffer parameters...\n");
        int fb_ok = 1;

        /* Check address is non-null and above 1MB (below that is BIOS/VGA) */
        if (boot_info.framebuffer_addr == 0) {
            serial_puts("[BOOT] ERROR: framebuffer address is NULL!\n");
            fb_ok = 0;
        } else if (boot_info.framebuffer_addr < 0x100000) {
            serial_puts("[BOOT] WARNING: framebuffer address < 1MB (may be VGA text)\n");
        }

        /* Check dimensions are sane */
        if (boot_info.fb_width == 0 || boot_info.fb_height == 0) {
            serial_puts("[BOOT] ERROR: framebuffer dimensions are zero!\n");
            fb_ok = 0;
        }
        if (boot_info.fb_width > 4096 || boot_info.fb_height > 4096) {
            serial_puts("[BOOT] WARNING: framebuffer dimensions > 4096, may be bogus\n");
        }

        /* Check pitch is at least width * bytes_per_pixel */
        {
            uint32_t min_pitch = boot_info.fb_width * (boot_info.fb_bpp / 8);
            if (boot_info.fb_pitch < min_pitch) {
                serial_puts("[BOOT] ERROR: fb_pitch too small for width!\n");
                serial_puts("[BOOT] Correcting pitch to minimum\n");
                boot_info.fb_pitch = min_pitch;
            }
        }

        /* Check BPP */
        if (boot_info.fb_bpp != 32) {
            serial_puts("[BOOT] WARNING: fb_bpp is not 32 (expected 32bpp BGRA)\n");
        }

        if (fb_ok) {
            serial_puts("[BOOT] Framebuffer validation: PASS\n");
        } else {
            serial_puts("[BOOT] Framebuffer validation: FAIL — disabling GUI\n");
            boot_info.fb_available = 0;
        }
    } else {
        serial_puts("[BOOT] No framebuffer — text mode only\n");
    }

    /* 7. Hand off to Lateralus kernel */
    serial_puts("[BOOT] Jumping to kernel_main()...\n");
    vga_puts("[boot] Starting Lateralus kernel...\n\n");

    kernel_main();

    /* Should never return */
    serial_puts("[BOOT] FATAL: kernel_main() returned!\n");
    vga_color = 0x4F;  /* white on red */
    vga_puts("\n*** KERNEL PANIC: kernel_main() returned ***\n");
    while (1) __asm__ volatile ("hlt");
}
