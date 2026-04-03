/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — PS/2 Mouse Driver Implementation
 * ═══════════════════════════════════════════════════════════════════════
 * Standard PS/2 mouse: 3-byte packets.
 * Byte 0: [Y-overflow | X-overflow | Y-sign | X-sign | 1 | Mid | Right | Left]
 * Byte 1: X movement
 * Byte 2: Y movement
 * ═══════════════════════════════════════════════════════════════════════ */

#include "mouse.h"

/* ── Port I/O (defined in kernel_stub.c, declared here) ───────────────── */

extern void outb(uint16_t port, uint8_t val);
extern uint8_t inb(uint16_t port);

/* ── PS/2 Controller ports ────────────────────────────────────────────── */

#define PS2_DATA    0x60
#define PS2_STATUS  0x64
#define PS2_CMD     0x64

/* ── Global mouse state ──────────────────────────────────────────────── */

static MouseState ms = { 0, 0, 0, 0, 0, {0,0,0}, 0, 0 };

/* ── Wait helpers ─────────────────────────────────────────────────────── */

static void mouse_wait_write(void) {
    int timeout = 100000;
    while (timeout-- > 0) {
        if (!(inb(PS2_STATUS) & 0x02)) return;
    }
}

static void mouse_wait_read(void) {
    int timeout = 100000;
    while (timeout-- > 0) {
        if (inb(PS2_STATUS) & 0x01) return;
    }
}

/* ── Send command to mouse (via PS/2 controller) ──────────────────────── */

static void mouse_write(uint8_t byte) {
    mouse_wait_write();
    outb(PS2_CMD, 0xD4);      /* "next byte goes to port 2 (mouse)" */
    mouse_wait_write();
    outb(PS2_DATA, byte);
}

static uint8_t mouse_read(void) {
    mouse_wait_read();
    return inb(PS2_DATA);
}

/* ── Initialize PS/2 mouse ────────────────────────────────────────────── */

void mouse_init(void) {
    /* Enable auxiliary device (mouse) */
    mouse_wait_write();
    outb(PS2_CMD, 0xA8);

    /* Enable IRQ12 — read controller config, set bit 1, write back */
    mouse_wait_write();
    outb(PS2_CMD, 0x20);       /* read config byte */
    mouse_wait_read();
    uint8_t config = inb(PS2_DATA);
    config |= 0x02;            /* enable IRQ12 (auxiliary interrupt) */
    config &= ~0x20;           /* clear "disable mouse clock" bit */
    mouse_wait_write();
    outb(PS2_CMD, 0x60);       /* write config byte */
    mouse_wait_write();
    outb(PS2_DATA, config);

    /* Reset mouse */
    mouse_write(0xFF);
    mouse_read();              /* ACK */
    mouse_read();              /* self-test result (0xAA) */
    mouse_read();              /* mouse ID */

    /* Set defaults */
    mouse_write(0xF6);
    mouse_read();              /* ACK */

    /* Enable data reporting */
    mouse_write(0xF4);
    mouse_read();              /* ACK */

    ms.cycle = 0;
    ms.ready = 0;
}

/* ── Handle one byte from IRQ12 ───────────────────────────────────────── */

void mouse_handle_byte(uint8_t byte) {
    ms.packet[ms.cycle] = byte;

    if (ms.cycle == 0) {
        /* Byte 0 must have bit 3 set (always-1 bit) — resync if not */
        if (!(byte & 0x08)) {
            ms.cycle = 0;
            return;
        }
    }

    ms.cycle++;
    if (ms.cycle >= 3) {
        ms.cycle = 0;
        ms.ready = 1;

        /* Decode packet */
        uint8_t flags = ms.packet[0];
        ms.left   = (flags & 0x01) ? 1 : 0;
        ms.right  = (flags & 0x02) ? 1 : 0;
        ms.middle = (flags & 0x04) ? 1 : 0;

        /* Discard if overflow */
        if (flags & 0xC0) {
            ms.ready = 0;
            return;
        }

        /* X movement (sign-extend via bit 4 of flags) */
        int16_t raw_dx = (int16_t)ms.packet[1];
        if (flags & 0x10) raw_dx |= 0xFF00;  /* sign extend */
        ms.dx = (int8_t)raw_dx;

        /* Y movement (sign-extend via bit 5 of flags) */
        int16_t raw_dy = (int16_t)ms.packet[2];
        if (flags & 0x20) raw_dy |= 0xFF00;  /* sign extend */
        ms.dy = (int8_t)raw_dy;
    }
}

MouseState *mouse_get_state(void) {
    return &ms;
}
