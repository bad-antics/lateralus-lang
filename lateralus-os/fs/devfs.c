/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — /dev Virtual Device Filesystem Implementation
 * ═══════════════════════════════════════════════════════════════════════
 * Creates device files under /dev/ in ramfs.  Each device "file" is
 * regenerated on read to simulate device behaviour.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "devfs.h"
#include "ramfs.h"

/* ── Externals ────────────────────────────────────────────────────────── */
extern volatile uint64_t tick_count;

/* We need boot_info for framebuffer details */
#include "../gui/bootinfo.h"
extern BootInfo boot_info;

/* ── Simple helpers (local) ───────────────────────────────────────────── */

static int df_strlen(const char *s) {
    int n = 0;
    while (s[n]) n++;
    return n;
}

static void df_strcpy(char *dst, const char *src) {
    while (*src) *dst++ = *src++;
    *dst = '\0';
}

static void df_strcat(char *dst, const char *src) {
    while (*dst) dst++;
    while (*src) *dst++ = *src++;
    *dst = '\0';
}

static void df_uint_to_str(uint64_t val, char *buf, int buflen) {
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char tmp[24];
    int i = 0;
    while (val > 0 && i < 22) {
        tmp[i++] = '0' + (val % 10);
        val /= 10;
    }
    int j = 0;
    while (i > 0 && j < buflen - 1) buf[j++] = tmp[--i];
    buf[j] = '\0';
}

/* ── LFSR Pseudo-Random Number Generator ─────────────────────────────── */

static uint64_t lfsr_state = 0;

static void lfsr_seed(void) {
    lfsr_state = tick_count ^ 0x5DEECE66DULL;
    if (lfsr_state == 0) lfsr_state = 1;
}

static uint32_t lfsr_next(void) {
    /* xorshift64 */
    uint64_t s = lfsr_state;
    s ^= s << 13;
    s ^= s >> 7;
    s ^= s << 17;
    lfsr_state = s;
    return (uint32_t)(s & 0xFFFFFFFF);
}

/* ── Device ramfs indices ─────────────────────────────────────────────── */

static int dev_dir_idx    = -1;
static int dev_null_idx   = -1;
static int dev_zero_idx   = -1;
static int dev_random_idx = -1;
static int dev_serial_idx = -1;
static int dev_fb0_idx    = -1;

/* ═══════════════════════════════════════════════════════════════════════
 * Device Content Generators
 * ═══════════════════════════════════════════════════════════════════════ */

static void gen_null(void) {
    /* /dev/null is always empty */
    ramfs_write(dev_null_idx, "", 0);
}

static void gen_zero(void) {
    /* /dev/zero returns 64 zero bytes (printable representation) */
    char buf[128];
    df_strcpy(buf, "(zero device: infinite NUL stream)\n");
    df_strcat(buf, "\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\n");
    df_strcat(buf, "\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\n");
    ramfs_write(dev_zero_idx, buf, df_strlen(buf));
}

static void gen_random(void) {
    /* /dev/random returns a few lines of hex random data */
    char buf[256];
    char hex[12];
    const char *hx = "0123456789abcdef";

    lfsr_seed();

    df_strcpy(buf, "");

    /* 4 lines of 16 random hex bytes each */
    for (int line = 0; line < 4; line++) {
        for (int i = 0; i < 8; i++) {
            uint32_t r = lfsr_next();
            uint8_t b1 = (r >> 0) & 0xFF;
            uint8_t b2 = (r >> 8) & 0xFF;
            hex[0] = hx[b1 >> 4]; hex[1] = hx[b1 & 0xF];
            hex[2] = ' ';
            hex[3] = hx[b2 >> 4]; hex[4] = hx[b2 & 0xF];
            hex[5] = ' ';
            hex[6] = '\0';
            df_strcat(buf, hex);
        }
        df_strcat(buf, "\n");
    }

    ramfs_write(dev_random_idx, buf, df_strlen(buf));
}

static void gen_serial(void) {
    /* /dev/serial shows serial port info */
    char buf[128];
    df_strcpy(buf, "COM1 (0x3F8) 115200 baud 8N1\n");
    df_strcat(buf, "Status: active\n");
    ramfs_write(dev_serial_idx, buf, df_strlen(buf));
}

static void gen_fb0(void) {
    /* /dev/fb0 shows framebuffer info */
    char buf[256];
    char num[24];

    df_strcpy(buf, "Framebuffer: ");
    if (boot_info.fb_available) {
        df_uint_to_str(boot_info.fb_width, num, sizeof(num));
        df_strcat(buf, num);
        df_strcat(buf, "x");
        df_uint_to_str(boot_info.fb_height, num, sizeof(num));
        df_strcat(buf, num);
        df_strcat(buf, "x");
        df_uint_to_str(boot_info.fb_bpp, num, sizeof(num));
        df_strcat(buf, num);
        df_strcat(buf, "\n");

        df_strcat(buf, "Address:     0x");
        /* Simple hex of fb addr */
        {
            uint64_t addr = boot_info.framebuffer_addr;
            const char *hx = "0123456789abcdef";
            char hbuf[17];
            for (int i = 15; i >= 0; i--) {
                hbuf[15 - i] = hx[(addr >> (i * 4)) & 0xF];
            }
            hbuf[16] = '\0';
            /* Skip leading zeros */
            char *p = hbuf;
            while (*p == '0' && *(p + 1)) p++;
            df_strcat(buf, p);
        }
        df_strcat(buf, "\n");

        df_strcat(buf, "Pitch:       ");
        df_uint_to_str(boot_info.fb_pitch, num, sizeof(num));
        df_strcat(buf, num);
        df_strcat(buf, " bytes/row\n");
    } else {
        df_strcat(buf, "not available (text mode)\n");
    }

    ramfs_write(dev_fb0_idx, buf, df_strlen(buf));
}

/* ═══════════════════════════════════════════════════════════════════════
 * Public API
 * ═══════════════════════════════════════════════════════════════════════ */

void devfs_init(void) {
    /* Create /dev directory under root (ramfs index 0) */
    dev_dir_idx = ramfs_mkdir(0, "dev");
    if (dev_dir_idx < 0) return;

    /* Create device files */
    dev_null_idx   = ramfs_create(dev_dir_idx, "null");
    dev_zero_idx   = ramfs_create(dev_dir_idx, "zero");
    dev_random_idx = ramfs_create(dev_dir_idx, "random");
    dev_serial_idx = ramfs_create(dev_dir_idx, "serial");
    dev_fb0_idx    = ramfs_create(dev_dir_idx, "fb0");

    /* Generate initial content */
    gen_null();
    gen_zero();
    gen_random();
    gen_serial();
    gen_fb0();
}

int devfs_refresh_file(const char *name) {
    if (!name) return -1;

    const char *n = name;
    /* Skip leading "/dev/" if present */
    if (n[0] == '/') {
        n++;
        if (n[0] == 'd' && n[1] == 'e' && n[2] == 'v' && n[3] == '/') {
            n += 4;
        }
    }

    if (n[0] == 'n' && n[1] == 'u') { gen_null();   return 0; }
    if (n[0] == 'z' && n[1] == 'e') { gen_zero();   return 0; }
    if (n[0] == 'r' && n[1] == 'a') { gen_random(); return 0; }
    if (n[0] == 's' && n[1] == 'e') { gen_serial(); return 0; }
    if (n[0] == 'f' && n[1] == 'b') { gen_fb0();    return 0; }

    return -1;
}
