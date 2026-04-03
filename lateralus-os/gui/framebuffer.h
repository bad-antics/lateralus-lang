/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Framebuffer Driver API (Enhanced v0.2.0)
 * ═══════════════════════════════════════════════════════════════════════
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */
#ifndef LTL_FRAMEBUFFER_H
#define LTL_FRAMEBUFFER_H

#include "types.h"

/* ── Color helpers ────────────────────────────────────────────────────── */

#define FB_RGB(r, g, b) ((uint32_t)((r) << 16 | (g) << 8 | (b)))

/* Named colors — Catppuccin Mocha palette */
#define COL_BLACK       FB_RGB(0x12, 0x12, 0x12)
#define COL_WHITE       FB_RGB(0xF0, 0xF0, 0xF0)
#define COL_BG_DARK     FB_RGB(0x1E, 0x1E, 0x2E)
#define COL_BG_DARKER   FB_RGB(0x11, 0x11, 0x1B)
#define COL_BG_MID      FB_RGB(0x28, 0x28, 0x3C)
#define COL_BG_LIGHT    FB_RGB(0x35, 0x35, 0x50)
#define COL_SURFACE0    FB_RGB(0x31, 0x32, 0x44)
#define COL_SURFACE1    FB_RGB(0x45, 0x47, 0x5A)
#define COL_SURFACE2    FB_RGB(0x58, 0x5B, 0x70)
#define COL_OVERLAY0    FB_RGB(0x6C, 0x70, 0x86)
#define COL_OVERLAY1    FB_RGB(0x7F, 0x84, 0x9C)
#define COL_ACCENT      FB_RGB(0x74, 0x87, 0xE8)
#define COL_ACCENT2     FB_RGB(0xA6, 0xE3, 0xA1)
#define COL_ACCENT3     FB_RGB(0xF9, 0xE2, 0xAF)
#define COL_ACCENT4     FB_RGB(0xF3, 0x8B, 0xA8)
#define COL_TEXT        FB_RGB(0xCD, 0xD6, 0xF4)
#define COL_SUBTEXT     FB_RGB(0xA6, 0xAD, 0xC8)
#define COL_TEXT_DIM    FB_RGB(0x6C, 0x70, 0x86)
#define COL_LAVENDER    FB_RGB(0xB4, 0xBE, 0xFE)
#define COL_BORDER      FB_RGB(0x45, 0x47, 0x5A)
#define COL_TASKBAR     FB_RGB(0x18, 0x18, 0x25)
#define COL_TITLE_BG    FB_RGB(0x31, 0x32, 0x44)
#define COL_CLOSE_RED   FB_RGB(0xF3, 0x8B, 0xA8)
#define COL_MIN_YEL     FB_RGB(0xF9, 0xE2, 0xAF)
#define COL_MAX_GRN     FB_RGB(0xA6, 0xE3, 0xA1)

/* ── Framebuffer state ────────────────────────────────────────────────── */

typedef struct {
    uint32_t *addr;         /* Render target (backbuf or hw)    */
    uint32_t *hw_addr;      /* Real hardware framebuffer addr   */
    uint32_t *backbuf;      /* Back buffer (NULL if disabled)   */
    uint32_t  width;        /* Screen width in pixels           */
    uint32_t  height;       /* Screen height in pixels          */
    uint32_t  pitch;        /* Bytes per scanline               */
    uint32_t  buf_size;     /* Total buffer size in bytes       */
    uint8_t   bpp;          /* Bits per pixel (should be 32)    */
    int       available;    /* 1 if framebuffer was provided    */
    int       double_buf;   /* 1 if double-buffered             */
} Framebuffer;

extern Framebuffer fb;

/* ── Core drawing ─────────────────────────────────────────────────────── */

void fb_init(uint32_t *addr, uint32_t w, uint32_t h, uint32_t pitch, uint8_t bpp);

/* ── Double buffering ─────────────────────────────────────────────────── */

void fb_enable_double_buffer(void *backbuf_mem);
void fb_swap(void);   /* Copy back buffer → hardware framebuffer */
void fb_putpixel(int32_t x, int32_t y, uint32_t color);
void fb_fill_rect(int32_t x, int32_t y, int32_t w, int32_t h, uint32_t color);
void fb_draw_rect(int32_t x, int32_t y, int32_t w, int32_t h, uint32_t color);
void fb_draw_line(int32_t x0, int32_t y0, int32_t x1, int32_t y1, uint32_t color);
void fb_draw_circle(int32_t cx, int32_t cy, int32_t r, uint32_t color);
void fb_fill_circle(int32_t cx, int32_t cy, int32_t r, uint32_t color);
void fb_clear(uint32_t color);

/* ── Rounded rectangles ───────────────────────────────────────────────── */

void fb_fill_rounded_rect(int32_t x, int32_t y, int32_t w, int32_t h,
                           int32_t radius, uint32_t color);

/* ── Text rendering (8x16 bitmap font) ────────────────────────────────── */

void fb_putchar(int32_t x, int32_t y, char c, uint32_t fg, uint32_t bg);
void fb_putchar_nobg(int32_t x, int32_t y, char c, uint32_t fg);
void fb_puts(int32_t x, int32_t y, const char *s, uint32_t fg, uint32_t bg);
void fb_puts_nobg(int32_t x, int32_t y, const char *s, uint32_t fg);
int  fb_text_width(const char *s);

/* Font metrics */
#define FONT_W 8
#define FONT_H 16

/* ── Blending ─────────────────────────────────────────────────────────── */

uint32_t fb_blend(uint32_t bg, uint32_t fg, uint8_t alpha);

/* ── Gradient ─────────────────────────────────────────────────────────── */

void fb_fill_gradient_v(int32_t x, int32_t y, int32_t w, int32_t h,
                         uint32_t top_color, uint32_t bot_color);

/* ── Hardware cursor helpers (bypass double buffer for instant cursor) ── */

void     fb_putpixel_hw(int32_t x, int32_t y, uint32_t color);
uint32_t fb_getpixel_hw(int32_t x, int32_t y);

/* ── Diagnostics ──────────────────────────────────────────────────────── */

void fb_dump_diagnostics(void);

#endif /* LTL_FRAMEBUFFER_H */
