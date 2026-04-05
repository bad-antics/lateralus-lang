/* =======================================================================
 * LateralusOS — Functional GUI Terminal Implementation
 * =======================================================================
 * Full interactive terminal emulator with VFS integration.
 *
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ======================================================================= */

#include "terminal.h"
#include "../fs/ramfs.h"
#include "../kernel/tasks.h"
#include "../kernel/heap.h"

/* -- Terminal pool ------------------------------------------------------ */

static GuiTerminal terminals[TERM_MAX_TERMS];
static int term_total = 0;

/* -- String helpers ----------------------------------------------------- */

static int _tlen(const char *s) { int n = 0; while (s[n]) n++; return n; }

static void _tcpy(char *dst, const char *src, int max) {
    int i = 0;
    while (src[i] && i < max - 1) { dst[i] = src[i]; i++; }
    dst[i] = 0;
}

static int _tcmp(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return (int)(unsigned char)*a - (int)(unsigned char)*b;
}

static int _tncmp(const char *a, const char *b, int n) {
    for (int i = 0; i < n; i++) {
        if (a[i] != b[i]) return (int)(unsigned char)a[i] - (int)(unsigned char)b[i];
        if (a[i] == 0) return 0;
    }
    return 0;
}

static void _tcat(char *dst, const char *src, int max) {
    int n = _tlen(dst);
    int i = 0;
    while (src[i] && n + i < max - 1) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

static void _titoa(uint64_t val, char *buf, int buflen) {
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char rev[24]; int rp = 0;
    while (val > 0 && rp < 23) { rev[rp++] = '0' + (val % 10); val /= 10; }
    int pos = 0;
    while (rp > 0 && pos < buflen - 1) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
}

static void _thex(uint64_t val, char *buf, int buflen) {
    const char *hex = "0123456789ABCDEF";
    char tmp[19] = "0x0000000000000000";
    for (int i = 17; i >= 2; i--) { tmp[i] = hex[val & 0xF]; val >>= 4; }
    _tcpy(buf, tmp, buflen);
}

/* -- Initialize terminal subsystem -------------------------------------- */

void term_init(void) {
    for (int i = 0; i < TERM_MAX_TERMS; i++) {
        terminals[i].active = 0;
    }
    term_total = 0;
}

/* -- Add a new line to the terminal buffer ------------------------------ */

static void term_new_line(GuiTerminal *t) {
    if (t->line_count < TERM_MAX_LINES) {
        t->lines[t->line_count][0] = 0;
        t->line_count++;
    } else {
        /* Scroll: shift all lines up by 1 */
        for (int i = 0; i < TERM_MAX_LINES - 1; i++) {
            _tcpy(t->lines[i], t->lines[i + 1], TERM_COLS);
        }
        t->lines[TERM_MAX_LINES - 1][0] = 0;
    }
    t->dirty = 1;
}

/* -- Output a character ------------------------------------------------- */

void term_putc(GuiTerminal *t, char c) {
    if (c == '\n') {
        term_new_line(t);
        return;
    }
    if (t->line_count == 0) {
        t->lines[0][0] = 0;
        t->line_count = 1;
    }
    int cur_line = t->line_count - 1;
    int len = _tlen(t->lines[cur_line]);
    if (len < TERM_COLS - 1) {
        t->lines[cur_line][len] = c;
        t->lines[cur_line][len + 1] = 0;
    } else {
        /* Line full — wrap to new line */
        term_new_line(t);
        cur_line = t->line_count - 1;
        t->lines[cur_line][0] = c;
        t->lines[cur_line][1] = 0;
    }
    t->dirty = 1;
}

/* -- Output a string ---------------------------------------------------- */

void term_puts(GuiTerminal *t, const char *s) {
    while (*s) {
        term_putc(t, *s);
        s++;
    }
}

/* -- Output a number ---------------------------------------------------- */

void term_put_uint(GuiTerminal *t, uint64_t val) {
    char buf[24];
    _titoa(val, buf, 24);
    term_puts(t, buf);
}

/* -- Output hex --------------------------------------------------------- */

void term_put_hex(GuiTerminal *t, uint64_t val) {
    char buf[24];
    _thex(val, buf, 24);
    term_puts(t, buf);
}

/* -- Print prompt ------------------------------------------------------- */

static void term_prompt(GuiTerminal *t) {
    term_puts(t, "lateralus:");
    term_puts(t, t->cwd);
    term_puts(t, "$ ");
}

/* -- History push ------------------------------------------------------- */

static void hist_push(GuiTerminal *t, const char *cmd) {
    if (cmd[0] == '\0') return;
    int dst = t->hist_count % TERM_HIST_SIZE;
    _tcpy(t->history[dst], cmd, TERM_CMD_SIZE);
    t->hist_count++;
}

/* =======================================================================
 * Terminal Commands
 * ======================================================================= */

/* Helper: resolve path relative to cwd */
static int resolve_rel(GuiTerminal *t, const char *path) {
    if (path[0] == '/') {
        return ramfs_resolve_path(path);
    }
    /* Build absolute path from cwd + relative */
    char abs[128];
    _tcpy(abs, t->cwd, 128);
    if (abs[_tlen(abs) - 1] != '/') _tcat(abs, "/", 128);
    _tcat(abs, path, 128);
    return ramfs_resolve_path(abs);
}

static void cmd_help(GuiTerminal *t) {
    term_puts(t, "LateralusOS Terminal Commands:\n");
    term_puts(t, "  help        Show this help\n");
    term_puts(t, "  ls [dir]    List directory\n");
    term_puts(t, "  cat <file>  Show file contents\n");
    term_puts(t, "  touch <f>   Create empty file\n");
    term_puts(t, "  mkdir <d>   Create directory\n");
    term_puts(t, "  rm <f>      Remove file/dir\n");
    term_puts(t, "  echo <msg>  Print message\n");
    term_puts(t, "  cd <dir>    Change directory\n");
    term_puts(t, "  pwd         Print working dir\n");
    term_puts(t, "  uname       System information\n");
    term_puts(t, "  uptime      Time since boot\n");
    term_puts(t, "  free        Memory usage\n");
    term_puts(t, "  tasks       List scheduler tasks\n");
    term_puts(t, "  clear       Clear terminal\n");
    term_puts(t, "  history     Command history\n");
    term_puts(t, "  neofetch    System info banner\n");
}

static void cmd_ls(GuiTerminal *t, const char *args) {
    int dir;
    if (args && args[0]) {
        dir = resolve_rel(t, args);
    } else {
        dir = t->cwd_node;
    }
    if (dir < 0) {
        term_puts(t, "ls: no such directory\n");
        return;
    }
    char buf[1024];
    if (ramfs_list(dir, buf, 1024) == 0) {
        if (buf[0] == 0) {
            term_puts(t, "(empty)\n");
        } else {
            term_puts(t, buf);
        }
    } else {
        term_puts(t, "ls: not a directory\n");
    }
}

static void cmd_cat(GuiTerminal *t, const char *args) {
    if (!args || !args[0]) {
        term_puts(t, "Usage: cat <file>\n");
        return;
    }
    int node = resolve_rel(t, args);
    if (node < 0) {
        term_puts(t, "cat: ");
        term_puts(t, args);
        term_puts(t, ": no such file\n");
        return;
    }
    if (ramfs_node_type(node) == RAMFS_DIR) {
        term_puts(t, "cat: ");
        term_puts(t, args);
        term_puts(t, ": is a directory\n");
        return;
    }
    char buf[RAMFS_MAX_CONTENT];
    int n = ramfs_read(node, buf, RAMFS_MAX_CONTENT);
    if (n > 0) {
        term_puts(t, buf);
        /* Ensure trailing newline */
        if (buf[n - 1] != '\n') term_putc(t, '\n');
    }
}

static void cmd_touch(GuiTerminal *t, const char *args) {
    if (!args || !args[0]) {
        term_puts(t, "Usage: touch <filename>\n");
        return;
    }
    /* Check if file already exists */
    int existing = resolve_rel(t, args);
    if (existing >= 0) return;  /* file exists, touch is a no-op */

    int idx = ramfs_create(t->cwd_node, args);
    if (idx < 0) {
        term_puts(t, "touch: cannot create file\n");
    }
}

static void cmd_mkdir(GuiTerminal *t, const char *args) {
    if (!args || !args[0]) {
        term_puts(t, "Usage: mkdir <dirname>\n");
        return;
    }
    int idx = ramfs_mkdir(t->cwd_node, args);
    if (idx < 0) {
        term_puts(t, "mkdir: cannot create directory\n");
    }
}

static void cmd_rm(GuiTerminal *t, const char *args) {
    if (!args || !args[0]) {
        term_puts(t, "Usage: rm <file|dir>\n");
        return;
    }
    int node = resolve_rel(t, args);
    if (node < 0) {
        term_puts(t, "rm: ");
        term_puts(t, args);
        term_puts(t, ": no such file\n");
        return;
    }
    if (node == 0) {
        term_puts(t, "rm: cannot remove root\n");
        return;
    }
    if (ramfs_remove(node) < 0) {
        term_puts(t, "rm: cannot remove (dir not empty?)\n");
    }
}

static void cmd_cd(GuiTerminal *t, const char *args) {
    if (!args || !args[0] || _tcmp(args, "~") == 0 ||
        _tcmp(args, "/home") == 0) {
        /* cd with no args or ~ → go to /home */
        int home = ramfs_resolve_path("/home");
        if (home >= 0) {
            t->cwd_node = home;
            _tcpy(t->cwd, "/home", TERM_PATH_SIZE);
        }
        return;
    }
    if (_tcmp(args, "/") == 0) {
        t->cwd_node = 0;
        _tcpy(t->cwd, "/", TERM_PATH_SIZE);
        return;
    }
    if (_tcmp(args, "..") == 0) {
        int parent = ramfs_node_parent(t->cwd_node);
        if (parent >= 0) {
            t->cwd_node = parent;
            ramfs_get_path(parent, t->cwd, TERM_PATH_SIZE);
        }
        return;
    }
    int dir = resolve_rel(t, args);
    if (dir < 0) {
        term_puts(t, "cd: ");
        term_puts(t, args);
        term_puts(t, ": no such directory\n");
        return;
    }
    if (ramfs_node_type(dir) != RAMFS_DIR) {
        term_puts(t, "cd: ");
        term_puts(t, args);
        term_puts(t, ": not a directory\n");
        return;
    }
    t->cwd_node = dir;
    ramfs_get_path(dir, t->cwd, TERM_PATH_SIZE);
}

static void cmd_pwd(GuiTerminal *t) {
    term_puts(t, t->cwd);
    term_putc(t, '\n');
}

static void cmd_echo(GuiTerminal *t, const char *args) {
    if (!args) { term_putc(t, '\n'); return; }

    /* Check for redirect: echo text > file */
    const char *redir = args;
    while (*redir && !(*redir == ' ' && *(redir + 1) == '>')) redir++;

    if (*redir && *(redir + 1) == '>') {
        /* Get the text before > */
        char text[256];
        int tlen = (int)(redir - args);
        for (int i = 0; i < tlen && i < 255; i++) text[i] = args[i];
        text[tlen] = 0;

        /* Get the filename after > */
        const char *fname = redir + 2;
        while (*fname == ' ') fname++;
        if (!*fname) { term_puts(t, "echo: missing filename\n"); return; }

        /* Find or create file */
        int node = resolve_rel(t, fname);
        if (node < 0) {
            node = ramfs_create(t->cwd_node, fname);
        }
        if (node < 0) {
            term_puts(t, "echo: cannot create file\n");
            return;
        }
        /* Add newline */
        _tcat(text, "\n", 256);
        ramfs_write(node, text, _tlen(text));
    } else {
        term_puts(t, args);
        term_putc(t, '\n');
    }
}

static void cmd_uname(GuiTerminal *t) {
    term_puts(t, "LateralusOS v0.2.0 (x86_64)\n");
    term_puts(t, "Kernel:  lateralus-kernel 0.1.0\n");
    term_puts(t, "Arch:    x86_64 (long mode)\n");
    term_puts(t, "Shell:   ltlsh 0.1.0\n");
}

static void cmd_uptime(GuiTerminal *t) {
    uint64_t ticks = tick_count;
    uint64_t secs  = ticks / 1000;
    uint64_t mins  = secs / 60;
    uint64_t hours = mins / 60;

    term_puts(t, "Up ");
    if (hours > 0) {
        term_put_uint(t, hours);
        term_puts(t, "h ");
    }
    term_put_uint(t, mins % 60);
    term_puts(t, "m ");
    term_put_uint(t, secs % 60);
    term_puts(t, "s  (");
    term_put_uint(t, ticks);
    term_puts(t, " ticks)\n");
}

static void cmd_free(GuiTerminal *t) {
    HeapStats hs = heap_get_stats();
    uint64_t total_mb = total_system_memory / (1024 * 1024);
    uint64_t heap_used_kb = hs.allocated / 1024;
    uint64_t heap_free_kb = (hs.end > hs.next) ?
                             (hs.end - hs.next) / 1024 : 0;

    term_puts(t, "Memory:  ");
    term_put_uint(t, total_mb);
    term_puts(t, " MB total\n");
    term_puts(t, "Heap:    ");
    term_put_uint(t, heap_used_kb);
    term_puts(t, " KB used, ");
    term_put_uint(t, heap_free_kb);
    term_puts(t, " KB free\n");
    term_puts(t, "Allocs:  ");
    term_put_uint(t, hs.alloc_count);
    term_puts(t, "\n");
}

static void cmd_tasks(GuiTerminal *t) {
    char buf[1024];
    tasks_list(buf, 1024);
    term_puts(t, buf);
    term_puts(t, "Active tasks: ");
    term_put_uint(t, (uint64_t)tasks_active_count());
    term_putc(t, '\n');
}

static void cmd_clear(GuiTerminal *t) {
    t->line_count = 0;
    t->scroll_offset = 0;
    t->dirty = 1;
}

static void cmd_history(GuiTerminal *t) {
    int start = (t->hist_count > TERM_HIST_SIZE) ?
                 t->hist_count - TERM_HIST_SIZE : 0;
    int total = (t->hist_count > TERM_HIST_SIZE) ?
                 TERM_HIST_SIZE : t->hist_count;
    for (int i = 0; i < total; i++) {
        term_puts(t, "  ");
        term_put_uint(t, (uint64_t)(start + i + 1));
        term_puts(t, "  ");
        term_puts(t, t->history[(start + i) % TERM_HIST_SIZE]);
        term_putc(t, '\n');
    }
}

static void cmd_neofetch(GuiTerminal *t) {
    uint64_t secs = tick_count / 1000;
    HeapStats hs = heap_get_stats();
    uint64_t heap_kb = hs.allocated / 1024;

    term_puts(t, "\n");
    term_puts(t, "    *         lateralus@lateralus\n");
    term_puts(t, "   * *        -------------------\n");
    term_puts(t, "  *   *       OS:     LateralusOS v0.2.0\n");
    term_puts(t, " *     *      Kernel: lateralus-kernel 0.1.0\n");
    term_puts(t, "  *   *       Arch:   x86_64 (long mode)\n");
    term_puts(t, "   * *        Shell:  ltlsh 0.1.0\n");
    term_puts(t, "    *         Display: 1024x768x32\n");
    term_puts(t, "              Theme: Catppuccin Mocha\n");
    term_puts(t, "              Uptime: ");
    term_put_uint(t, secs / 60);
    term_puts(t, "m ");
    term_put_uint(t, secs % 60);
    term_puts(t, "s\n");
    term_puts(t, "              Memory: ");
    term_put_uint(t, heap_kb);
    term_puts(t, " KB used\n");
    term_puts(t, "\n");
}

/* =======================================================================
 * Command Dispatcher
 * ======================================================================= */

void term_exec(GuiTerminal *t, const char *cmd) {
    /* Trim leading spaces */
    while (*cmd == ' ') cmd++;
    if (*cmd == '\0') return;

    /* Split command and args */
    const char *args = cmd;
    while (*args && *args != ' ') args++;
    int cmd_name_len = (int)(args - cmd);
    while (*args == ' ') args++;
    if (*args == '\0') args = NULL;

    /* Match command */
    if (cmd_name_len == 4 && _tncmp(cmd, "help", 4) == 0) {
        cmd_help(t);
    } else if (cmd_name_len == 2 && _tncmp(cmd, "ls", 2) == 0) {
        cmd_ls(t, args);
    } else if (cmd_name_len == 3 && _tncmp(cmd, "cat", 3) == 0) {
        cmd_cat(t, args);
    } else if (cmd_name_len == 5 && _tncmp(cmd, "touch", 5) == 0) {
        cmd_touch(t, args);
    } else if (cmd_name_len == 5 && _tncmp(cmd, "mkdir", 5) == 0) {
        cmd_mkdir(t, args);
    } else if (cmd_name_len == 2 && _tncmp(cmd, "rm", 2) == 0) {
        cmd_rm(t, args);
    } else if (cmd_name_len == 4 && _tncmp(cmd, "echo", 4) == 0) {
        cmd_echo(t, args);
    } else if (cmd_name_len == 2 && _tncmp(cmd, "cd", 2) == 0) {
        cmd_cd(t, args);
    } else if (cmd_name_len == 3 && _tncmp(cmd, "pwd", 3) == 0) {
        cmd_pwd(t);
    } else if (cmd_name_len == 5 && _tncmp(cmd, "uname", 5) == 0) {
        cmd_uname(t);
    } else if (cmd_name_len == 6 && _tncmp(cmd, "uptime", 6) == 0) {
        cmd_uptime(t);
    } else if (cmd_name_len == 4 && _tncmp(cmd, "free", 4) == 0) {
        cmd_free(t);
    } else if (cmd_name_len == 5 && _tncmp(cmd, "tasks", 5) == 0) {
        cmd_tasks(t);
    } else if (cmd_name_len == 5 && _tncmp(cmd, "clear", 5) == 0) {
        cmd_clear(t);
    } else if (cmd_name_len == 7 && _tncmp(cmd, "history", 7) == 0) {
        cmd_history(t);
    } else if (cmd_name_len == 8 && _tncmp(cmd, "neofetch", 8) == 0) {
        cmd_neofetch(t);
    } else {
        term_puts(t, "ltlsh: command not found: ");
        /* Print just the command name */
        for (int i = 0; i < cmd_name_len; i++) term_putc(t, cmd[i]);
        term_putc(t, '\n');
        term_puts(t, "Type 'help' for commands.\n");
    }
}

/* =======================================================================
 * Key Input
 * ======================================================================= */

void term_key(GuiTerminal *t, char c) {
    if (c == '\n') {
        /* Execute command */
        t->cmd_buf[t->cmd_len] = '\0';
        term_putc(t, '\n');
        if (t->cmd_len > 0) {
            hist_push(t, t->cmd_buf);
            t->hist_pos = t->hist_count;
            term_exec(t, t->cmd_buf);
        }
        t->cmd_len = 0;
        term_prompt(t);
    } else if (c == 8 || c == 127) {
        /* Backspace */
        if (t->cmd_len > 0) {
            t->cmd_len--;
            /* Remove last char from current line */
            int cur = t->line_count - 1;
            if (cur >= 0) {
                int len = _tlen(t->lines[cur]);
                if (len > 0) {
                    t->lines[cur][len - 1] = 0;
                }
            }
            t->dirty = 1;
        }
    } else if (c >= 32 && c < 127) {
        /* Printable character */
        if (t->cmd_len < TERM_CMD_SIZE - 1) {
            t->cmd_buf[t->cmd_len++] = c;
            term_putc(t, c);
        }
    }
}

/* =======================================================================
 * Create Terminal
 * ======================================================================= */

int term_create(GuiContext *gui) {
    /* Find free terminal slot */
    int tidx = -1;
    for (int i = 0; i < TERM_MAX_TERMS; i++) {
        if (!terminals[i].active) { tidx = i; break; }
    }
    if (tidx < 0) return -1;

    GuiTerminal *t = &terminals[tidx];

    /* Create window */
    int win = gui_create_window(gui, "Terminal",
                                 60 + tidx * 30, 80 + tidx * 30,
                                 620, 420);
    if (win < 0) return -1;

    /* Dark terminal background */
    gui->windows[win].body_bg = COL_BLACK;
    gui->windows[win].is_terminal = 1;

    /* Initialize terminal state */
    t->active         = 1;
    t->win_idx        = win;
    t->line_count     = 0;
    t->scroll_offset  = 0;
    t->cmd_len        = 0;
    t->cursor_tick    = 0;
    t->cursor_visible = 1;
    t->dirty          = 1;
    t->hist_count     = 0;
    t->hist_pos       = 0;

    /* Start in /home */
    int home = ramfs_resolve_path("/home");
    if (home >= 0) {
        t->cwd_node = home;
        _tcpy(t->cwd, "/home", TERM_PATH_SIZE);
    } else {
        t->cwd_node = 0;
        _tcpy(t->cwd, "/", TERM_PATH_SIZE);
    }

    /* Welcome message */
    term_puts(t, "ltlsh 0.1.0 -- LateralusOS Terminal\n");
    term_puts(t, "Type 'help' for available commands.\n");
    term_puts(t, "\n");
    term_prompt(t);

    term_total++;
    return tidx;
}

/* =======================================================================
 * Get Terminal by Window
 * ======================================================================= */

GuiTerminal *term_get_by_window(int win_idx) {
    for (int i = 0; i < TERM_MAX_TERMS; i++) {
        if (terminals[i].active && terminals[i].win_idx == win_idx)
            return &terminals[i];
    }
    return NULL;
}

/* =======================================================================
 * Refresh — Copy visible lines to window content
 * ======================================================================= */

void term_refresh(GuiTerminal *t, GuiContext *gui) {
    if (!t->active || !t->dirty) return;
    if (t->win_idx < 0 || t->win_idx >= gui->window_count) return;

    Window *win = &gui->windows[t->win_idx];
    if (!win->visible) {
        t->active = 0;
        term_total--;
        return;
    }

    /* Calculate how many lines fit in window content area */
    int32_t content_h = win->h - TITLE_BAR_H - 16;
    int visible_lines = content_h / (FONT_H + 2);
    if (visible_lines > 40) visible_lines = 40;

    /* Build content string from last N lines */
    char buf[2048];
    buf[0] = 0;
    int start = t->line_count - visible_lines - t->scroll_offset;
    if (start < 0) start = 0;
    int end = start + visible_lines;
    if (end > t->line_count) end = t->line_count;

    for (int i = start; i < end; i++) {
        _tcat(buf, t->lines[i], 2048);
        if (i < end - 1) _tcat(buf, "\n", 2048);
    }

    /* Add blinking cursor */
    if (t->cursor_visible) {
        _tcat(buf, "_", 2048);
    }

    _tcpy(win->content, buf, 2048);
    t->dirty = 0;
}

/* =======================================================================
 * Tick — cursor blink
 * ======================================================================= */

void term_tick(GuiTerminal *t, uint32_t tick) {
    if (!t->active) return;
    t->cursor_tick++;
    if (t->cursor_tick % 500 == 0) {
        t->cursor_visible = !t->cursor_visible;
        t->dirty = 1;
    }
}

/* =======================================================================
 * Term count
 * ======================================================================= */

int term_count(void) {
    return term_total;
}

/* -- Initialize subsystem (placeholder for static init) ----------------- */

void term_subsystem_init(void) {
    term_init();
}
