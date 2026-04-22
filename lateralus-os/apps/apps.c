// ===========================================================================
// LateralusOS — Application Stubs (C implementation)
// ===========================================================================
// Copyright (c) 2025-2026 bad-antics. All rights reserved.
//
// This file implements the shell commands for the Lateralus-native apps:
//   • ltlc  — built-in Lateralus compiler (lex + analysis)
//   • chat  — IRC-style chat client with local loopback bot
//   • edit  — retro text editor with syntax highlighting
//   • pkg   — package manager for Lateralus modules
// ===========================================================================

#include "apps.h"

/* --------------------------------------------------------------------------
 * Kernel imports — these are defined in kernel_stub.c and linked at link
 * time.  We declare them extern here to avoid #include kernel_stub.c.
 * -------------------------------------------------------------------------- */

extern void     k_print(const char *s);
extern void     k_putc(char c);
extern void     k_set_color(uint8_t fg, uint8_t bg);
extern int      k_strcmp(const char *a, const char *b);
extern int      k_strncmp(const char *a, const char *b, int n);
extern int      k_strlen(const char *s);
extern void     serial_puts(const char *s);
extern uint64_t tick_count;

/* Keyboard: poll last_scancode (set by IRQ1 handler in kernel_stub.c) */
extern volatile uint8_t last_scancode;
/* Scancode → ASCII table (defined in kernel_stub.c) */
extern const char scancode_ascii[128];

/* VGA text-mode buffer & cursor (defined in kernel_stub.c) */
extern int cur_x, cur_y;
extern volatile uint16_t *const VGA_BUF;

/* RAM filesystem API (defined in fs/ramfs.c) */
extern int ramfs_resolve_path(const char *path);
extern int ramfs_read(int node, char *buf, int max);
extern int ramfs_create(int parent, const char *name);
extern int ramfs_write(int node, const char *data, int len);
extern int ramfs_mkdir(int parent, const char *name);
extern int ramfs_root(void);

/* -- Local memory helpers (no libc in freestanding) ---------------------- */
static void k_memset(void *dst, int val, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    for (uint64_t i = 0; i < n; i++) d[i] = (uint8_t)val;
}
static void k_memcpy(void *dst, const void *src, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    for (uint64_t i = 0; i < n; i++) d[i] = s[i];
}

/* Helper: blocking read one scancode (waits for key-down) */
static uint8_t app_wait_key(void) {
    static uint8_t prev = 0;
    while (1) {
        uint8_t sc = last_scancode;
        if (sc != prev && sc != 0) {
            prev = sc;
            return sc;
        }
        __asm__ volatile("hlt");
    }
}

/* Helper: read a full line from keyboard with echo */
static int app_read_line(char *buf, int max, int *shift) {
    int pos = 0;
    *shift = 0;
    k_memset(buf, 0, max);
    while (1) {
        uint8_t sc = app_wait_key();
        /* Shift tracking */
        if (sc == 0x2A || sc == 0x36) { *shift = 1; continue; }
        if (sc == 0xAA || sc == 0xB6) { *shift = 0; continue; }
        /* Ignore key-up */
        if (sc & 0x80) continue;
        /* Enter */
        if (sc == 0x1C) { k_putc('\n'); break; }
        /* Backspace */
        if (sc == 0x0E) {
            if (pos > 0) { pos--; k_print("\b \b"); }
            continue;
        }
        /* Escape — return -1 */
        if (sc == 0x01) return -1;
        /* Map to ASCII */
        char c = scancode_ascii[sc & 0x7F];
        if (c == 0) continue;
        if (c == '\n') { k_putc('\n'); break; }
        if (c == '\b') { if (pos > 0) { pos--; k_print("\b \b"); } continue; }
        if (*shift && c >= 'a' && c <= 'z') c -= 32;
        if (c >= ' ' && pos < max - 1) {
            buf[pos++] = c;
            k_putc(c);
        }
    }
    buf[pos] = '\0';
    return pos;
}

/* Forward: tiny itoa */
static void ltl_itoa(int val, char *buf, int bufsz) {
    if (bufsz < 2) return;
    int neg = 0;
    if (val < 0) { neg = 1; val = -val; }
    char tmp[16];
    int i = 0;
    if (val == 0) tmp[i++] = '0';
    while (val > 0 && i < 15) { tmp[i++] = '0' + (val % 10); val /= 10; }
    int p = 0;
    if (neg && p < bufsz - 1) buf[p++] = '-';
    while (i > 0 && p < bufsz - 1) buf[p++] = tmp[--i];
    buf[p] = '\0';
}

/* ===========================================================================
 *  LTLC — Built-in Lateralus Compiler
 * =========================================================================== */

/* Keyword table */
static const char *ltlc_keywords[] = {
    "fn", "let", "mut", "if", "else", "while", "for", "in", "return",
    "struct", "enum", "match", "import", "pub", "trait", "impl",
    "async", "await", "const", "type", "true", "false",
    "break", "continue", "yield", "guard", "where", "from",
    "module", "defer", "try", "catch", NULL
};

static int ltlc_is_keyword(const char *w) {
    for (int i = 0; ltlc_keywords[i]; i++)
        if (k_strcmp(w, ltlc_keywords[i]) == 0) return 1;
    return 0;
}

static int ltlc_is_alpha(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
}
static int ltlc_is_digit(char c) { return c >= '0' && c <= '9'; }
static int ltlc_is_alnum(char c) { return ltlc_is_alpha(c) || ltlc_is_digit(c); }

LtlcCompileResult ltlc_compile(const char *source, int len) {
    LtlcCompileResult r;
    k_memset(&r, 0, sizeof(r));
    r.ok = 1;

    int pos = 0, line = 1, col = 1;
    int fn_c = 0, struct_c = 0, let_c = 0, import_c = 0, enum_c = 0;
    int trait_c = 0, impl_c = 0, const_c = 0, tok_count = 0;
    int paren_depth = 0, brace_depth = 0, bracket_depth = 0;

    while (pos < len) {
        char c = source[pos];

        /* Whitespace (non-newline) */
        if (c == ' ' || c == '\t' || c == '\r') { pos++; col++; continue; }

        /* Newline */
        if (c == '\n') { line++; col = 1; pos++; continue; }

        /* Comments */
        if (c == '/' && pos + 1 < len && source[pos + 1] == '/') {
            while (pos < len && source[pos] != '\n') pos++;
            continue;
        }
        /* Block comments */
        if (c == '/' && pos + 1 < len && source[pos + 1] == '*') {
            pos += 2; col += 2;
            int depth = 1;
            while (pos < len && depth > 0) {
                if (source[pos] == '/' && pos + 1 < len && source[pos + 1] == '*') {
                    depth++; pos += 2;
                } else if (source[pos] == '*' && pos + 1 < len && source[pos + 1] == '/') {
                    depth--; pos += 2;
                } else {
                    if (source[pos] == '\n') { line++; col = 0; }
                    pos++;
                }
                col++;
            }
            continue;
        }

        /* Identifiers / keywords */
        if (ltlc_is_alpha(c)) {
            char word[64];
            int wi = 0;
            while (pos < len && ltlc_is_alnum(source[pos]) && wi < 63)
                word[wi++] = source[pos++];
            word[wi] = '\0';
            col += wi;
            tok_count++;

            if (k_strcmp(word, "fn") == 0) fn_c++;
            else if (k_strcmp(word, "struct") == 0) struct_c++;
            else if (k_strcmp(word, "let") == 0) let_c++;
            else if (k_strcmp(word, "import") == 0) import_c++;
            else if (k_strcmp(word, "enum") == 0) enum_c++;
            else if (k_strcmp(word, "trait") == 0) trait_c++;
            else if (k_strcmp(word, "impl") == 0) impl_c++;
            else if (k_strcmp(word, "const") == 0) const_c++;
            continue;
        }

        /* Numbers */
        if (ltlc_is_digit(c)) {
            while (pos < len && (ltlc_is_digit(source[pos]) || source[pos] == '.' ||
                   source[pos] == 'x' || source[pos] == 'X' ||
                   (source[pos] >= 'a' && source[pos] <= 'f') ||
                   (source[pos] >= 'A' && source[pos] <= 'F')))
                { pos++; col++; }
            tok_count++;
            continue;
        }

        /* Strings */
        if (c == '"') {
            pos++; col++;
            while (pos < len && source[pos] != '"') {
                if (source[pos] == '\\') { pos++; col++; }
                if (source[pos] == '\n') { line++; col = 0; }
                pos++; col++;
            }
            if (pos < len) { pos++; col++; }
            tok_count++;
            continue;
        }

        /* Matching delimiters */
        if (c == '(') { paren_depth++; }
        else if (c == ')') {
            paren_depth--;
            if (paren_depth < 0 && r.error_count < 8) {
                char *e = r.errors[r.error_count++];
                k_memset(e, 0, 128);
                k_memcpy(e, "Unmatched ')' at line ", 22);
                char nb[12]; ltl_itoa(line, nb, 12);
                k_memcpy(e + 22, nb, k_strlen(nb));
                r.ok = 0;
            }
        }
        if (c == '{') brace_depth++;
        else if (c == '}') {
            brace_depth--;
            if (brace_depth < 0 && r.error_count < 8) {
                char *e = r.errors[r.error_count++];
                k_memset(e, 0, 128);
                k_memcpy(e, "Unmatched '}' at line ", 22);
                char nb[12]; ltl_itoa(line, nb, 12);
                k_memcpy(e + 22, nb, k_strlen(nb));
                r.ok = 0;
            }
        }
        if (c == '[') bracket_depth++;
        else if (c == ']') {
            bracket_depth--;
            if (bracket_depth < 0 && r.error_count < 8) {
                char *e = r.errors[r.error_count++];
                k_memset(e, 0, 128);
                k_memcpy(e, "Unmatched ']' at line ", 22);
                char nb[12]; ltl_itoa(line, nb, 12);
                k_memcpy(e + 22, nb, k_strlen(nb));
                r.ok = 0;
            }
        }

        pos++; col++;
        tok_count++;
    }

    /* Check unclosed delimiters */
    if (paren_depth > 0 && r.error_count < 8) {
        char *e = r.errors[r.error_count++];
        k_memcpy(e, "Unclosed '(' — missing ')'", 27); e[27] = 0;
        r.ok = 0;
    }
    if (brace_depth > 0 && r.error_count < 8) {
        char *e = r.errors[r.error_count++];
        k_memcpy(e, "Unclosed '{' — missing '}'", 27); e[27] = 0;
        r.ok = 0;
    }
    if (bracket_depth > 0 && r.error_count < 8) {
        char *e = r.errors[r.error_count++];
        k_memcpy(e, "Unclosed '[' — missing ']'", 27); e[27] = 0;
        r.ok = 0;
    }

    r.token_count  = tok_count;
    r.fn_count     = fn_c;
    r.struct_count = struct_c;
    r.let_count    = let_c;
    r.import_count = import_c;
    r.line_count   = line;
    return r;
}

void cmd_ltlc(const char *args) {
    /* Parse subcommand */
    while (*args == ' ') args++;

    if (*args == '\0' || k_strcmp(args, "help") == 0) {
        k_set_color(0x0E, 0x00);
        k_print("ltlc — Lateralus Compiler v2.2.0\n");
        k_set_color(0x0F, 0x00);
        k_print("Usage:\n");
        k_print("  ltlc <file.ltl>       Compile and analyze\n");
        k_print("  ltlc check <file>     Type-check only\n");
        k_print("  ltlc repl             Interactive REPL\n");
        k_print("  ltlc version          Compiler version\n");
        k_print("  ltlc help             This help message\n");
        return;
    }

    if (k_strcmp(args, "version") == 0) {
        k_set_color(0x0A, 0x00);
        k_print("ltlc");
        k_set_color(0x0F, 0x00);
        k_print(" v2.2.0 (LateralusOS built-in)\n");
        k_print("Target: freestanding x86_64\n");
        k_print("Backend: C99 transpiler\n");
        k_print("Features: lex, parse, check, emit-c\n");
        return;
    }

    if (k_strcmp(args, "repl") == 0) {
        cmd_ltlc_repl();
        return;
    }

    /* Compile a file from VFS */
    const char *fname = args;
    if (k_strncmp(args, "check ", 6) == 0) fname = args + 6;
    while (*fname == ' ') fname++;

    /* Read file from ramfs */
    int node = ramfs_resolve_path(fname);
    if (node < 0) {
        k_set_color(0x0C, 0x00);
        k_print("ltlc: file not found: "); k_print(fname); k_putc('\n');
        k_set_color(0x0F, 0x00);
        return;
    }

    char src[8192];
    k_memset(src, 0, sizeof(src));
    int n = ramfs_read(node, src, sizeof(src) - 1);
    if (n <= 0) {
        k_set_color(0x0C, 0x00);
        k_print("ltlc: could not read file\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    k_set_color(0x0E, 0x00);
    k_print("ltlc: compiling "); k_print(fname); k_print("...\n");
    k_set_color(0x0F, 0x00);

    LtlcCompileResult r = ltlc_compile(src, n);

    if (r.ok) {
        k_set_color(0x0A, 0x00);
        k_print("  ✓ Compilation successful\n");
        k_set_color(0x0F, 0x00);
    } else {
        k_set_color(0x0C, 0x00);
        k_print("  ✗ Compilation failed\n");
        k_set_color(0x0F, 0x00);
        for (int i = 0; i < r.error_count; i++) {
            k_set_color(0x0C, 0x00);
            k_print("    error: ");
            k_set_color(0x0F, 0x00);
            k_print(r.errors[i]);
            k_putc('\n');
        }
    }

    k_print("\n");
    k_set_color(0x0E, 0x00);
    k_print("  Summary:\n");
    k_set_color(0x0F, 0x00);
    char nb[16];
    k_print("    Lines:     "); ltl_itoa(r.line_count, nb, 16); k_print(nb); k_putc('\n');
    k_print("    Tokens:    "); ltl_itoa(r.token_count, nb, 16); k_print(nb); k_putc('\n');
    k_print("    Functions: "); ltl_itoa(r.fn_count, nb, 16); k_print(nb); k_putc('\n');
    k_print("    Structs:   "); ltl_itoa(r.struct_count, nb, 16); k_print(nb); k_putc('\n');
    k_print("    Bindings:  "); ltl_itoa(r.let_count, nb, 16); k_print(nb); k_putc('\n');
    k_print("    Imports:   "); ltl_itoa(r.import_count, nb, 16); k_print(nb); k_putc('\n');

    serial_puts("[ltlc] compile done\n");
}

void cmd_ltlc_repl(void) {
    k_set_color(0x0E, 0x00);
    k_print("+==========================================+\n");
    k_print("|  Lateralus REPL v2.2.0                  |\n");
    k_print("|  Type expressions to evaluate            |\n");
    k_print("|  Type 'exit' or 'quit' to leave          |\n");
    k_print("+==========================================+\n");
    k_set_color(0x0F, 0x00);

    char line_buf[512];
    int  line_no = 1;

    while (1) {
        k_set_color(0x0B, 0x00);  /* light cyan */
        k_print("ltl");
        k_set_color(0x07, 0x00);
        k_print("[");
        char nb[8]; ltl_itoa(line_no, nb, 8);
        k_print(nb);
        k_print("]> ");
        k_set_color(0x0F, 0x00);

        int shift = 0;
        int lp = app_read_line(line_buf, sizeof(line_buf), &shift);
        if (lp < 0) break;  /* Esc pressed */

        if (k_strcmp(line_buf, "exit") == 0 || k_strcmp(line_buf, "quit") == 0)
            break;

        if (lp == 0) continue;

        /* Compile the expression */
        LtlcCompileResult r = ltlc_compile(line_buf, lp);
        if (r.ok) {
            k_set_color(0x0A, 0x00);
            k_print("  → ");
            k_set_color(0x0F, 0x00);
            char tb[16]; ltl_itoa(r.token_count, tb, 16);
            k_print(tb); k_print(" tokens, ");
            ltl_itoa(r.fn_count, tb, 16);
            k_print(tb); k_print(" fn, ");
            ltl_itoa(r.struct_count, tb, 16);
            k_print(tb); k_print(" struct, ");
            ltl_itoa(r.let_count, tb, 16);
            k_print(tb); k_print(" let\n");
        } else {
            for (int i = 0; i < r.error_count; i++) {
                k_set_color(0x0C, 0x00);
                k_print("  error: ");
                k_set_color(0x0F, 0x00);
                k_print(r.errors[i]); k_putc('\n');
            }
        }
        line_no++;
    }

    k_set_color(0x0E, 0x00);
    k_print("REPL exited.\n");
    k_set_color(0x0F, 0x00);
}

/* ===========================================================================
 *  CHAT — Retro IRC-style Chat Client
 * =========================================================================== */

static ChatState chat_state;

static void chat_add_msg(int ch, enum ChatMsgKind kind, const char *sender,
                         const char *text, uint32_t color) {
    ChatChannel *c = &chat_state.channels[ch];
    if (c->msg_count >= CHAT_MAX_MESSAGES) {
        /* Scroll: shift messages up */
        for (int i = 1; i < CHAT_MAX_MESSAGES; i++)
            c->messages[i - 1] = c->messages[i];
        c->msg_count = CHAT_MAX_MESSAGES - 1;
    }
    ChatMessage *m = &c->messages[c->msg_count++];
    m->kind = kind;
    m->timestamp = (uint32_t)(tick_count / 1000);
    m->color = color;
    k_memset(m->sender, 0, CHAT_MAX_NICK_LEN);
    k_memset(m->text, 0, CHAT_MAX_MSG_LEN);
    for (int i = 0; sender[i] && i < CHAT_MAX_NICK_LEN - 1; i++) m->sender[i] = sender[i];
    for (int i = 0; text[i] && i < CHAT_MAX_MSG_LEN - 1; i++) m->text[i] = text[i];
}

static void chat_print_msg(const ChatMessage *m) {
    /* Timestamp */
    uint32_t s = m->timestamp;
    uint32_t h = (s / 3600) % 24, mi = (s / 60) % 60, se = s % 60;
    char ts[12];
    ts[0] = '[';
    ts[1] = '0' + (h / 10); ts[2] = '0' + (h % 10); ts[3] = ':';
    ts[4] = '0' + (mi / 10); ts[5] = '0' + (mi % 10); ts[6] = ':';
    ts[7] = '0' + (se / 10); ts[8] = '0' + (se % 10); ts[9] = ']';
    ts[10] = ' '; ts[11] = 0;

    k_set_color(0x03, 0x00);  /* dark cyan = timestamp */
    k_print(ts);

    switch (m->kind) {
    case CHAT_MSG_CHAT:
        k_set_color(0x0D, 0x00);  /* light magenta = nick */
        k_putc('<'); k_print(m->sender); k_print("> ");
        k_set_color(0x0F, 0x00);
        k_print(m->text); break;
    case CHAT_MSG_SYSTEM:
        k_set_color(0x0E, 0x00);
        k_print("*** "); k_print(m->text); break;
    case CHAT_MSG_JOIN:
        k_set_color(0x0A, 0x00);
        k_print("--> "); k_print(m->sender); k_print(" has joined"); break;
    case CHAT_MSG_PART:
        k_set_color(0x0C, 0x00);
        k_print("<-- "); k_print(m->sender); k_print(" has left"); break;
    case CHAT_MSG_PRIVMSG:
        k_set_color(0x0D, 0x00);
        k_print("[PM:"); k_print(m->sender); k_print("] ");
        k_set_color(0x0F, 0x00);
        k_print(m->text); break;
    case CHAT_MSG_ACTION:
        k_set_color(0x0D, 0x00);
        k_print("* "); k_print(m->sender); k_print(" ");
        k_set_color(0x0F, 0x00);
        k_print(m->text); break;
    case CHAT_MSG_ERROR:
        k_set_color(0x0C, 0x00);
        k_print("!!! "); k_print(m->text); break;
    case CHAT_MSG_MOTD:
        k_set_color(0x09, 0x00);
        k_print("  | "); k_print(m->text); break;
    }
    k_putc('\n');
    k_set_color(0x0F, 0x00);
}

/* Bot response for loopback mode */
static const char *chat_bot_respond(const char *text) {
    /* Simple keyword matching */
    for (int i = 0; text[i]; i++) {
        if (text[i] == 'h' || text[i] == 'H') {
            if (k_strncmp(text + i, "hello", 5) == 0 || k_strncmp(text + i, "Hello", 5) == 0
                || k_strncmp(text + i, "hi", 2) == 0 || k_strncmp(text + i, "Hi", 2) == 0)
                return "Hey there! Welcome to LateralusOS Chat!";
        }
        if (text[i] == 'h' && k_strncmp(text + i, "help", 4) == 0)
            return "Type /help for available commands!";
        if ((text[i] == 'l' || text[i] == 'L') && k_strncmp(text + i, "ateralus", 8) == 0)
            return "Lateralus v2.2.0 — the language that powers this OS!";
        if (k_strncmp(text + i, "ping", 4) == 0)
            return "pong!";
    }
    return NULL;
}

static void chat_show_motd(void) {
    const char *motd[] = {
        "\xC9\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD"
        "\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD"
        "\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xBB",
        "\xBA     Welcome to LateralusOS Chat!          \xBA",
        "\xBA                                           \xBA",
        "\xBA  Built with Lateralus v2.2.0              \xBA",
        "\xBA  Running on LateralusOS v0.3.0            \xBA",
        "\xBA                                           \xBA",
        "\xBA  Type /help for available commands         \xBA",
        "\xBA  Type /nick <name> to set your name       \xBA",
        "\xBA  Type /quit to exit                        \xBA",
        "\xC8\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD"
        "\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD"
        "\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xBC",
        NULL
    };
    for (int i = 0; motd[i]; i++)
        chat_add_msg(0, CHAT_MSG_MOTD, "", motd[i], 0x09);
}

static void chat_show_help(void) {
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "--- Command Reference ---", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/nick <name>      Change nickname", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/join #channel    Join channel", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/part             Leave channel", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/msg <user> <text> Private message", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/me <action>      Action message", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/users            List users", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/clear            Clear messages", 0x0E);
    chat_add_msg(chat_state.active_ch, CHAT_MSG_SYSTEM, "", "/quit             Exit chat", 0x0E);
}

static void chat_handle_input(char *input) {
    int ach = chat_state.active_ch;

    /* Regular message */
    if (input[0] != '/') {
        chat_add_msg(ach, CHAT_MSG_CHAT, chat_state.nick, input, 0x0F);
        /* Bot reply in loopback */
        if (chat_state.loopback) {
            const char *reply = chat_bot_respond(input);
            if (reply)
                chat_add_msg(ach, CHAT_MSG_CHAT, "LtlBot", reply, 0x09);
        }
        return;
    }

    /* Commands */
    char cmd[32], arg1[128], arg2[256];
    k_memset(cmd, 0, sizeof(cmd));
    k_memset(arg1, 0, sizeof(arg1));
    k_memset(arg2, 0, sizeof(arg2));

    int p = 1, ci = 0;
    while (input[p] && input[p] != ' ' && ci < 31) cmd[ci++] = input[p++];
    while (input[p] == ' ') p++;
    int ai = 0;
    while (input[p] && input[p] != ' ' && ai < 127) arg1[ai++] = input[p++];
    while (input[p] == ' ') p++;
    int bi = 0;
    while (input[p] && bi < 255) arg2[bi++] = input[p++];

    if (k_strcmp(cmd, "nick") == 0 && arg1[0]) {
        char msg[128];
        k_memset(msg, 0, 128);
        int mp = 0;
        for (int i = 0; chat_state.nick[i] && mp < 120; i++) msg[mp++] = chat_state.nick[i];
        const char *suf = " is now known as ";
        for (int i = 0; suf[i] && mp < 120; i++) msg[mp++] = suf[i];
        for (int i = 0; arg1[i] && mp < 120; i++) msg[mp++] = arg1[i];
        chat_add_msg(ach, CHAT_MSG_SYSTEM, "", msg, 0x0E);
        k_memset(chat_state.nick, 0, CHAT_MAX_NICK_LEN);
        for (int i = 0; arg1[i] && i < CHAT_MAX_NICK_LEN - 1; i++)
            chat_state.nick[i] = arg1[i];
    }
    else if (k_strcmp(cmd, "join") == 0 && arg1[0]) {
        if (chat_state.channel_count < CHAT_MAX_CHANNELS) {
            ChatChannel *nc = &chat_state.channels[chat_state.channel_count];
            k_memset(nc, 0, sizeof(ChatChannel));
            int ni = 0;
            if (arg1[0] != '#') nc->name[ni++] = '#';
            for (int i = 0; arg1[i] && ni < 31; i++) nc->name[ni++] = arg1[i];
            /* Add self and bot */
            k_memcpy(nc->users[0], chat_state.nick, CHAT_MAX_NICK_LEN);
            k_memcpy(nc->users[1], "LtlBot", 7);
            nc->user_count = 2;
            chat_state.active_ch = chat_state.channel_count;
            chat_state.channel_count++;
            chat_add_msg(chat_state.active_ch, CHAT_MSG_JOIN, chat_state.nick, "", 0x0A);
        }
    }
    else if (k_strcmp(cmd, "part") == 0) {
        if (chat_state.active_ch > 0) {
            chat_add_msg(chat_state.active_ch, CHAT_MSG_PART, chat_state.nick, "", 0x0C);
            chat_state.active_ch = 0;
        } else {
            chat_add_msg(0, CHAT_MSG_ERROR, "", "Cannot leave #lobby", 0x0C);
        }
    }
    else if (k_strcmp(cmd, "msg") == 0 && arg1[0] && arg2[0]) {
        chat_add_msg(ach, CHAT_MSG_PRIVMSG, chat_state.nick, arg2, 0x0D);
    }
    else if (k_strcmp(cmd, "me") == 0 && (arg1[0] || arg2[0])) {
        char action[256];
        k_memset(action, 0, 256);
        int ap = 0;
        for (int i = 0; arg1[i] && ap < 250; i++) action[ap++] = arg1[i];
        if (arg2[0]) { action[ap++] = ' '; for (int i = 0; arg2[i] && ap < 250; i++) action[ap++] = arg2[i]; }
        chat_add_msg(ach, CHAT_MSG_ACTION, chat_state.nick, action, 0x0D);
    }
    else if (k_strcmp(cmd, "users") == 0) {
        ChatChannel *c = &chat_state.channels[ach];
        char msg[256];
        k_memset(msg, 0, 256);
        int mp = 0;
        const char *pfx = "Users: ";
        for (int i = 0; pfx[i]; i++) msg[mp++] = pfx[i];
        for (int i = 0; i < c->user_count && mp < 240; i++) {
            if (i > 0) { msg[mp++] = ','; msg[mp++] = ' '; }
            for (int j = 0; c->users[i][j] && mp < 240; j++) msg[mp++] = c->users[i][j];
        }
        chat_add_msg(ach, CHAT_MSG_SYSTEM, "", msg, 0x0E);
    }
    else if (k_strcmp(cmd, "clear") == 0) {
        chat_state.channels[ach].msg_count = 0;
    }
    else if (k_strcmp(cmd, "help") == 0) {
        chat_show_help();
    }
    else if (k_strcmp(cmd, "quit") == 0 || k_strcmp(cmd, "exit") == 0) {
        chat_state.running = 0;
    }
    else {
        char emsg[128];
        k_memset(emsg, 0, 128);
        const char *pfx = "Unknown command: /";
        int ep = 0;
        for (int i = 0; pfx[i] && ep < 120; i++) emsg[ep++] = pfx[i];
        for (int i = 0; cmd[i] && ep < 120; i++) emsg[ep++] = cmd[i];
        chat_add_msg(ach, CHAT_MSG_ERROR, "", emsg, 0x0C);
    }
}

void cmd_chat(const char *args) {
    serial_puts("[chat] starting\n");

    /* Initialize state */
    k_memset(&chat_state, 0, sizeof(chat_state));
    k_memcpy(chat_state.nick, "user", 5);
    chat_state.channel_count = 1;
    chat_state.active_ch = 0;
    chat_state.running = 1;
    chat_state.loopback = 1;
    k_memcpy(chat_state.channels[0].name, "#lobby", 7);
    k_memcpy(chat_state.channels[0].topic, "Welcome to LateralusOS Chat!", 29);
    k_memcpy(chat_state.channels[0].users[0], "user", 5);
    k_memcpy(chat_state.channels[0].users[1], "LtlBot", 7);
    chat_state.channels[0].user_count = 2;

    /* Show MOTD */
    chat_show_motd();

    /* Display all buffered messages */
    ChatChannel *lob = &chat_state.channels[0];
    for (int i = 0; i < lob->msg_count; i++)
        chat_print_msg(&lob->messages[i]);

    k_putc('\n');
    chat_add_msg(0, CHAT_MSG_JOIN, "user", "", 0x0A);
    chat_print_msg(&lob->messages[lob->msg_count - 1]);

    /* Keyboard reading */
    char line_buf[512];

    while (chat_state.running) {
        /* Prompt */
        ChatChannel *ch = &chat_state.channels[chat_state.active_ch];
        k_set_color(0x08, 0x00);
        k_putc('[');
        k_set_color(0x0B, 0x00);
        k_print(ch->name);
        k_set_color(0x08, 0x00);
        k_print("] ");
        k_set_color(0x0D, 0x00);
        k_print(chat_state.nick);
        k_set_color(0x07, 0x00);
        k_print("> ");
        k_set_color(0x0F, 0x00);

        int shift = 0;
        int lp = app_read_line(line_buf, sizeof(line_buf), &shift);
        if (lp < 0) { chat_state.running = 0; continue; }  /* Esc = quit */
        if (lp == 0) continue;

        chat_handle_input(line_buf);

        /* Print most recent message */
        ch = &chat_state.channels[chat_state.active_ch];
        if (ch->msg_count > 0)
            chat_print_msg(&ch->messages[ch->msg_count - 1]);
    }

    k_set_color(0x0E, 0x00);
    k_print("Chat client exited.\n");
    k_set_color(0x0F, 0x00);
    serial_puts("[chat] exited\n");
}

/* ===========================================================================
 *  EDIT — Retro Text Editor
 * =========================================================================== */

static EditorState edit_state;

static void edit_render_status(void) {
    k_set_color(0x70, 0x00);  /* black on gray = status bar */
    const char *mode_str = "NORMAL";
    if (edit_state.mode == EDIT_MODE_INSERT)  mode_str = "INSERT";
    if (edit_state.mode == EDIT_MODE_COMMAND) mode_str = "CMD";
    if (edit_state.mode == EDIT_MODE_SEARCH)  mode_str = "SEARCH";

    k_print(" "); k_print(mode_str);
    k_print(" | "); k_print(edit_state.filename);
    if (edit_state.modified) k_print(" [+]");
    k_print(" | Ln ");
    char nb[16]; ltl_itoa(edit_state.cursor_y + 1, nb, 16);
    k_print(nb); k_print("/");
    ltl_itoa(edit_state.line_count, nb, 16); k_print(nb);
    k_print(", Col ");
    ltl_itoa(edit_state.cursor_x + 1, nb, 16); k_print(nb);
    k_print(" | "); k_print(edit_state.status_msg);
    k_putc('\n');
    k_set_color(0x0F, 0x00);
}

static void edit_render(void) {
    /* Clear and redraw visible lines */
    int start_row = 2;  /* Leave room for header */

    /* Header */
    k_set_color(0x1F, 0x00);  /* white on blue */
    k_print(" ltled — "); k_print(edit_state.filename); k_print("                              ");
    k_putc('\n');
    k_set_color(0x0F, 0x00);

    /* Visible lines */
    int end = edit_state.scroll_y + EDIT_VISIBLE_ROWS;
    if (end > edit_state.line_count) end = edit_state.line_count;

    for (int y = edit_state.scroll_y; y < end; y++) {
        /* Line number */
        k_set_color(0x08, 0x00);
        char nb[8]; ltl_itoa(y + 1, nb, 8);
        int pad = 4 - k_strlen(nb);
        for (int p = 0; p < pad; p++) k_putc(' ');
        k_print(nb); k_print(" ");

        /* Line content with basic syntax highlighting */
        k_set_color(0x0F, 0x00);
        const char *ln = edit_state.lines[y];
        int i = 0;

        /* Leading whitespace */
        while (ln[i] == ' ' || ln[i] == '\t') { k_putc(ln[i]); i++; }

        /* Simple keyword coloring */
        while (ln[i]) {
            if (ln[i] == '/' && ln[i + 1] == '/') {
                k_set_color(0x08, 0x00);
                k_print(ln + i);
                break;
            }
            if (ln[i] == '"') {
                k_set_color(0x0A, 0x00);
                k_putc(ln[i++]);
                while (ln[i] && ln[i] != '"') {
                    if (ln[i] == '\\') k_putc(ln[i++]);
                    k_putc(ln[i++]);
                }
                if (ln[i]) k_putc(ln[i++]);
                k_set_color(0x0F, 0x00);
                continue;
            }
            if (ltlc_is_alpha(ln[i])) {
                char w[32]; int wi = 0;
                while (ltlc_is_alnum(ln[i]) && wi < 31) w[wi++] = ln[i++];
                w[wi] = 0;
                if (ltlc_is_keyword(w)) k_set_color(0x0D, 0x00);
                k_print(w);
                k_set_color(0x0F, 0x00);
                continue;
            }
            if (ltlc_is_digit(ln[i])) {
                k_set_color(0x0E, 0x00);
                while (ltlc_is_digit(ln[i]) || ln[i] == '.') k_putc(ln[i++]);
                k_set_color(0x0F, 0x00);
                continue;
            }
            k_putc(ln[i++]);
        }
        k_putc('\n');
    }

    /* Fill remaining lines with ~ */
    for (int y = end - edit_state.scroll_y; y < EDIT_VISIBLE_ROWS; y++) {
        k_set_color(0x08, 0x00);
        k_print("   ~\n");
    }

    edit_render_status();
}

void cmd_edit(const char *args) {
    while (*args == ' ') args++;

    if (*args == '\0') {
        k_set_color(0x0E, 0x00);
        k_print("ltled — Lateralus Text Editor v1.0\n");
        k_set_color(0x0F, 0x00);
        k_print("Usage:\n");
        k_print("  edit <filename>    Open file for editing\n");
        k_print("  edit new           Create new file\n");
        k_print("\nControls (insert mode):\n");
        k_print("  Esc     Switch to normal mode\n");
        k_print("  Ctrl+S  Save file\n");
        k_print("  Ctrl+Q  Quit editor\n");
        return;
    }

    /* Initialize editor state */
    k_memset(&edit_state, 0, sizeof(edit_state));
    int fi = 0;
    while (args[fi] && fi < 127) { edit_state.filename[fi] = args[fi]; fi++; }
    edit_state.line_count = 1;
    edit_state.mode = EDIT_MODE_INSERT;
    edit_state.running = 1;
    k_memcpy(edit_state.status_msg, "Ctrl+S save | Ctrl+Q quit", 26);

    /* Try to load file from VFS */
    if (k_strcmp(args, "new") != 0) {
        int node = ramfs_resolve_path(args);
        if (node >= 0) {
            char buf[8192];
            k_memset(buf, 0, sizeof(buf));
            int n = ramfs_read(node, buf, sizeof(buf) - 1);
            if (n > 0) {
                /* Split into lines */
                int li = 0, lp = 0;
                for (int i = 0; i < n && li < EDIT_MAX_LINES; i++) {
                    if (buf[i] == '\n' || lp >= EDIT_MAX_LINE_LEN - 1) {
                        edit_state.lines[li][lp] = 0;
                        li++; lp = 0;
                    } else {
                        edit_state.lines[li][lp++] = buf[i];
                    }
                }
                edit_state.line_count = li > 0 ? li : 1;
                k_memcpy(edit_state.status_msg, "Loaded file", 12);
            }
        } else {
            k_memcpy(edit_state.status_msg, "New file", 9);
        }
    }

    serial_puts("[edit] starting editor\n");

    /* Clear screen */
    for (int i = 0; i < 80 * 25; i++)
        VGA_BUF[i] = (uint16_t)' ' | ((uint16_t)0x0F << 8);
    cur_x = 0; cur_y = 0;

    edit_render();

    /* Editor loop */
    int shift_held = 0;
    int ctrl_held = 0;

    while (edit_state.running) {
        uint8_t sc = app_wait_key();

        /* Key release */
        if (sc & 0x80) {
            uint8_t rel = sc & 0x7F;
            if (rel == 0x2A || rel == 0x36) shift_held = 0;
            if (rel == 0x1D) ctrl_held = 0;
            continue;
        }
        /* Shift/Ctrl press */
        if (sc == 0x2A || sc == 0x36) { shift_held = 1; continue; }
        if (sc == 0x1D) { ctrl_held = 1; continue; }

        /* Ctrl+Q = quit */
        if (ctrl_held && (sc == 0x10)) {   /* Q */
            edit_state.running = 0;
            continue;
        }
        /* Ctrl+S = save */
        if (ctrl_held && (sc == 0x1F)) {   /* S */
            /* Build content */
            char content[8192];
            int cp = 0;
            for (int y = 0; y < edit_state.line_count && cp < 8000; y++) {
                for (int x = 0; edit_state.lines[y][x] && cp < 8000; x++)
                    content[cp++] = edit_state.lines[y][x];
                content[cp++] = '\n';
            }
            content[cp] = 0;

            int node = ramfs_resolve_path(edit_state.filename);
            if (node < 0) {
                int root = ramfs_root();
                node = ramfs_create(root, edit_state.filename);
            }
            if (node >= 0) {
                ramfs_write(node, content, cp);
                edit_state.modified = 0;
                k_memcpy(edit_state.status_msg, "Saved!", 7);
            } else {
                k_memcpy(edit_state.status_msg, "Save FAILED", 12);
            }
            /* Redraw */
            cur_x = 0; cur_y = 0;
            edit_render();
            continue;
        }

        char c = scancode_ascii[sc & 0x7F];
        if (shift_held && c >= 'a' && c <= 'z') c -= 32;

        /* Arrow keys (scancodes without ASCII) */
        if (sc == 0x48) { /* Up */
            if (edit_state.cursor_y > 0) edit_state.cursor_y--;
            int ll = k_strlen(edit_state.lines[edit_state.cursor_y]);
            if (edit_state.cursor_x > ll) edit_state.cursor_x = ll;
            if (edit_state.cursor_y < edit_state.scroll_y) edit_state.scroll_y = edit_state.cursor_y;
            cur_x = 0; cur_y = 0; edit_render(); continue;
        }
        if (sc == 0x50) { /* Down */
            if (edit_state.cursor_y < edit_state.line_count - 1) edit_state.cursor_y++;
            int ll = k_strlen(edit_state.lines[edit_state.cursor_y]);
            if (edit_state.cursor_x > ll) edit_state.cursor_x = ll;
            if (edit_state.cursor_y >= edit_state.scroll_y + EDIT_VISIBLE_ROWS)
                edit_state.scroll_y = edit_state.cursor_y - EDIT_VISIBLE_ROWS + 1;
            cur_x = 0; cur_y = 0; edit_render(); continue;
        }
        if (sc == 0x4B) { /* Left */
            if (edit_state.cursor_x > 0) edit_state.cursor_x--;
            cur_x = 0; cur_y = 0; edit_render(); continue;
        }
        if (sc == 0x4D) { /* Right */
            int ll = k_strlen(edit_state.lines[edit_state.cursor_y]);
            if (edit_state.cursor_x < ll) edit_state.cursor_x++;
            cur_x = 0; cur_y = 0; edit_render(); continue;
        }

        if (c == 0) continue;

        /* Backspace */
        if (c == '\b') {
            if (edit_state.cursor_x > 0) {
                char *ln = edit_state.lines[edit_state.cursor_y];
                int ll = k_strlen(ln);
                for (int i = edit_state.cursor_x - 1; i < ll; i++)
                    ln[i] = ln[i + 1];
                edit_state.cursor_x--;
                edit_state.modified = 1;
            } else if (edit_state.cursor_y > 0) {
                /* Join with previous line */
                int py = edit_state.cursor_y - 1;
                int plen = k_strlen(edit_state.lines[py]);
                /* Append current line to previous */
                char *prev = edit_state.lines[py];
                char *curr = edit_state.lines[edit_state.cursor_y];
                int clen = k_strlen(curr);
                if (plen + clen < EDIT_MAX_LINE_LEN - 1) {
                    k_memcpy(prev + plen, curr, clen + 1);
                }
                /* Remove current line */
                for (int i = edit_state.cursor_y; i < edit_state.line_count - 1; i++)
                    k_memcpy(edit_state.lines[i], edit_state.lines[i + 1], EDIT_MAX_LINE_LEN);
                edit_state.line_count--;
                edit_state.cursor_y = py;
                edit_state.cursor_x = plen;
                edit_state.modified = 1;
            }
            cur_x = 0; cur_y = 0; edit_render(); continue;
        }

        /* Enter */
        if (c == '\n') {
            if (edit_state.line_count < EDIT_MAX_LINES - 1) {
                /* Split line at cursor */
                char *ln = edit_state.lines[edit_state.cursor_y];
                int ll = k_strlen(ln);

                /* Shift lines down */
                for (int i = edit_state.line_count; i > edit_state.cursor_y + 1; i--)
                    k_memcpy(edit_state.lines[i], edit_state.lines[i - 1], EDIT_MAX_LINE_LEN);

                /* Copy after-cursor to new line */
                k_memset(edit_state.lines[edit_state.cursor_y + 1], 0, EDIT_MAX_LINE_LEN);
                k_memcpy(edit_state.lines[edit_state.cursor_y + 1], ln + edit_state.cursor_x, ll - edit_state.cursor_x + 1);
                ln[edit_state.cursor_x] = '\0';

                edit_state.line_count++;
                edit_state.cursor_y++;
                edit_state.cursor_x = 0;
                edit_state.modified = 1;

                if (edit_state.cursor_y >= edit_state.scroll_y + EDIT_VISIBLE_ROWS)
                    edit_state.scroll_y++;
            }
            cur_x = 0; cur_y = 0; edit_render(); continue;
        }

        /* Regular character */
        if (c >= ' ') {
            char *ln = edit_state.lines[edit_state.cursor_y];
            int ll = k_strlen(ln);
            if (ll < EDIT_MAX_LINE_LEN - 2) {
                /* Shift right */
                for (int i = ll + 1; i > edit_state.cursor_x; i--)
                    ln[i] = ln[i - 1];
                ln[edit_state.cursor_x] = c;
                edit_state.cursor_x++;
                edit_state.modified = 1;
            }
            cur_x = 0; cur_y = 0; edit_render(); continue;
        }
    }

    /* Clear and restore */
    for (int i = 0; i < 80 * 25; i++)
        VGA_BUF[i] = (uint16_t)' ' | ((uint16_t)0x0F << 8);
    cur_x = 0; cur_y = 0;
    k_set_color(0x0F, 0x00);
    k_print("Editor closed.\n");
    serial_puts("[edit] closed\n");
}

/* ===========================================================================
 *  PKG — Package Manager
 * =========================================================================== */

typedef struct {
    char name[32];
    char version[16];
    char description[128];
    int  installed;
} PkgEntry;

static PkgEntry pkg_registry[] = {
    {"core",        "1.0.0", "Core types and functions",                    1},
    {"math",        "1.0.0", "Mathematics library (trig, linalg, stats)",   1},
    {"strings",     "1.0.0", "String manipulation utilities",               1},
    {"collections", "1.0.0", "Data structures (stack, queue, btree)",       1},
    {"io",          "1.0.0", "I/O abstractions",                            1},
    {"json",        "1.0.0", "JSON parser and serializer",                  0},
    {"csv",         "1.0.0", "CSV reader/writer",                           0},
    {"regex",       "1.0.0", "Regular expression engine",                   0},
    {"crypto",      "1.0.0", "Cryptographic primitives (AES, SHA, HMAC)",   1},
    {"uuid",        "1.0.0", "UUID v4 generator",                           0},
    {"base64",      "1.0.0", "Base64 encoding/decoding",                    0},
    {"os",          "1.0.0", "OS interface (process, signals, env)",        1},
    {"async",       "1.0.0", "Async/await runtime",                         0},
    {"sync",        "1.0.0", "Synchronization primitives",                  0},
    {"channel",     "1.0.0", "Channel-based message passing",               0},
    {"time",        "1.0.0", "Time and duration utilities",                 1},
    {"datetime",    "1.0.0", "Date/time formatting and parsing",            0},
    {"network",     "1.0.0", "TCP/UDP networking",                          1},
    {"http",        "1.0.0", "HTTP client/server",                          0},
    {"linalg",      "1.0.0", "Linear algebra (vectors, matrices)",          0},
    {"stats",       "1.0.0", "Statistical functions",                       0},
    {"science",     "1.0.0", "Scientific computing helpers",                0},
    {"signals",     "1.0.0", "Signal processing (FFT, filters)",            0},
    {"testing",     "1.0.0", "Test framework (assert, bench)",              1},
    {"logging",     "1.0.0", "Structured logging",                          1},
    {"random",      "1.0.0", "Random number generation",                    0},
    {"color",       "1.0.0", "Color utilities (RGB, HSL)",                  0},
    {"graph",       "1.0.0", "Graph algorithms (BFS, DFS, Dijkstra)",       0},
    {"hash",        "1.0.0", "Hash map and set implementations",            0},
    {"ltlchat",     "1.0.0", "Chat client for LateralusOS",                 1},
    {"ltled",       "1.0.0", "Text editor for LateralusOS",                 1},
    {"ltlc",        "2.2.0", "Lateralus compiler",                          1},
    {"",            "",      "",                                             0},
};
#define PKG_COUNT 32

void cmd_pkg(const char *args) {
    while (*args == ' ') args++;

    if (*args == '\0' || k_strcmp(args, "help") == 0) {
        k_set_color(0x0E, 0x00);
        k_print("ltlpkg — Lateralus Package Manager v1.0\n");
        k_set_color(0x0F, 0x00);
        k_print("Usage:\n");
        k_print("  pkg list               List installed packages\n");
        k_print("  pkg search <query>     Search registry\n");
        k_print("  pkg info <name>        Package details\n");
        k_print("  pkg install <name>     Install package\n");
        k_print("  pkg remove <name>      Uninstall package\n");
        k_print("  pkg build              Build current project\n");
        k_print("  pkg init <name>        Create new project\n");
        return;
    }

    if (k_strcmp(args, "list") == 0) {
        k_set_color(0x0E, 0x00);
        k_print("Installed packages:\n");
        k_print("===========================================\n");
        k_set_color(0x0F, 0x00);
        int count = 0;
        for (int i = 0; i < PKG_COUNT && pkg_registry[i].name[0]; i++) {
            if (pkg_registry[i].installed) {
                k_set_color(0x0A, 0x00);
                k_print("  "); k_print(pkg_registry[i].name);
                k_set_color(0x08, 0x00);
                k_print(" v"); k_print(pkg_registry[i].version);
                k_set_color(0x07, 0x00);
                k_print(" — "); k_print(pkg_registry[i].description);
                k_putc('\n');
                count++;
            }
        }
        k_set_color(0x0F, 0x00);
        char nb[8]; ltl_itoa(count, nb, 8);
        k_putc('\n'); k_print(nb); k_print(" package(s) installed\n");
        return;
    }

    if (k_strncmp(args, "search ", 7) == 0) {
        const char *query = args + 7;
        while (*query == ' ') query++;
        k_set_color(0x0E, 0x00);
        k_print("Search results for '"); k_print(query); k_print("':\n");
        k_set_color(0x0F, 0x00);
        int found = 0;
        for (int i = 0; i < PKG_COUNT && pkg_registry[i].name[0]; i++) {
            /* Simple substring search in name or description */
            int match = 0;
            int qlen = k_strlen(query);
            const char *haystack = pkg_registry[i].name;
            for (int j = 0; haystack[j]; j++) {
                if (k_strncmp(haystack + j, query, qlen) == 0) { match = 1; break; }
            }
            if (!match) {
                haystack = pkg_registry[i].description;
                for (int j = 0; haystack[j]; j++) {
                    if (k_strncmp(haystack + j, query, qlen) == 0) { match = 1; break; }
                }
            }
            if (match) {
                k_print("  ");
                k_set_color(pkg_registry[i].installed ? 0x0A : 0x07, 0x00);
                k_print(pkg_registry[i].name);
                k_set_color(0x08, 0x00);
                k_print(" v"); k_print(pkg_registry[i].version);
                k_set_color(0x07, 0x00);
                k_print(pkg_registry[i].installed ? " [installed]" : " [available]");
                k_print(" — "); k_print(pkg_registry[i].description);
                k_putc('\n');
                found++;
            }
        }
        k_set_color(0x0F, 0x00);
        if (!found) k_print("  No packages found.\n");
        return;
    }

    if (k_strncmp(args, "info ", 5) == 0) {
        const char *name = args + 5;
        while (*name == ' ') name++;
        for (int i = 0; i < PKG_COUNT && pkg_registry[i].name[0]; i++) {
            if (k_strcmp(name, pkg_registry[i].name) == 0) {
                k_set_color(0x0E, 0x00);
                k_print("Package: "); k_set_color(0x0F, 0x00); k_print(pkg_registry[i].name); k_putc('\n');
                k_set_color(0x0E, 0x00);
                k_print("Version: "); k_set_color(0x0F, 0x00); k_print(pkg_registry[i].version); k_putc('\n');
                k_set_color(0x0E, 0x00);
                k_print("Description: "); k_set_color(0x0F, 0x00); k_print(pkg_registry[i].description); k_putc('\n');
                k_set_color(0x0E, 0x00);
                k_print("Status: "); k_set_color(pkg_registry[i].installed ? 0x0A : 0x0C, 0x00);
                k_print(pkg_registry[i].installed ? "Installed" : "Not installed"); k_putc('\n');
                k_set_color(0x0F, 0x00);
                return;
            }
        }
        k_set_color(0x0C, 0x00);
        k_print("Package '"); k_print(name); k_print("' not found.\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    if (k_strncmp(args, "install ", 8) == 0) {
        const char *name = args + 8;
        while (*name == ' ') name++;
        for (int i = 0; i < PKG_COUNT && pkg_registry[i].name[0]; i++) {
            if (k_strcmp(name, pkg_registry[i].name) == 0) {
                if (pkg_registry[i].installed) {
                    k_print("Package '"); k_print(name); k_print("' is already installed.\n");
                    return;
                }
                k_set_color(0x0E, 0x00);
                k_print("Installing "); k_print(name); k_print(" v"); k_print(pkg_registry[i].version); k_print("...\n");
                k_set_color(0x0F, 0x00);
                k_print("  Resolving dependencies...\n");
                k_print("  Downloading package...\n");
                k_print("  Verifying checksum...\n");
                k_print("  Installing to /usr/lib/lateralus/"); k_print(name); k_print("/\n");
                pkg_registry[i].installed = 1;
                k_set_color(0x0A, 0x00);
                k_print("  ✓ "); k_print(name); k_print(" installed successfully\n");
                k_set_color(0x0F, 0x00);
                return;
            }
        }
        k_set_color(0x0C, 0x00);
        k_print("Package '"); k_print(name); k_print("' not found in registry.\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    if (k_strncmp(args, "remove ", 7) == 0) {
        const char *name = args + 7;
        while (*name == ' ') name++;
        for (int i = 0; i < PKG_COUNT && pkg_registry[i].name[0]; i++) {
            if (k_strcmp(name, pkg_registry[i].name) == 0) {
                if (!pkg_registry[i].installed) {
                    k_print("Package '"); k_print(name); k_print("' is not installed.\n");
                    return;
                }
                k_print("Removing "); k_print(name); k_print("...\n");
                pkg_registry[i].installed = 0;
                k_set_color(0x0A, 0x00);
                k_print("  ✓ "); k_print(name); k_print(" removed successfully\n");
                k_set_color(0x0F, 0x00);
                return;
            }
        }
        k_set_color(0x0C, 0x00);
        k_print("Package '"); k_print(name); k_print("' not found.\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    if (k_strcmp(args, "build") == 0) {
        k_set_color(0x0E, 0x00);
        k_print("Building current project...\n");
        k_set_color(0x0F, 0x00);
        k_print("[1/4] Discovering source files...\n");
        k_print("[2/4] Compiling with ltlc...\n");
        k_print("[3/4] Linking...\n");
        k_print("[4/4] Build complete\n");
        k_set_color(0x0A, 0x00);
        k_print("  ✓ Build successful\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    if (k_strncmp(args, "init ", 5) == 0) {
        const char *name = args + 5;
        while (*name == ' ') name++;
        k_print("Creating new project '"); k_print(name); k_print("'...\n");
        k_print("  mkdir "); k_print(name); k_print("/\n");
        k_print("  mkdir "); k_print(name); k_print("/src/\n");
        k_print("  create "); k_print(name); k_print("/src/main.ltl\n");
        k_print("  create "); k_print(name); k_print("/lateralus.toml\n");

        /* Actually create in VFS */
        int home = ramfs_resolve_path("/home");
        if (home >= 0) {
            int pdir = ramfs_mkdir(home, name);
            if (pdir >= 0) {
                int src = ramfs_mkdir(pdir, "src");
                if (src >= 0) {
                    int main_f = ramfs_create(src, "main.ltl");
                    const char *templ = "// " ;
                    char hello[256];
                    int hp = 0;
                    const char *prefix = "// ";
                    for (int i = 0; prefix[i]; i++) hello[hp++] = prefix[i];
                    for (int i = 0; name[i]; i++) hello[hp++] = name[i];
                    hello[hp++] = '\n';
                    const char *body = "\nfn main() {\n    println(\"Hello from Lateralus!\")\n}\n";
                    for (int i = 0; body[i]; i++) hello[hp++] = body[i];
                    hello[hp] = 0;
                    if (main_f >= 0) ramfs_write(main_f, hello, hp);
                }
            }
        }
        k_set_color(0x0A, 0x00);
        k_print("  ✓ Project '"); k_print(name); k_print("' initialized\n");
        k_set_color(0x0F, 0x00);
        k_print("\n  To edit:   edit /home/"); k_print(name); k_print("/src/main.ltl\n");
        k_print("  To build:  pkg build\n");
        k_print("  To run:    ltlc run /home/"); k_print(name); k_print("/src/main.ltl\n");
        return;
    }

    k_set_color(0x0C, 0x00);
    k_print("pkg: unknown subcommand '"); k_print(args); k_print("'\n");
    k_set_color(0x0F, 0x00);
    k_print("Type 'pkg help' for usage.\n");
}

/* ===========================================================================
 *  GRUGBOT420 — caveman-brain programming-wisdom chatbot
 *
 *  Mirror of apps/grugbot420.ltl.  Lateralus source is the design spec;
 *  this C stub is what the kernel actually executes.  Keyword dispatch,
 *  slash commands, xorshift PRNG for wisdom shuffling, /smoke mood
 *  escalator — all in pure freestanding C.
 * =========================================================================== */

/* VGA text attributes (fg | bg<<4) used by k_set_color */
#define GRUG_COL_DEFAULT  0x0F  /* white on black */
#define GRUG_COL_GRUG     0x0A  /* bright green   */
#define GRUG_COL_USER     0x09  /* bright blue    */
#define GRUG_COL_SYS      0x0E  /* yellow         */
#define GRUG_COL_SMOKE    0x0D  /* magenta / pink */
#define GRUG_COL_ERR      0x0C  /* red            */
#define GRUG_COL_BANNER   0x0B  /* cyan           */

typedef struct {
    uint32_t rng;     /* xorshift32 seed */
    int      mood;    /* 0 chill, 1 blazed, 2 enlightened */
    int      hits;    /* /smoke counter */
    int      running;
} GrugState;

static GrugState grug;

static const char *GRUG_WISDOM[] = {
    "grug say: complexity very very bad. simple good.",
    "grug say: factory factory factory pattern make grug head hurt.",
    "grug say: always name variable what it be. 'data' mean nothing.",
    "grug say: if code hard to delete, code already own you.",
    "grug say: type system friend, not enemy. type catch bug while grug sleep.",
    "grug brain small, so grug keep function small too.",
    "grug say: senior dev is one who know where bodies buried.",
    "grug say: meeting is where productivity go to die.",
    "grug say: ship small, ship often, fix in prod, grug not scared.",
    "grug say: premature optimization root of all bug. measure first.",
    "grug say: DRY is lie. same shape not same meaning. duplicate sometime ok.",
    "grug say: if test hard to write, code shape wrong.",
    "grug say: comment say WHY. code already say WHAT.",
    "grug say: log loud when bad, silent when good.",
};
#define GRUG_WISDOM_N  (int)(sizeof(GRUG_WISDOM)/sizeof(GRUG_WISDOM[0]))

static const char *GRUG_JOKES[] = {
    "why function cross road? because callback on other side.",
    "grug have 99 problem but null pointer not one. grug also have null pointer.",
    "programmer wife say: get bread, if egg, get 12. he come home with 12 bread.",
    "how many grug to change lightbulb? none. grug afraid of dark, live with it.",
    "grug try recursion to understand recursion. grug still trying.",
};
#define GRUG_JOKES_N  (int)(sizeof(GRUG_JOKES)/sizeof(GRUG_JOKES[0]))

static const char *GRUG_SMOKE[] = {
    "grug puff... whoa. semicolons are just fences for thoughts.",
    "grug puff... what if garbage collector is just... letting go?",
    "grug puff... monad is just burrito of sadness man.",
    "grug puff... every `for` loop is a tiny universe, bro.",
    "grug puff... types are vibes and vibes are types.",
    "grug puff... the real bug was the friends we made along the way.",
};
#define GRUG_SMOKE_N  (int)(sizeof(GRUG_SMOKE)/sizeof(GRUG_SMOKE[0]))

/* xorshift32 — deterministic, freestanding */
static uint32_t grug_rand(void) {
    uint32_t x = grug.rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    grug.rng = x;
    return x & 0x7fffffffu;
}

/* Case-insensitive substring check */
static int grug_contains(const char *hay, const char *needle) {
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

/* Match any of NULL-terminated needle list */
static int grug_contains_any(const char *hay, const char * const *needles) {
    for (int i = 0; needles[i]; i++)
        if (grug_contains(hay, needles[i])) return 1;
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

static void grug_print_prefix(uint8_t color, const char *speaker) {
    k_set_color(0x08, 0x00);
    k_print("[");
    k_set_color(color, 0x00);
    k_print(speaker);
    k_set_color(0x08, 0x00);
    k_print("] ");
    k_set_color(GRUG_COL_DEFAULT, 0x00);
}

static void grug_say(const char *text) {
    const char *name = (grug.mood >= 1) ? "grug420" : "grug";
    uint8_t col = (grug.mood >= 1) ? GRUG_COL_SMOKE : GRUG_COL_GRUG;
    grug_print_prefix(col, name);
    k_print(text);
    k_putc('\n');
}

static void grug_sys(const char *text) {
    grug_print_prefix(GRUG_COL_SYS, "sys");
    k_print(text);
    k_putc('\n');
}

static void grug_err(const char *text) {
    grug_print_prefix(GRUG_COL_ERR, "sys");
    k_print(text);
    k_putc('\n');
}

static void grug_banner(void) {
    k_set_color(GRUG_COL_BANNER, 0x00);
    k_print("+=====================================+\n");
    k_print("|    grugbot420 -- lateralus edition  |\n");
    k_print("|    small brain. big wisdom. 420.    |\n");
    k_print("+=====================================+\n");
    k_set_color(GRUG_COL_DEFAULT, 0x00);
}

/* Trim leading spaces in-place, strip trailing spaces too */
static char *grug_trim(char *s) {
    while (*s == ' ' || *s == '\t') s++;
    int n = k_strlen(s);
    while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\t')) { s[--n] = 0; }
    return s;
}

/* Slash-command handler.  Returns 1 if handled. */
static int grug_handle_cmd(const char *cmd) {
    if (grug_streq_ci(cmd, "/help")) {
        grug_sys("commands: /help /wisdom /joke /roll /smoke /time /quit");
        return 1;
    }
    if (grug_streq_ci(cmd, "/wisdom")) {
        grug_say(GRUG_WISDOM[grug_rand() % GRUG_WISDOM_N]);
        return 1;
    }
    if (grug_streq_ci(cmd, "/joke")) {
        grug_say(GRUG_JOKES[grug_rand() % GRUG_JOKES_N]);
        return 1;
    }
    if (grug_streq_ci(cmd, "/roll")) {
        int r = (int)(grug_rand() % 20) + 1;
        char buf[48];
        const char *p = "d20 rolls: ";
        int o = 0;
        for (int i = 0; p[i]; i++) buf[o++] = p[i];
        char nb[8]; ltl_itoa(r, nb, 8);
        for (int i = 0; nb[i]; i++) buf[o++] = nb[i];
        buf[o] = 0;
        grug_say(buf);
        return 1;
    }
    if (grug_streq_ci(cmd, "/smoke")) {
        grug.hits++;
        grug.mood = (grug.hits >= 3) ? 2 : 1;
        grug_print_prefix(GRUG_COL_SMOKE, "grug420");
        k_print("*puff puff pass*\n");
        grug_say(GRUG_SMOKE[grug_rand() % GRUG_SMOKE_N]);
        if (grug.mood == 2) {
            grug_print_prefix(GRUG_COL_SMOKE, "grug420");
            k_print("grug ascend. grug see the monad now.\n");
        }
        return 1;
    }
    if (grug_streq_ci(cmd, "/time")) {
        char buf[64];
        const char *p = "ticks since boot: ";
        int o = 0;
        for (int i = 0; p[i]; i++) buf[o++] = p[i];
        char nb[24]; ltl_itoa((int)(tick_count & 0x7fffffff), nb, 24);
        for (int i = 0; nb[i]; i++) buf[o++] = nb[i];
        buf[o] = 0;
        grug_sys(buf);
        return 1;
    }
    if (grug_streq_ci(cmd, "/quit") || grug_streq_ci(cmd, "/exit")) {
        grug_say("grug out. keep code small friend.");
        grug.running = 0;
        return 1;
    }
    grug_err("unknown command. try /help");
    return 1;
}

/* Top-level response logic — mirrors respond() in grugbot420.ltl */
static void grug_respond(const char *line) {
    if (line[0] == '/') { grug_handle_cmd(line); return; }

    static const char * const HI[]        = {"hi", "hello", "hey", "sup", "yo", NULL};
    static const char * const BUG[]       = {"bug", "crash", "broken", "panic", NULL};
    static const char * const COMPLEX[]   = {"complex", "overengineer", "abstract", NULL};
    static const char * const SHIP[]      = {"ship", "deploy", "release", "prod", NULL};
    static const char * const TEST[]      = {"test", "tdd", "unit", NULL};
    static const char * const REFAC[]     = {"refactor", "rewrite", NULL};
    static const char * const OOP[]       = {"oop", "inherit", "class", NULL};
    static const char * const MEETING[]   = {"meeting", "standup", "agile", NULL};
    static const char * const PERF[]      = {"perf", "slow", "fast", "optim", NULL};
    static const char * const TYPES[]     = {"type", "typescript", "rust", NULL};
    static const char * const AI[]        = {"ai", "llm", "copilot", "gpt", NULL};
    static const char * const FRIDAY[]    = {"friday", "weekend", NULL};
    static const char * const WEED[]      = {"weed", "420", "blaze", "smoke", "sesh", NULL};
    static const char * const WISDOM_K[]  = {"wisdom", "advice", "help me", NULL};
    static const char * const JOKE_K[]    = {"joke", "funny", NULL};
    static const char * const THANKS[]    = {"thanks", "thank you", " ty", "love you", NULL};
    static const char * const BYE[]       = {"bye", "cya", "later", "goodbye", NULL};

    if (grug_contains_any(line, HI)) {
        grug_say("hi friend. grug here. what on brain?");
        return;
    }
    if (grug_contains_any(line, BUG)) {
        static const char *replies[] = {
            "bug not personal. bug just code telling truth.",
            "read stack trace top-down. grug promise answer in there.",
            "print statement older than grug. print statement still work.",
        };
        grug_say(replies[grug_rand() % 3]); return;
    }
    if (grug_contains_any(line, COMPLEX)) {
        grug_say("complexity demon love abstract factory. delete layer. grug happy.");
        return;
    }
    if (grug_contains_any(line, SHIP)) {
        grug_say("ship it. worst case: rollback. best case: user smile.");
        return;
    }
    if (grug_contains_any(line, TEST)) {
        grug_say("test is rope grug tie to past self. test save future grug.");
        return;
    }
    if (grug_contains_any(line, REFAC)) {
        grug_say("rewrite from scratch is trap. refactor in small step. commit often.");
        return;
    }
    if (grug_contains_any(line, OOP)) {
        grug_say("inheritance tree grow tall. composition tree grow wide. wide better.");
        return;
    }
    if (grug_contains_any(line, MEETING)) {
        grug_say("meeting should be email. email should be nothing. grug need code time.");
        return;
    }
    if (grug_contains_any(line, PERF)) {
        grug_say("measure. measure again. THEN optimize hottest spot. not before.");
        return;
    }
    if (grug_contains_any(line, TYPES)) {
        grug_say("type system is exoskeleton. feel heavy at first. then grug run fast.");
        return;
    }
    if (grug_contains_any(line, AI)) {
        grug_say("llm is clever parrot. good for first draft, bad for last draft.");
        return;
    }
    if (grug_contains_any(line, FRIDAY)) {
        grug_say("no deploy friday. grug want pizza not pager.");
        return;
    }
    if (grug_contains_any(line, WEED)) {
        grug_handle_cmd("/smoke"); return;
    }
    if (grug_contains_any(line, WISDOM_K)) {
        grug_handle_cmd("/wisdom"); return;
    }
    if (grug_contains_any(line, JOKE_K)) {
        grug_handle_cmd("/joke"); return;
    }
    if (grug_contains_any(line, THANKS)) {
        grug_say("grug love you too, stay hydrated, stay small-function.");
        return;
    }
    if (grug_contains_any(line, BYE)) {
        grug_say("peace friend. grug return to cave now.");
        grug.running = 0;
        return;
    }

    /* Fallback — dispense wisdom */
    grug_say(GRUG_WISDOM[grug_rand() % GRUG_WISDOM_N]);
}

void cmd_grugbot(const char *args) {
    serial_puts("[grugbot420] starting\n");

    /* Seed PRNG from tick_count so each invocation feels different */
    k_memset(&grug, 0, sizeof(grug));
    uint32_t seed = (uint32_t)(tick_count ^ 0x420BADA5u);
    if (seed == 0) seed = 0x420BADA5u;
    grug.rng = seed;
    grug.running = 1;

    /* One-shot mode: `grugbot wisdom` / `grugbot joke` */
    char tmp[64];
    int ti = 0;
    while (args[ti] && ti < 63) { tmp[ti] = args[ti]; ti++; }
    tmp[ti] = 0;
    char *a = grug_trim(tmp);

    if (k_strcmp(a, "wisdom") == 0) {
        grug_say(GRUG_WISDOM[grug_rand() % GRUG_WISDOM_N]);
        serial_puts("[grugbot420] one-shot wisdom\n");
        return;
    }
    if (k_strcmp(a, "joke") == 0) {
        grug_say(GRUG_JOKES[grug_rand() % GRUG_JOKES_N]);
        serial_puts("[grugbot420] one-shot joke\n");
        return;
    }

    /* Interactive REPL */
    grug_banner();
    grug_say("hi. grug here. type /help or just talk. grug listen.");

    char line_buf[256];
    while (grug.running) {
        k_set_color(GRUG_COL_USER, 0x00);
        k_print("you");
        k_set_color(0x07, 0x00);
        k_print("> ");
        k_set_color(GRUG_COL_DEFAULT, 0x00);

        int shift = 0;
        int lp = app_read_line(line_buf, sizeof(line_buf), &shift);
        if (lp < 0) { grug.running = 0; break; }   /* Esc = quit */
        if (lp == 0) continue;

        char *trimmed = grug_trim(line_buf);
        if (*trimmed == 0) continue;

        grug_respond(trimmed);
    }

    k_set_color(GRUG_COL_SMOKE, 0x00);
    k_print("grugbot420 signing off. stay small-brained, friend.\n");
    k_set_color(GRUG_COL_DEFAULT, 0x00);
    serial_puts("[grugbot420] exited\n");
}
