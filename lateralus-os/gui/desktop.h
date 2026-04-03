/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Desktop Environment
 * ═══════════════════════════════════════════════════════════════════════
 * High-level desktop manager: launches default windows, handles the
 * main GUI event loop, and bridges the kernel's IRQ-driven input to
 * the GUI widget system.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_DESKTOP_H
#define LATERALUS_DESKTOP_H

#include "gui.h"

/* ── Desktop state ────────────────────────────────────────────────────── */

typedef struct {
    GuiContext  gui;
    uint8_t     mode;        /* 0 = text (VGA), 1 = GUI (framebuffer) */
    uint32_t    frame_count;
    uint32_t    uptime_ticks; /* kernel ticks since boot */
    int         sysmon_idx;  /* window index of system monitor (-1 = none) */
    uint8_t     alt_held;    /* 1 = Alt key currently held */
    uint8_t     ctrl_held;   /* 1 = Ctrl key currently held */
} Desktop;

/* ── Public API ───────────────────────────────────────────────────────── */

/* Initialize the desktop (sets up default windows + wallpaper) */
void desktop_init(Desktop *dt);

/* Main loop tick — called from kernel timer IRQ or polling loop */
void desktop_tick(Desktop *dt);

/* Process mouse packet from PS/2 driver */
void desktop_mouse_event(Desktop *dt, int8_t dx, int8_t dy,
                          uint8_t left, uint8_t right);

/* Process keyboard scancode from PS/2 driver */
void desktop_key_event(Desktop *dt, char ascii);

/* Full render (call when dirty) */
void desktop_render(Desktop *dt);

/* Open the "About" window */
void desktop_open_about(Desktop *dt);

/* Open the terminal window */
void desktop_open_terminal(Desktop *dt);

/* Open system monitor */
void desktop_open_sysmon(Desktop *dt);

/* Open a file viewer window */
void desktop_open_file_viewer(Desktop *dt, const char *name, const char *content);

/* Setup start menu + context menu + desktop icons */
void desktop_setup_menus(Desktop *dt);
void desktop_setup_icons(Desktop *dt);

#endif /* LATERALUS_DESKTOP_H */
