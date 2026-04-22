/* =======================================================================
 * LateralusOS — Functional GUI Terminal
 * =======================================================================
 * Full interactive terminal emulator within a GUI window.
 * Supports command input, output scrollback, and VFS integration.
 *
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ======================================================================= */

#ifndef LATERALUS_TERMINAL_H
#define LATERALUS_TERMINAL_H

#include "gui.h"

/* -- Limits ------------------------------------------------------------- */

#define TERM_MAX_LINES   200
#define TERM_COLS         80
#define TERM_CMD_SIZE    128
#define TERM_PATH_SIZE    64
#define TERM_MAX_TERMS     4
#define TERM_HIST_SIZE    16

/* -- Terminal state ----------------------------------------------------- */

typedef struct {
    /* Scrollback buffer — circular line buffer */
    char    lines[TERM_MAX_LINES][TERM_COLS];
    int     line_count;        /* total lines written */
    int     scroll_offset;     /* lines scrolled up from bottom */

    /* Command input */
    char    cmd_buf[TERM_CMD_SIZE];
    int     cmd_len;

    /* Working directory (VFS path) */
    char    cwd[TERM_PATH_SIZE];
    int     cwd_node;          /* ramfs node index of cwd */

    /* Associated GUI window */
    int     win_idx;

    /* State */
    uint8_t active;
    uint32_t cursor_tick;
    uint8_t  cursor_visible;

    /* Command history */
    char    history[TERM_HIST_SIZE][TERM_CMD_SIZE];
    int     hist_count;
    int     hist_pos;

    /* Dirty flag — set when content changes, cleared after refresh */
    uint8_t dirty;

    /* grugbot420 interactive mode ------------------------------------- */
    uint8_t  grug_mode;     /* 1 = input feeds grugbot, not shell */
    uint8_t  grug_mood;     /* 0 chill, 1 blazed, 2 enlightened */
    uint8_t  grug_hits;
    uint32_t grug_rng;      /* xorshift32 seed */
} GuiTerminal;

/* -- Kernel info access (defined in kernel_stub.c / heap.c) ------------- */

extern volatile uint64_t tick_count;
extern uint64_t total_system_memory;

/* -- Public API --------------------------------------------------------- */

/* Initialize the terminal subsystem */
void term_init(void);

/* Create a new terminal attached to a new window. Returns terminal index or -1. */
int term_create(GuiContext *gui);

/* Get terminal by its window index, or NULL if not a terminal window */
GuiTerminal *term_get_by_window(int win_idx);

/* Process a keystroke for the terminal */
void term_key(GuiTerminal *t, char c);

/* Output a character to the terminal */
void term_putc(GuiTerminal *t, char c);

/* Output a string to the terminal */
void term_puts(GuiTerminal *t, const char *s);

/* Output a number to the terminal */
void term_put_uint(GuiTerminal *t, uint64_t val);

/* Output a hex number */
void term_put_hex(GuiTerminal *t, uint64_t val);

/* Execute a command in the terminal */
void term_exec(GuiTerminal *t, const char *cmd);

/* Update the window content from the terminal buffer */
void term_refresh(GuiTerminal *t, GuiContext *gui);

/* Tick — cursor blink, etc. */
void term_tick(GuiTerminal *t, uint32_t tick);

/* Get number of active terminals */
int term_count(void);

/* Start grugbot420 mode inside a freshly created terminal (idx from term_create) */
void term_start_grugbot(int tidx);

#endif /* LATERALUS_TERMINAL_H */
