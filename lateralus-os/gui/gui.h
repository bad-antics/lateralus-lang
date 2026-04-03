/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — GUI Widget System
 * ═══════════════════════════════════════════════════════════════════════
 * Window, Button, Label, Panel, Taskbar — all rendered via framebuffer.
 * Catppuccin-inspired dark theme.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_GUI_H
#define LATERALUS_GUI_H

#include "framebuffer.h"

/* ── Constants ────────────────────────────────────────────────────────── */

#define MAX_WINDOWS      16
#define MAX_BUTTONS      32
#define MAX_LABELS       64
#define MAX_MENU_ITEMS    8
#define MAX_DESKTOP_ICONS 8
#define TITLE_BAR_H      28
#define TASKBAR_H        36
#define BTN_CIRCLE_R      6
#define WIN_BORDER        2
#define WIN_SHADOW        3
#define WIN_CORNER_R      8
#define ICON_SIZE        48
#define ICON_PAD         16
#define MENU_ITEM_H      28
#define MENU_W          180
#define RESIZE_HANDLE    12

/* ── Widget types ─────────────────────────────────────────────────────── */

typedef enum {
    WIDGET_LABEL,
    WIDGET_BUTTON,
    WIDGET_PANEL,
    WIDGET_TEXTBOX,
} WidgetType;

/* ── Label ────────────────────────────────────────────────────────────── */

typedef struct {
    int32_t   x, y;
    char      text[128];
    uint32_t  fg;
    uint32_t  bg;
    uint8_t   visible;
} Label;

/* ── Button ───────────────────────────────────────────────────────────── */

typedef void (*ButtonCallback)(void *ctx);

typedef struct {
    int32_t        x, y, w, h;
    char           label[64];
    uint32_t       bg;
    uint32_t       fg;
    uint32_t       hover_bg;
    uint8_t        pressed;
    uint8_t        hovered;
    uint8_t        visible;
    uint8_t        corner_r;
    ButtonCallback on_click;
    void          *ctx;
} Button;

/* ── Panel ────────────────────────────────────────────────────────────── */

typedef struct {
    int32_t  x, y, w, h;
    uint32_t bg;
    uint8_t  corner_r;
    uint8_t  visible;
} Panel;

/* ── Window ───────────────────────────────────────────────────────────── */

typedef struct {
    int32_t   x, y, w, h;
    char      title[64];
    uint8_t   visible;
    uint8_t   focused;
    uint8_t   minimized;
    uint8_t   dragging;
    uint8_t   resizing;                  /* 1 if resize in progress    */
    int32_t   drag_ox, drag_oy;          /* offset from window origin */
    int32_t   min_w, min_h;              /* minimum size (200×150)    */

    /* Content area */
    char      content[2048];             /* simple text content */
    int32_t   content_scroll;

    /* Appearance */
    uint32_t  title_bg;
    uint32_t  title_fg;
    uint32_t  body_bg;
    uint32_t  border_color;

    /* Buttons inside title bar (close, min, max) */
    int32_t   btn_close_x, btn_close_y;
    int32_t   btn_min_x, btn_min_y;
    int32_t   btn_max_x, btn_max_y;

    /* Animation state */
    uint8_t   anim_state;                /* 0=none, 1=opening, 2=closing, 3=minimizing */
    uint8_t   anim_frame;                /* current frame (0-8) */

    /* Terminal flag */
    uint8_t   is_terminal;               /* 1 if this window hosts a GUI terminal */
} Window;

/* ── Taskbar ──────────────────────────────────────────────────────────── */

typedef struct {
    int32_t  y;                          /* top of taskbar (screen_h - TASKBAR_H) */
    uint32_t bg;
    char     clock_str[16];
    uint8_t  start_hovered;
} Taskbar;

/* ── Mouse cursor state ───────────────────────────────────────────────── */

typedef struct {
    int32_t  x, y;
    uint8_t  left_btn;
    uint8_t  right_btn;
    uint8_t  prev_left;
    uint8_t  prev_right;
    uint32_t saved_pixels[16 * 16];      /* pixels under cursor */
} Mouse;

/* ── Menu (start menu & context menu) ─────────────────────────────────── */

typedef void (*MenuAction)(void *ctx);

typedef struct {
    char       label[32];
    uint32_t   icon_color;               /* colored dot left of label */
    MenuAction action;
} MenuItem;

typedef struct {
    int32_t   x, y, w, h;
    MenuItem  items[MAX_MENU_ITEMS];
    int       item_count;
    uint8_t   visible;
    int       hover_idx;                 /* -1 = none */
} Menu;

/* ── Desktop icon ─────────────────────────────────────────────────────── */

typedef void (*IconAction)(void *ctx);

typedef struct {
    int32_t    x, y;
    char       label[24];
    uint32_t   color;                    /* icon fill color */
    char       glyph;                    /* single char shown big */
    IconAction action;
    void      *ctx;
    uint8_t    selected;
    uint8_t    hovered;
} DesktopIcon;

/* ── Notification tray ────────────────────────────────────────────────── */

typedef struct {
    char     status[64];                 /* e.g. "MEM: 2%  UP: 0:05" */
    uint32_t fg;
} NotifTray;

/* ── GUI context (entire GUI state) ───────────────────────────────────── */

typedef struct {
    Window   windows[MAX_WINDOWS];
    int      window_count;
    int      focus_idx;                  /* index of focused window, -1 = none */

    Button   buttons[MAX_BUTTONS];
    int      button_count;

    Label    labels[MAX_LABELS];
    int      label_count;

    DesktopIcon icons[MAX_DESKTOP_ICONS];
    int         icon_count;

    Taskbar    taskbar;
    Mouse      mouse;
    Menu       start_menu;
    Menu       context_menu;
    NotifTray  notif;
    uint8_t    running;

    uint32_t tick;                       /* incremented by timer */

    /* Alt+Tab window switcher */
    uint8_t  tab_visible;                /* 1 = switcher overlay shown */
    int      tab_idx;                   /* currently highlighted window */

    /* Wallpaper animation phase */
    uint32_t wallpaper_phase;
} GuiContext;

/* ── Public API ───────────────────────────────────────────────────────── */

void gui_init(GuiContext *ctx);

/* Window management */
int  gui_create_window(GuiContext *ctx, const char *title,
                       int32_t x, int32_t y, int32_t w, int32_t h);
void gui_close_window(GuiContext *ctx, int idx);
void gui_minimize_window(GuiContext *ctx, int idx);
void gui_set_content(GuiContext *ctx, int idx, const char *text);

/* Buttons */
int  gui_create_button(GuiContext *ctx, int32_t x, int32_t y,
                       int32_t w, int32_t h, const char *label,
                       ButtonCallback cb, void *data);

/* Labels */
int  gui_create_label(GuiContext *ctx, int32_t x, int32_t y,
                      const char *text, uint32_t fg);

/* Desktop icons */
int  gui_add_icon(GuiContext *ctx, int32_t x, int32_t y,
                  const char *label, char glyph, uint32_t color,
                  IconAction action, void *data);

/* Menus */
void gui_add_menu_item(Menu *menu, const char *label, uint32_t icon_color,
                       MenuAction action);
void gui_show_context_menu(GuiContext *ctx, int32_t x, int32_t y);

/* Notification tray */
void gui_set_notif(GuiContext *ctx, const char *status);

/* Rendering */
void gui_render_all(GuiContext *ctx);
void gui_render_taskbar(GuiContext *ctx);
void gui_render_window(GuiContext *ctx, int idx);
void gui_render_cursor(GuiContext *ctx);
void gui_render_cursor_hw(GuiContext *ctx);  /* draws to hw framebuffer directly */
void gui_reset_hw_cursor(void);              /* reset tracking before fb_swap */
int  gui_is_rendering(void);                 /* true while render+swap in progress */
void gui_render_wallpaper(GuiContext *ctx);
void gui_render_icons(GuiContext *ctx);
void gui_render_menu(GuiContext *ctx, Menu *menu);

/* Event handling */
void gui_handle_mouse_move(GuiContext *ctx, int32_t dx, int32_t dy);
void gui_handle_mouse_click(GuiContext *ctx, uint8_t left, uint8_t right);
void gui_handle_key(GuiContext *ctx, char key);
void gui_tick(GuiContext *ctx);

/* Alt+Tab window switcher */
void gui_show_tab_switcher(GuiContext *ctx);
void gui_tab_next(GuiContext *ctx);
void gui_tab_prev(GuiContext *ctx);
void gui_tab_select(GuiContext *ctx);
void gui_render_tab_switcher(GuiContext *ctx);

/* Helpers */
void gui_update_clock(GuiContext *ctx, uint32_t uptime_secs);

#endif /* LATERALUS_GUI_H */
