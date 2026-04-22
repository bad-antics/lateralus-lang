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
    term_puts(t, "  apps        List installed applications\n");
    term_puts(t, "  grugbot     grugbot420 -- caveman wisdom chatbot\n");
    term_puts(t, "  chat        IRC-style chat (info)\n");
    term_puts(t, "  edit <f>    Text editor (info)\n");
    term_puts(t, "  ltlc <f>    Lateralus compiler (info)\n");
    term_puts(t, "  pkg <cmd>   Package manager (info)\n");
    term_puts(t, "  about       About LateralusOS\n");
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
 * grugbot420 — caveman wisdom chatbot (interactive mode)
 *
 * When a terminal is in grug_mode, each Enter-terminated line is routed
 * through grug_respond() instead of the shell dispatcher.  Output is
 * written straight into the terminal scrollback via term_puts.
 * ======================================================================= */

static const char *GRUG_WISDOM[] = {
    "grug say: complexity very very bad. simple good.",
    "grug say: factory factory factory make grug head hurt.",
    "grug say: name variable what it be. 'data' mean nothing.",
    "grug say: if code hard to delete, code already own you.",
    "grug say: type system friend, not enemy. type catch bug.",
    "grug brain small, so grug keep function small too.",
    "grug say: senior dev is one who know where bodies buried.",
    "grug say: meeting is where productivity go to die.",
    "grug say: ship small, ship often, fix in prod, grug not scared.",
    "grug say: premature optimization root of all bug. measure first.",
    "grug say: DRY is lie. same shape not same meaning.",
    "grug say: if test hard to write, code shape wrong.",
    "grug say: comment say WHY. code already say WHAT.",
    "grug say: log loud when bad, silent when good.",
};
static const int GRUG_WISDOM_N = sizeof(GRUG_WISDOM)/sizeof(GRUG_WISDOM[0]);

static const char *GRUG_JOKES[] = {
    "why function cross road? because callback on other side.",
    "grug have 99 problem but null pointer not one. grug also have null.",
    "how many grug to change lightbulb? none. grug afraid of dark.",
    "grug try recursion to understand recursion. grug still trying.",
    "wife say get bread, if egg get 12. he come home with 12 bread.",
};
static const int GRUG_JOKES_N = sizeof(GRUG_JOKES)/sizeof(GRUG_JOKES[0]);

static const char *GRUG_SMOKE[] = {
    "grug puff... semicolons are just fences for thoughts.",
    "grug puff... garbage collector is just letting go man.",
    "grug puff... monad is just burrito of sadness.",
    "grug puff... every for-loop is a tiny universe bro.",
    "grug puff... types are vibes and vibes are types.",
    "grug puff... the real bug was friends we made along the way.",
};
static const int GRUG_SMOKE_N = sizeof(GRUG_SMOKE)/sizeof(GRUG_SMOKE[0]);

static uint32_t grug_rand(GuiTerminal *t) {
    uint32_t x = t->grug_rng;
    if (x == 0) x = 0x420BADA5u;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    t->grug_rng = x;
    return x & 0x7fffffffu;
}

/* Case-insensitive substring search */
static int grug_has(const char *hay, const char *needle) {
    if (!hay || !needle || !*needle) return 0;
    for (int i = 0; hay[i]; i++) {
        int j = 0;
        while (needle[j]) {
            char a = hay[i + j];
            char b = needle[j];
            if (!a) return 0;
            if (a >= 'A' && a <= 'Z') a += 32;
            if (b >= 'A' && b <= 'Z') b += 32;
            if (a != b) break;
            j++;
        }
        if (!needle[j]) return 1;
    }
    return 0;
}

static int grug_streq_ci(const char *a, const char *b) {
    int i = 0;
    for (;; i++) {
        char x = a[i], y = b[i];
        if (x >= 'A' && x <= 'Z') x += 32;
        if (y >= 'A' && y <= 'Z') y += 32;
        if (x != y) return 0;
        if (!x) return 1;
    }
}

static void grug_say(GuiTerminal *t, const char *text) {
    term_puts(t, "[");
    term_puts(t, (t->grug_mood >= 1) ? "grug420" : "grug");
    term_puts(t, "] ");
    term_puts(t, text);
    term_putc(t, '\n');
}

static void grug_sys(GuiTerminal *t, const char *text) {
    term_puts(t, "[sys] ");
    term_puts(t, text);
    term_putc(t, '\n');
}

static void grug_banner(GuiTerminal *t) {
    term_puts(t, "+=====================================+\n");
    term_puts(t, "|    grugbot420 -- lateralus edition  |\n");
    term_puts(t, "|    small brain. big wisdom. 420.    |\n");
    term_puts(t, "+=====================================+\n");
}

static void grug_prompt(GuiTerminal *t) {
    term_puts(t, "you> ");
}

/* Forward */
static void grug_start(GuiTerminal *t);
static void grug_respond(GuiTerminal *t, const char *line);

static void grug_exit(GuiTerminal *t) {
    t->grug_mode = 0;
    term_puts(t, "\ngrugbot420 signing off. back to shell.\n");
    term_prompt(t);
}

static void grug_handle_cmd(GuiTerminal *t, const char *cmd) {
    if (grug_streq_ci(cmd, "/help")) {
        grug_sys(t, "commands: /help /wisdom /joke /roll /smoke /time /bench /quit");
        return;
    }
    if (grug_streq_ci(cmd, "/wisdom")) {
        grug_say(t, GRUG_WISDOM[grug_rand(t) % GRUG_WISDOM_N]); return;
    }
    if (grug_streq_ci(cmd, "/joke")) {
        grug_say(t, GRUG_JOKES[grug_rand(t) % GRUG_JOKES_N]); return;
    }
    if (grug_streq_ci(cmd, "/roll")) {
        char buf[48]; _tcpy(buf, "d20 rolls: ", 48);
        char nb[8]; _titoa((grug_rand(t) % 20) + 1, nb, 8);
        _tcat(buf, nb, 48);
        grug_say(t, buf); return;
    }
    if (grug_streq_ci(cmd, "/smoke")) {
        t->grug_hits++;
        t->grug_mood = (t->grug_hits >= 3) ? 2 : 1;
        term_puts(t, "[grug420] *puff puff pass*\n");
        grug_say(t, GRUG_SMOKE[grug_rand(t) % GRUG_SMOKE_N]);
        if (t->grug_mood == 2)
            term_puts(t, "[grug420] grug ascend. grug see the monad now.\n");
        return;
    }
    if (grug_streq_ci(cmd, "/time")) {
        char buf[64]; _tcpy(buf, "ticks since boot: ", 64);
        char nb[24]; _titoa(tick_count, nb, 24);
        _tcat(buf, nb, 64);
        grug_sys(t, buf); return;
    }
    if (grug_streq_ci(cmd, "/bench")) {
        /* Benchmark grug_respond over N iterations using a fixed corpus.
         * Timing uses the kernel's millisecond PIT tick (1 kHz). */
        static const char *CORPUS[] = {
            "hello grug",
            "i have a bug in my code",
            "complexity is killing my project",
            "should i ship on friday?",
            "talk to me about types",
            "how do i write tests",
            "lets refactor this oop mess",
            "llm wrote my code, is that ok",
            "give me wisdom",
            "tell a joke",
            "blaze it",
            "thanks friend",
            "random question about the weather",
            "/roll",
            "/wisdom",
            "/joke",
        };
        const int CORPUS_N = (int)(sizeof(CORPUS)/sizeof(CORPUS[0]));
        const int ITERS = 10000;

        /* Snapshot + suppress scrollback writes during the hot loop by
         * temporarily pointing respond at a scratch terminal. We reuse
         * `t` but drain lines each batch so the buffer does not explode. */
        uint64_t t0 = tick_count;
        int prev_lines = t->line_count;

        for (int i = 0; i < ITERS; i++) {
            grug_respond(t, CORPUS[i % CORPUS_N]);
            /* Truncate scrollback every 64 iterations so we benchmark
             * the response engine, not line scrolling. */
            if ((i & 0x3F) == 0x3F) {
                t->line_count = prev_lines;
            }
        }
        uint64_t t1 = tick_count;
        t->line_count = prev_lines;
        t->dirty = 1;

        uint64_t elapsed_ms = (t1 > t0) ? (t1 - t0) : 1;
        uint64_t per_1k_us  = (elapsed_ms * 1000ULL) / ((uint64_t)ITERS / 1000ULL);
        uint64_t ops_per_s  = ((uint64_t)ITERS * 1000ULL) / elapsed_ms;

        char buf[96], nb[24];
        term_puts(t, "[bench] grug_respond x ");
        _titoa(ITERS, nb, 24); term_puts(t, nb);
        term_puts(t, " calls\n");

        _tcpy(buf, "[bench] elapsed: ", 96);
        _titoa(elapsed_ms, nb, 24); _tcat(buf, nb, 96);
        _tcat(buf, " ms\n", 96); term_puts(t, buf);

        _tcpy(buf, "[bench] throughput: ", 96);
        _titoa(ops_per_s, nb, 24); _tcat(buf, nb, 96);
        _tcat(buf, " resp/sec\n", 96); term_puts(t, buf);

        _tcpy(buf, "[bench] per-1k calls: ", 96);
        _titoa(per_1k_us, nb, 24); _tcat(buf, nb, 96);
        _tcat(buf, " us\n", 96); term_puts(t, buf);
        return;
    }
    if (grug_streq_ci(cmd, "/quit") || grug_streq_ci(cmd, "/exit")) {
        grug_say(t, "grug out. keep code small friend.");
        grug_exit(t); return;
    }
    grug_sys(t, "unknown command. try /help");
}

static void grug_respond(GuiTerminal *t, const char *line) {
    if (line[0] == '/') { grug_handle_cmd(t, line); return; }
    if (line[0] == 0)   { return; }

    if (grug_has(line, "hi") || grug_has(line, "hello") || grug_has(line, "hey") ||
        grug_has(line, "sup") || grug_has(line, "yo")) {
        grug_say(t, "hi friend. grug here. what on brain?"); return;
    }
    if (grug_has(line, "bug") || grug_has(line, "crash") ||
        grug_has(line, "broken") || grug_has(line, "panic")) {
        static const char *replies[] = {
            "bug not personal. bug just code telling truth.",
            "read stack trace top-down. answer in there.",
            "print statement older than grug. still work.",
        };
        grug_say(t, replies[grug_rand(t) % 3]); return;
    }
    if (grug_has(line, "complex") || grug_has(line, "overengineer") || grug_has(line, "abstract")) {
        grug_say(t, "complexity demon love abstract factory. delete layer."); return;
    }
    if (grug_has(line, "ship") || grug_has(line, "deploy") || grug_has(line, "release") || grug_has(line, "prod")) {
        grug_say(t, "ship it. worst case rollback. best case user smile."); return;
    }
    if (grug_has(line, "test") || grug_has(line, "tdd") || grug_has(line, "unit")) {
        grug_say(t, "test is rope grug tie to past self. test save future grug."); return;
    }
    if (grug_has(line, "refactor") || grug_has(line, "rewrite")) {
        grug_say(t, "rewrite from scratch is trap. small step. commit often."); return;
    }
    if (grug_has(line, "oop") || grug_has(line, "inherit") || grug_has(line, "class")) {
        grug_say(t, "inheritance tall, composition wide. wide better."); return;
    }
    if (grug_has(line, "meeting") || grug_has(line, "standup") || grug_has(line, "agile")) {
        grug_say(t, "meeting should be email. email should be nothing."); return;
    }
    if (grug_has(line, "perf") || grug_has(line, "slow") || grug_has(line, "fast") || grug_has(line, "optim")) {
        grug_say(t, "measure first. optimize hottest spot. not before."); return;
    }
    if (grug_has(line, "type") || grug_has(line, "rust")) {
        grug_say(t, "type system is exoskeleton. heavy at first, then grug run fast."); return;
    }
    if (grug_has(line, "ai") || grug_has(line, "llm") || grug_has(line, "copilot") || grug_has(line, "gpt")) {
        grug_say(t, "llm is clever parrot. good first draft, bad last draft."); return;
    }
    if (grug_has(line, "friday") || grug_has(line, "weekend")) {
        grug_say(t, "no deploy friday. grug want pizza not pager."); return;
    }
    if (grug_has(line, "weed") || grug_has(line, "420") ||
        grug_has(line, "blaze") || grug_has(line, "smoke") || grug_has(line, "sesh")) {
        grug_handle_cmd(t, "/smoke"); return;
    }
    if (grug_has(line, "wisdom") || grug_has(line, "advice")) {
        grug_handle_cmd(t, "/wisdom"); return;
    }
    if (grug_has(line, "joke") || grug_has(line, "funny")) {
        grug_handle_cmd(t, "/joke"); return;
    }
    if (grug_has(line, "thanks") || grug_has(line, "thank you") || grug_has(line, "love you")) {
        grug_say(t, "grug love you too, stay hydrated, stay small-function."); return;
    }
    if (grug_has(line, "bye") || grug_has(line, "cya") || grug_has(line, "later") || grug_has(line, "goodbye")) {
        grug_say(t, "peace friend. grug return to cave now.");
        grug_exit(t); return;
    }
    /* Fallback */
    grug_say(t, GRUG_WISDOM[grug_rand(t) % GRUG_WISDOM_N]);
}

static void grug_start(GuiTerminal *t) {
    t->grug_mode = 1;
    t->grug_mood = 0;
    t->grug_hits = 0;
    t->grug_rng  = (uint32_t)(tick_count ^ 0x420BADA5u);
    if (t->grug_rng == 0) t->grug_rng = 0x420BADA5u;
    grug_banner(t);
    grug_say(t, "hi. grug here. type /help or just talk. grug listen.");
    grug_prompt(t);
}

void term_start_grugbot(int tidx) {
    if (tidx < 0 || tidx >= TERM_MAX_TERMS) return;
    GuiTerminal *t = &terminals[tidx];
    if (!t->active) return;
    term_puts(t, "\n");
    grug_start(t);
}

/* =======================================================================
 * App stubs — minimal info windows for apps that need VGA text mode
 * ======================================================================= */

static void cmd_apps(GuiTerminal *t) {
    term_puts(t, "Installed Applications:\n");
    term_puts(t, "\n");
    term_puts(t, "  grugbot   caveman wisdom chatbot     [interactive]\n");
    term_puts(t, "  chat      IRC-style chat client      [text shell]\n");
    term_puts(t, "  edit      ltled text editor          [text shell]\n");
    term_puts(t, "  ltlc      Lateralus compiler/REPL    [text shell]\n");
    term_puts(t, "  pkg       package manager            [text shell]\n");
    term_puts(t, "\n");
    term_puts(t, "Type an app name to launch or learn more.\n");
    term_puts(t, "Apps marked [text shell] run in VGA mode -- press ESC\n");
    term_puts(t, "at the GUI to drop into the text shell, then type the\n");
    term_puts(t, "command.\n");
}

static void cmd_chat_info(GuiTerminal *t) {
    term_puts(t, "chat -- IRC-style chat client\n");
    term_puts(t, "\n");
    term_puts(t, "Interactive keyboard-driven app. Not yet ported to the\n");
    term_puts(t, "GUI terminal. Launch from the text shell:\n");
    term_puts(t, "  1. Press ESC to exit GUI\n");
    term_puts(t, "  2. At root@lateralus:/$ type: chat\n");
}

static void cmd_edit_info(GuiTerminal *t, const char *args) {
    (void)args;
    term_puts(t, "edit -- ltled retro text editor\n");
    term_puts(t, "\n");
    term_puts(t, "Launch from the text shell (press ESC to exit GUI),\n");
    term_puts(t, "then type:  edit <filename>\n");
}

static void cmd_ltlc_info(GuiTerminal *t, const char *args) {
    (void)args;
    term_puts(t, "ltlc -- Lateralus compiler / analyzer\n");
    term_puts(t, "\n");
    term_puts(t, "Lexer + parser for .ltl sources. Launch from text shell:\n");
    term_puts(t, "  ltlc <file.ltl>   analyze a file\n");
    term_puts(t, "  ltlc repl         interactive REPL\n");
}

static void cmd_pkg_info(GuiTerminal *t, const char *args) {
    (void)args;
    term_puts(t, "pkg -- package manager\n");
    term_puts(t, "\n");
    term_puts(t, "Launch from the text shell:\n");
    term_puts(t, "  pkg list | pkg install <n> | pkg build | pkg init <n>\n");
}

static void cmd_about(GuiTerminal *t) {
    term_puts(t, "LateralusOS v0.3.0\n");
    term_puts(t, "Spiral Out, Keep Going\n");
    term_puts(t, "\n");
    term_puts(t, "Built with the Lateralus programming language.\n");
    term_puts(t, "(c) 2025-2026 bad-antics\n");
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
    } else if ((cmd_name_len == 7 && _tncmp(cmd, "grugbot", 7) == 0) ||
               (cmd_name_len == 10 && _tncmp(cmd, "grugbot420", 10) == 0)) {
        /* One-shot subcommands: `grugbot wisdom` / `grugbot joke` */
        if (args && _tncmp(args, "wisdom", 6) == 0) {
            /* Seed once */
            if (t->grug_rng == 0) t->grug_rng = (uint32_t)(tick_count ^ 0x420BADA5u);
            grug_say(t, GRUG_WISDOM[grug_rand(t) % GRUG_WISDOM_N]);
        } else if (args && _tncmp(args, "joke", 4) == 0) {
            if (t->grug_rng == 0) t->grug_rng = (uint32_t)(tick_count ^ 0x420BADA5u);
            grug_say(t, GRUG_JOKES[grug_rand(t) % GRUG_JOKES_N]);
        } else {
            grug_start(t);
        }
    } else if (cmd_name_len == 4 && _tncmp(cmd, "apps", 4) == 0) {
        cmd_apps(t);
    } else if (cmd_name_len == 4 && _tncmp(cmd, "chat", 4) == 0) {
        cmd_chat_info(t);
    } else if (cmd_name_len == 4 && _tncmp(cmd, "edit", 4) == 0) {
        cmd_edit_info(t, args);
    } else if (cmd_name_len == 4 && _tncmp(cmd, "ltlc", 4) == 0) {
        cmd_ltlc_info(t, args);
    } else if (cmd_name_len == 3 && _tncmp(cmd, "pkg", 3) == 0) {
        cmd_pkg_info(t, args);
    } else if (cmd_name_len == 5 && _tncmp(cmd, "about", 5) == 0) {
        cmd_about(t);
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
        if (t->grug_mode) {
            /* Feed input to grugbot rather than shell */
            char line[TERM_CMD_SIZE];
            _tcpy(line, t->cmd_buf, TERM_CMD_SIZE);
            t->cmd_len = 0;
            grug_respond(t, line);
            if (t->grug_mode) grug_prompt(t);
        } else {
            if (t->cmd_len > 0) {
                hist_push(t, t->cmd_buf);
                t->hist_pos = t->hist_count;
                term_exec(t, t->cmd_buf);
            }
            t->cmd_len = 0;
            if (!t->grug_mode) term_prompt(t);
        }
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
    t->grug_mode      = 0;
    t->grug_mood      = 0;
    t->grug_hits      = 0;
    t->grug_rng       = 0;

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
