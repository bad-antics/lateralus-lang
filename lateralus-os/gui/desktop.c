/* =======================================================================
 * LateralusOS — Desktop Environment Implementation
 * ======================================================================= */

#include "desktop.h"
#include "terminal.h"
#include "../fs/ramfs.h"
#include "../drivers/speaker.h"
#include "../kernel/tasks.h"

/* -- Tiny helpers ------------------------------------------------------- */

static void _dscpy(char *dst, const char *src, int max) {
    int i = 0;
    while (src[i] && i < max - 1) { dst[i] = src[i]; i++; }
    dst[i] = 0;
}

static int _dlen(const char *s) { int n = 0; while (s[n]) n++; return n; }

static int _dstreq(const char *a, const char *b) {
    while (*a && *b) { if (*a != *b) return 0; a++; b++; }
    return *a == *b;
}

static void _dcat(char *dst, const char *src, int max) {
    int n = _dlen(dst);
    int i = 0;
    while (src[i] && n + i < max - 1) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

static void _ditoa(uint64_t val, char *buf, int buflen) {
    int pos = 0;
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char rev[24]; int rp = 0;
    while (val > 0 && rp < 23) { rev[rp++] = '0' + (val % 10); val /= 10; }
    while (rp > 0 && pos < buflen - 1) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
}

/* -- Global desktop pointer (for menu callbacks) ------------------------ */

static Desktop *g_desktop = 0;

/* -- Menu action callbacks ---------------------------------------------- */

static void action_open_terminal(void *ctx) {
    (void)ctx;
    if (g_desktop) desktop_open_terminal(g_desktop);
}

static void action_open_about(void *ctx) {
    (void)ctx;
    if (g_desktop) desktop_open_about(g_desktop);
}

static void action_open_sysmon(void *ctx) {
    (void)ctx;
    if (g_desktop) desktop_open_sysmon(g_desktop);
}

static void action_open_readme(void *ctx) {
    (void)ctx;
    if (g_desktop) {
        desktop_open_file_viewer(g_desktop, "README",
            "LateralusOS v0.2.0\n"
            "==================\n"
            "\n"
            "A bare-metal operating system built\n"
            "with the Lateralus language.\n"
            "\n"
            "Boot: Multiboot2 → GRUB2 → x86_64\n"
            "GUI:  1024x768 framebuffer, double-buffered\n"
            "Theme: Catppuccin Mocha\n"
            "\n"
            "Keyboard Shortcuts:\n"
            "  Ctrl+T   Open Terminal\n"
            "  Ctrl+A   Open About\n"
            "  Ctrl+S   Open System Monitor\n"
            "  Ctrl+G   Open grugbot420\n"
            "  ESC      Exit GUI → text shell\n"
            "\n"
            "Copyright (c) 2025 bad-antics\n"
            "Spiral Out, Keep Going"
        );
    }
}

/* -- grugbot420 launcher: opens a terminal + auto-starts grug ---------- */

static void action_open_grugbot(void *ctx) {
    (void)ctx;
    if (!g_desktop) return;
    int tidx = term_create(&g_desktop->gui);
    if (tidx < 0) return;
    /* Rename window so it's clearly grugbot */
    if (tidx < MAX_WINDOWS) {
        /* Find the window we just created (most recent terminal) */
        for (int i = g_desktop->gui.window_count - 1; i >= 0; i--) {
            if (g_desktop->gui.windows[i].is_terminal) {
                _dscpy(g_desktop->gui.windows[i].title, "grugbot420", 64);
                break;
            }
        }
    }
    term_start_grugbot(tidx);
    extern volatile uint64_t tick_count;
    speaker_window_open(tick_count);
}

/* -- Additional info-window launchers ---------------------------------- */

static void action_open_files(void *ctx) {
    (void)ctx;
    if (!g_desktop) return;
    desktop_open_file_viewer(g_desktop, "Files",
        "LateralusFS -- RAM File System\n"
        "==============================\n"
        "\n"
        "Directories:\n"
        "  /         root\n"
        "  /home     user files\n"
        "  /proc     process info (auto-generated)\n"
        "  /dev      device nodes\n"
        "  /tmp      scratch space\n"
        "\n"
        "Use Terminal + 'ls' / 'cat' / 'cd' to\n"
        "navigate.\n"
    );
}

static void action_open_editor(void *ctx) {
    (void)ctx;
    if (!g_desktop) return;
    desktop_open_file_viewer(g_desktop, "ltled Editor",
        "ltled -- Retro Text Editor\n"
        "==========================\n"
        "\n"
        "Mode-based editor with syntax\n"
        "highlighting for Lateralus.\n"
        "\n"
        "GUI port in progress. Launch from\n"
        "text shell:\n"
        "  1. Press ESC to exit the GUI\n"
        "  2. Run:  edit <filename>\n"
        "\n"
        "Supported file types: .ltl, .md,\n"
        ".txt, .cfg\n"
    );
}

static void action_open_chat(void *ctx) {
    (void)ctx;
    if (!g_desktop) return;
    desktop_open_file_viewer(g_desktop, "ltlchat",
        "ltlchat -- IRC-style Chat Client\n"
        "================================\n"
        "\n"
        "Terminal chat client with local\n"
        "loopback bot and (future) TCP\n"
        "network mode.\n"
        "\n"
        "Launch from text shell:\n"
        "  1. Press ESC to exit the GUI\n"
        "  2. Run:  chat\n"
        "\n"
        "Commands: /nick /join /msg /quit\n"
        "          /users /help\n"
    );
}

static void action_open_calc(void *ctx) {
    (void)ctx;
    if (!g_desktop) return;
    desktop_open_file_viewer(g_desktop, "Calculator",
        "Calculator\n"
        "==========\n"
        "\n"
        " Scientific calculator with memory\n"
        " and history.\n"
        "\n"
        " Keys: 0-9 . + - * /  = C  sqrt\n"
        "       sin cos tan log ln pi e\n"
        "\n"
        " (GUI buttons forthcoming -- type\n"
        "  expressions via keyboard for now)\n"
    );
}

static void action_open_ltlc(void *ctx) {
    (void)ctx;
    if (!g_desktop) return;
    desktop_open_file_viewer(g_desktop, "ltlc Compiler",
        "ltlc -- Lateralus Compiler\n"
        "==========================\n"
        "\n"
        "Built-in lexer + static analyzer\n"
        "for .ltl sources.\n"
        "\n"
        "Launch from text shell:\n"
        "  ltlc <file.ltl>  analyze a file\n"
        "  ltlc repl        interactive REPL\n"
        "\n"
        "Reports token, function, struct,\n"
        "and binding counts.\n"
    );
}

static void action_open_package(void *ctx) {
    (void)ctx;
    if (!g_desktop) return;
    desktop_open_file_viewer(g_desktop, "Package Manager",
        "pkg -- Package Manager\n"
        "======================\n"
        "\n"
        "Launch from text shell:\n"
        "  pkg list            installed\n"
        "  pkg install <name>  add package\n"
        "  pkg build           compile src\n"
        "  pkg init <name>     new project\n"
    );
}

/* -- Setup start menu --------------------------------------------------- */

void desktop_setup_menus(Desktop *dt) {
    Menu *sm = &dt->gui.start_menu;
    sm->item_count = 0;
    gui_add_menu_item(sm, "Terminal",       COL_BLACK,    action_open_terminal);
    gui_add_menu_item(sm, "grugbot420",     COL_ACCENT2,  action_open_grugbot);
    gui_add_menu_item(sm, "Files",          COL_ACCENT3,  action_open_files);
    gui_add_menu_item(sm, "ltled Editor",   COL_ACCENT,   action_open_editor);
    gui_add_menu_item(sm, "ltlchat",        COL_ACCENT4,  action_open_chat);
    gui_add_menu_item(sm, "Calculator",     COL_LAVENDER, action_open_calc);
    gui_add_menu_item(sm, "ltlc Compiler",  COL_ACCENT,   action_open_ltlc);
    gui_add_menu_item(sm, "Packages",       COL_ACCENT3,  action_open_package);
    gui_add_menu_item(sm, "System Monitor", COL_ACCENT2,  action_open_sysmon);
    gui_add_menu_item(sm, "README",         COL_ACCENT3,  action_open_readme);
    gui_add_menu_item(sm, "About",          COL_ACCENT,   action_open_about);

    Menu *cm = &dt->gui.context_menu;
    cm->item_count = 0;
    gui_add_menu_item(cm, "New Terminal",    COL_BLACK,    action_open_terminal);
    gui_add_menu_item(cm, "grugbot420",      COL_ACCENT2,  action_open_grugbot);
    gui_add_menu_item(cm, "Files",           COL_ACCENT3,  action_open_files);
    gui_add_menu_item(cm, "System Monitor",  COL_ACCENT2,  action_open_sysmon);
    gui_add_menu_item(cm, "About",           COL_ACCENT,   action_open_about);
    gui_add_menu_item(cm, "README",          COL_ACCENT3,  action_open_readme);
}

/* -- Desktop icon callbacks --------------------------------------------- */

static void icon_terminal(void *ctx) { (void)ctx; action_open_terminal(0); }
static void icon_sysmon(void *ctx)   { (void)ctx; action_open_sysmon(0); }
static void icon_about(void *ctx)    { (void)ctx; action_open_about(0); }
static void icon_readme(void *ctx)   { (void)ctx; action_open_readme(0); }
static void icon_grugbot(void *ctx)  { (void)ctx; action_open_grugbot(0); }
static void icon_files(void *ctx)    { (void)ctx; action_open_files(0); }
static void icon_editor(void *ctx)   { (void)ctx; action_open_editor(0); }
static void icon_chat(void *ctx)     { (void)ctx; action_open_chat(0); }
static void icon_calc(void *ctx)     { (void)ctx; action_open_calc(0); }
static void icon_ltlc(void *ctx)     { (void)ctx; action_open_ltlc(0); }
static void icon_pkg(void *ctx)      { (void)ctx; action_open_package(0); }

void desktop_setup_icons(Desktop *dt) {
    int32_t ix = 24, iy = 24;
    int32_t spacing = ICON_SIZE + ICON_PAD + FONT_H + 8;

    /* Column 1 — system apps */
    gui_add_icon(&dt->gui, ix, iy,                 "Terminal",  '>',  COL_BLACK,    icon_terminal, 0);
    gui_add_icon(&dt->gui, ix, iy + spacing,       "grugbot",   '4',  COL_ACCENT2,  icon_grugbot,  0);
    gui_add_icon(&dt->gui, ix, iy + spacing * 2,   "Files",     'F',  COL_ACCENT3,  icon_files,    0);
    gui_add_icon(&dt->gui, ix, iy + spacing * 3,   "Editor",    'E',  COL_ACCENT,   icon_editor,   0);
    gui_add_icon(&dt->gui, ix, iy + spacing * 4,   "Chat",      'C',  COL_ACCENT4,  icon_chat,     0);

    /* Column 2 — tools */
    int32_t ix2 = ix + ICON_SIZE + ICON_PAD * 2 + 48;
    gui_add_icon(&dt->gui, ix2, iy,                "Calc",      '=',  COL_LAVENDER, icon_calc,     0);
    gui_add_icon(&dt->gui, ix2, iy + spacing,      "ltlc",      'L',  COL_ACCENT,   icon_ltlc,     0);
    gui_add_icon(&dt->gui, ix2, iy + spacing * 2,  "Packages",  'P',  COL_ACCENT3,  icon_pkg,      0);
    gui_add_icon(&dt->gui, ix2, iy + spacing * 3,  "Monitor",   '#',  COL_ACCENT2,  icon_sysmon,   0);
    gui_add_icon(&dt->gui, ix2, iy + spacing * 4,  "README",    'R',  COL_ACCENT3,  icon_readme,   0);

    /* Also keep an About icon handy */
    gui_add_icon(&dt->gui, ix2, iy + spacing * 5,  "About",     '?',  COL_ACCENT,   icon_about,    0);
}

/* -- Initialize desktop ------------------------------------------------ */

void desktop_init(Desktop *dt) {
    if (!dt) return;
    dt->mode         = 1;   /* GUI mode */
    dt->frame_count  = 0;
    dt->uptime_ticks = 0;
    dt->sysmon_idx   = -1;
    dt->alt_held     = 0;
    dt->ctrl_held    = 0;
    g_desktop        = dt;

    gui_init(&dt->gui);

    /* Initialize subsystems */
    term_init();

    /* Setup menus and icons */
    desktop_setup_menus(dt);
    desktop_setup_icons(dt);

    /* Open a welcome "About" window by default */
    desktop_open_about(dt);

    /* And spin up grugbot420 so its interface is visible on desktop */
    action_open_grugbot(0);
}

/* -- Find existing window by title and focus it ------------------------- */

static int _focus_existing(GuiContext *gui, const char *title) {
    for (int i = 0; i < gui->window_count; i++) {
        Window *w = &gui->windows[i];
        /* Skip invisible or closing windows */
        if (!w->visible || w->anim_state == 2) continue;
        if (!_dstreq(w->title, title)) continue;
        /* Found — cancel any animation, un-minimize, focus */
        w->minimized  = 0;
        w->anim_state = 0;
        w->anim_frame = 0;
        for (int j = 0; j < gui->window_count; j++)
            gui->windows[j].focused = 0;
        w->focused = 1;
        gui->focus_idx = i;
        return 1;
    }
    return 0;
}

/* -- Open "About LateralusOS" ------------------------------------------- */

void desktop_open_about(Desktop *dt) {
    /* Reuse existing window if open */
    if (_focus_existing(&dt->gui, "About LateralusOS")) return;

    int idx = gui_create_window(&dt->gui, "About LateralusOS",
                                 120, 80, 500, 340);
    if (idx < 0) return;

    gui_set_content(&dt->gui, idx,
        "LateralusOS v0.2.0\n"
        "Spiral Out, Keep Going\n"
        "\n"
        "A bare-metal operating system built\n"
        "with the Lateralus programming language.\n"
        "\n"
        "Features:\n"
        "  - x86_64 long mode (4 GB mapped)\n"
        "  - Multiboot2 / GRUB2 boot\n"
        "  - Framebuffer GUI (1024x768x32)\n"
        "  - Double-buffered rendering\n"
        "  - Gradient wallpaper + animated spirals\n"
        "  - Catppuccin Mocha theme v2\n"
        "  - Window manager + drag/resize\n"
        "  - macOS traffic light buttons w/ glyphs\n"
        "  - Start menu + context menu\n"
        "  - Desktop icons\n"
        "  - PS/2 mouse + keyboard\n"
        "  - RAM filesystem\n"
        "  - Interactive terminal (ltlsh)\n"
        "  - Cooperative task scheduler\n"
        "  - PC speaker audio\n"
        "\n"
        "Copyright (c) 2025-2026 bad-antics"
    );
}

/* -- Open terminal window — functional terminal ------------------------- */

void desktop_open_terminal(Desktop *dt) {
    int tidx = term_create(&dt->gui);
    if (tidx < 0) {
        /* Fallback: cosmetic terminal */
        int idx = gui_create_window(&dt->gui, "Terminal",
                                     80, 120, 600, 400);
        if (idx < 0) return;
        dt->gui.windows[idx].body_bg = COL_BLACK;
        gui_set_content(&dt->gui, idx,
            "ltlsh 0.2.0 -- LateralusOS Shell\n"
            "Error: max terminals reached.\n"
            "lateralus> _"
        );
    }
    /* Play window-open sound */
    extern volatile uint64_t tick_count;
    speaker_window_open(tick_count);
}

/* -- Open system monitor ------------------------------------------------ */

void desktop_open_sysmon(Desktop *dt) {
    /* Reuse existing window if open */
    if (_focus_existing(&dt->gui, "System Monitor")) return;

    int idx = gui_create_window(&dt->gui, "System Monitor",
                                 250, 60, 480, 380);
    if (idx < 0) return;

    dt->sysmon_idx = idx;
    dt->gui.windows[idx].body_bg = COL_BG_DARKER;

    gui_set_content(&dt->gui, idx,
        "System Monitor\n"
        "==============================\n"
        "\n"
        "CPU:      x86_64 (long mode)\n"
        "Memory:   256 MB (4 GB identity-mapped)\n"
        "Heap:     Active (bump allocator)\n"
        "Timer:    PIT @ 1000 Hz\n"
        "Display:  1024x768x32 framebuffer\n"
        "Renderer: Double-buffered (RAM backbuf)\n"
        "Input:    PS/2 keyboard + mouse\n"
        "Storage:  RAM filesystem (64 inodes)\n"
        "Tasks:    Cooperative scheduler\n"
        "\n"
        "Uptime:   0s\n"
        "Frames:   0\n"
        "\n"
        "Kernel: lateralus-kernel 0.1.0\n"
        "Shell:  ltlsh 0.1.0"
    );
}

/* -- Open file viewer --------------------------------------------------- */

void desktop_open_file_viewer(Desktop *dt, const char *name, const char *content) {
    /* Reuse existing window if same name is open */
    if (_focus_existing(&dt->gui, name)) return;

    int idx = gui_create_window(&dt->gui, name,
                                 200, 60, 550, 450);
    if (idx < 0) return;
    gui_set_content(&dt->gui, idx, content);
}

/* -- Update system monitor content -------------------------------------- */

static void desktop_update_sysmon(Desktop *dt) {
    if (dt->sysmon_idx < 0 || dt->sysmon_idx >= dt->gui.window_count) {
        dt->sysmon_idx = -1;
        return;
    }
    Window *win = &dt->gui.windows[dt->sysmon_idx];
    if (!win->visible || !_dstreq(win->title, "System Monitor")) {
        dt->sysmon_idx = -1;
        return;
    }

    char buf[2048];
    char num[24];
    buf[0] = 0;

    _dcat(buf, "System Monitor\n", 2048);
    _dcat(buf, "\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\x1a\n", 2048);
    _dcat(buf, "\n", 2048);
    _dcat(buf, "CPU:      x86_64 (long mode)\n", 2048);
    _dcat(buf, "Memory:   256 MB (4 GB identity-mapped)\n", 2048);
    _dcat(buf, "Heap:     Active (bump allocator)\n", 2048);
    _dcat(buf, "Timer:    PIT @ 1000 Hz\n", 2048);
    _dcat(buf, "Display:  1024x768x32 framebuffer\n", 2048);
    _dcat(buf, "Renderer: Double-buffered (RAM backbuf)\n", 2048);
    _dcat(buf, "Input:    PS/2 keyboard + mouse\n", 2048);
    _dcat(buf, "Storage:  RAM filesystem (64 inodes)\n", 2048);
    _dcat(buf, "Tasks:    Cooperative scheduler\n", 2048);
    _dcat(buf, "\n", 2048);

    _dcat(buf, "Uptime:   ", 2048);
    uint32_t secs = dt->uptime_ticks / 1000;
    uint32_t mins = secs / 60;
    uint32_t hours = mins / 60;
    if (hours > 0) {
        _ditoa(hours, num, 24); _dcat(buf, num, 2048); _dcat(buf, "h ", 2048);
    }
    _ditoa(mins % 60, num, 24); _dcat(buf, num, 2048); _dcat(buf, "m ", 2048);
    _ditoa(secs % 60, num, 24); _dcat(buf, num, 2048); _dcat(buf, "s\n", 2048);

    _dcat(buf, "Frames:   ", 2048);
    _ditoa(dt->frame_count, num, 24); _dcat(buf, num, 2048);
    _dcat(buf, "\n", 2048);

    _dcat(buf, "\nKernel: lateralus-kernel 0.1.0\n", 2048);
    _dcat(buf, "Shell:  ltlsh 0.1.0", 2048);

    _dscpy(win->content, buf, 2048);
}

/* -- Update notification tray ------------------------------------------- */

static void desktop_update_notif(Desktop *dt) {
    char status[64];
    char num[16];
    status[0] = 0;

    _dcat(status, "UP:", 64);
    uint32_t secs = dt->uptime_ticks / 1000;
    _ditoa(secs / 60, num, 16); _dcat(status, num, 64);
    _dcat(status, "m  FPS:", 64);
    /* Approximate FPS from frame_count and uptime */
    if (secs > 0) {
        _ditoa(dt->frame_count / secs, num, 16);
    } else {
        _dscpy(num, "60", 16);
    }
    _dcat(status, num, 64);

    gui_set_notif(&dt->gui, status);
}

/* -- Desktop tick (called from timer) ----------------------------------- */

void desktop_tick(Desktop *dt) {
    if (!dt) return;
    dt->uptime_ticks++;
    gui_tick(&dt->gui);

    /* Tick speaker */
    speaker_tick((uint64_t)dt->uptime_ticks);

    /* Tick task scheduler */
    tasks_tick((uint64_t)dt->uptime_ticks);

    /* Tick all terminals (cursor blink) */
    for (int w = 0; w < dt->gui.window_count; w++) {
        if (dt->gui.windows[w].is_terminal && dt->gui.windows[w].visible) {
            GuiTerminal *t = term_get_by_window(w);
            if (t) {
                term_tick(t, dt->uptime_ticks);
                term_refresh(t, &dt->gui);
            }
        }
    }

    /* Update clock every ~1000 ticks (assuming 1kHz PIT) */
    if (dt->uptime_ticks % 1000 == 0) {
        gui_update_clock(&dt->gui, dt->uptime_ticks / 1000);
    }

    /* Update system monitor every ~2000 ticks (~2s) */
    if (dt->uptime_ticks % 2000 == 0) {
        desktop_update_sysmon(dt);
        desktop_update_notif(dt);
    }

    /* Detect if any window is being dragged or resized */
    int drag_active = 0;
    for (int i = 0; i < dt->gui.window_count && !drag_active; i++) {
        if (dt->gui.windows[i].dragging || dt->gui.windows[i].resizing)
            drag_active = 1;
    }

    /* Re-render at higher frequency during drags (every 2 ticks ≈ 500 FPS)
     * to keep the window visually tracking the cursor without ghosting.
     * Normal mode: every 16 ticks (~60 FPS). */
    int render_interval = drag_active ? 2 : 16;
    if (dt->uptime_ticks % render_interval == 0) {
        desktop_render(dt);
        dt->frame_count++;
    }
}

/* -- Mouse event -------------------------------------------------------- */

void desktop_mouse_event(Desktop *dt, int8_t dx, int8_t dy,
                          uint8_t left, uint8_t right) {
    if (!dt) return;
    gui_handle_mouse_move(&dt->gui, (int32_t)dx, -(int32_t)dy);
    gui_handle_mouse_click(&dt->gui, left, right);
}

/* -- Keyboard event ----------------------------------------------------- */

void desktop_key_event(Desktop *dt, char ascii) {
    if (!dt) return;
    /* Ctrl+T = open terminal */
    if (ascii == 20) {  /* ASCII 20 = ^T */
        desktop_open_terminal(dt);
        return;
    }
    /* Ctrl+A = open about */
    if (ascii == 1) {   /* ASCII 1 = ^A */
        desktop_open_about(dt);
        return;
    }
    /* Ctrl+S = open system monitor */
    if (ascii == 19) {  /* ASCII 19 = ^S */
        desktop_open_sysmon(dt);
        return;
    }
    /* Ctrl+G = launch grugbot420 */
    if (ascii == 7) {   /* ASCII 7 = ^G */
        action_open_grugbot(0);
        return;
    }

    /* Route to terminal if focused window is a terminal */
    if (dt->gui.focus_idx >= 0 && dt->gui.focus_idx < dt->gui.window_count) {
        Window *win = &dt->gui.windows[dt->gui.focus_idx];
        if (win->visible && !win->minimized && win->is_terminal) {
            GuiTerminal *t = term_get_by_window(dt->gui.focus_idx);
            if (t) {
                term_key(t, ascii);
                t->dirty = 1;
                return;
            }
        }
    }

    gui_handle_key(&dt->gui, ascii);
}

/* -- Full render -------------------------------------------------------- */

void desktop_render(Desktop *dt) {
    if (!dt || !fb.available) return;
    gui_render_all(&dt->gui);
}
