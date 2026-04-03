/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — GUI Widget System Implementation
 * ═══════════════════════════════════════════════════════════════════════
 * Renders windows with macOS-style title bars, a bottom taskbar with
 * clock, desktop wallpaper gradient, and mouse cursor.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "gui.h"

/* ── Tiny string helpers (no libc) ────────────────────────────────────── */

static int _slen(const char *s) { int n = 0; while (s[n]) n++; return n; }

static void _scpy(char *dst, const char *src, int max) {
    int i = 0;
    while (src[i] && i < max - 1) { dst[i] = src[i]; i++; }
    dst[i] = 0;
}

static void _scat(char *dst, const char *src, int max) {
    int n = _slen(dst);
    int i = 0;
    while (src[i] && n + i < max - 1) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

/* ── Number → string (for clock) ──────────────────────────────────────── */

static void _itoa2(int val, char *buf) {
    buf[0] = '0' + (val / 10) % 10;
    buf[1] = '0' + val % 10;
    buf[2] = 0;
}

/* ── Initialization ───────────────────────────────────────────────────── */

void gui_init(GuiContext *ctx) {
    if (!ctx) return;
    for (int i = 0; i < MAX_WINDOWS; i++)  ctx->windows[i].visible = 0;
    for (int i = 0; i < MAX_BUTTONS; i++)  ctx->buttons[i].visible = 0;
    for (int i = 0; i < MAX_LABELS; i++)   ctx->labels[i].visible  = 0;

    ctx->window_count = 0;
    ctx->button_count = 0;
    ctx->label_count  = 0;
    ctx->icon_count   = 0;
    ctx->focus_idx    = -1;
    ctx->running      = 1;
    ctx->tick         = 0;

    /* Taskbar */
    ctx->taskbar.y  = (int32_t)fb.height - TASKBAR_H;
    ctx->taskbar.bg = COL_TASKBAR;
    ctx->taskbar.start_hovered = 0;
    _scpy(ctx->taskbar.clock_str, "00:00", 16);

    /* Mouse — center of screen */
    ctx->mouse.x        = (int32_t)fb.width / 2;
    ctx->mouse.y        = (int32_t)fb.height / 2;
    ctx->mouse.left_btn = 0;
    ctx->mouse.right_btn = 0;
    ctx->mouse.prev_left = 0;
    ctx->mouse.prev_right = 0;

    /* Start menu */
    ctx->start_menu.x = 4;
    ctx->start_menu.y = 0;   /* computed when shown */
    ctx->start_menu.w = MENU_W;
    ctx->start_menu.item_count = 0;
    ctx->start_menu.visible = 0;
    ctx->start_menu.hover_idx = -1;

    /* Context menu */
    ctx->context_menu.x = 0;
    ctx->context_menu.y = 0;
    ctx->context_menu.w = MENU_W;
    ctx->context_menu.item_count = 0;
    ctx->context_menu.visible = 0;
    ctx->context_menu.hover_idx = -1;

    /* Notification tray */
    ctx->notif.status[0] = 0;
    ctx->notif.fg = COL_SUBTEXT;

    /* Alt+Tab switcher */
    ctx->tab_visible = 0;
    ctx->tab_idx     = 0;

    /* Wallpaper animation */
    ctx->wallpaper_phase = 0;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Window Management
 * ═══════════════════════════════════════════════════════════════════════ */

int gui_create_window(GuiContext *ctx, const char *title,
                      int32_t x, int32_t y, int32_t w, int32_t h) {
    /* First try to reuse a closed (invisible) window slot */
    int idx = -1;
    for (int i = 0; i < ctx->window_count; i++) {
        if (!ctx->windows[i].visible && ctx->windows[i].anim_state == 0) {
            idx = i;
            break;
        }
    }
    /* No free slot — allocate a new one if room */
    if (idx < 0) {
        if (ctx->window_count >= MAX_WINDOWS) return -1;
        idx = ctx->window_count++;
    }
    Window *win = &ctx->windows[idx];

    win->x = x;  win->y = y;  win->w = w;  win->h = h;
    _scpy(win->title, title, 64);
    win->visible   = 1;
    win->focused   = 1;
    win->minimized = 0;
    win->dragging  = 0;
    win->resizing  = 0;
    win->min_w     = 200;
    win->min_h     = 150;
    win->content_scroll = 0;
    win->content[0] = 0;

    /* Animation — start with opening animation */
    win->anim_state = 1;   /* opening */
    win->anim_frame = 0;

    /* Terminal flag (set by caller if needed) */
    win->is_terminal = 0;

    /* Colors */
    win->title_bg     = COL_TITLE_BG;
    win->title_fg     = COL_TEXT;
    win->body_bg      = COL_SURFACE0;
    win->border_color = COL_OVERLAY0;

    /* Title-bar button positions (relative to window) */
    win->btn_close_x = win->x + 14;
    win->btn_close_y = win->y + TITLE_BAR_H / 2;
    win->btn_min_x   = win->x + 34;
    win->btn_min_y   = win->y + TITLE_BAR_H / 2;
    win->btn_max_x   = win->x + 54;
    win->btn_max_y   = win->y + TITLE_BAR_H / 2;

    /* Defocus all others */
    for (int i = 0; i < ctx->window_count - 1; i++)
        ctx->windows[i].focused = 0;
    ctx->focus_idx = idx;

    return idx;
}

void gui_close_window(GuiContext *ctx, int idx) {
    if (idx < 0 || idx >= ctx->window_count) return;
    Window *win = &ctx->windows[idx];
    if (!win->visible) return;
    if (win->anim_state == 2) {
        /* Already closing — force immediate close */
        win->visible = 0;
        win->anim_state = 0;
        win->anim_frame = 0;
        if (ctx->focus_idx == idx) ctx->focus_idx = -1;
        return;
    }
    /* Start closing animation */
    win->anim_state = 2;
    win->anim_frame = 0;
}

void gui_minimize_window(GuiContext *ctx, int idx) {
    if (idx < 0 || idx >= ctx->window_count) return;
    /* Start minimize animation */
    ctx->windows[idx].anim_state = 3;
    ctx->windows[idx].anim_frame = 0;
}

void gui_set_content(GuiContext *ctx, int idx, const char *text) {
    if (idx < 0 || idx >= ctx->window_count) return;
    _scpy(ctx->windows[idx].content, text, 2048);
}

/* ═══════════════════════════════════════════════════════════════════════
 * Buttons & Labels
 * ═══════════════════════════════════════════════════════════════════════ */

int gui_create_button(GuiContext *ctx, int32_t x, int32_t y,
                      int32_t w, int32_t h, const char *label,
                      ButtonCallback cb, void *data) {
    if (ctx->button_count >= MAX_BUTTONS) return -1;
    int idx = ctx->button_count++;
    Button *btn = &ctx->buttons[idx];
    btn->x = x;  btn->y = y;  btn->w = w;  btn->h = h;
    _scpy(btn->label, label, 64);
    btn->bg       = COL_SURFACE1;
    btn->fg       = COL_TEXT;
    btn->hover_bg = COL_ACCENT;
    btn->pressed  = 0;
    btn->hovered  = 0;
    btn->visible  = 1;
    btn->corner_r = 4;
    btn->on_click = cb;
    btn->ctx      = data;
    return idx;
}

int gui_create_label(GuiContext *ctx, int32_t x, int32_t y,
                     const char *text, uint32_t fg) {
    if (ctx->label_count >= MAX_LABELS) return -1;
    int idx = ctx->label_count++;
    Label *lbl = &ctx->labels[idx];
    lbl->x = x;  lbl->y = y;
    _scpy(lbl->text, text, 128);
    lbl->fg      = fg;
    lbl->bg      = 0;   /* transparent (don't draw bg) */
    lbl->visible = 1;
    return idx;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Desktop Icons
 * ═══════════════════════════════════════════════════════════════════════ */

int gui_add_icon(GuiContext *ctx, int32_t x, int32_t y,
                 const char *label, char glyph, uint32_t color,
                 IconAction action, void *data) {
    if (ctx->icon_count >= MAX_DESKTOP_ICONS) return -1;
    int idx = ctx->icon_count++;
    DesktopIcon *ic = &ctx->icons[idx];
    ic->x      = x;
    ic->y      = y;
    _scpy(ic->label, label, 24);
    ic->glyph  = glyph;
    ic->color  = color;
    ic->action = action;
    ic->ctx    = data;
    ic->selected = 0;
    ic->hovered  = 0;
    return idx;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Menus (Start menu & context menu)
 * ═══════════════════════════════════════════════════════════════════════ */

void gui_add_menu_item(Menu *menu, const char *label, uint32_t icon_color,
                       MenuAction action) {
    if (menu->item_count >= MAX_MENU_ITEMS) return;
    MenuItem *mi = &menu->items[menu->item_count++];
    _scpy(mi->label, label, 32);
    mi->icon_color = icon_color;
    mi->action     = action;
    menu->h = menu->item_count * MENU_ITEM_H + 8;
}

void gui_show_context_menu(GuiContext *ctx, int32_t x, int32_t y) {
    ctx->context_menu.x = x;
    ctx->context_menu.y = y;
    ctx->context_menu.visible = 1;
    ctx->context_menu.hover_idx = -1;
    /* Clamp to screen */
    if (x + ctx->context_menu.w > (int32_t)fb.width)
        ctx->context_menu.x = (int32_t)fb.width - ctx->context_menu.w;
    if (y + ctx->context_menu.h > (int32_t)fb.height - TASKBAR_H)
        ctx->context_menu.y = (int32_t)fb.height - TASKBAR_H - ctx->context_menu.h;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Notification tray
 * ═══════════════════════════════════════════════════════════════════════ */

void gui_set_notif(GuiContext *ctx, const char *status) {
    _scpy(ctx->notif.status, status, 64);
}

/* ═══════════════════════════════════════════════════════════════════════
 * Rendering — Wallpaper
 * ═══════════════════════════════════════════════════════════════════════ */

/* ── Integer sine table (0-255 → -127 to 127) ────────────────────────── */

static const int8_t _sin_tab[64] = {
      0,  12,  25,  37,  49,  60,  71,  81,
     90,  98, 106, 112, 117, 122, 125, 126,
    127, 126, 125, 122, 117, 112, 106,  98,
     90,  81,  71,  60,  49,  37,  25,  12,
      0, -12, -25, -37, -49, -60, -71, -81,
    -90, -98,-106,-112,-117,-122,-125,-126,
   -127,-126,-125,-122,-117,-112,-106, -98,
    -90, -81, -71, -60, -49, -37, -25, -12,
};

static int _isin(int phase) { return _sin_tab[(phase & 63)]; }
static int _icos(int phase) { return _sin_tab[((phase + 16) & 63)]; }

void gui_render_wallpaper(GuiContext *ctx) {
    uint32_t phase = ctx->wallpaper_phase;
    int32_t desk_h = (int32_t)fb.height - TASKBAR_H;

    /* ── Background: vertical gradient (deep purple → dark navy) ─────── */
    /* Slowly shift hue over time for subtle life */
    int shift = _isin((int)(phase / 8)) / 16;
    uint32_t top_color = FB_RGB(0x14 + shift, 0x10, 0x28 + shift);
    uint32_t bot_color = FB_RGB(0x1E, 0x1E + shift/2, 0x2E);
    fb_fill_gradient_v(0, 0, (int32_t)fb.width, desk_h, top_color, bot_color);

    /* ── Twinkling stars — 4-point sparkle pattern ───────────────────── */
    for (int i = 0; i < 18; i++) {
        int32_t sx = (97 * i + 41) % ((int32_t)fb.width - 20) + 10;
        int32_t sy = (163 * i + 73) % (desk_h - 100) + 30;
        int bright = _isin((int)(phase / 2 + i * 10));
        if (bright > 30) {
            uint8_t lum = (uint8_t)(0x40 + bright / 2);
            uint32_t star_col = FB_RGB(lum, lum, lum + 0x30);
            /* Center dot */
            fb_putpixel(sx, sy, star_col);
            /* Cross arms (4 points) */
            int arm = 1 + bright / 64;
            for (int a = 1; a <= arm; a++) {
                uint8_t alum = (uint8_t)(lum * (arm - a + 1) / (arm + 1));
                uint32_t acol = FB_RGB(alum, alum, alum + 0x18);
                fb_putpixel(sx + a, sy, acol);
                fb_putpixel(sx - a, sy, acol);
                fb_putpixel(sx, sy + a, acol);
                fb_putpixel(sx, sy - a, acol);
            }
        }
    }

    /* ── Fibonacci spiral dots — larger filled circles ───────────────── */
    int32_t cx = (int32_t)fb.width / 2;
    int32_t cy = desk_h / 2 + 30;
    uint32_t spiral_colors[5] = { COL_ACCENT, COL_ACCENT2, COL_ACCENT3,
                                   COL_ACCENT4, COL_LAVENDER };
    for (int ring = 0; ring < 5; ring++) {
        int radius = 60 + ring * 40;
        int dot_size = 2 + ring / 2;
        for (int a = 0; a < 64; a += 8) {
            int angle = a + (int)(phase / 3) + ring * 8;
            int32_t px = cx + (_icos(angle) * radius) / 127;
            int32_t py = cy + (_isin(angle) * radius) / 127;
            if (px > dot_size && px < (int32_t)fb.width - dot_size &&
                py > dot_size && py < desk_h - dot_size) {
                /* Alpha-blended dot for glow effect */
                uint32_t base_bg = FB_RGB(0x18, 0x14, 0x2A);
                uint32_t glow = fb_blend(base_bg, spiral_colors[ring], 60);
                fb_fill_circle(px, py, dot_size + 1, glow);
                fb_fill_circle(px, py, dot_size, spiral_colors[ring]);
            }
        }
    }

    /* ── Centered logo text ──────────────────────────────────────────── */
    const char *logo = "LateralusOS";
    int tw = fb_text_width(logo);
    int lx = ((int32_t)fb.width - tw) / 2;
    int ly = desk_h / 2 - 50;

    /* Semi-transparent background panel behind logo */
    int panel_w = tw + 40;
    int panel_h = FONT_H * 2 + 20;
    int panel_x = lx - 20;
    int panel_y = ly - 6;
    fb_fill_rounded_rect(panel_x, panel_y, panel_w, panel_h, 10,
                         fb_blend(FB_RGB(0x10, 0x10, 0x1A), top_color, 140));

    fb_puts_nobg(lx, ly, logo, COL_LAVENDER);

    /* Subtitle */
    const char *sub = "v0.2.0 -- Spiral Out, Keep Going";
    int sw = fb_text_width(sub);
    fb_puts_nobg(((int32_t)fb.width - sw) / 2, ly + FONT_H + 6, sub, COL_SUBTEXT);
}

/* ═══════════════════════════════════════════════════════════════════════
 * Rendering — Desktop Icons
 * ═══════════════════════════════════════════════════════════════════════ */

void gui_render_icons(GuiContext *ctx) {
    for (int i = 0; i < ctx->icon_count; i++) {
        DesktopIcon *ic = &ctx->icons[i];
        int32_t ix = ic->x, iy = ic->y;

        /* Selection/hover highlight */
        if (ic->selected || ic->hovered) {
            uint32_t hl = ic->selected ? fb_blend(COL_ACCENT, COL_BG_DARK, 80)
                                       : fb_blend(COL_ACCENT, COL_BG_DARK, 40);
            fb_fill_rounded_rect(ix - 4, iy - 4, ICON_SIZE + 8,
                                 ICON_SIZE + FONT_H + 12, 6, hl);
        }

        /* Icon square with rounded corners */
        fb_fill_rounded_rect(ix, iy, ICON_SIZE, ICON_SIZE, 10, ic->color);

        /* Single centered glyph */
        int32_t gx = ix + (ICON_SIZE - FONT_W) / 2;
        int32_t gy = iy + (ICON_SIZE - FONT_H) / 2;
        fb_putchar(gx, gy, ic->glyph, COL_WHITE, ic->color);

        /* Label below icon — transparent background */
        int lw = fb_text_width(ic->label);
        int32_t lx = ix + (ICON_SIZE - lw) / 2;
        fb_puts_nobg(lx, iy + ICON_SIZE + 4, ic->label, COL_TEXT);
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Rendering — Menu (popup)
 * ═══════════════════════════════════════════════════════════════════════ */

void gui_render_menu(GuiContext *ctx, Menu *menu) {
    if (!menu->visible || menu->item_count == 0) return;
    (void)ctx;

    int32_t mx = menu->x, my = menu->y;
    int32_t mw = menu->w, mh = menu->h;

    /* Shadow */
    fb_fill_rect(mx + 3, my + 3, mw, mh, fb_blend(COL_BLACK, COL_BG_DARK, 100));

    /* Background */
    fb_fill_rounded_rect(mx, my, mw, mh, 6, COL_SURFACE0);
    fb_draw_rect(mx, my, mw, mh, COL_OVERLAY0);

    /* Items */
    for (int i = 0; i < menu->item_count; i++) {
        MenuItem *mi = &menu->items[i];
        int32_t iy = my + 4 + i * MENU_ITEM_H;

        /* Hover highlight */
        if (menu->hover_idx == i) {
            fb_fill_rounded_rect(mx + 4, iy, mw - 8, MENU_ITEM_H, 4, COL_ACCENT);
        }

        /* Colored dot */
        fb_fill_circle(mx + 16, iy + MENU_ITEM_H / 2, 4, mi->icon_color);

        /* Label */
        uint32_t fg = (menu->hover_idx == i) ? COL_WHITE : COL_TEXT;
        uint32_t bg = (menu->hover_idx == i) ? COL_ACCENT : COL_SURFACE0;
        fb_puts(mx + 28, iy + 6, mi->label, fg, bg);
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Rendering — Taskbar
 * ═══════════════════════════════════════════════════════════════════════ */

void gui_render_taskbar(GuiContext *ctx) {
    int32_t ty = ctx->taskbar.y;

    /* Background with subtle top border */
    fb_fill_rect(0, ty, (int32_t)fb.width, TASKBAR_H, ctx->taskbar.bg);
    fb_fill_rect(0, ty, (int32_t)fb.width, 1, COL_OVERLAY0);

    /* Start button — left side with spiral glyph */
    uint32_t start_bg = ctx->taskbar.start_hovered ? COL_ACCENT : COL_SURFACE1;
    fb_fill_rounded_rect(4, ty + 4, 80, TASKBAR_H - 8, 6, start_bg);
    /* Draw a small spiral indicator */
    fb_fill_circle(18, ty + TASKBAR_H / 2, 3, COL_LAVENDER);
    fb_draw_circle(18, ty + TASKBAR_H / 2, 5, COL_ACCENT);
    fb_puts(28, ty + 10, "Start", COL_TEXT, start_bg);

    /* Window tabs — in middle */
    int tab_x = 92;
    for (int i = 0; i < ctx->window_count; i++) {
        if (!ctx->windows[i].visible) continue;
        uint32_t tab_bg = (ctx->focus_idx == i) ? COL_SURFACE2 : COL_SURFACE0;
        fb_fill_rounded_rect(tab_x, ty + 4, 120, TASKBAR_H - 8, 4, tab_bg);

        /* Truncate title to fit */
        char tab_title[16];
        _scpy(tab_title, ctx->windows[i].title, 14);
        fb_puts(tab_x + 8, ty + 10, tab_title, COL_TEXT, tab_bg);
        tab_x += 128;
    }

    /* Clock — right side */
    int cw = fb_text_width(ctx->taskbar.clock_str);
    fb_puts((int32_t)fb.width - cw - 12, ty + 10,
            ctx->taskbar.clock_str, COL_TEXT, ctx->taskbar.bg);

    /* Notification tray — left of clock */
    if (ctx->notif.status[0]) {
        int nw = fb_text_width(ctx->notif.status);
        fb_puts((int32_t)fb.width - cw - nw - 28, ty + 10,
                ctx->notif.status, ctx->notif.fg, ctx->taskbar.bg);
        /* Separator dot */
        fb_fill_circle((int32_t)fb.width - cw - 20, ty + TASKBAR_H / 2,
                       2, COL_OVERLAY0);
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Rendering — Window
 * ═══════════════════════════════════════════════════════════════════════ */

void gui_render_window(GuiContext *ctx, int idx) {
    Window *win = &ctx->windows[idx];
    if (!win->visible || win->minimized) return;

    /* ── Snapshot geometry ─────────────────────────────────────────────
     * Copy x/y/w/h into locals ONCE.  IRQ12 can mutate win->x/y at
     * any moment during a drag, so if we read win->x multiple times
     * throughout this function some drawing calls would use the old
     * position and others the new one, producing tearing/ghost images.
     * By snapshotting here, the entire window renders at one consistent
     * position per frame. */
    int32_t x = win->x, y = win->y, w = win->w, h = win->h;
    uint32_t body_bg   = win->body_bg;
    uint32_t title_fg  = win->title_fg;
    uint8_t  focused   = win->focused;

    /* ── Animation handling ───────────────────────────────────────────── */
    if (win->anim_state == 1) {
        /* Opening animation — scale from center */
        win->anim_frame++;
        int scale = win->anim_frame * 12;  /* 0..96 over 8 frames */
        if (scale > 100) scale = 100;
        int32_t cx_a = x + w / 2;
        int32_t cy_a = y + h / 2;
        w = w * scale / 100;
        h = h * scale / 100;
        x = cx_a - w / 2;
        y = cy_a - h / 2;
        if (w < 20) w = 20;
        if (h < 20) h = 20;
        if (win->anim_frame >= 8) {
            win->anim_state = 0;
            x = win->x; y = win->y; w = win->w; h = win->h;
        }
    } else if (win->anim_state == 2) {
        /* Closing animation — shrink to center */
        win->anim_frame++;
        int scale = 100 - win->anim_frame * 14;
        if (scale < 5) scale = 5;
        int32_t cx_a = x + w / 2;
        int32_t cy_a = y + h / 2;
        w = w * scale / 100;
        h = h * scale / 100;
        x = cx_a - w / 2;
        y = cy_a - h / 2;
        if (win->anim_frame >= 7) {
            /* Animation done — actually close */
            win->visible = 0;
            win->anim_state = 0;
            if (ctx->focus_idx == idx) ctx->focus_idx = -1;
            return;
        }
    } else if (win->anim_state == 3) {
        /* Minimize animation — slide down to taskbar */
        win->anim_frame++;
        int32_t target_y = (int32_t)fb.height - TASKBAR_H;
        int progress = win->anim_frame * 15;
        if (progress > 100) progress = 100;
        y = win->y + (target_y - win->y) * progress / 100;
        w = win->w * (100 - progress / 2) / 100;
        h = win->h * (100 - progress) / 100;
        if (h < 10) h = 10;
        if (win->anim_frame >= 7) {
            win->minimized = 1;
            win->anim_state = 0;
            if (ctx->focus_idx == idx) ctx->focus_idx = -1;
            return;
        }
    }

    /* Shadow */
    fb_fill_rect(x + WIN_SHADOW, y + WIN_SHADOW, w, h,
                 fb_blend(COL_BLACK, COL_BG_DARK, 80));

    /* Window body */
    fb_fill_rounded_rect(x, y, w, h, WIN_CORNER_R, body_bg);

    /* Title bar gradient — wider range for more visual impact */
    uint32_t tb_top = focused ? FB_RGB(0x3A, 0x3C, 0x52) : COL_SURFACE0;
    uint32_t tb_bot = focused ? COL_SURFACE0 : FB_RGB(0x24, 0x26, 0x38);
    /* Fill the title bar area first with the body colour (rounds corners),
     * then draw the gradient inset by 1px so the rounded-rect body colour
     * peeks through at the corners — no more 0x00000000 black artefacts. */
    fb_fill_gradient_v(x + 1, y + 1, w - 2, TITLE_BAR_H - 1, tb_top, tb_bot);

    /* Title bar separator */
    fb_fill_rect(x, y + TITLE_BAR_H - 1, w, 1, COL_OVERLAY0);

    /* Traffic light buttons (macOS-style circles with hover glyphs) */
    int cy_btn = y + TITLE_BAR_H / 2;
    fb_fill_circle(x + 14, cy_btn, BTN_CIRCLE_R, COL_CLOSE_RED);
    fb_fill_circle(x + 34, cy_btn, BTN_CIRCLE_R, COL_MIN_YEL);
    fb_fill_circle(x + 54, cy_btn, BTN_CIRCLE_R, COL_MAX_GRN);

    /* Show glyphs on traffic light buttons when window is focused */
    if (focused) {
        uint32_t glyph_col = FB_RGB(0x30, 0x20, 0x20);
        /* Close: x (two diagonal lines) */
        fb_draw_line(x + 11, cy_btn - 3, x + 17, cy_btn + 3, glyph_col);
        fb_draw_line(x + 17, cy_btn - 3, x + 11, cy_btn + 3, glyph_col);
        /* Minimize: - (horizontal line) */
        fb_draw_line(x + 31, cy_btn, x + 37, cy_btn, glyph_col);
        /* Maximize: + (cross) */
        fb_draw_line(x + 51, cy_btn - 3, x + 57, cy_btn + 3, glyph_col);
        fb_draw_line(x + 54, cy_btn - 3, x + 54, cy_btn + 3, glyph_col);
        fb_draw_line(x + 51, cy_btn, x + 57, cy_btn, glyph_col);
    }

    /* Update button positions for hit testing */
    win->btn_close_x = x + 14;
    win->btn_close_y = cy_btn;
    win->btn_min_x   = x + 34;
    win->btn_min_y   = cy_btn;
    win->btn_max_x   = x + 54;
    win->btn_max_y   = cy_btn;

    /* Title text — centered, drawn without background so the gradient
     * shows through cleanly (no flat-colored band behind text). */
    int tw = fb_text_width(win->title);
    int tx = x + (w - tw) / 2;
    fb_puts_nobg(tx, y + 6, win->title, title_fg);

    /* Window border */
    fb_draw_rect(x, y, w, h, focused ? COL_ACCENT : COL_OVERLAY0);

    /* Resize handle — bottom-right corner (diagonal lines) */
    if (focused) {
        int32_t rx = x + w - RESIZE_HANDLE;
        int32_t ry = y + h - RESIZE_HANDLE;
        for (int d = 3; d <= 9; d += 3) {
            fb_draw_line(rx + d, ry + RESIZE_HANDLE - 1,
                         rx + RESIZE_HANDLE - 1, ry + d,
                         COL_OVERLAY1);
        }
    }

    /* Content area */
    int32_t cx = x + 8;
    int32_t cy_c = y + TITLE_BAR_H + 8;
    int32_t cw_c = w - 16;
    int32_t ch_c = h - TITLE_BAR_H - 16;

    /* Clip content to window */
    if (win->content[0]) {
        int32_t ty_c = cy_c;
        const char *p = win->content;
        while (*p && ty_c + FONT_H < cy_c + ch_c) {
            /* Find end of line */
            const char *eol = p;
            int line_w = 0;
            while (*eol && *eol != '\n' && line_w + FONT_W < cw_c) {
                eol++;
                line_w += FONT_W;
            }
            /* Draw line */
            int32_t lx = cx;
            while (p < eol) {
                fb_putchar(lx, ty_c, *p, COL_TEXT, body_bg);
                lx += FONT_W;
                p++;
            }
            if (*p == '\n') p++;
            ty_c += FONT_H + 2;
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Rendering — Mouse Cursor
 * ═══════════════════════════════════════════════════════════════════════ */

/* A simple 12x16 arrow cursor bitmap */
static const uint8_t cursor_data[16] = {
    0x80, 0xC0, 0xE0, 0xF0,
    0xF8, 0xFC, 0xFE, 0xFF,
    0xF8, 0xF8, 0xCC, 0x0C,
    0x06, 0x06, 0x03, 0x00,
};

/* Save pixels under cursor from the hardware framebuffer */
static void _cursor_save(GuiContext *ctx, int32_t x, int32_t y) {
    for (int row = 0; row < 16; row++) {
        for (int col = 0; col < 8; col++) {
            ctx->mouse.saved_pixels[row * 16 + col] =
                fb_getpixel_hw(x + col, y + row);
        }
    }
}

/* Restore saved pixels to the hardware framebuffer (erase old cursor) */
static void _cursor_restore(GuiContext *ctx, int32_t old_x, int32_t old_y) {
    for (int row = 0; row < 16; row++) {
        for (int col = 0; col < 8; col++) {
            fb_putpixel_hw(old_x + col, old_y + row,
                           ctx->mouse.saved_pixels[row * 16 + col]);
        }
    }
}

/* Draw cursor shape at (x,y) directly to hardware framebuffer */
static void _cursor_draw_hw(int32_t mx, int32_t my) {
    for (int row = 0; row < 16; row++) {
        uint8_t bits = cursor_data[row];
        for (int col = 0; col < 8; col++) {
            if (bits & (0x80 >> col)) {
                uint32_t c = COL_WHITE;
                if (col == 0 || row == 0 ||
                    !(cursor_data[row] & (0x80 >> (col - 1))) ||
                    (row > 0 && !(cursor_data[row-1] & (0x80 >> col))))
                    c = COL_BLACK;
                fb_putpixel_hw(mx + col, my + row, c);
            }
        }
    }
}

/* Tracking for hardware cursor overlay position */
static int32_t _hw_cursor_x = -1;
static int32_t _hw_cursor_y = -1;
static int     _hw_cursor_valid = 0;

/* Called after fb_swap() to draw cursor on the fresh hw scene.
 * Also called from IRQ12 handler for instant cursor updates between frames. */
void gui_render_cursor_hw(GuiContext *ctx) {
    int32_t mx = ctx->mouse.x, my = ctx->mouse.y;

    /* If there's an old hw cursor, restore the pixels under it */
    if (_hw_cursor_valid) {
        _cursor_restore(ctx, _hw_cursor_x, _hw_cursor_y);
    }

    /* Save pixels at new position, then draw cursor */
    _cursor_save(ctx, mx, my);
    _cursor_draw_hw(mx, my);

    _hw_cursor_x = mx;
    _hw_cursor_y = my;
    _hw_cursor_valid = 1;
}

/* Reset hw cursor tracking (call before fb_swap to avoid stale restore) */
void gui_reset_hw_cursor(void) {
    _hw_cursor_valid = 0;
}

void gui_render_cursor(GuiContext *ctx) {
    int32_t mx = ctx->mouse.x, my = ctx->mouse.y;
    for (int row = 0; row < 16; row++) {
        uint8_t bits = cursor_data[row];
        for (int col = 0; col < 8; col++) {
            if (bits & (0x80 >> col)) {
                /* White fill with black outline */
                uint32_t c = COL_WHITE;
                if (col == 0 || row == 0 ||
                    !(cursor_data[row] & (0x80 >> (col - 1))) ||
                    (row > 0 && !(cursor_data[row-1] & (0x80 >> col))))
                    c = COL_BLACK;
                fb_putpixel(mx + col, my + row, c);
            }
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Rendering — Full Scene
 * ═══════════════════════════════════════════════════════════════════════ */

/* Guard flag: prevents IRQ12 hw-cursor draw from racing with fb_swap.
 * When set, the IRQ12 handler skips gui_render_cursor_hw() so that stale
 * pixels from the old frame are never pasted onto the freshly swapped scene. */
static volatile uint8_t _render_active = 0;

int gui_is_rendering(void) { return _render_active; }

void gui_render_all(GuiContext *ctx) {
    /* Safety check: bail out if framebuffer is not ready */
    if (!fb.available || !ctx) return;

    /* Mark render active for the ENTIRE render pass.
     * This prevents IRQ12's gui_handle_mouse_move() from mutating
     * win->x/y/w/h mid-frame, which would cause half the window to be
     * drawn at the old position and half at the new one (tearing). */
    _render_active = 1;

    gui_render_wallpaper(ctx);
    gui_render_icons(ctx);

    /* Snapshot focus_idx — IRQ12 could change it via gui_handle_mouse_click
     * (there’s a tiny window before _render_active is set). Using a local
     * prevents a window from being rendered twice or skipped. */
    int focus = ctx->focus_idx;

    /* Render windows back to front (focus last = visually on top) */
    for (int i = 0; i < ctx->window_count; i++) {
        if (i != focus)
            gui_render_window(ctx, i);
    }
    if (focus >= 0 && focus < ctx->window_count)
        gui_render_window(ctx, focus);

    /* Standalone buttons */
    for (int i = 0; i < ctx->button_count; i++) {
        Button *btn = &ctx->buttons[i];
        if (!btn->visible) continue;
        uint32_t bg = btn->hovered ? btn->hover_bg : btn->bg;
        fb_fill_rounded_rect(btn->x, btn->y, btn->w, btn->h, btn->corner_r, bg);
        int tw = fb_text_width(btn->label);
        int tx = btn->x + (btn->w - tw) / 2;
        int ty = btn->y + (btn->h - FONT_H) / 2;
        fb_puts(tx, ty, btn->label, btn->fg, bg);
    }

    gui_render_taskbar(ctx);

    /* Menus (drawn above everything except cursor) */
    gui_render_menu(ctx, &ctx->start_menu);
    gui_render_menu(ctx, &ctx->context_menu);

    /* Alt+Tab switcher overlay */
    gui_render_tab_switcher(ctx);

    /* ── Critical section: swap + cursor must be atomic w.r.t. IRQ12 ─── *
     * If IRQ12 fires between gui_reset_hw_cursor() and fb_swap(), it     *
     * would save stale old-frame pixels; then gui_render_cursor_hw()     *
     * after the swap would restore those stale pixels onto the fresh     *
     * frame, creating window "ghost trails" during drags.               */
    __asm__ volatile ("cli");
    gui_reset_hw_cursor();
    fb_swap();
    gui_render_cursor_hw(ctx);
    __asm__ volatile ("sti");

    _render_active = 0;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Event Handling
 * ═══════════════════════════════════════════════════════════════════════ */

static int _point_in_rect(int32_t px, int32_t py,
                           int32_t rx, int32_t ry, int32_t rw, int32_t rh) {
    return px >= rx && px < rx + rw && py >= ry && py < ry + rh;
}

static int _point_in_circle(int32_t px, int32_t py,
                              int32_t cx, int32_t cy, int32_t r) {
    int32_t dx = px - cx, dy = py - cy;
    return dx * dx + dy * dy <= r * r;
}

/* Check if a click at (mx,my) hits window i.  Returns 1 if consumed.
 * Extracted so gui_handle_mouse_click can test the focused (top-most)
 * window first, then fall back to other windows in reverse order. */
static int _try_window_click(GuiContext *ctx, int i, int32_t mx, int32_t my) {
    Window *win = &ctx->windows[i];
    if (!win->visible || win->minimized) return 0;

    /* Close button */
    if (_point_in_circle(mx, my, win->btn_close_x, win->btn_close_y, BTN_CIRCLE_R + 4)) {
        gui_close_window(ctx, i);
        return 1;
    }
    /* Minimize button */
    if (_point_in_circle(mx, my, win->btn_min_x, win->btn_min_y, BTN_CIRCLE_R + 4)) {
        gui_minimize_window(ctx, i);
        return 1;
    }
    /* Maximize button */
    if (_point_in_circle(mx, my, win->btn_max_x, win->btn_max_y, BTN_CIRCLE_R + 4)) {
        win->x = 0; win->y = 0;
        win->w = (int32_t)fb.width;
        win->h = (int32_t)fb.height - TASKBAR_H;
        return 1;
    }
    /* Resize handle — bottom-right corner */
    if (_point_in_rect(mx, my, win->x + win->w - RESIZE_HANDLE,
                       win->y + win->h - RESIZE_HANDLE,
                       RESIZE_HANDLE, RESIZE_HANDLE)) {
        win->resizing = 1;
        for (int j = 0; j < ctx->window_count; j++)
            ctx->windows[j].focused = 0;
        win->focused = 1;
        ctx->focus_idx = i;
        return 1;
    }
    /* Title bar drag */
    if (_point_in_rect(mx, my, win->x + 64, win->y, win->w - 64, TITLE_BAR_H)) {
        win->dragging = 1;
        win->drag_ox  = mx - win->x;
        win->drag_oy  = my - win->y;
        for (int j = 0; j < ctx->window_count; j++)
            ctx->windows[j].focused = 0;
        win->focused = 1;
        ctx->focus_idx = i;
        return 1;
    }
    /* Click inside window body → focus */
    if (_point_in_rect(mx, my, win->x, win->y, win->w, win->h)) {
        for (int j = 0; j < ctx->window_count; j++)
            ctx->windows[j].focused = 0;
        win->focused = 1;
        ctx->focus_idx = i;
        return 1;
    }
    return 0;
}

void gui_handle_mouse_move(GuiContext *ctx, int32_t dx, int32_t dy) {
    if (!ctx) return;
    ctx->mouse.x += dx;
    ctx->mouse.y += dy;
    /* Clamp to screen */
    if (ctx->mouse.x < 0) ctx->mouse.x = 0;
    if (ctx->mouse.y < 0) ctx->mouse.y = 0;
    if ((uint32_t)ctx->mouse.x >= fb.width)  ctx->mouse.x = (int32_t)fb.width - 1;
    if ((uint32_t)ctx->mouse.y >= fb.height) ctx->mouse.y = (int32_t)fb.height - 1;

    int32_t mx = ctx->mouse.x, my = ctx->mouse.y;

    /* Window dragging / resizing — skip if a render is in progress.
     * IRQ12 can fire in the middle of gui_render_window(), so if we
     * update win->x/y/w/h now, part of the window would render at the
     * old position and part at the new one, producing visible tearing
     * and ghost images.  The position will catch up on the next frame
     * from the main-loop call to gui_handle_mouse_move (non-IRQ). */
    if (!_render_active) {
        for (int i = 0; i < ctx->window_count; i++) {
            Window *win = &ctx->windows[i];
            if (win->dragging && ctx->mouse.left_btn) {
                win->x = mx - win->drag_ox;
                win->y = my - win->drag_oy;
                /* Clamp so the title bar stays at least partially on-screen.
                 * This prevents windows from being dragged completely off
                 * the edge where the user can never reach the title bar. */
                if (win->x + win->w < 80) win->x = 80 - win->w;
                if (win->x > (int32_t)fb.width - 80) win->x = (int32_t)fb.width - 80;
                if (win->y < 0) win->y = 0;
                if (win->y > (int32_t)fb.height - TASKBAR_H - 30)
                    win->y = (int32_t)fb.height - TASKBAR_H - 30;
            }
            /* Window resizing */
            if (win->resizing && ctx->mouse.left_btn) {
                int32_t new_w = mx - win->x;
                int32_t new_h = my - win->y;
                if (new_w >= win->min_w) win->w = new_w;
                if (new_h >= win->min_h) win->h = new_h;
                /* Cap to screen bounds */
                if (win->w > (int32_t)fb.width) win->w = (int32_t)fb.width;
                if (win->h > (int32_t)fb.height - TASKBAR_H)
                    win->h = (int32_t)fb.height - TASKBAR_H;
            }
        }
    }

    /* Button hover detection */
    for (int i = 0; i < ctx->button_count; i++) {
        Button *btn = &ctx->buttons[i];
        if (!btn->visible) continue;
        btn->hovered = _point_in_rect(mx, my, btn->x, btn->y, btn->w, btn->h);
    }

    /* Desktop icon hover */
    for (int i = 0; i < ctx->icon_count; i++) {
        ctx->icons[i].hovered = _point_in_rect(mx, my,
            ctx->icons[i].x - 4, ctx->icons[i].y - 4,
            ICON_SIZE + 8, ICON_SIZE + FONT_H + 12);
    }

    /* Start menu hover */
    if (ctx->start_menu.visible) {
        Menu *sm = &ctx->start_menu;
        sm->hover_idx = -1;
        if (_point_in_rect(mx, my, sm->x, sm->y, sm->w, sm->h)) {
            int rel_y = my - sm->y - 4;
            if (rel_y >= 0) {
                int idx = rel_y / MENU_ITEM_H;
                if (idx < sm->item_count) sm->hover_idx = idx;
            }
        }
    }

    /* Context menu hover */
    if (ctx->context_menu.visible) {
        Menu *cm = &ctx->context_menu;
        cm->hover_idx = -1;
        if (_point_in_rect(mx, my, cm->x, cm->y, cm->w, cm->h)) {
            int rel_y = my - cm->y - 4;
            if (rel_y >= 0) {
                int idx = rel_y / MENU_ITEM_H;
                if (idx < cm->item_count) cm->hover_idx = idx;
            }
        }
    }

    /* Start button hover */
    ctx->taskbar.start_hovered = _point_in_rect(mx, my, 4, ctx->taskbar.y + 4, 80, TASKBAR_H - 8);
}

void gui_handle_mouse_click(GuiContext *ctx, uint8_t left, uint8_t right) {
    /* If a render is in progress, skip click processing entirely.
     * We intentionally do NOT update prev_left/prev_right here so that
     * the "just pressed" / "just released" edge is preserved and will
     * be correctly detected on the next call after the render completes.
     * This prevents window creation, closure, focus changes, and drag
     * initiation from racing with the render pipeline (IRQ12 can fire
     * mid-render and call this via desktop_mouse_event). */
    if (_render_active) return;

    uint8_t just_pressed = left && !ctx->mouse.prev_left;
    uint8_t just_released = !left && ctx->mouse.prev_left;
    uint8_t right_pressed = right && !ctx->mouse.prev_right;
    ctx->mouse.left_btn  = left;
    ctx->mouse.right_btn = right;
    ctx->mouse.prev_left = left;
    ctx->mouse.prev_right = right;

    int32_t mx = ctx->mouse.x, my = ctx->mouse.y;

    if (just_released) {
        /* Stop dragging/resizing all windows */
        for (int i = 0; i < ctx->window_count; i++) {
            ctx->windows[i].dragging = 0;
            ctx->windows[i].resizing = 0;
        }
    }

    /* ── Right-click: show context menu ─────────────────────────────── */
    if (right_pressed) {
        ctx->start_menu.visible = 0;
        /* Only on desktop area (not on windows or taskbar) */
        int on_window = 0;
        for (int i = 0; i < ctx->window_count; i++) {
            Window *win = &ctx->windows[i];
            if (win->visible && !win->minimized &&
                _point_in_rect(mx, my, win->x, win->y, win->w, win->h))
                on_window = 1;
        }
        if (!on_window && my < ctx->taskbar.y) {
            gui_show_context_menu(ctx, mx, my);
        } else {
            ctx->context_menu.visible = 0;
        }
        return;
    }

    if (!just_pressed) return;

    /* ── Start menu click ───────────────────────────────────────────── */
    if (ctx->start_menu.visible) {
        Menu *sm = &ctx->start_menu;
        if (_point_in_rect(mx, my, sm->x, sm->y, sm->w, sm->h)) {
            if (sm->hover_idx >= 0 && sm->hover_idx < sm->item_count) {
                MenuItem *mi = &sm->items[sm->hover_idx];
                if (mi->action) mi->action(ctx);
            }
            sm->visible = 0;
            return;
        }
        sm->visible = 0;
    }

    /* ── Context menu click ─────────────────────────────────────────── */
    if (ctx->context_menu.visible) {
        Menu *cm = &ctx->context_menu;
        if (_point_in_rect(mx, my, cm->x, cm->y, cm->w, cm->h)) {
            if (cm->hover_idx >= 0 && cm->hover_idx < cm->item_count) {
                MenuItem *mi = &cm->items[cm->hover_idx];
                if (mi->action) mi->action(ctx);
            }
            cm->visible = 0;
            return;
        }
        cm->visible = 0;
    }

    /* ── Desktop icon double-click (simulate with single click) ─────── */
    for (int i = 0; i < ctx->icon_count; i++) {
        DesktopIcon *ic = &ctx->icons[i];
        if (_point_in_rect(mx, my, ic->x - 4, ic->y - 4,
                           ICON_SIZE + 8, ICON_SIZE + FONT_H + 12)) {
            /* Deselect all, select this one */
            for (int j = 0; j < ctx->icon_count; j++)
                ctx->icons[j].selected = 0;
            ic->selected = 1;
            if (ic->action) ic->action(ic->ctx);
            return;
        }
    }

    /* Check windows front-to-back matching visual z-order:
     * The focused window is rendered last (on top), so test it first.
     * Then check remaining windows in reverse index order (higher index
     * is rendered later among non-focused windows, so visually above). */
    if (ctx->focus_idx >= 0 && ctx->focus_idx < ctx->window_count) {
        if (_try_window_click(ctx, ctx->focus_idx, mx, my)) return;
    }
    for (int i = ctx->window_count - 1; i >= 0; i--) {
        if (i == ctx->focus_idx) continue;
        if (_try_window_click(ctx, i, mx, my)) return;
    }

    /* ── Start button click — toggle start menu ─────────────────────── */
    if (_point_in_rect(mx, my, 4, ctx->taskbar.y + 4, 80, TASKBAR_H - 8)) {
        ctx->start_menu.visible = !ctx->start_menu.visible;
        ctx->start_menu.y = ctx->taskbar.y - ctx->start_menu.h;
        ctx->context_menu.visible = 0;
        return;
    }

    /* Taskbar window tabs — click to restore minimized window */
    int tab_x = 92;
    for (int i = 0; i < ctx->window_count; i++) {
        if (!ctx->windows[i].visible) continue;
        if (_point_in_rect(mx, my, tab_x, ctx->taskbar.y + 4, 120, TASKBAR_H - 8)) {
            ctx->windows[i].minimized = 0;
            for (int j = 0; j < ctx->window_count; j++)
                ctx->windows[j].focused = 0;
            ctx->windows[i].focused = 1;
            ctx->focus_idx = i;
            return;
        }
        tab_x += 128;
    }

    /* Standalone buttons */
    for (int i = 0; i < ctx->button_count; i++) {
        Button *btn = &ctx->buttons[i];
        if (!btn->visible) continue;
        if (_point_in_rect(mx, my, btn->x, btn->y, btn->w, btn->h)) {
            btn->pressed = 1;
            if (btn->on_click) btn->on_click(btn->ctx);
            return;
        }
    }

    /* Click on empty desktop → deselect icons */
    for (int i = 0; i < ctx->icon_count; i++)
        ctx->icons[i].selected = 0;
}

void gui_handle_key(GuiContext *ctx, char key) {
    if (ctx->focus_idx < 0 || ctx->focus_idx >= ctx->window_count) return;
    Window *win = &ctx->windows[ctx->focus_idx];
    if (!win->visible || win->minimized) return;

    int len = _slen(win->content);
    if (key == 8 || key == 127) {
        /* Backspace */
        if (len > 0) win->content[len - 1] = 0;
    } else if (key >= 32 && key < 127 && len < 2046) {
        win->content[len]     = key;
        win->content[len + 1] = 0;
    } else if (key == '\n' && len < 2046) {
        win->content[len]     = '\n';
        win->content[len + 1] = 0;
    }
}

void gui_tick(GuiContext *ctx) {
    ctx->tick++;
    /* Advance wallpaper animation slowly (every 4th tick) for smooth gentle motion */
    if (ctx->tick % 4 == 0)
        ctx->wallpaper_phase++;

    /* Advance window animations */
    for (int i = 0; i < ctx->window_count; i++) {
        Window *win = &ctx->windows[i];
        if (win->anim_state > 0 && win->visible) {
            /* Animation frames are advanced in render_window */
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Alt+Tab Window Switcher
 * ═══════════════════════════════════════════════════════════════════════ */

void gui_show_tab_switcher(GuiContext *ctx) {
    ctx->tab_visible = 1;
    ctx->tab_idx = ctx->focus_idx;
    if (ctx->tab_idx < 0) ctx->tab_idx = 0;
}

void gui_tab_next(GuiContext *ctx) {
    if (!ctx->tab_visible) gui_show_tab_switcher(ctx);
    /* Find next visible window */
    int start = ctx->tab_idx;
    for (int tries = 0; tries < ctx->window_count; tries++) {
        ctx->tab_idx = (ctx->tab_idx + 1) % ctx->window_count;
        if (ctx->windows[ctx->tab_idx].visible) return;
    }
    ctx->tab_idx = start;
}

void gui_tab_prev(GuiContext *ctx) {
    if (!ctx->tab_visible) gui_show_tab_switcher(ctx);
    int start = ctx->tab_idx;
    for (int tries = 0; tries < ctx->window_count; tries++) {
        ctx->tab_idx = ctx->tab_idx - 1;
        if (ctx->tab_idx < 0) ctx->tab_idx = ctx->window_count - 1;
        if (ctx->windows[ctx->tab_idx].visible) return;
    }
    ctx->tab_idx = start;
}

void gui_tab_select(GuiContext *ctx) {
    ctx->tab_visible = 0;
    if (ctx->tab_idx >= 0 && ctx->tab_idx < ctx->window_count) {
        Window *win = &ctx->windows[ctx->tab_idx];
        if (win->visible) {
            win->minimized = 0;
            for (int j = 0; j < ctx->window_count; j++)
                ctx->windows[j].focused = 0;
            win->focused = 1;
            ctx->focus_idx = ctx->tab_idx;
        }
    }
}

void gui_render_tab_switcher(GuiContext *ctx) {
    if (!ctx->tab_visible) return;

    /* Count visible windows */
    int vis_count = 0;
    for (int i = 0; i < ctx->window_count; i++) {
        if (ctx->windows[i].visible) vis_count++;
    }
    if (vis_count == 0) { ctx->tab_visible = 0; return; }

    /* Calculate overlay size */
    int item_w = 180;
    int item_h = 32;
    int pad = 8;
    int panel_w = item_w + pad * 2;
    int panel_h = vis_count * item_h + pad * 2;
    int panel_x = ((int32_t)fb.width - panel_w) / 2;
    int panel_y = ((int32_t)fb.height - panel_h) / 2;

    /* Semi-transparent overlay background */
    fb_fill_rounded_rect(panel_x - 2, panel_y - 2,
                          panel_w + 4, panel_h + 4, 10,
                          fb_blend(COL_BLACK, COL_BG_DARK, 180));
    fb_fill_rounded_rect(panel_x, panel_y, panel_w, panel_h, 8,
                          COL_SURFACE0);
    fb_draw_rect(panel_x, panel_y, panel_w, panel_h, COL_ACCENT);

    /* Title */
    fb_puts(panel_x + pad, panel_y - FONT_H - 4, "Switch Window",
            COL_TEXT, COL_SURFACE0);

    /* List windows */
    int yi = panel_y + pad;
    for (int i = 0; i < ctx->window_count; i++) {
        if (!ctx->windows[i].visible) continue;

        uint32_t bg = (i == ctx->tab_idx) ? COL_ACCENT : COL_SURFACE0;
        uint32_t fg = (i == ctx->tab_idx) ? COL_WHITE : COL_TEXT;

        fb_fill_rounded_rect(panel_x + pad, yi, item_w, item_h - 4, 4, bg);

        /* Window title */
        char title[20];
        _scpy(title, ctx->windows[i].title, 18);
        fb_puts(panel_x + pad + 8, yi + 6, title, fg, bg);

        yi += item_h;
    }
}

void gui_update_clock(GuiContext *ctx, uint32_t uptime_secs) {
    char h[4], m[4], s[4];
    _itoa2((int)(uptime_secs / 3600) % 24, h);
    _itoa2((int)(uptime_secs / 60) % 60, m);
    _itoa2((int)(uptime_secs % 60), s);
    ctx->taskbar.clock_str[0] = h[0];
    ctx->taskbar.clock_str[1] = h[1];
    ctx->taskbar.clock_str[2] = ':';
    ctx->taskbar.clock_str[3] = m[0];
    ctx->taskbar.clock_str[4] = m[1];
    ctx->taskbar.clock_str[5] = ':';
    ctx->taskbar.clock_str[6] = s[0];
    ctx->taskbar.clock_str[7] = s[1];
    ctx->taskbar.clock_str[8] = 0;
}
