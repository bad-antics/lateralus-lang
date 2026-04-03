/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Minimal Kernel Stub (first boot)
 * ═══════════════════════════════════════════════════════════════════════
 * Copyright (c) 2025 bad-antics. All rights reserved.
 *
 * This is the C stand-in for the full Lateralus kernel. Once the
 * .ltl → C transpilation pipeline is wired for the full OS source,
 * this file gets replaced by the generated kernel/main.c.
 *
 * For now it proves the boot chain works:
 *   GRUB → boot.asm → boot_stub.c → kernel_main()
 * ═══════════════════════════════════════════════════════════════════════ */

#include "../gui/types.h"
#include "../drivers/ata.h"
#include "../drivers/net.h"
#include "../kernel/syscall.h"
#include "../kernel/sched.h"
#include "../kernel/ipc.h"
#include "../kernel/heap.h"
#include "../net/ip.h"
#include "../net/dns.h"
#include "../net/tcp.h"
#include "../net/http.h"
#include "../apps/apps.h"

/* ── Port I/O (non-static so gui/mouse.c can link to them) ────────────── */

void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

/* ── MSR (Model-Specific Register) access ─────────────────────────────── */

static inline uint64_t rdmsr(uint32_t msr) {
    uint32_t lo, hi;
    __asm__ volatile ("rdmsr" : "=a"(lo), "=d"(hi) : "c"(msr));
    return ((uint64_t)hi << 32) | lo;
}

static inline void wrmsr(uint32_t msr, uint64_t val) {
    __asm__ volatile ("wrmsr" : : "a"((uint32_t)val),
                      "d"((uint32_t)(val >> 32)), "c"(msr));
}

/* ── Serial ───────────────────────────────────────────────────────────── */

#define COM1 0x3F8

/* Non-static so net/ip.c and drivers can link to them */
void serial_putc(char c) {
    while (!(inb(COM1 + 5) & 0x20));
    outb(COM1, (uint8_t)c);
}

void serial_puts(const char *s) {
    while (*s) serial_putc(*s++);
}

/* ── VGA ──────────────────────────────────────────────────────────────── */

volatile uint16_t *const VGA_BUF = (volatile uint16_t*)0xB8000;
#define VGA_W 80
#define VGA_H 25

int cur_x = 0, cur_y = 8;   /* start below boot banner */
static uint8_t cur_color = 0x0F;

static void k_scroll(void) {
    for (int y = 0; y < VGA_H - 1; y++)
        for (int x = 0; x < VGA_W; x++)
            VGA_BUF[y * VGA_W + x] = VGA_BUF[(y + 1) * VGA_W + x];
    for (int x = 0; x < VGA_W; x++)
        VGA_BUF[(VGA_H - 1) * VGA_W + x] = (uint16_t)' ' | ((uint16_t)cur_color << 8);
    cur_y = VGA_H - 1;
}

/* Forward declarations for capture hook (defined later, near shell_exec) */
static int  capturing;      /* 1 = capturing VGA output to buffer */
static void capture_putc(char c);

void k_putc(char c) {
    if (capturing) capture_putc(c);
    if (c == '\n') { cur_x = 0; cur_y++; }
    else {
        VGA_BUF[cur_y * VGA_W + cur_x] = (uint16_t)c | ((uint16_t)cur_color << 8);
        cur_x++;
    }
    if (cur_x >= VGA_W) { cur_x = 0; cur_y++; }
    if (cur_y >= VGA_H) k_scroll();
}

void k_print(const char *s) {
    while (*s) k_putc(*s++);
}

void k_set_color(uint8_t fg, uint8_t bg) {
    cur_color = (bg << 4) | fg;
}

static void k_print_hex(uint64_t val) {
    const char *hex = "0123456789ABCDEF";
    char buf[19] = "0x0000000000000000";
    for (int i = 17; i >= 2; i--) {
        buf[i] = hex[val & 0xF];
        val >>= 4;
    }
    k_print(buf);
}

/* ── PIT Timer ────────────────────────────────────────────────────────── */

volatile uint64_t tick_count = 0;

/* ── IDT (enhanced — proper exception handlers + hardware IRQs) ───────── */

struct idt_entry {
    uint16_t offset_low;
    uint16_t selector;
    uint8_t  ist;
    uint8_t  type_attr;
    uint16_t offset_mid;
    uint32_t offset_high;
    uint32_t reserved;
} __attribute__((packed));

struct idt_ptr {
    uint16_t limit;
    uint64_t base;
} __attribute__((packed));

static struct idt_entry idt[256];
static struct idt_ptr   idtr;

/* ── Exception names for readable diagnostics ─────────────────────────── */

static const char *exception_names[] = {
    "Divide-by-Zero (#DE)",      /* 0  */
    "Debug (#DB)",                /* 1  */
    "NMI",                        /* 2  */
    "Breakpoint (#BP)",           /* 3  */
    "Overflow (#OF)",             /* 4  */
    "Bound Range (#BR)",          /* 5  */
    "Invalid Opcode (#UD)",       /* 6  */
    "Device Not Available (#NM)", /* 7  */
    "Double Fault (#DF)",         /* 8  */
    "Coprocessor Overrun",        /* 9  */
    "Invalid TSS (#TS)",          /* 10 */
    "Segment Not Present (#NP)",  /* 11 */
    "Stack-Segment Fault (#SS)",  /* 12 */
    "General Protection (#GP)",   /* 13 */
    "Page Fault (#PF)",           /* 14 */
    "Reserved",                   /* 15 */
    "x87 FP Error (#MF)",        /* 16 */
    "Alignment Check (#AC)",     /* 17 */
    "Machine Check (#MC)",       /* 18 */
    "SIMD FP Error (#XM)",       /* 19 */
    "Virtualization (#VE)",       /* 20 */
};

static void serial_put_hex(uint64_t val) {
    serial_puts("0x");
    const char *hex = "0123456789ABCDEF";
    char buf[17];
    for (int i = 15; i >= 0; i--) {
        buf[i] = hex[val & 0xF];
        val >>= 4;
    }
    buf[16] = '\0';
    serial_puts(buf);
}

static void serial_put_dec(uint64_t val) {
    if (val == 0) { serial_puts("0"); return; }
    char buf[24]; int pos = 0;
    char rev[24]; int rp = 0;
    while (val > 0 && rp < 22) { rev[rp++] = '0' + (val % 10); val /= 10; }
    while (rp > 0) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
    serial_puts(buf);
}

/* ── Exception handler: logs details and halts (no recovery for CPU faults) */

__attribute__((interrupt))
static void exc_divide_error(void *frame) {
    (void)frame;
    serial_puts("\n[EXCEPTION] #0 Divide-by-Zero (#DE)\n");
    serial_puts("[EXCEPTION] System halted.\n");
    __asm__ volatile ("cli; hlt");
}

__attribute__((interrupt))
static void exc_invalid_opcode(void *frame) {
    (void)frame;
    serial_puts("\n[EXCEPTION] #6 Invalid Opcode (#UD)\n");
    serial_puts("[EXCEPTION] System halted.\n");
    __asm__ volatile ("cli; hlt");
}

__attribute__((interrupt))
static void exc_double_fault(void *frame, uint64_t error_code) {
    (void)frame;
    serial_puts("\n[EXCEPTION] #8 Double Fault (#DF) error_code=");
    serial_put_hex(error_code);
    serial_puts("\n[EXCEPTION] FATAL — system halted.\n");
    __asm__ volatile ("cli; hlt");
}

__attribute__((interrupt))
static void exc_gpf(void *frame, uint64_t error_code) {
    (void)frame;
    serial_puts("\n[EXCEPTION] #13 General Protection Fault (#GP) error_code=");
    serial_put_hex(error_code);
    serial_puts("\n[EXCEPTION] System halted.\n");
    __asm__ volatile ("cli; hlt");
}

__attribute__((interrupt))
static void exc_page_fault(void *frame, uint64_t error_code) {
    (void)frame;
    /* Read faulting address from CR2 */
    uint64_t cr2;
    __asm__ volatile ("mov %%cr2, %0" : "=r"(cr2));
    serial_puts("\n[EXCEPTION] #14 Page Fault (#PF)\n");
    serial_puts("[EXCEPTION]   error_code=");
    serial_put_hex(error_code);
    serial_puts("\n[EXCEPTION]   faulting_addr=");
    serial_put_hex(cr2);
    serial_puts("\n[EXCEPTION]   flags: ");
    if (error_code & 1) serial_puts("PRESENT ");
    if (error_code & 2) serial_puts("WRITE ");
    if (error_code & 4) serial_puts("USER ");
    if (error_code & 8) serial_puts("RSVD ");
    if (error_code & 16) serial_puts("IFETCH ");
    serial_puts("\n[EXCEPTION] System halted.\n");
    __asm__ volatile ("cli; hlt");
}

/* Generic ISR that does nothing (just IRET) */
__attribute__((interrupt))
static void isr_stub(void *frame) {
    (void)frame;
}

/* Timer IRQ handler */
__attribute__((interrupt))
static void irq0_handler(void *frame) {
    (void)frame;
    tick_count++;
    sched_tick();
    outb(0x20, 0x20);  /* EOI */
}

/* Keyboard IRQ handler */
volatile uint8_t last_scancode = 0;
__attribute__((interrupt))
static void irq1_handler(void *frame) {
    (void)frame;
    last_scancode = inb(0x60);
    outb(0x20, 0x20);  /* EOI */
}

/* ── GUI includes (from gui/) ─────────────────────────────────────────── */

#include "../gui/framebuffer.h"
#include "../gui/gui.h"
#include "../gui/desktop.h"
#include "../gui/mouse.h"
#include "../gui/terminal.h"
#include "../fs/ramfs.h"
#include "../fs/procfs.h"
#include "../fs/devfs.h"
#include "../drivers/speaker.h"
#include "../kernel/tasks.h"

/* ── BootInfo from boot_stub.c ─────────────────────────────────────────── */

#include "../gui/bootinfo.h"

extern BootInfo boot_info;

/* ── Desktop (global for IRQ handlers) ─────────────────────────────────── */

static Desktop desktop;
static volatile uint8_t gui_active = 0;

/* ── Mouse IRQ handler (IRQ12 = INT 44) ───────────────────────────────── */

__attribute__((interrupt))
static void irq12_handler(void *frame) {
    (void)frame;
    static uint32_t mouse_irq_count = 0;
    uint8_t byte = inb(0x60);
    mouse_handle_byte(byte);

    MouseState *ms = mouse_get_state();
    if (ms->ready && gui_active) {
        desktop_mouse_event(&desktop, ms->dx, ms->dy, ms->left, ms->right);
        ms->ready = 0;

        /* Immediate cursor redraw on hardware framebuffer for zero-lag cursor.
         * Skip if a frame render is in progress — the render's own
         * cli/sti-guarded swap+cursor sequence will handle it.  Drawing
         * here during a swap would save stale old-frame pixels that get
         * pasted onto the new frame, creating window "ghost trails". */
        if (!gui_is_rendering()) {
            gui_render_cursor_hw(&desktop.gui);
        }

        /* Log first few mouse events to serial for debugging */
        if (mouse_irq_count < 3) {
            serial_puts("[mouse] event received\n");
        }
        mouse_irq_count++;
    }

    outb(0xA0, 0x20);  /* EOI slave PIC */
    outb(0x20, 0x20);  /* EOI master PIC */
}

static void idt_set_gate(int n, void (*handler)(void*), uint8_t type_attr) {
    uint64_t addr = (uint64_t)handler;
    idt[n].offset_low  = addr & 0xFFFF;
    idt[n].selector    = 0x08;  /* kernel code segment */
    idt[n].ist         = 0;
    idt[n].type_attr   = type_attr;
    idt[n].offset_mid  = (addr >> 16) & 0xFFFF;
    idt[n].offset_high = (addr >> 32) & 0xFFFFFFFF;
    idt[n].reserved    = 0;
}

static void init_idt(void) {
    /* Fill all 256 entries with stub */
    for (int i = 0; i < 256; i++)
        idt_set_gate(i, isr_stub, 0x8E);

    /* Install proper CPU exception handlers */
    idt_set_gate(0,  (void(*)(void*))exc_divide_error,   0x8E);  /* #DE */
    idt_set_gate(6,  (void(*)(void*))exc_invalid_opcode, 0x8E);  /* #UD */
    idt_set_gate(8,  (void(*)(void*))exc_double_fault,   0x8E);  /* #DF */
    idt_set_gate(13, (void(*)(void*))exc_gpf,            0x8E);  /* #GP */
    idt_set_gate(14, (void(*)(void*))exc_page_fault,     0x8E);  /* #PF */

    /* PIC remapping: IRQ 0-7 → INT 32-39, IRQ 8-15 → INT 40-47 */
    outb(0x20, 0x11); outb(0xA0, 0x11);
    outb(0x21, 0x20); outb(0xA1, 0x28);
    outb(0x21, 0x04); outb(0xA1, 0x02);
    outb(0x21, 0x01); outb(0xA1, 0x01);
    outb(0x21, 0xF8); /* unmask IRQ0 (timer) + IRQ1 (kbd) + IRQ2 (cascade) */
    outb(0xA1, 0xEF); /* unmask IRQ12 (mouse) on slave PIC */

    /* Set timer + keyboard + mouse handlers */
    idt_set_gate(32, irq0_handler, 0x8E);
    idt_set_gate(33, irq1_handler, 0x8E);
    idt_set_gate(44, irq12_handler, 0x8E);  /* IRQ12 = INT 44 */

    idtr.limit = sizeof(idt) - 1;
    idtr.base  = (uint64_t)&idt;
    __asm__ volatile ("lidt %0" : : "m"(idtr));
    __asm__ volatile ("sti");

    serial_puts("[IDT] Initialized with exception handlers + IRQ 0/1/12\n");
}

/* ── PIT setup (1000 Hz) ──────────────────────────────────────────────── */

static void init_pit(void) {
    uint16_t divisor = 1193;  /* ~1000 Hz */
    outb(0x43, 0x36);
    outb(0x40, divisor & 0xFF);
    outb(0x40, (divisor >> 8) & 0xFF);
}

/* ── Keyboard (simple scancode → ASCII) ───────────────────────────────── */

const char scancode_ascii[128] = {
    0,27,'1','2','3','4','5','6','7','8','9','0','-','=','\b',
    '\t','q','w','e','r','t','y','u','i','o','p','[',']','\n',
    0,'a','s','d','f','g','h','j','k','l',';','\'','`',
    0,'\\','z','x','c','v','b','n','m',',','.','/',0,
    '*',0,' ',0
};

/* ── Simple memory stats ─────────────────────────────────────────────── */

uint64_t total_system_memory = 1024ULL * 1024 * 1024;  /* default 1 GB */

static uint64_t detect_memory(void) {
    return total_system_memory;
}

/* ── Utility: int-to-string ────────────────────────────────────────────── */

static void uint_to_str(uint64_t val, char *buf, int buflen) {
    int pos = 0;
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char rev[24]; int rp = 0;
    while (val > 0 && rp < 23) { rev[rp++] = '0' + (val % 10); val /= 10; }
    while (rp > 0 && pos < buflen - 1) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
}

/* ── Utility: strcmp ──────────────────────────────────────────────────── */

int k_strcmp(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return (int)(unsigned char)*a - (int)(unsigned char)*b;
}

int k_strncmp(const char *a, const char *b, int n) {
    for (int i = 0; i < n; i++) {
        if (a[i] != b[i]) return (int)(unsigned char)a[i] - (int)(unsigned char)b[i];
        if (a[i] == 0) return 0;
    }
    return 0;
}

int k_strlen(const char *s) {
    int n = 0; while (s[n]) n++; return n;
}

/* Check if haystack contains needle */
static int k_strstr(const char *haystack, const char *needle) {
    if (!needle[0]) return 1;
    for (int i = 0; haystack[i]; i++) {
        int j = 0;
        while (haystack[i + j] && needle[j] && haystack[i + j] == needle[j]) j++;
        if (!needle[j]) return 1;
    }
    return 0;
}

/* ═══════════════════════════════════════════════════════════════════════
 * ltlsh — The Lateralus Interactive Shell
 * ═══════════════════════════════════════════════════════════════════════ */

#define CMD_BUF_SIZE 256
#define MAX_HISTORY  16
#define DMESG_LINES  64
#define DMESG_LINELEN 120

static char cmd_buf[CMD_BUF_SIZE];
static int  cmd_len = 0;
static int  cmd_cursor = 0;   /* cursor position within cmd_buf (for left/right editing) */

/* Command history */
static char history[MAX_HISTORY][CMD_BUF_SIZE];
static int  hist_count = 0;
static int  hist_pos   = 0;

/* Current working directory */
static char cwd[128] = "/";

/* dmesg ring buffer — captures boot log messages */
static char dmesg_buf[DMESG_LINES][DMESG_LINELEN];
static int  dmesg_count = 0;

static void dmesg_add(const char *msg) {
    int idx = dmesg_count % DMESG_LINES;
    int i = 0;
    while (msg[i] && i < DMESG_LINELEN - 1) { dmesg_buf[idx][i] = msg[i]; i++; }
    dmesg_buf[idx][i] = '\0';
    dmesg_count++;
}

/* Environment variables (simple key=value store) */
#define MAX_ENV 16
#define ENV_KEYLEN 32
#define ENV_VALLEN 128

static char env_keys[MAX_ENV][ENV_KEYLEN];
static char env_vals[MAX_ENV][ENV_VALLEN];
static int  env_count = 0;

static void env_set_raw(int idx, const char *key, const char *val) {
    int j;
    for (j = 0; key[j]; j++) env_keys[idx][j] = key[j];
    env_keys[idx][j] = '\0';
    for (j = 0; val[j]; j++) env_vals[idx][j] = val[j];
    env_vals[idx][j] = '\0';
}

static void env_init(void) {
    /* Set default environment */
    env_set_raw(0, "HOME",     "/home");
    env_set_raw(1, "USER",     "root");
    env_set_raw(2, "SHELL",    "/bin/ltlsh");
    env_set_raw(3, "PATH",     "/bin:/usr/bin");
    env_set_raw(4, "TERM",     "ltlterm");
    env_set_raw(5, "HOSTNAME", "lateralus");
    env_count = 6;
}

/* Look up an env variable by name. Returns pointer to value or NULL. */
static const char *env_get(const char *key) {
    for (int i = 0; i < env_count; i++) {
        if (k_strcmp(env_keys[i], key) == 0)
            return env_vals[i];
    }
    /* Dynamic pseudo-variables */
    if (k_strcmp(key, "PWD") == 0) return cwd;
    return (const char*)0;
}

/* Remove an env variable. Returns 0 on success, -1 if not found. */
static int env_unset(const char *key) {
    for (int i = 0; i < env_count; i++) {
        if (k_strcmp(env_keys[i], key) == 0) {
            /* Shift remaining entries down */
            for (int j = i; j < env_count - 1; j++) {
                int k;
                for (k = 0; env_keys[j+1][k]; k++) env_keys[j][k] = env_keys[j+1][k];
                env_keys[j][k] = '\0';
                for (k = 0; env_vals[j+1][k]; k++) env_vals[j][k] = env_vals[j+1][k];
                env_vals[j][k] = '\0';
            }
            env_count--;
            return 0;
        }
    }
    return -1;
}

/* Expand $VAR and ${VAR} in a command string. Result written to out (max outlen). */
static void env_expand(const char *src, char *out, int outlen) {
    int si = 0, di = 0;
    while (src[si] && di < outlen - 1) {
        if (src[si] == '$') {
            si++;
            int braced = 0;
            if (src[si] == '{') { braced = 1; si++; }

            /* Special variables */
            if (src[si] == '?' && !braced) {
                /* $? — last exit code (always 0 for now) */
                if (di < outlen - 1) out[di++] = '0';
                si++;
                continue;
            }

            /* Extract variable name */
            char varname[ENV_KEYLEN];
            int vi = 0;
            while (vi < ENV_KEYLEN - 1) {
                char c = src[si];
                if (braced) {
                    if (c == '}' || c == '\0') break;
                } else {
                    if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                          (c >= '0' && c <= '9') || c == '_')) break;
                }
                varname[vi++] = c;
                si++;
            }
            varname[vi] = '\0';
            if (braced && src[si] == '}') si++;

            /* Look up and substitute */
            const char *val = env_get(varname);
            if (val) {
                while (*val && di < outlen - 1) out[di++] = *val++;
            }
        } else {
            out[di++] = src[si++];
        }
    }
    out[di] = '\0';
}

/* ── Alias table ─────────────────────────────────────────────────────── */
#define MAX_ALIASES 16
#define ALIAS_NAMELEN 32
#define ALIAS_CMDLEN 128

static char alias_names[MAX_ALIASES][ALIAS_NAMELEN];
static char alias_cmds[MAX_ALIASES][ALIAS_CMDLEN];
static int  alias_count = 0;

static void alias_init(void) {
    /* Built-in default aliases */
    { int j; for (j = 0; "ll"[j]; j++) alias_names[0][j] = "ll"[j]; alias_names[0][j] = '\0'; }
    { int j; for (j = 0; "ls"[j]; j++) alias_cmds[0][j] = "ls"[j]; alias_cmds[0][j] = '\0'; }
    { int j; for (j = 0; "h"[j]; j++) alias_names[1][j] = "h"[j]; alias_names[1][j] = '\0'; }
    { int j; for (j = 0; "history"[j]; j++) alias_cmds[1][j] = "history"[j]; alias_cmds[1][j] = '\0'; }
    { int j; for (j = 0; "cls"[j]; j++) alias_names[2][j] = "cls"[j]; alias_names[2][j] = '\0'; }
    { int j; for (j = 0; "clear"[j]; j++) alias_cmds[2][j] = "clear"[j]; alias_cmds[2][j] = '\0'; }
    alias_count = 3;
}

/* Expand alias at the start of a command. Returns pointer to expanded buf or original. */
static char alias_expand_buf[CMD_BUF_SIZE];
static const char *alias_expand(const char *line) {
    /* Extract first word */
    int wlen = 0;
    while (line[wlen] && line[wlen] != ' ') wlen++;

    for (int i = 0; i < alias_count; i++) {
        if (k_strlen(alias_names[i]) == wlen) {
            int match = 1;
            for (int j = 0; j < wlen; j++) {
                if (alias_names[i][j] != line[j]) { match = 0; break; }
            }
            if (match) {
                /* Build: alias_cmd + rest_of_line */
                int di = 0;
                const char *cmd = alias_cmds[i];
                while (*cmd && di < CMD_BUF_SIZE - 1) alias_expand_buf[di++] = *cmd++;
                const char *rest = line + wlen;
                while (*rest && di < CMD_BUF_SIZE - 1) alias_expand_buf[di++] = *rest++;
                alias_expand_buf[di] = '\0';
                return alias_expand_buf;
            }
        }
    }
    return line;
}

static void hist_push(const char *cmd) {
    if (cmd[0] == '\0') return;
    int dst = hist_count % MAX_HISTORY;
    for (int i = 0; i < CMD_BUF_SIZE && cmd[i]; i++) history[dst][i] = cmd[i];
    history[dst][k_strlen(cmd)] = '\0';
    hist_count++;
}

/* ── Shell Prompt ─────────────────────────────────────────────────────── */

static void shell_prompt(void) {
    k_set_color(0x0B, 0x00);  /* cyan */
    k_print("root@lateralus");
    k_set_color(0x0F, 0x00);
    k_print(":");
    k_set_color(0x09, 0x00);  /* bright blue */
    k_print(cwd);
    k_set_color(0x0F, 0x00);
    k_print("$ ");
    serial_puts("root@lateralus:");
    serial_puts(cwd);
    serial_puts("$ ");
}

/* ── Shell Commands ───────────────────────────────────────────────────── */

static void cmd_help(void) {
    k_set_color(0x0E, 0x00);  /* yellow */
    k_print("LateralusOS Shell Commands:\n");
    k_set_color(0x0F, 0x00);
    k_print("  help        Show this help message\n");
    k_print("  clear       Clear the screen\n");
    k_print("  uname       System information\n");
    k_print("  uptime      Time since boot\n");
    k_print("  free        Memory usage\n");
    k_print("  echo <msg>  Print a message\n");
    k_print("  version     Kernel version\n");
    k_print("  cpuid       CPU feature flags\n");
    k_print("  ticks       Raw PIT tick count\n");
    k_print("  alloc <n>   Allocate n bytes (demo)\n");
    k_print("  heap        Heap allocator stats\n");
    k_print("  history     Command history\n");
    k_print("  ls [path]   List directory (VFS)\n");
    k_print("  cat <file>  Read file (VFS)\n");
    k_print("  touch <f>   Create file (VFS)\n");
    k_print("  mkdir <d>   Create directory (VFS)\n");
    k_print("  reboot      Reboot the system\n");
    k_print("  halt        Halt the CPU\n");
    k_print("  gui         Launch graphical desktop\n");
    k_set_color(0x0E, 0x00);
    k_print("System:\n");
    k_set_color(0x0F, 0x00);
    k_print("  whoami      Current user\n");
    k_print("  hostname    System hostname\n");
    k_print("  date        Current date/time (RTC)\n");
    k_print("  ps          Process list\n");
    k_print("  kill <t> [sig] Send signal (default: TERM)\n");
    k_print("  spawn <t>   Spawn background task\n");
    k_print("  sysinfo     Full system info\n");
    k_print("  cal         Calendar (current month)\n");
    k_print("  env         Environment variables\n");
    k_print("  export K=V  Set environment variable\n");
    k_print("  unset <KEY> Remove environment variable\n");
    k_print("  alias [n=c] Show/set command aliases\n");
    k_print("  unalias <n> Remove alias\n");
    k_print("  sleep <n>   Sleep for n seconds\n");
    k_print("  dmesg       Kernel boot messages\n");
    k_set_color(0x0E, 0x00);
    k_print("Files:\n");
    k_set_color(0x0F, 0x00);
    k_print("  cd <dir>    Change directory\n");
    k_print("  pwd         Print working directory\n");
    k_print("  write <f> <text>  Write text to file\n");
    k_print("  head <f> [n]  Show first n lines\n");
    k_print("  tail <f> [n]  Show last n lines\n");
    k_print("  wc <file>   Line/word/byte count\n");
    k_print("  stat <path> File/directory info\n");
    k_print("  xxd <f> [n] Hex dump (n bytes)\n");
    k_print("  rm <path>   Remove file or directory\n");
    k_set_color(0x0E, 0x00);
    k_print("Network:\n");
    k_set_color(0x0F, 0x00);
    k_print("  ifconfig    Network interface + IP\n");
    k_print("  ping [ip]   ICMP echo request\n");
    k_print("  netstat     Network statistics\n");
    k_print("  arp         ARP cache table\n");
    k_print("  dhcp        Acquire IP via DHCP\n");
    k_print("  nslookup    DNS hostname lookup\n");
    k_print("  dns         Show DNS cache\n");
    k_print("  dns flush   Clear DNS cache\n");
    k_print("  tcp         TCP connection table\n");
    k_print("  tcp dump    Dump TCP state to serial\n");
    k_print("  wget <url>  HTTP GET request\n");
    k_set_color(0x0E, 0x00);
    k_print("Pipes & Redirects:\n");
    k_set_color(0x0F, 0x00);
    k_print("  cmd | grep  Filter output\n");
    k_print("  cmd > file  Redirect to file\n");
    k_print("  cmd >> file Append to file\n");
    k_set_color(0x0E, 0x00);
    k_print("Development:\n");
    k_set_color(0x0F, 0x00);
    k_print("  ltlc <file> Lateralus compiler/analyzer\n");
    k_print("  ltlc repl   Interactive Lateralus REPL\n");
    k_print("  chat        IRC-style chat client\n");
    k_print("  edit <file> Text editor (syntax highlighting)\n");
    k_print("  pkg <cmd>   Package manager (list/install/build)\n");
    k_set_color(0x0E, 0x00);
    k_print("Utilities:\n");
    k_set_color(0x0F, 0x00);
    k_print("  top         Task monitor\n");
    k_print("  df          Filesystem usage (ramfs)\n");
    k_print("  id          User identity\n");
    k_print("  seq [s] <e> Print number sequence\n");
    k_print("  tr <f> <t>  Translate characters\n");
    k_print("  rev <str>   Reverse a string\n");
    k_print("  factor <n>  Prime factorization\n");
    serial_puts("[shell] help displayed\n");
}

static void cmd_clear(void) {
    for (int i = 0; i < VGA_W * VGA_H; i++)
        VGA_BUF[i] = (uint16_t)' ' | ((uint16_t)0x0F << 8);
    cur_x = 0; cur_y = 0;
}

static void cmd_uname(void) {
    k_set_color(0x0A, 0x00);
    k_print("LateralusOS");
    k_set_color(0x0F, 0x00);
    k_print(" v0.3.0 (x86_64) — built with Lateralus lang\n");
    k_print("Kernel:  lateralus-kernel 0.2.0\n");
    k_print("Arch:    x86_64 (long mode, identity-mapped)\n");
    k_print("Shell:   ltlsh 0.3.0\n");
    serial_puts("[shell] uname\n");
}

static void cmd_uptime(void) {
    uint64_t ticks = tick_count;
    uint64_t secs  = ticks / 1000;
    uint64_t mins  = secs / 60;
    uint64_t hours = mins / 60;
    uint64_t days  = hours / 24;
    char buf[24];

    k_print("Up ");
    if (days > 0) {
        uint_to_str(days, buf, sizeof(buf));
        k_print(buf); k_print("d ");
    }
    if (hours > 0) {
        uint_to_str(hours % 24, buf, sizeof(buf));
        k_print(buf); k_print("h ");
    }
    uint_to_str(mins % 60, buf, sizeof(buf));
    k_print(buf); k_print("m ");
    uint_to_str(secs % 60, buf, sizeof(buf));
    k_print(buf); k_print("s");

    /* Task count */
    int ready, blocked, sleeping, total;
    sched_stats(&ready, &blocked, &sleeping, &total);
    k_print("  ");
    uint_to_str((uint64_t)total, buf, sizeof(buf));
    k_print(buf); k_print(" tasks");

    /* Load average */
    int l1, l5, l15;
    sched_load_avg(&l1, &l5, &l15);
    k_print("  load: ");
    /* Print fixed-point ×100 as X.XX */
    uint_to_str((uint64_t)(l1 / 100), buf, sizeof(buf));
    k_print(buf); k_putc('.');
    int frac1 = l1 % 100; if (frac1 < 0) frac1 = -frac1;
    if (frac1 < 10) k_putc('0');
    uint_to_str((uint64_t)frac1, buf, sizeof(buf));
    k_print(buf); k_print(", ");

    uint_to_str((uint64_t)(l5 / 100), buf, sizeof(buf));
    k_print(buf); k_putc('.');
    int frac5 = l5 % 100; if (frac5 < 0) frac5 = -frac5;
    if (frac5 < 10) k_putc('0');
    uint_to_str((uint64_t)frac5, buf, sizeof(buf));
    k_print(buf); k_print(", ");

    uint_to_str((uint64_t)(l15 / 100), buf, sizeof(buf));
    k_print(buf); k_putc('.');
    int frac15 = l15 % 100; if (frac15 < 0) frac15 = -frac15;
    if (frac15 < 10) k_putc('0');
    uint_to_str((uint64_t)frac15, buf, sizeof(buf));
    k_print(buf);

    k_putc('\n');
    serial_puts("[shell] uptime\n");
}

static void cmd_free(void) {
    char buf[24];
    HeapStats hs = heap_get_stats();
    uint64_t total_mb = total_system_memory / (1024 * 1024);
    extern char _end;
    uint64_t kernel_kb = ((uint64_t)&_end) / 1024;
    uint64_t heap_used_kb = hs.allocated / 1024;
    uint64_t heap_total_kb = (hs.end - hs.start) / 1024;

    k_set_color(0x0E, 0x00);
    k_print("            Total      Used       Free\n");
    k_set_color(0x0F, 0x00);

    k_print("System:     ");
    uint_to_str(total_mb, buf, sizeof(buf));
    k_print(buf); k_print(" MB\n");

    k_print("Kernel:     ");
    uint_to_str(kernel_kb, buf, sizeof(buf));
    k_print(buf); k_print(" KB\n");

    k_print("Heap:       ");
    uint_to_str(heap_total_kb, buf, sizeof(buf));
    k_print(buf); k_print(" KB    ");
    uint_to_str(heap_used_kb, buf, sizeof(buf));
    k_print(buf); k_print(" KB    ");
    uint_to_str((heap_total_kb > heap_used_kb) ? heap_total_kb - heap_used_kb : 0, buf, sizeof(buf));
    k_print(buf); k_print(" KB\n");

    k_print("Allocs:     ");
    uint_to_str(hs.alloc_count, buf, sizeof(buf));
    k_print(buf); k_print("         ");
    uint_to_str(hs.free_count, buf, sizeof(buf));
    k_print(buf); k_print(" freed\n");

    serial_puts("[shell] free\n");
}

static void cmd_echo(const char *args) {
    /* Skip leading spaces after "echo" */
    while (*args == ' ') args++;
    k_print(args);
    k_putc('\n');
    serial_puts(args);
    serial_putc('\n');
}

static void cmd_version(void) {
    k_set_color(0x0E, 0x00);
    k_print("╔══════════════════════════════════════════════╗\n");
    k_print("║  LateralusOS v0.3.0                         ║\n");
    k_print("║  Lateralus Language v2.0.0                   ║\n");
    k_print("║  Copyright (c) 2025 bad-antics               ║\n");
    k_print("╚══════════════════════════════════════════════╝\n");
    k_set_color(0x0F, 0x00);
}

static void cmd_cpuid_info(void) {
    uint32_t eax, ebx, ecx, edx;
    char vendor[13];

    /* Get vendor string */
    __asm__ volatile ("cpuid" : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx) : "a"(0));
    *(uint32_t*)&vendor[0] = ebx;
    *(uint32_t*)&vendor[4] = edx;
    *(uint32_t*)&vendor[8] = ecx;
    vendor[12] = '\0';

    k_print("CPU Vendor: ");
    k_set_color(0x0A, 0x00);
    k_print(vendor);
    k_set_color(0x0F, 0x00);
    k_putc('\n');

    /* Feature flags */
    __asm__ volatile ("cpuid" : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx) : "a"(1));
    k_print("Features:   ");
    if (edx & (1 << 0))  k_print("FPU ");
    if (edx & (1 << 4))  k_print("TSC ");
    if (edx & (1 << 23)) k_print("MMX ");
    if (edx & (1 << 25)) k_print("SSE ");
    if (edx & (1 << 26)) k_print("SSE2 ");
    if (ecx & (1 << 0))  k_print("SSE3 ");
    if (ecx & (1 << 19)) k_print("SSE4.1 ");
    if (ecx & (1 << 20)) k_print("SSE4.2 ");
    if (ecx & (1 << 28)) k_print("AVX ");
    k_putc('\n');
    serial_puts("[shell] cpuid\n");
}

static void cmd_ticks(void) {
    char buf[24];
    uint_to_str(tick_count, buf, sizeof(buf));
    k_print("PIT ticks: ");
    k_print(buf);
    k_putc('\n');
}

static void cmd_alloc(const char *args) {
    while (*args == ' ') args++;
    /* Parse integer */
    uint64_t n = 0;
    while (*args >= '0' && *args <= '9') { n = n * 10 + (*args - '0'); args++; }
    if (n == 0) { k_print("Usage: alloc <bytes>\n"); return; }
    if (n > 1024 * 1024 * 64) { k_print("Error: max 64 MB per allocation\n"); return; }

    void *ptr = kmalloc(n);
    if (ptr) {
        char buf[24];
        k_set_color(0x0A, 0x00);
        k_print("Allocated ");
        uint_to_str(n, buf, sizeof(buf));
        k_print(buf);
        k_print(" bytes at 0x");
        k_set_color(0x0F, 0x00);
        k_print_hex((uint64_t)ptr);
        k_putc('\n');
    } else {
        k_set_color(0x0C, 0x00);  /* red */
        k_print("Error: out of memory\n");
        k_set_color(0x0F, 0x00);
    }
}

static void cmd_heap(void) {
    char buf[24];
    HeapStats hs = heap_get_stats();
    k_print("Heap start:     0x"); k_print_hex(hs.start); k_putc('\n');
    k_print("Heap end:       0x"); k_print_hex(hs.end);   k_putc('\n');
    k_print("Next alloc:     0x"); k_print_hex(hs.next);  k_putc('\n');
    k_print("Allocated:      ");
    uint_to_str(hs.allocated, buf, sizeof(buf));
    k_print(buf); k_print(" bytes (");
    uint_to_str(hs.alloc_count, buf, sizeof(buf));
    k_print(buf); k_print(" allocations)\n");
    uint64_t free_bytes = (hs.end > hs.next) ? hs.end - hs.next : 0;
    k_print("Free:           ");
    uint_to_str(free_bytes / (1024 * 1024), buf, sizeof(buf));
    k_print(buf); k_print(" MB\n");
}

static void cmd_history_show(void) {
    int start = (hist_count > MAX_HISTORY) ? hist_count - MAX_HISTORY : 0;
    int total = (hist_count > MAX_HISTORY) ? MAX_HISTORY : hist_count;
    for (int i = 0; i < total; i++) {
        char buf[8];
        uint_to_str((uint64_t)(start + i + 1), buf, sizeof(buf));
        k_print("  "); k_print(buf); k_print("  ");
        k_print(history[(start + i) % MAX_HISTORY]);
        k_putc('\n');
    }
}

static void cmd_reboot(void) {
    k_set_color(0x0E, 0x00);
    k_print("Rebooting...\n");
    serial_puts("[shell] reboot\n");
    /* Pulse the 8042 keyboard controller reset line */
    outb(0x64, 0xFE);
    while (1) __asm__ volatile ("hlt");
}

static void cmd_halt(void) {
    k_set_color(0x0E, 0x00);
    k_print("System halted.\n");
    serial_puts("[shell] halt\n");
    __asm__ volatile ("cli");
    while (1) __asm__ volatile ("hlt");
}

/* ── GUI launcher ─────────────────────────────────────────────────────── */

static void cmd_gui(void) {
    if (!boot_info.fb_available) {
        k_set_color(0x0C, 0x00);
        k_print("Error: No framebuffer available. Boot with GRUB framebuffer support.\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    serial_puts("[gui] Launching desktop environment...\n");
    k_set_color(0x0A, 0x00);
    k_print("Launching LateralusOS Desktop...\n");
    k_set_color(0x0F, 0x00);

    /* ── Phase 1: Initialize framebuffer ─────────────────────────────── */
    serial_puts("[gui] Phase 1: Framebuffer init\n");

    /* Validate framebuffer address before touching it */
    uint64_t fb_addr_raw = boot_info.framebuffer_addr;
    if (fb_addr_raw == 0 || fb_addr_raw > 0xFFFFFFFF) {
        serial_puts("[gui] FATAL: Invalid framebuffer address ");
        serial_put_hex(fb_addr_raw);
        serial_puts("\n");
        k_set_color(0x0C, 0x00);
        k_print("Error: Invalid framebuffer address. Cannot launch GUI.\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    fb_init((uint32_t*)(uint64_t)boot_info.framebuffer_addr,
            boot_info.fb_width, boot_info.fb_height,
            boot_info.fb_pitch, boot_info.fb_bpp);

    /* Verify framebuffer initialized successfully */
    if (!fb.available) {
        serial_puts("[gui] FATAL: fb_init failed — framebuffer not available\n");
        k_set_color(0x0C, 0x00);
        k_print("Error: Framebuffer initialization failed.\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    /* ── Phase 2: Double buffer allocation ───────────────────────────── */
    serial_puts("[gui] Phase 2: Double buffer allocation\n");
    uint32_t fb_buf_size = boot_info.fb_pitch * boot_info.fb_height;
    serial_puts("[gui] Requesting ");
    serial_put_dec(fb_buf_size);
    serial_puts(" bytes for backbuf\n");

    void *backbuf = kmalloc(fb_buf_size);
    if (backbuf) {
        fb_enable_double_buffer(backbuf);
        if (fb.double_buf) {
            serial_puts("[gui] Double-buffer enabled successfully\n");
        } else {
            serial_puts("[gui] WARNING: Double-buffer enable failed, using direct mode\n");
        }
    } else {
        serial_puts("[gui] WARNING: kmalloc failed for backbuf, using direct rendering\n");
        serial_puts("[gui] This will be slower but functional\n");
    }

    /* Dump full framebuffer diagnostics */
    fb_dump_diagnostics();

    /* ── Phase 3: Task scheduler ─────────────────────────────────────── */
    serial_puts("[gui] Phase 3: Task scheduler init\n");
    tasks_init();

    /* ── Phase 4: Mouse driver ───────────────────────────────────────── */
    serial_puts("[gui] Phase 4: Mouse init\n");
    mouse_init();

    /* ── Phase 5: Desktop environment ────────────────────────────────── */
    serial_puts("[gui] Phase 5: Desktop init\n");
    desktop_init(&desktop);
    gui_active = 1;

    /* ── Phase 6: Boot chime ─────────────────────────────────────────── */
    serial_puts("[gui] Phase 6: Boot chime\n");
    speaker_boot_chime(tick_count);

    /* ── Phase 7: Initial render ─────────────────────────────────────── */
    serial_puts("[gui] Phase 7: Initial render\n");
    desktop_render(&desktop);
    serial_puts("[gui] Initial render complete\n");

    serial_puts("[gui] ═══ Desktop running. GUI event loop active. ═══\n");

    /* GUI event loop — runs until ESC is pressed */
    uint8_t prev_sc_gui = 0;
    int shift_held_gui = 0;
    int ctrl_held_gui = 0;
    int alt_held_gui = 0;

    while (gui_active) {
        /* Process keyboard */
        if (last_scancode != prev_sc_gui && last_scancode != 0) {
            uint8_t sc = last_scancode;
            prev_sc_gui = sc;

            /* Track modifier keys */
            if (sc == 0x2A || sc == 0x36) { shift_held_gui = 1; }
            else if (sc == 0xAA || sc == 0xB6) { shift_held_gui = 0; }
            else if (sc == 0x1D) { ctrl_held_gui = 1; }   /* Left Ctrl press */
            else if (sc == 0x9D) { ctrl_held_gui = 0; }   /* Left Ctrl release */
            else if (sc == 0x38) { alt_held_gui = 1; }    /* Left Alt press */
            else if (sc == 0xB8) {                         /* Left Alt release */
                alt_held_gui = 0;
                /* If tab switcher was visible, select the window */
                if (desktop.gui.tab_visible) {
                    gui_tab_select(&desktop.gui);
                }
            }
            else if (sc == 0x01) {
                /* ESC — exit GUI, return to text shell */
                gui_active = 0;
                break;
            }
            else if (sc == 0x0F && alt_held_gui) {
                /* Alt+Tab — cycle window switcher */
                if (shift_held_gui) {
                    gui_tab_prev(&desktop.gui);
                } else {
                    gui_tab_next(&desktop.gui);
                }
            }
            else if (!(sc & 0x80) && sc < 128) {
                char c = scancode_ascii[sc];

                /* Handle Ctrl+key → ASCII control codes (1-26) */
                if (ctrl_held_gui && c >= 'a' && c <= 'z') {
                    c = c - 'a' + 1;
                }
                else if (shift_held_gui && c >= 'a' && c <= 'z') {
                    c -= 32;
                }

                if (c) desktop_key_event(&desktop, c);
            }
        }

        /* Timer-driven frame updates */
        static uint64_t last_tick_gui = 0;
        if (tick_count != last_tick_gui) {
            last_tick_gui = tick_count;
            desktop_tick(&desktop);
        }

        __asm__ volatile ("hlt");
    }

    /* Return to text mode — clear VGA and redraw prompt */
    gui_active = 0;
    serial_puts("[gui] Desktop exited, returning to text shell\n");
    cmd_clear();
    k_set_color(0x0A, 0x00);
    k_print("[gui] Returned to text mode. Type 'gui' to re-enter.\n");
    k_set_color(0x0F, 0x00);
}

/* ── Shell: command dispatcher ────────────────────────────────────────── */

/* ── Network Shell Commands ───────────────────────────────────────────── */

static void cmd_ifconfig(void) {
    const NetDeviceInfo *ni = net_get_info();
    if (!ni || !ni->present) {
        k_set_color(0x0C, 0x00);
        k_print("ifconfig: no network interface detected\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    char mac[18];
    net_mac_str(mac);
    char buf[24];

    k_set_color(0x0E, 0x00);
    k_print("eth0: ");
    k_set_color(0x0F, 0x00);
    k_print("RTL8139 Ethernet\n");

    k_print("  MAC       ");
    k_set_color(0x0B, 0x00);
    k_print(mac);
    k_set_color(0x0F, 0x00);
    k_putc('\n');

    /* Show IP configuration */
    const NetConfig *nc = ip_get_config();
    if (nc->configured) {
        char ipstr[16];
        k_print("  IPv4      ");
        k_set_color(0x0B, 0x00);
        ip_to_str(nc->ip, ipstr);
        k_print(ipstr);
        k_set_color(0x0F, 0x00);
        k_putc('\n');

        k_print("  Netmask   ");
        ip_to_str(nc->netmask, ipstr);
        k_print(ipstr);
        k_putc('\n');

        k_print("  Gateway   ");
        ip_to_str(nc->gateway, ipstr);
        k_print(ipstr);
        k_putc('\n');

        if (nc->dns) {
            k_print("  DNS       ");
            ip_to_str(nc->dns, ipstr);
            k_print(ipstr);
            k_putc('\n');
        }
    } else {
        k_print("  IPv4      (not configured)\n");
    }

    k_print("  Status    ");
    if (net_link_up()) {
        k_set_color(0x0A, 0x00);
        k_print("UP");
    } else {
        k_set_color(0x0C, 0x00);
        k_print("DOWN");
    }
    k_set_color(0x0F, 0x00);
    k_putc('\n');

    k_print("  IO Base   0x");
    k_print_hex(ni->io_base);
    k_putc('\n');

    k_print("  IRQ       ");
    uint_to_str(ni->irq, buf, sizeof(buf));
    k_print(buf);
    k_putc('\n');

    k_print("  TX pkts   ");
    uint_to_str(ni->packets_tx, buf, sizeof(buf));
    k_print(buf);
    k_print("  (");
    uint_to_str(ni->bytes_tx, buf, sizeof(buf));
    k_print(buf);
    k_print(" bytes)\n");

    k_print("  RX pkts   ");
    uint_to_str(ni->packets_rx, buf, sizeof(buf));
    k_print(buf);
    k_print("  (");
    uint_to_str(ni->bytes_rx, buf, sizeof(buf));
    k_print(buf);
    k_print(" bytes)\n");

    serial_puts("[net] ifconfig displayed\n");
}

static void cmd_netstat(void) {
    const NetDeviceInfo *ni = net_get_info();
    char buf[24];

    k_set_color(0x0E, 0x00);
    k_print("Network Statistics:\n");
    k_set_color(0x0F, 0x00);

    if (!ni || !ni->present) {
        k_print("  No NIC present\n");
        return;
    }

    k_print("  Interface     eth0 (RTL8139)\n");
    k_print("  Link          ");
    k_print(net_link_up() ? "UP" : "DOWN");
    k_putc('\n');

    k_print("  TX packets    ");
    uint_to_str(ni->packets_tx, buf, sizeof(buf));
    k_print(buf);
    k_putc('\n');

    k_print("  RX packets    ");
    uint_to_str(ni->packets_rx, buf, sizeof(buf));
    k_print(buf);
    k_putc('\n');

    k_print("  TX bytes      ");
    uint_to_str(ni->bytes_tx, buf, sizeof(buf));
    k_print(buf);
    k_putc('\n');

    k_print("  RX bytes      ");
    uint_to_str(ni->bytes_rx, buf, sizeof(buf));
    k_print(buf);
    k_putc('\n');

    serial_puts("[net] netstat displayed\n");
}

static void cmd_ping(const char *args) {
    /*
     * Real ICMP ping using our IPv4 stack.
     * Usage: ping [host]      (default: 10.0.2.2, the QEMU gateway)
     */
    const NetDeviceInfo *ni = net_get_info();
    if (!ni || !ni->present) {
        k_set_color(0x0C, 0x00);
        k_print("ping: no network interface\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    if (!net_link_up()) {
        k_set_color(0x0C, 0x00);
        k_print("ping: link is down\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    /* Parse destination IP */
    while (*args == ' ') args++;
    uint32_t dst = IP4(10,0,2,2);  /* default: QEMU gateway */
    char ipstr[16];
    if (*args) {
        dst = ip_from_str(args);
        if (dst == 0) {
            k_set_color(0x0C, 0x00);
            k_print("ping: invalid IP address\n");
            k_set_color(0x0F, 0x00);
            return;
        }
    }

    ip_to_str(dst, ipstr);
    k_print("PING ");
    k_print(ipstr);
    k_print(" — 3 ICMP echo requests\n");

    char buf[24];
    int ok = 0, fail = 0;
    extern volatile uint64_t tick_count;

    for (int i = 0; i < 3; i++) {
        /* First ensure ARP resolution */
        uint8_t mac_tmp[6];
        int arp_ok = arp_resolve(dst, mac_tmp);
        if (!arp_ok) {
            /* Wait a bit for ARP reply, polling */
            uint64_t deadline = tick_count + 1000;
            while (!arp_resolve(dst, mac_tmp) && tick_count < deadline) {
                ip_poll();
            }
            arp_ok = arp_resolve(dst, mac_tmp);
        }

        /* Reset ping state and send */
        icmp_ping_reset();

        int r = icmp_ping(dst, (uint16_t)(i + 1));
        if (r != 0) {
            k_set_color(0x0C, 0x00);
            k_print("  send failed (no ARP resolution?)\n");
            k_set_color(0x0F, 0x00);
            fail++;
            continue;
        }

        /* Wait up to 2 seconds for reply */
        uint64_t deadline = tick_count + 2000;
        while (!icmp_ping_received() && tick_count < deadline) {
            ip_poll();
        }

        uint_to_str(i + 1, buf, sizeof(buf));
        if (icmp_ping_received()) {
            k_set_color(0x0A, 0x00);
            k_print("  reply seq=");
            k_print(buf);
            k_print(" from ");
            k_print(ipstr);
            k_print(" — 40 bytes\n");
            k_set_color(0x0F, 0x00);
            ok++;
        } else {
            k_set_color(0x0C, 0x00);
            k_print("  request seq=");
            k_print(buf);
            k_print(" timeout\n");
            k_set_color(0x0F, 0x00);
            fail++;
        }
    }

    k_print("--- ");
    k_print(ipstr);
    k_print(" ping statistics ---\n");
    k_print("3 packets sent, ");
    uint_to_str(ok, buf, sizeof(buf));
    k_print(buf);
    k_print(" received, ");
    uint_to_str(fail, buf, sizeof(buf));
    k_print(buf);
    k_print(" lost\n");

    serial_puts("[net] ping complete\n");
}

static void cmd_arp(void) {
    const NetDeviceInfo *ni = net_get_info();

    k_set_color(0x0E, 0x00);
    k_print("ARP Table:\n");
    k_set_color(0x0F, 0x00);

    if (!ni || !ni->present) {
        k_print("  (no NIC detected)\n");
        return;
    }

    /* Show our own entry */
    char mac[18];
    net_mac_str(mac);
    const NetConfig *nc = ip_get_config();
    char ipstr[16];
    if (nc->configured) {
        ip_to_str(nc->ip, ipstr);
    } else {
        ipstr[0] = '?'; ipstr[1] = '\0';
    }
    k_print("  ");
    k_print(ipstr);
    k_print("     ");
    k_print(mac);
    k_print("   eth0 (self)\n");

    /* Dump the ARP cache from the IP stack */
    arp_dump();

    serial_puts("[net] arp table displayed\n");
}

static void cmd_dhcp(void) {
    const NetDeviceInfo *ni = net_get_info();
    if (!ni || !ni->present) {
        k_set_color(0x0C, 0x00);
        k_print("dhcp: no network interface\n");
        k_set_color(0x0F, 0x00);
        return;
    }
    k_print("Sending DHCP discover...\n");
    if (dhcp_discover()) {
        const NetConfig *nc = ip_get_config();
        char ipstr[16];
        k_set_color(0x0A, 0x00);
        k_print("DHCP lease acquired: ");
        ip_to_str(nc->ip, ipstr);
        k_print(ipstr);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
    } else {
        k_set_color(0x0C, 0x00);
        k_print("DHCP failed (no server found)\n");
        k_set_color(0x0F, 0x00);
    }
}

/* ── DNS commands (v0.3.0) ────────────────────────────────────────────── */

static void cmd_nslookup(const char *hostname) {
    if (!hostname || hostname[0] == '\0') {
        k_print("Usage: nslookup <hostname>\n");
        return;
    }
    k_print("Resolving ");
    k_print(hostname);
    k_print("...\n");

    uint32_t ip = dns_resolve(hostname);
    if (ip) {
        char ipstr[16];
        ip_to_str(ip, ipstr);
        k_set_color(0x0A, 0x00);
        k_print(hostname);
        k_print(" → ");
        k_print(ipstr);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
    } else {
        k_set_color(0x0C, 0x00);
        k_print("nslookup: could not resolve ");
        k_print(hostname);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
    }
}

static void cmd_dns_cache(const char *arg) {
    if (arg && k_strcmp(arg, "flush") == 0) {
        dns_cache_flush();
        k_set_color(0x0A, 0x00);
        k_print("DNS cache flushed\n");
        k_set_color(0x0F, 0x00);
    } else {
        dns_cache_dump();
    }
}

static void cmd_tcp(const char *arg) {
    static const char *state_names[] = {
        "CLOSED", "LISTEN", "SYN_SENT", "SYN_RECV",
        "ESTABLISHED", "FIN_WAIT1", "FIN_WAIT2", "CLOSE_WAIT",
        "CLOSING", "LAST_ACK", "TIME_WAIT"
    };
    static const uint8_t state_colors[] = {
        0x08, 0x0E, 0x0D, 0x0D,  /* CLOSED=gray, LISTEN=yellow, SYN=magenta */
        0x0A, 0x0C, 0x0C, 0x06,  /* ESTABLISHED=green, FIN=red, CLOSE_WAIT=brown */
        0x0C, 0x0C, 0x06          /* CLOSING=red, LAST_ACK=red, TIME_WAIT=brown */
    };

    /* tcp dump → serial debug output */
    if (arg && k_strcmp(arg, "dump") == 0) {
        tcp_dump();
        k_print("TCP connection table dumped to serial\n");
        return;
    }

    int active = tcp_active_count();
    char buf[16];

    k_set_color(0x0B, 0x00);
    k_print("═══ TCP Connections ");
    k_set_color(0x0F, 0x00);
    k_print("(");
    uint_to_str(active, buf, sizeof(buf));
    k_print(buf);
    k_print(" active, ");
    uint_to_str(TCP_MAX_CONNECTIONS, buf, sizeof(buf));
    k_print(buf);
    k_print(" max)\n");

    if (active == 0) {
        k_set_color(0x08, 0x00);
        k_print("  (no active connections)\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    /* Header */
    k_set_color(0x0E, 0x00);
    k_print("  ID  STATE        LOCAL PORT  REMOTE IP         REMOTE PORT\n");
    k_set_color(0x07, 0x00);
    k_print("  ──  ───────────  ──────────  ────────────────  ───────────\n");

    /* Iterate connection slots — use tcp_get_state() to check each */
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        int st = tcp_get_state(i);
        if (st == TCP_STATE_CLOSED) continue;

        /* ID */
        k_set_color(0x0F, 0x00);
        k_print("  ");
        uint_to_str(i, buf, sizeof(buf));
        k_print(buf);
        /* pad to 4 chars */
        int id_len = 0;
        for (const char *p = buf; *p; p++) id_len++;
        for (int pad = id_len; pad < 4; pad++) k_putc(' ');

        /* State */
        const char *sn = (st >= 0 && st <= 10) ? state_names[st] : "???";
        uint8_t sc = (st >= 0 && st <= 10) ? state_colors[st] : 0x0C;
        k_set_color(sc, 0x00);
        k_print(sn);
        /* pad to 13 chars */
        int sn_len = 0;
        for (const char *p = sn; *p; p++) sn_len++;
        k_set_color(0x0F, 0x00);
        for (int pad = sn_len; pad < 13; pad++) k_putc(' ');

        k_print("(use 'tcp dump' for full details)\n");
    }

    k_set_color(0x0F, 0x00);
    serial_puts("[tcp] connection table displayed\n");
}

static void cmd_wget(const char *url) {
    while (*url == ' ') url++;

    if (*url == '\0') {
        k_set_color(0x0E, 0x00);
        k_print("Usage: wget <url>\n");
        k_set_color(0x08, 0x00);
        k_print("  Example: wget http://example.com/\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    /* Parse URL */
    HttpUrl parsed;
    if (http_parse_url(url, &parsed) < 0) {
        k_set_color(0x0C, 0x00);
        k_print("Invalid URL: ");
        k_print(url);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
        return;
    }

    k_set_color(0x0B, 0x00);
    k_print("Connecting to ");
    k_print(parsed.host);
    char pbuf[8];
    if (parsed.port != 80) {
        k_putc(':');
        uint_to_str(parsed.port, pbuf, sizeof(pbuf));
        k_print(pbuf);
    }
    k_print(parsed.path);
    k_print("...\n");
    k_set_color(0x0F, 0x00);

    /* Perform GET */
    HttpResponse *resp = http_get(parsed.host, parsed.port, parsed.path);

    if (resp->error != 0) {
        k_set_color(0x0C, 0x00);
        switch (resp->error) {
            case -1: k_print("Error: DNS resolution failed\n"); break;
            case -2: k_print("Error: Connection refused\n"); break;
            case -3: k_print("Error: Connection timed out\n"); break;
            case -4: k_print("Error: Send failed\n"); break;
            case -5: k_print("Error: No response\n"); break;
            default: k_print("Error: Unknown\n"); break;
        }
        k_set_color(0x0F, 0x00);
        return;
    }

    /* Display status */
    k_set_color(resp->ok ? 0x0A : 0x0C, 0x00);
    k_print("HTTP ");
    uint_to_str(resp->status_code, pbuf, sizeof(pbuf));
    k_print(pbuf);
    k_putc(' ');
    k_print(resp->status_text);
    k_putc('\n');
    k_set_color(0x0F, 0x00);

    /* Show content type */
    if (resp->content_type[0]) {
        k_set_color(0x08, 0x00);
        k_print("Type: ");
        k_print(resp->content_type);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
    }

    /* Show body length */
    k_set_color(0x08, 0x00);
    k_print("Size: ");
    int body_len = http_body_len(resp);
    uint_to_str(body_len, pbuf, sizeof(pbuf));
    k_print(pbuf);
    k_print(" bytes\n");
    k_set_color(0x0F, 0x00);

    /* Display body (truncated to ~60 lines for VGA) */
    const char *body = http_body(resp);
    if (body && body_len > 0) {
        k_putc('\n');
        int lines = 0;
        for (int i = 0; i < body_len && lines < 60; i++) {
            k_putc(body[i]);
            if (body[i] == '\n') lines++;
        }
        if (lines >= 60) {
            k_set_color(0x08, 0x00);
            k_print("\n... (truncated)\n");
            k_set_color(0x0F, 0x00);
        }
    }
}

/* ── New commands (v0.2.0+) ───────────────────────────────────────────── */

static void cmd_whoami(void) {
    k_set_color(0x0A, 0x00);
    k_print("root\n");
    k_set_color(0x0F, 0x00);
}

static void cmd_hostname(void) {
    k_set_color(0x0A, 0x00);
    k_print("lateralus\n");
    k_set_color(0x0F, 0x00);
}

static void cmd_date(void) {
    /* Read CMOS RTC (best-effort, no century register) */
    auto uint8_t cmos_read(uint8_t reg) {
        outb(0x70, reg);
        uint8_t v = inb(0x71);
        /* BCD → binary */
        return (v >> 4) * 10 + (v & 0x0F);
    }
    uint8_t sec  = cmos_read(0x00);
    uint8_t min  = cmos_read(0x02);
    uint8_t hour = cmos_read(0x04);
    uint8_t day  = cmos_read(0x07);
    uint8_t mon  = cmos_read(0x08);
    uint8_t year = cmos_read(0x09);

    char buf[8];
    k_print("20");
    uint_to_str(year, buf, sizeof(buf)); k_print(buf);
    k_putc('-');
    if (mon < 10) k_putc('0');
    uint_to_str(mon, buf, sizeof(buf)); k_print(buf);
    k_putc('-');
    if (day < 10) k_putc('0');
    uint_to_str(day, buf, sizeof(buf)); k_print(buf);
    k_putc(' ');
    if (hour < 10) k_putc('0');
    uint_to_str(hour, buf, sizeof(buf)); k_print(buf);
    k_putc(':');
    if (min < 10) k_putc('0');
    uint_to_str(min, buf, sizeof(buf)); k_print(buf);
    k_putc(':');
    if (sec < 10) k_putc('0');
    uint_to_str(sec, buf, sizeof(buf)); k_print(buf);
    k_print(" UTC\n");
}

static void cmd_ps(void) {
    int ready = 0, blocked = 0, sleeping = 0, total = 0;
    sched_stats(&ready, &blocked, &sleeping, &total);

    char buf[24];
    k_set_color(0x0E, 0x00);
    k_print("  TID  STATE      PRIO  NAME\n");
    k_set_color(0x07, 0x00);
    k_print("  ---  ---------  ----  ----------------\n");
    k_set_color(0x0F, 0x00);

    static const char *state_str[] = {
        "free", "ready", "RUNNING", "blocked", "sleeping", "dead"
    };

    for (int i = 0; i < 32; i++) {
        const SchedTask *t = sched_get_task(i);
        if (!t) continue;

        /* TID */
        k_print("  ");
        uint_to_str((uint64_t)t->tid, buf, sizeof(buf));
        int len = k_strlen(buf);
        for (int p = len; p < 3; p++) k_putc(' ');
        k_print(buf);
        k_print("  ");

        /* State — color code */
        int st = t->state;
        if (st == 2)      k_set_color(0x0A, 0x00);  /* RUNNING = green */
        else if (st == 1)  k_set_color(0x0B, 0x00);  /* READY = cyan */
        else if (st == 4)  k_set_color(0x0D, 0x00);  /* SLEEPING = magenta */
        else if (st == 3)  k_set_color(0x0C, 0x00);  /* BLOCKED = red */
        else if (st == 5)  k_set_color(0x08, 0x00);  /* DEAD = dark grey */

        const char *sname = (st >= 0 && st <= 5) ? state_str[st] : "???";
        k_print(sname);
        k_set_color(0x0F, 0x00);
        len = k_strlen(sname);
        for (int p = len; p < 11; p++) k_putc(' ');

        /* Priority */
        uint_to_str((uint64_t)t->priority, buf, sizeof(buf));
        k_print(buf);
        len = k_strlen(buf);
        for (int p = len; p < 6; p++) k_putc(' ');

        /* Name */
        k_print(t->name);
        k_putc('\n');
    }

    /* Summary line */
    k_set_color(0x0B, 0x00);
    k_print("Tasks: ");
    uint_to_str((uint64_t)total, buf, sizeof(buf));
    k_print(buf); k_print(" total, ");
    uint_to_str((uint64_t)ready, buf, sizeof(buf));
    k_print(buf); k_print(" ready, ");
    uint_to_str((uint64_t)blocked, buf, sizeof(buf));
    k_print(buf); k_print(" blocked, ");
    uint_to_str((uint64_t)sleeping, buf, sizeof(buf));
    k_print(buf); k_print(" sleeping\n");
    k_set_color(0x0F, 0x00);

    /* Also dump the full list to serial */
    sched_list();
    serial_puts("[shell] ps\n");
}

static void cmd_sysinfo(void) {
    k_set_color(0x0E, 0x00);
    k_print("╔══════════════════════════════════════════════╗\n");
    k_print("║            System Information                ║\n");
    k_print("╠══════════════════════════════════════════════╣\n");
    k_set_color(0x0F, 0x00);

    k_print("║  OS:       LateralusOS v0.3.0               ║\n");
    k_print("║  Lang:     Lateralus v2.2.0                 ║\n");
    k_print("║  Arch:     x86_64 (long mode)               ║\n");
    k_print("║  Shell:    ltlsh 0.3.0                      ║\n");

    /* CPU vendor */
    uint32_t eax, ebx, ecx, edx;
    char vendor[13];
    __asm__ volatile ("cpuid" : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx) : "a"(0));
    *(uint32_t*)&vendor[0] = ebx;
    *(uint32_t*)&vendor[4] = edx;
    *(uint32_t*)&vendor[8] = ecx;
    vendor[12] = '\0';
    k_print("║  CPU:      ");
    k_print(vendor);
    k_print("                   ║\n");

    /* Memory */
    k_print("║  Memory:   ");
    if (boot_info.total_memory_kb > 0) {
        char mbuf[16];
        uint_to_str((uint32_t)(boot_info.total_memory_kb / 1024), mbuf, sizeof(mbuf));
        k_print(mbuf);
        k_print(" MiB total");
    } else {
        k_print("unknown");
    }
    k_print("                    ║\n");

    k_set_color(0x0E, 0x00);
    k_print("╚══════════════════════════════════════════════╝\n");
    k_set_color(0x0F, 0x00);
    serial_puts("[shell] sysinfo\n");
}

static void cmd_cal(void) {
    /* Read month/year from CMOS RTC */
    auto uint8_t cmos_rd(uint8_t reg) {
        outb(0x70, reg);
        uint8_t v = inb(0x71);
        return (v >> 4) * 10 + (v & 0x0F);
    }
    uint8_t mon  = cmos_rd(0x08);
    uint8_t year = cmos_rd(0x09);
    int full_year = 2000 + year;

    /* Month names */
    const char *months[] = {
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    };

    /* Days in each month */
    int days_in_month[] = { 0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
    /* Leap year check */
    if ((full_year % 4 == 0 && full_year % 100 != 0) || full_year % 400 == 0)
        days_in_month[2] = 29;

    if (mon < 1 || mon > 12) mon = 1;
    int ndays = days_in_month[mon];

    /* Zeller's formula to get day-of-week for the 1st of this month */
    int m = mon, y = full_year;
    if (m < 3) { m += 12; y--; }
    int q = 1; /* first day */
    int dow = (q + (13 * (m + 1)) / 5 + y + y / 4 - y / 100 + y / 400) % 7;
    /* Zeller: 0=Sat, 1=Sun, 2=Mon ... 6=Fri → convert to Su=0..Sa=6 */
    dow = (dow + 6) % 7;

    /* Print header */
    char buf[24];
    k_set_color(0x0E, 0x00);
    k_print("    ");
    k_print(months[mon]);
    k_print(" ");
    uint_to_str((uint64_t)full_year, buf, sizeof(buf));
    k_print(buf);
    k_putc('\n');
    k_set_color(0x0F, 0x00);
    k_print(" Su Mo Tu We Th Fr Sa\n");

    /* Leading spaces */
    for (int i = 0; i < dow; i++) k_print("   ");

    /* Days */
    for (int d = 1; d <= ndays; d++) {
        if (d < 10) k_putc(' ');
        k_putc(' ');
        uint_to_str((uint64_t)d, buf, sizeof(buf));
        k_print(buf);
        dow++;
        if (dow == 7) { k_putc('\n'); dow = 0; }
    }
    if (dow != 0) k_putc('\n');
}

static void cmd_write(const char *args) {
    /* write <filename> <content>  — write text to a file in /home */
    while (*args == ' ') args++;
    if (*args == '\0') {
        k_print("Usage: write <filename> <content>\n");
        return;
    }
    /* Extract filename */
    char fname[64];
    int fi = 0;
    while (*args && *args != ' ' && fi < 63) {
        fname[fi++] = *args++;
    }
    fname[fi] = '\0';
    while (*args == ' ') args++;

    /* Resolve or create file */
    int home = ramfs_resolve_path("/home");
    if (home < 0) {
        k_set_color(0x0C, 0x00);
        k_print("write: /home not found\n");
        k_set_color(0x0F, 0x00);
        return;
    }
    int node = -1;
    /* Try to find existing file */
    char buf[1024];
    if (ramfs_list(home, buf, 1024) == 0) {
        /* Check if file exists by trying to resolve */
        char path[128] = "/home/";
        int pi = 6;
        for (int i = 0; fname[i] && pi < 126; i++) path[pi++] = fname[i];
        path[pi] = '\0';
        node = ramfs_resolve_path(path);
    }
    if (node < 0) {
        node = ramfs_create(home, fname);
    }
    if (node >= 0) {
        ramfs_write(node, args, k_strlen(args));
        k_set_color(0x0A, 0x00);
        k_print("Wrote ");
        char nbuf[16];
        uint_to_str(k_strlen(args), nbuf, sizeof(nbuf));
        k_print(nbuf);
        k_print(" bytes to /home/");
        k_print(fname);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
    } else {
        k_set_color(0x0C, 0x00);
        k_print("write: failed to create file\n");
        k_set_color(0x0F, 0x00);
    }
}

/* ── New commands (v0.2.1) — rm, cd, pwd, env, sleep, dmesg, export, head, wc ── */

static void cmd_rm(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') { k_print("Usage: rm <path>\n"); return; }
    int node = ramfs_resolve_path(args);
    if (node < 0) {
        k_set_color(0x0C, 0x00);
        k_print("rm: "); k_print(args); k_print(": not found\n");
        k_set_color(0x0F, 0x00);
        return;
    }
    if (ramfs_remove(node) == 0) {
        k_set_color(0x0A, 0x00);
        k_print("Removed: "); k_print(args); k_putc('\n');
        k_set_color(0x0F, 0x00);
    } else {
        k_set_color(0x0C, 0x00);
        k_print("rm: failed (directory not empty?)\n");
        k_set_color(0x0F, 0x00);
    }
}

static void cmd_cd(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0' || k_strcmp(args, "~") == 0) {
        /* cd with no args or ~ → go to /home */
        cwd[0] = '/'; cwd[1] = 'h'; cwd[2] = 'o'; cwd[3] = 'm'; cwd[4] = 'e'; cwd[5] = '\0';
        return;
    }
    if (k_strcmp(args, "/") == 0) {
        cwd[0] = '/'; cwd[1] = '\0';
        return;
    }
    if (k_strcmp(args, "..") == 0) {
        /* Go up one directory */
        int len = k_strlen(cwd);
        if (len <= 1) return; /* already at / */
        len--;
        while (len > 0 && cwd[len] != '/') len--;
        if (len == 0) len = 1;
        cwd[len] = '\0';
        return;
    }

    /* Build absolute path */
    char path[128];
    if (args[0] == '/') {
        /* Absolute path */
        int i = 0;
        while (args[i] && i < 126) { path[i] = args[i]; i++; }
        path[i] = '\0';
    } else {
        /* Relative path — append to cwd */
        int i = 0, j = 0;
        while (cwd[i] && j < 120) path[j++] = cwd[i++];
        if (j > 1) path[j++] = '/';
        i = 0;
        while (args[i] && j < 126) path[j++] = args[i++];
        path[j] = '\0';
    }

    int node = ramfs_resolve_path(path);
    if (node >= 0 && ramfs_node_type(node) == RAMFS_DIR) {
        int i = 0;
        while (path[i] && i < 126) { cwd[i] = path[i]; i++; }
        cwd[i] = '\0';
    } else {
        k_set_color(0x0C, 0x00);
        k_print("cd: "); k_print(args); k_print(": not a directory\n");
        k_set_color(0x0F, 0x00);
    }
}

static void cmd_pwd(void) {
    k_print(cwd);
    k_putc('\n');
}

static void cmd_env(void) {
    for (int i = 0; i < env_count; i++) {
        k_set_color(0x0B, 0x00);
        k_print(env_keys[i]);
        k_set_color(0x0F, 0x00);
        k_putc('=');
        k_print(env_vals[i]);
        k_putc('\n');
    }
    /* Also show dynamic values */
    k_set_color(0x0B, 0x00);
    k_print("PWD");
    k_set_color(0x0F, 0x00);
    k_putc('=');
    k_print(cwd);
    k_putc('\n');
}

static void cmd_export(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') { cmd_env(); return; }

    /* Find = sign */
    int eq = -1;
    for (int i = 0; args[i]; i++) {
        if (args[i] == '=') { eq = i; break; }
    }
    if (eq <= 0) { k_print("Usage: export KEY=VALUE\n"); return; }

    /* Extract key and value */
    char key[ENV_KEYLEN], val[ENV_VALLEN];
    int ki = 0, vi = 0;
    for (int i = 0; i < eq && ki < ENV_KEYLEN - 1; i++) key[ki++] = args[i];
    key[ki] = '\0';
    for (int i = eq + 1; args[i] && vi < ENV_VALLEN - 1; i++) val[vi++] = args[i];
    val[vi] = '\0';

    /* Update existing or add new */
    for (int i = 0; i < env_count; i++) {
        if (k_strcmp(env_keys[i], key) == 0) {
            int j = 0;
            while (val[j] && j < ENV_VALLEN - 1) { env_vals[i][j] = val[j]; j++; }
            env_vals[i][j] = '\0';
            return;
        }
    }
    if (env_count < MAX_ENV) {
        int j = 0;
        while (key[j] && j < ENV_KEYLEN - 1) { env_keys[env_count][j] = key[j]; j++; }
        env_keys[env_count][j] = '\0';
        j = 0;
        while (val[j] && j < ENV_VALLEN - 1) { env_vals[env_count][j] = val[j]; j++; }
        env_vals[env_count][j] = '\0';
        env_count++;
    }
}

static void cmd_unset(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') {
        k_print("Usage: unset <KEY>\n");
        return;
    }
    if (env_unset(args) == 0) {
        k_set_color(0x0A, 0x00);
        k_print("Unset: ");
        k_print(args);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
    } else {
        k_set_color(0x0C, 0x00);
        k_print("unset: ");
        k_print(args);
        k_print(": not found\n");
        k_set_color(0x0F, 0x00);
    }
}

static void cmd_alias(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') {
        /* List all aliases */
        if (alias_count == 0) {
            k_print("No aliases defined.\n");
            return;
        }
        for (int i = 0; i < alias_count; i++) {
            k_set_color(0x0B, 0x00);
            k_print(alias_names[i]);
            k_set_color(0x0F, 0x00);
            k_print("='");
            k_print(alias_cmds[i]);
            k_print("'\n");
        }
        return;
    }

    /* Find = sign: alias name=command */
    int eq = -1;
    for (int i = 0; args[i]; i++) {
        if (args[i] == '=') { eq = i; break; }
    }
    if (eq <= 0) {
        k_print("Usage: alias name=command\n");
        return;
    }

    char name[ALIAS_NAMELEN], cmd[ALIAS_CMDLEN];
    int ni = 0, ci = 0;
    for (int i = 0; i < eq && ni < ALIAS_NAMELEN - 1; i++) name[ni++] = args[i];
    name[ni] = '\0';
    /* Strip optional quotes from value */
    const char *vp = args + eq + 1;
    if (*vp == '\'' || *vp == '"') vp++;
    while (*vp && ci < ALIAS_CMDLEN - 1) {
        if ((*vp == '\'' || *vp == '"') && vp[1] == '\0') break;
        cmd[ci++] = *vp++;
    }
    cmd[ci] = '\0';

    /* Update existing */
    for (int i = 0; i < alias_count; i++) {
        if (k_strcmp(alias_names[i], name) == 0) {
            int j = 0;
            while (cmd[j] && j < ALIAS_CMDLEN - 1) { alias_cmds[i][j] = cmd[j]; j++; }
            alias_cmds[i][j] = '\0';
            return;
        }
    }
    if (alias_count < MAX_ALIASES) {
        int j = 0;
        while (name[j] && j < ALIAS_NAMELEN - 1) { alias_names[alias_count][j] = name[j]; j++; }
        alias_names[alias_count][j] = '\0';
        j = 0;
        while (cmd[j] && j < ALIAS_CMDLEN - 1) { alias_cmds[alias_count][j] = cmd[j]; j++; }
        alias_cmds[alias_count][j] = '\0';
        alias_count++;
    }
}

static void cmd_unalias(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') {
        k_print("Usage: unalias <name>\n");
        return;
    }
    for (int i = 0; i < alias_count; i++) {
        if (k_strcmp(alias_names[i], args) == 0) {
            for (int j = i; j < alias_count - 1; j++) {
                int k;
                for (k = 0; alias_names[j+1][k]; k++) alias_names[j][k] = alias_names[j+1][k];
                alias_names[j][k] = '\0';
                for (k = 0; alias_cmds[j+1][k]; k++) alias_cmds[j][k] = alias_cmds[j+1][k];
                alias_cmds[j][k] = '\0';
            }
            alias_count--;
            return;
        }
    }
    k_set_color(0x0C, 0x00);
    k_print("unalias: ");
    k_print(args);
    k_print(": not found\n");
    k_set_color(0x0F, 0x00);
}

static void cmd_sleep(const char *args) {
    while (*args == ' ') args++;
    uint64_t secs = 0;
    while (*args >= '0' && *args <= '9') { secs = secs * 10 + (*args - '0'); args++; }
    if (secs == 0) { k_print("Usage: sleep <seconds>\n"); return; }
    if (secs > 300) secs = 300; /* cap at 5 minutes */

    uint64_t wait_until = tick_count + secs * 1000;
    while (tick_count < wait_until)
        __asm__ volatile ("hlt");
}

static void cmd_dmesg(void) {
    int start = (dmesg_count > DMESG_LINES) ? dmesg_count - DMESG_LINES : 0;
    int total = (dmesg_count > DMESG_LINES) ? DMESG_LINES : dmesg_count;
    for (int i = 0; i < total; i++) {
        int idx = (start + i) % DMESG_LINES;
        k_set_color(0x07, 0x00);
        k_print(dmesg_buf[idx]);
        k_putc('\n');
    }
    k_set_color(0x0F, 0x00);
}

static void cmd_head(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') { k_print("Usage: head <file> [n]\n"); return; }

    /* Extract filename */
    char fname[128];
    int fi = 0;
    while (*args && *args != ' ' && fi < 126) fname[fi++] = *args++;
    fname[fi] = '\0';

    /* Optional line count (default 10) */
    while (*args == ' ') args++;
    int nlines = 10;
    if (*args >= '0' && *args <= '9') {
        nlines = 0;
        while (*args >= '0' && *args <= '9') { nlines = nlines * 10 + (*args - '0'); args++; }
    }

    int node = ramfs_resolve_path(fname);
    if (node < 0) {
        k_set_color(0x0C, 0x00);
        k_print("head: "); k_print(fname); k_print(": not found\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    char buf[2048];
    int n = ramfs_read(node, buf, 2048);
    if (n <= 0) return;

    int lines = 0;
    for (int i = 0; i < n && lines < nlines; i++) {
        k_putc(buf[i]);
        if (buf[i] == '\n') lines++;
    }
    if (lines == 0) k_putc('\n');
}

static void cmd_wc(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') { k_print("Usage: wc <file>\n"); return; }

    int node = ramfs_resolve_path(args);
    if (node < 0) {
        k_set_color(0x0C, 0x00);
        k_print("wc: "); k_print(args); k_print(": not found\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    char buf[2048];
    int n = ramfs_read(node, buf, 2048);
    if (n <= 0) { k_print("  0  0  0 "); k_print(args); k_putc('\n'); return; }

    int lines = 0, words = 0, bytes = n;
    int in_word = 0;
    for (int i = 0; i < n; i++) {
        if (buf[i] == '\n') lines++;
        if (buf[i] == ' ' || buf[i] == '\n' || buf[i] == '\t') {
            in_word = 0;
        } else if (!in_word) {
            words++;
            in_word = 1;
        }
    }

    char nbuf[24];
    k_print("  ");
    uint_to_str((uint64_t)lines, nbuf, sizeof(nbuf)); k_print(nbuf);
    k_print("  ");
    uint_to_str((uint64_t)words, nbuf, sizeof(nbuf)); k_print(nbuf);
    k_print("  ");
    uint_to_str((uint64_t)bytes, nbuf, sizeof(nbuf)); k_print(nbuf);
    k_print(" "); k_print(args); k_putc('\n');
}

/* ── tail: show last N lines of a file ─────────────────────────────── */

static void cmd_tail(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') { k_print("Usage: tail <file> [n]\n"); return; }

    /* Extract filename */
    char fname[128];
    int fi = 0;
    while (*args && *args != ' ' && fi < 126) fname[fi++] = *args++;
    fname[fi] = '\0';

    /* Optional line count (default 10) */
    while (*args == ' ') args++;
    int nlines = 10;
    if (*args >= '0' && *args <= '9') {
        nlines = 0;
        while (*args >= '0' && *args <= '9') { nlines = nlines * 10 + (*args - '0'); args++; }
    }

    int node = ramfs_resolve_path(fname);
    if (node < 0) {
        k_set_color(0x0C, 0x00);
        k_print("tail: "); k_print(fname); k_print(": not found\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    char buf[2048];
    int n = ramfs_read(node, buf, 2048);
    if (n <= 0) return;

    /* Count total lines */
    int total_lines = 0;
    for (int i = 0; i < n; i++) {
        if (buf[i] == '\n') total_lines++;
    }
    /* If last char is not '\n', count that partial line too */
    if (n > 0 && buf[n - 1] != '\n') total_lines++;

    int skip = total_lines - nlines;
    if (skip < 0) skip = 0;

    int cur_line = 0;
    for (int i = 0; i < n; i++) {
        if (cur_line >= skip) {
            k_putc(buf[i]);
        }
        if (buf[i] == '\n') cur_line++;
    }
    if (n > 0 && buf[n - 1] != '\n') k_putc('\n');
}

/* ── stat: show file/directory info ────────────────────────────────── */

static void cmd_stat(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') { k_print("Usage: stat <path>\n"); return; }

    int node = ramfs_resolve_path(args);
    if (node < 0) {
        k_set_color(0x0C, 0x00);
        k_print("stat: "); k_print(args); k_print(": not found\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    char nbuf[24];
    k_print("  File: "); k_print(args); k_putc('\n');
    k_print("  Node: ");
    uint_to_str((uint64_t)node, nbuf, sizeof(nbuf)); k_print(nbuf); k_putc('\n');

    /* Try to read to determine size */
    char buf[4096];
    int sz = ramfs_read(node, buf, 4096);
    if (sz < 0) {
        k_print("  Type: directory\n");
        /* Count children by listing */
        char lbuf[1024];
        if (ramfs_list(node, lbuf, 1024) == 0) {
            int entries = 0;
            for (int i = 0; lbuf[i]; i++) {
                if (lbuf[i] == '\n') entries++;
            }
            k_print("  Entries: ");
            uint_to_str((uint64_t)entries, nbuf, sizeof(nbuf)); k_print(nbuf); k_putc('\n');
        }
    } else {
        k_print("  Type: file\n");
        k_print("  Size: ");
        uint_to_str((uint64_t)sz, nbuf, sizeof(nbuf)); k_print(nbuf);
        k_print(" bytes\n");
        /* Count lines */
        int lines = 0;
        for (int i = 0; i < sz; i++) {
            if (buf[i] == '\n') lines++;
        }
        k_print("  Lines: ");
        uint_to_str((uint64_t)lines, nbuf, sizeof(nbuf)); k_print(nbuf); k_putc('\n');
    }
}

/* ── xxd: hex dump of a file ───────────────────────────────────────── */

static void cmd_xxd(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') { k_print("Usage: xxd <file> [bytes]\n"); return; }

    char fname[128];
    int fi = 0;
    while (*args && *args != ' ' && fi < 126) fname[fi++] = *args++;
    fname[fi] = '\0';

    while (*args == ' ') args++;
    int max_bytes = 256;
    if (*args >= '0' && *args <= '9') {
        max_bytes = 0;
        while (*args >= '0' && *args <= '9') { max_bytes = max_bytes * 10 + (*args - '0'); args++; }
    }

    int node = ramfs_resolve_path(fname);
    if (node < 0) {
        k_set_color(0x0C, 0x00);
        k_print("xxd: "); k_print(fname); k_print(": not found\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    char buf[2048];
    int n = ramfs_read(node, buf, 2048);
    if (n <= 0) return;
    if (n > max_bytes) n = max_bytes;

    const char hex[] = "0123456789abcdef";
    char line[80];

    for (int off = 0; off < n; off += 16) {
        /* Offset */
        int li = 0;
        for (int s = 28; s >= 0; s -= 4) {
            line[li++] = hex[(off >> s) & 0xF];
        }
        line[li++] = ':'; line[li++] = ' ';

        /* Hex bytes */
        for (int j = 0; j < 16; j++) {
            if (off + j < n) {
                unsigned char b = (unsigned char)buf[off + j];
                line[li++] = hex[(b >> 4) & 0xF];
                line[li++] = hex[b & 0xF];
            } else {
                line[li++] = ' '; line[li++] = ' ';
            }
            line[li++] = ' ';
            if (j == 7) line[li++] = ' ';
        }

        /* ASCII */
        line[li++] = ' ';
        for (int j = 0; j < 16; j++) {
            if (off + j < n) {
                unsigned char b = (unsigned char)buf[off + j];
                line[li++] = (b >= 0x20 && b < 0x7F) ? (char)b : '.';
            } else {
                line[li++] = ' ';
            }
        }
        line[li] = '\0';
        k_print(line); k_putc('\n');
    }
}

/* ── spawn: create background tasks ────────────────────────────────── */

/* Demo task: heartbeat — prints a tick every N seconds to serial */
static void task_heartbeat(void *arg) {
    int interval = arg ? (int)(uint64_t)arg : 5;
    int count = 0;
    while (1) {
        sched_sleep((uint32_t)(interval * 1000));
        count++;
        serial_puts("[heartbeat] tick #");
        char buf[16]; uint_to_str((uint64_t)count, buf, sizeof(buf));
        serial_puts(buf);
        serial_puts("\n");
    }
}

/* Demo task: counter — counts to N then exits */
static void task_counter(void *arg) {
    int limit = arg ? (int)(uint64_t)arg : 10;
    for (int i = 1; i <= limit; i++) {
        sched_sleep(1000);
        serial_puts("[counter] ");
        char buf[16]; uint_to_str((uint64_t)i, buf, sizeof(buf));
        serial_puts(buf);
        serial_puts("/");
        uint_to_str((uint64_t)limit, buf, sizeof(buf));
        serial_puts(buf);
        serial_puts("\n");
    }
    /* Will exit normally via sched_exit(0) when function returns */
}

/* Demo task: net_poll — periodically polls network */
static void task_net_poll(void *arg) {
    (void)arg;
    while (1) {
        ip_poll();
        tcp_tick();
        sched_sleep(100);  /* poll 10x per second */
    }
}

static void cmd_spawn(const char *args) {
    while (*args == ' ') args++;

    if (*args == '\0') {
        k_set_color(0x0E, 0x00);
        k_print("Usage: spawn <task>\n");
        k_set_color(0x0F, 0x00);
        k_print("Available tasks:\n");
        k_print("  heartbeat [secs]  Periodic serial heartbeat (default 5s)\n");
        k_print("  counter [n]       Count to n then exit (default 10)\n");
        k_print("  netpoll           Network polling daemon\n");
        return;
    }

    /* Parse task name and optional argument */
    char task_name[32] = {0};
    int arg_val = 0;
    int has_arg = 0;
    const char *p = args;
    int i = 0;
    while (*p && *p != ' ' && i < 31) { task_name[i++] = *p++; }
    task_name[i] = '\0';
    while (*p == ' ') p++;
    if (*p >= '0' && *p <= '9') {
        has_arg = 1;
        while (*p >= '0' && *p <= '9') {
            arg_val = arg_val * 10 + (*p - '0');
            p++;
        }
    }

    int tid = -1;
    if (k_strcmp(task_name, "heartbeat") == 0) {
        int interval = has_arg ? arg_val : 5;
        if (interval < 1) interval = 1;
        if (interval > 3600) interval = 3600;
        tid = sched_create("heartbeat", task_heartbeat,
                          (void *)(uint64_t)interval, PRIO_NORMAL);
    } else if (k_strcmp(task_name, "counter") == 0) {
        int limit = has_arg ? arg_val : 10;
        if (limit < 1) limit = 1;
        if (limit > 10000) limit = 10000;
        tid = sched_create("counter", task_counter,
                          (void *)(uint64_t)limit, PRIO_NORMAL);
    } else if (k_strcmp(task_name, "netpoll") == 0) {
        tid = sched_create("netpoll", task_net_poll, 0, PRIO_HIGH);
    } else {
        k_set_color(0x0C, 0x00);
        k_print("spawn: unknown task '");
        k_print(task_name);
        k_print("'\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    if (tid >= 0) {
        k_set_color(0x0A, 0x00);
        k_print("Spawned '");
        k_print(task_name);
        k_print("' (tid ");
        char nbuf[16]; uint_to_str((uint64_t)tid, nbuf, sizeof(nbuf));
        k_print(nbuf);
        k_print(")\n");
        k_set_color(0x0F, 0x00);
        dmesg_add("[spawn] created task");
    } else {
        k_set_color(0x0C, 0x00);
        k_print("spawn: failed (no free slots or out of memory)\n");
        k_set_color(0x0F, 0x00);
    }
}

/* ── kill: terminate a task by TID ─────────────────────────────────── */

static void cmd_kill(const char *args) {
    while (*args == ' ') args++;
    if (*args == '\0') {
        k_set_color(0x0E, 0x00);
        k_print("Usage: kill <tid> [signal]\n");
        k_set_color(0x0F, 0x00);
        k_print("Signals: TERM(1) KILL(2) INT(3) STOP(4) CONT(5) USR1(6) USR2(7)\n");
        return;
    }

    /* Parse TID */
    int tid = 0;
    const char *p = args;
    while (*p >= '0' && *p <= '9') {
        tid = tid * 10 + (*p - '0');
        p++;
    }
    if (p == args) {
        k_print("kill: invalid TID\n");
        return;
    }

    if (tid == 0) {
        k_set_color(0x0C, 0x00);
        k_print("kill: cannot kill idle task (tid 0)\n");
        k_set_color(0x0F, 0x00);
        return;
    }

    /* Parse optional signal (default: SIG_TERM) */
    int signum = SIG_TERM;
    while (*p == ' ') p++;
    if (*p != '\0') {
        /* Named signals */
        if (k_strcmp(p, "TERM") == 0 || k_strcmp(p, "term") == 0) signum = SIG_TERM;
        else if (k_strcmp(p, "KILL") == 0 || k_strcmp(p, "kill") == 0) signum = SIG_KILL;
        else if (k_strcmp(p, "INT") == 0 || k_strcmp(p, "int") == 0) signum = SIG_INT;
        else if (k_strcmp(p, "STOP") == 0 || k_strcmp(p, "stop") == 0) signum = SIG_STOP;
        else if (k_strcmp(p, "CONT") == 0 || k_strcmp(p, "cont") == 0) signum = SIG_CONT;
        else if (k_strcmp(p, "USR1") == 0 || k_strcmp(p, "usr1") == 0) signum = SIG_USR1;
        else if (k_strcmp(p, "USR2") == 0 || k_strcmp(p, "usr2") == 0) signum = SIG_USR2;
        else if (k_strcmp(p, "ALARM") == 0 || k_strcmp(p, "alarm") == 0) signum = SIG_ALARM;
        else if (*p >= '1' && *p <= '9') {
            signum = 0;
            while (*p >= '0' && *p <= '9') { signum = signum * 10 + (*p - '0'); p++; }
            if (signum <= 0 || signum >= SIG_MAX) {
                k_set_color(0x0C, 0x00);
                k_print("kill: invalid signal number\n");
                k_set_color(0x0F, 0x00);
                return;
            }
        } else {
            k_set_color(0x0C, 0x00);
            k_print("kill: unknown signal '");
            k_print(p);
            k_print("'\n");
            k_set_color(0x0F, 0x00);
            return;
        }
    }

    static const char *sig_display[] = {
        "NONE", "TERM", "KILL", "INT", "STOP", "CONT",
        "USR1", "USR2", "ALARM", "CHILD"
    };

    int rc = sched_signal(tid, signum);
    if (rc == 0) {
        k_set_color(0x0A, 0x00);
        k_print("Sent SIG_");
        k_print((signum < SIG_MAX) ? sig_display[signum] : "???");
        k_print(" to task ");
        char nbuf[16];
        uint_to_str((uint64_t)tid, nbuf, sizeof(nbuf));
        k_print(nbuf);
        k_putc('\n');
        k_set_color(0x0F, 0x00);
        dmesg_add("[kill] signal sent");
    } else {
        k_set_color(0x0C, 0x00);
        k_print("kill: no such task (tid ");
        char nbuf[16];
        uint_to_str((uint64_t)tid, nbuf, sizeof(nbuf));
        k_print(nbuf);
        k_print(")\n");
        k_set_color(0x0F, 0x00);
    }
}

/* ── v2.3: New shell commands ─────────────────────────────────────────── */

static void cmd_top(void) {
    /* Display running tasks with resource info (simplified top) */
    int ready = 0, blocked = 0, sleeping = 0, total = 0;
    sched_stats(&ready, &blocked, &sleeping, &total);

    char nbuf[24];
    k_set_color(0x0E, 0x00);
    k_print("Tasks: ");
    uint_to_str((uint64_t)total, nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print(" total, ");
    uint_to_str((uint64_t)ready, nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print(" ready, ");
    uint_to_str((uint64_t)sleeping, nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print(" sleeping, ");
    uint_to_str((uint64_t)blocked, nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print(" blocked\n");
    k_set_color(0x0F, 0x00);

    /* Uptime */
    uint64_t ms = tick_count * 10;
    uint64_t secs = ms / 1000;
    uint64_t mins = secs / 60;
    k_print("Uptime: ");
    uint_to_str(mins, nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print("m ");
    uint_to_str(secs % 60, nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print("s\n\n");

    /* Task table header */
    k_set_color(0x0B, 0x00);
    k_print("  TID  STATE      PRIO  NAME\n");
    k_set_color(0x07, 0x00);
    k_print("  ---  ---------  ----  ----\n");
    k_set_color(0x0F, 0x00);

    static const char *top_state[] = {
        "free", "ready", "RUNNING", "blocked", "sleeping", "dead"
    };

    for (int i = 0; i < 32; i++) {
        const SchedTask *t = sched_get_task(i);
        if (!t) continue;

        k_print("  ");
        uint_to_str((uint64_t)t->tid, nbuf, sizeof(nbuf));
        int nlen = k_strlen(nbuf);
        for (int s = nlen; s < 3; s++) k_putc(' ');
        k_print(nbuf);
        k_print("  ");

        int st = t->state;
        if (st == 2)      k_set_color(0x0A, 0x00);
        else if (st == 1)  k_set_color(0x0B, 0x00);
        else if (st == 4)  k_set_color(0x0D, 0x00);
        else if (st == 3)  k_set_color(0x0C, 0x00);
        else if (st == 5)  k_set_color(0x08, 0x00);
        const char *sname = (st >= 0 && st <= 5) ? top_state[st] : "???";
        k_print(sname);
        k_set_color(0x0F, 0x00);
        nlen = k_strlen(sname);
        for (int s = nlen; s < 11; s++) k_putc(' ');

        uint_to_str((uint64_t)t->priority, nbuf, sizeof(nbuf));
        k_print(nbuf);
        nlen = k_strlen(nbuf);
        for (int s = nlen; s < 6; s++) k_putc(' ');

        k_print(t->name);
        k_putc('\n');
    }
}

static void cmd_df(void) {
    /* Display filesystem usage (ramfs) */
    k_set_color(0x0E, 0x00);
    k_print("Filesystem        Type   Mounted on\n");
    k_set_color(0x0F, 0x00);

    k_print("ramfs             ramfs  /\n");
    k_print("procfs            proc   /proc\n");
    k_print("devfs             dev    /dev\n");

    /* Show ramfs root listing count as a proxy for usage */
    char lbuf[1024];
    int root = ramfs_root();
    int n = ramfs_list(root, lbuf, sizeof(lbuf));
    char nbuf[16];

    k_set_color(0x0B, 0x00);
    k_print("\nramfs: ");
    uint_to_str((uint64_t)(n > 0 ? n : 0), nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print(" entries in /\n");
    k_set_color(0x0F, 0x00);
}

static void cmd_id(void) {
    /* Display user identity */
    k_set_color(0x0A, 0x00);
    k_print("uid=0(root) gid=0(root) groups=0(root)\n");
    k_set_color(0x0F, 0x00);
}

static void cmd_seq(const char *args) {
    /* Print a sequence of numbers */
    while (*args == ' ') args++;
    int start = 1, end = 10;
    if (*args) {
        end = 0;
        while (*args >= '0' && *args <= '9') {
            end = end * 10 + (*args - '0');
            args++;
        }
        while (*args == ' ') args++;
        if (*args >= '0' && *args <= '9') {
            start = end;
            end = 0;
            while (*args >= '0' && *args <= '9') {
                end = end * 10 + (*args - '0');
                args++;
            }
        }
    }
    char nbuf[16];
    for (int i = start; i <= end; i++) {
        uint_to_str((uint64_t)i, nbuf, sizeof(nbuf));
        k_print(nbuf);
        k_putc('\n');
    }
}

static void cmd_tr(const char *args) {
    /* Simple character transliteration: tr <from> <to> */
    while (*args == ' ') args++;
    if (*args == '\0') {
        k_print("Usage: tr <from_char> <to_char>\n");
        return;
    }
    char from_ch = *args++;
    while (*args == ' ') args++;
    char to_ch = *args ? *args : '_';

    /* Apply to capture buffer if available, otherwise just report */
    k_set_color(0x0A, 0x00);
    k_print("tr: translate '");
    k_putc(from_ch);
    k_print("' -> '");
    k_putc(to_ch);
    k_print("'\n");
    k_set_color(0x0F, 0x00);
}

static void cmd_rev(const char *args) {
    /* Reverse a string */
    while (*args == ' ') args++;
    if (*args == '\0') {
        k_print("Usage: rev <string>\n");
        return;
    }
    int slen = 0;
    for (const char *p = args; *p; p++) slen++;
    for (int i = slen - 1; i >= 0; i--) {
        k_putc(args[i]);
    }
    k_putc('\n');
}

static void cmd_factor(const char *args) {
    /* Prime factorization of a number */
    while (*args == ' ') args++;
    unsigned long n = 0;
    while (*args >= '0' && *args <= '9') {
        n = n * 10 + (*args - '0');
        args++;
    }
    if (n < 2) {
        k_print("Usage: factor <number>\n");
        return;
    }
    char nbuf[24];
    uint_to_str(n, nbuf, sizeof(nbuf));
    k_print(nbuf);
    k_print(": ");

    unsigned long orig = n;
    (void)orig;
    for (unsigned long d = 2; d * d <= n; d++) {
        while (n % d == 0) {
            uint_to_str(d, nbuf, sizeof(nbuf));
            k_print(nbuf);
            n /= d;
            if (n > 1) k_putc(' ');
        }
    }
    if (n > 1) {
        uint_to_str(n, nbuf, sizeof(nbuf));
        k_print(nbuf);
    }
    k_putc('\n');
}

/* ── Output capture buffer for pipe/redirect ──────────────────────────── */

static char capture_buf[4096];
static int  capture_pos  = 0;
/* capturing is forward-declared near k_putc */

/* When capturing is on, k_putc also writes to capture_buf */
static void capture_putc(char c) {
    if (capturing && capture_pos < (int)sizeof(capture_buf) - 1) {
        capture_buf[capture_pos++] = c;
        capture_buf[capture_pos]   = '\0';
    }
}

static void capture_start(void) {
    capture_pos = 0;
    capture_buf[0] = '\0';
    capturing = 1;
}

static void capture_stop(void) {
    capturing = 0;
}

/* ── String search helper ─────────────────────────────────────────────── */

/* Find first unquoted occurrence of ch in s. Returns pointer or NULL. */
static char *find_unquoted(char *s, char ch) {
    int in_quote = 0;
    while (*s) {
        if (*s == '"') in_quote = !in_quote;
        if (!in_quote && *s == ch) return s;
        s++;
    }
    return (char*)0;
}

/* ── Core command dispatch (no pipe/redirect handling) ────────────────── */

static void shell_exec_simple(char *line) {
    /* Trim leading spaces */
    while (*line == ' ') line++;
    if (*line == '\0') return;

    /* Log to serial */
    serial_puts("[shell] > ");
    serial_puts(line);
    serial_putc('\n');

    hist_push(line);
    hist_pos = hist_count;

    if (k_strcmp(line, "help") == 0)                   cmd_help();
    else if (k_strcmp(line, "clear") == 0)              cmd_clear();
    else if (k_strcmp(line, "uname") == 0)              cmd_uname();
    else if (k_strcmp(line, "uptime") == 0)             cmd_uptime();
    else if (k_strcmp(line, "free") == 0)               cmd_free();
    else if (k_strcmp(line, "version") == 0)            cmd_version();
    else if (k_strcmp(line, "cpuid") == 0)              cmd_cpuid_info();
    else if (k_strcmp(line, "ticks") == 0)              cmd_ticks();
    else if (k_strcmp(line, "heap") == 0)               cmd_heap();
    else if (k_strcmp(line, "history") == 0)            cmd_history_show();
    else if (k_strcmp(line, "reboot") == 0)             cmd_reboot();
    else if (k_strcmp(line, "halt") == 0)               cmd_halt();
    else if (k_strcmp(line, "gui") == 0)                cmd_gui();
    else if (k_strcmp(line, "ifconfig") == 0)           cmd_ifconfig();
    else if (k_strcmp(line, "netstat") == 0)            cmd_netstat();
    else if (k_strcmp(line, "arp") == 0)                cmd_arp();
    else if (k_strcmp(line, "dhcp") == 0)               cmd_dhcp();
    else if (k_strncmp(line, "nslookup ", 9) == 0)     cmd_nslookup(line + 9);
    else if (k_strcmp(line, "nslookup") == 0)           cmd_nslookup("");
    else if (k_strncmp(line, "dns ", 4) == 0)          cmd_dns_cache(line + 4);
    else if (k_strcmp(line, "dns") == 0)                cmd_dns_cache("");
    else if (k_strncmp(line, "tcp ", 4) == 0)          cmd_tcp(line + 4);
    else if (k_strcmp(line, "tcp") == 0)                cmd_tcp("");
    else if (k_strncmp(line, "wget ", 5) == 0)         cmd_wget(line + 5);
    else if (k_strcmp(line, "wget") == 0)               cmd_wget("");
    else if (k_strcmp(line, "whoami") == 0)             cmd_whoami();
    else if (k_strcmp(line, "hostname") == 0)           cmd_hostname();
    else if (k_strcmp(line, "date") == 0)               cmd_date();
    else if (k_strcmp(line, "ps") == 0)                 cmd_ps();
    else if (k_strcmp(line, "sysinfo") == 0)            cmd_sysinfo();
    else if (k_strcmp(line, "cal") == 0)                cmd_cal();
    else if (k_strcmp(line, "pwd") == 0)                cmd_pwd();
    else if (k_strcmp(line, "env") == 0)                cmd_env();
    else if (k_strcmp(line, "dmesg") == 0)              cmd_dmesg();
    else if (k_strncmp(line, "ping", 4) == 0)          cmd_ping(line + 4);
    else if (k_strncmp(line, "echo ", 5) == 0)         cmd_echo(line + 5);
    else if (k_strncmp(line, "write ", 6) == 0)        cmd_write(line + 6);
    else if (k_strncmp(line, "alloc ", 6) == 0)        cmd_alloc(line + 6);
    else if (k_strncmp(line, "cd ", 3) == 0)           cmd_cd(line + 3);
    else if (k_strcmp(line, "cd") == 0)                 cmd_cd("");
    else if (k_strncmp(line, "rm ", 3) == 0)           cmd_rm(line + 3);
    else if (k_strncmp(line, "sleep ", 6) == 0)        cmd_sleep(line + 6);
    else if (k_strncmp(line, "export ", 7) == 0)       cmd_export(line + 7);
    else if (k_strncmp(line, "unset ", 6) == 0)        cmd_unset(line + 6);
    else if (k_strcmp(line, "unset") == 0)              cmd_unset("");
    else if (k_strncmp(line, "alias ", 6) == 0)        cmd_alias(line + 6);
    else if (k_strcmp(line, "alias") == 0)              cmd_alias("");
    else if (k_strncmp(line, "unalias ", 8) == 0)      cmd_unalias(line + 8);
    else if (k_strcmp(line, "unalias") == 0)            cmd_unalias("");
    else if (k_strncmp(line, "head ", 5) == 0)         cmd_head(line + 5);
    else if (k_strncmp(line, "tail ", 5) == 0)         cmd_tail(line + 5);
    else if (k_strncmp(line, "wc ", 3) == 0)           cmd_wc(line + 3);
    else if (k_strncmp(line, "stat ", 5) == 0)         cmd_stat(line + 5);
    else if (k_strncmp(line, "xxd ", 4) == 0)          cmd_xxd(line + 4);
    else if (k_strncmp(line, "kill ", 5) == 0)         cmd_kill(line + 5);
    else if (k_strncmp(line, "spawn ", 6) == 0)       cmd_spawn(line + 6);
    else if (k_strcmp(line, "spawn") == 0)             cmd_spawn("");
    else if (k_strncmp(line, "ls", 2) == 0) {
        char buf[1024];
        const char *path = line + 2;
        while (*path == ' ') path++;
        int dir;
        if (*path) {
            dir = ramfs_resolve_path(path);
        } else {
            dir = ramfs_resolve_path(cwd);
            if (dir < 0) dir = ramfs_root();
        }
        if (dir >= 0 && ramfs_list(dir, buf, 1024) == 0) {
            k_print(buf);
        } else {
            k_set_color(0x0C, 0x00);
            k_print("ls: no such directory\n");
            k_set_color(0x0F, 0x00);
        }
    }
    else if (k_strncmp(line, "cat ", 4) == 0) {
        const char *fname = line + 4;
        while (*fname == ' ') fname++;
        /* Auto-refresh /proc entries before reading */
        if (k_strncmp(fname, "/proc/", 6) == 0) {
            procfs_refresh_file(fname);
        }
        /* Auto-refresh /dev entries before reading */
        if (k_strncmp(fname, "/dev/", 5) == 0) {
            devfs_refresh_file(fname);
        }
        int node = ramfs_resolve_path(fname);
        if (node >= 0) {
            char buf[2048];
            int n = ramfs_read(node, buf, 2048);
            if (n > 0) k_print(buf);
            k_putc('\n');
        } else {
            k_set_color(0x0C, 0x00);
            k_print("cat: "); k_print(fname); k_print(": not found\n");
            k_set_color(0x0F, 0x00);
        }
    }
    else if (k_strncmp(line, "touch ", 6) == 0) {
        const char *fname = line + 6;
        while (*fname == ' ') fname++;
        int home = ramfs_resolve_path("/home");
        if (home >= 0) ramfs_create(home, fname);
    }
    else if (k_strncmp(line, "mkdir ", 6) == 0) {
        const char *dname = line + 6;
        while (*dname == ' ') dname++;
        int home = ramfs_resolve_path("/home");
        if (home >= 0) ramfs_mkdir(home, dname);
    }
    /* ── Development tools ─────────────────────────────────────────── */
    else if (k_strncmp(line, "ltlc ", 5) == 0) { cmd_ltlc(line + 5); }
    else if (k_strcmp(line, "ltlc") == 0)       { cmd_ltlc(""); }
    else if (k_strncmp(line, "chat ", 5) == 0)  { cmd_chat(line + 5); }
    else if (k_strcmp(line, "chat") == 0)        { cmd_chat(""); }
    else if (k_strncmp(line, "edit ", 5) == 0)  { cmd_edit(line + 5); }
    else if (k_strcmp(line, "edit") == 0)        { cmd_edit(""); }
    else if (k_strncmp(line, "pkg ", 4) == 0)   { cmd_pkg(line + 4); }
    else if (k_strcmp(line, "pkg") == 0)         { cmd_pkg(""); }
    /* ── v2.3 utilities ──────────────────────────────────────────── */
    else if (k_strcmp(line, "top") == 0)          { cmd_top(); }
    else if (k_strcmp(line, "df") == 0)           { cmd_df(); }
    else if (k_strcmp(line, "id") == 0)           { cmd_id(); }
    else if (k_strncmp(line, "seq ", 4) == 0)    { cmd_seq(line + 4); }
    else if (k_strcmp(line, "seq") == 0)          { cmd_seq(""); }
    else if (k_strncmp(line, "tr ", 3) == 0)     { cmd_tr(line + 3); }
    else if (k_strncmp(line, "rev ", 4) == 0)    { cmd_rev(line + 4); }
    else if (k_strncmp(line, "factor ", 7) == 0) { cmd_factor(line + 7); }
    else {
        k_set_color(0x0C, 0x00);  /* red */
        k_print("ltlsh: command not found: ");
        k_print(line);
        k_putc('\n');
        k_set_color(0x07, 0x00);  /* gray */
        k_print("Type 'help' for available commands.\n");
        k_set_color(0x0F, 0x00);
    }
}

/* ── shell_exec: pipe (|) and redirect (>, >>) wrapper ────────────────── */

/* Helper: trim leading/trailing spaces in-place, return trimmed pointer */
static char *trim_inplace(char *s) {
    while (*s == ' ') s++;
    int len = k_strlen(s);
    while (len > 0 && s[len - 1] == ' ') { s[--len] = '\0'; }
    return s;
}

/* Helper: resolve/create a file for redirect output.
   Returns ramfs node index, or -1 on failure. */
static int redirect_open_file(const char *path) {
    int idx = ramfs_resolve_path(path);
    if (idx >= 0) return idx;

    /* File doesn't exist — create it under /home */
    int home = ramfs_resolve_path("/home");
    if (home < 0) return -1;
    return ramfs_create(home, path);
}

static void shell_exec(char *line) {
    /* Trim leading spaces */
    while (*line == ' ') line++;
    if (*line == '\0') return;

    /* ── Environment variable expansion ($VAR, ${VAR}) ──── */
    static char expanded_buf[CMD_BUF_SIZE];
    int has_dollar = 0;
    for (int i = 0; line[i]; i++) { if (line[i] == '$') { has_dollar = 1; break; } }
    if (has_dollar) {
        env_expand(line, expanded_buf, CMD_BUF_SIZE);
        line = expanded_buf;
    }

    /* ── Alias expansion (first word only) ─────────────── */
    const char *aliased = alias_expand(line);
    if (aliased != line) {
        /* Copy back into a mutable buffer — alias_expand returns static buf */
        static char alias_copy[CMD_BUF_SIZE];
        int i = 0;
        while (aliased[i] && i < CMD_BUF_SIZE - 1) { alias_copy[i] = aliased[i]; i++; }
        alias_copy[i] = '\0';
        line = alias_copy;
    }

    /* ── Bang expansion: !N recalls history entry N ─────── */
    if (line[0] == '!' && line[1] >= '0' && line[1] <= '9') {
        int n = 0;
        const char *p = line + 1;
        while (*p >= '0' && *p <= '9') { n = n * 10 + (*p - '0'); p++; }
        if (n < hist_count) {
            int idx = n % MAX_HISTORY;
            static char bang_buf[CMD_BUF_SIZE];
            int i = 0;
            while (history[idx][i] && i < CMD_BUF_SIZE - 1) { bang_buf[i] = history[idx][i]; i++; }
            bang_buf[i] = '\0';
            k_set_color(0x07, 0x00);
            k_print(bang_buf);
            k_putc('\n');
            k_set_color(0x0F, 0x00);
            line = bang_buf;
        } else {
            k_print("ltlsh: !"); k_print(line + 1); k_print(": event not found\n");
            return;
        }
    }

    /* ── Check for pipe: cmd1 | cmd2 ────────────────────── */
    char *pipe_pos = find_unquoted(line, '|');
    if (pipe_pos) {
        *pipe_pos = '\0';
        char *left  = trim_inplace(line);
        char *right = trim_inplace(pipe_pos + 1);

        /* Capture output of left command */
        capture_start();
        shell_exec_simple(left);
        capture_stop();

        /* For the pipe, we print the captured output.
           The right command sees it via a global "pipe input" buffer.
           For now, pipe support means: left output is available in capture_buf,
           and we execute right normally — useful for e.g. "ls | grep pattern" */
        /* Simple approach: if right cmd is "grep <pattern>", filter capture_buf */
        if (k_strncmp(right, "grep ", 5) == 0) {
            const char *pattern = right + 5;
            while (*pattern == ' ') pattern++;
            /* Print lines from capture_buf that contain pattern */
            char linebuf[256];
            int lpos = 0;
            for (int i = 0; i <= capture_pos; i++) {
                if (i == capture_pos || capture_buf[i] == '\n') {
                    linebuf[lpos] = '\0';
                    if (lpos > 0) {
                        /* Simple substring search */
                        int found = 0;
                        for (int j = 0; j <= lpos - k_strlen(pattern); j++) {
                            if (k_strncmp(linebuf + j, pattern, k_strlen(pattern)) == 0) {
                                found = 1;
                                break;
                            }
                        }
                        if (found) {
                            k_print(linebuf);
                            k_putc('\n');
                        }
                    }
                    lpos = 0;
                } else if (lpos < 255) {
                    linebuf[lpos++] = capture_buf[i];
                }
            }
        }
        else if (k_strncmp(right, "wc", 2) == 0) {
            /* wc — count lines, words, bytes of piped input */
            int lines = 0, words = 0, bytes = capture_pos;
            int in_word = 0;
            for (int i = 0; i < capture_pos; i++) {
                if (capture_buf[i] == '\n') lines++;
                if (capture_buf[i] == ' ' || capture_buf[i] == '\n' || capture_buf[i] == '\t') {
                    in_word = 0;
                } else if (!in_word) {
                    in_word = 1;
                    words++;
                }
            }
            char nbuf[16];
            k_print("  ");
            uint_to_str(lines, nbuf, sizeof(nbuf));
            k_print(nbuf);
            k_print("  ");
            uint_to_str(words, nbuf, sizeof(nbuf));
            k_print(nbuf);
            k_print("  ");
            uint_to_str(bytes, nbuf, sizeof(nbuf));
            k_print(nbuf);
            k_putc('\n');
        }
        else if (k_strncmp(right, "head", 4) == 0) {
            /* head — show first N lines of piped input (default 10) */
            int n = 10;
            const char *arg = right + 4;
            while (*arg == ' ') arg++;
            if (*arg == '-') {
                arg++;
                n = 0;
                while (*arg >= '0' && *arg <= '9') { n = n * 10 + (*arg - '0'); arg++; }
            }
            int lines = 0;
            for (int i = 0; i < capture_pos && lines < n; i++) {
                k_putc(capture_buf[i]);
                if (capture_buf[i] == '\n') lines++;
            }
        }
        else if (k_strncmp(right, "tail", 4) == 0) {
            /* tail — show last N lines of piped input (default 10) */
            int n = 10;
            const char *arg = right + 4;
            while (*arg == ' ') arg++;
            if (*arg == '-') {
                arg++;
                n = 0;
                while (*arg >= '0' && *arg <= '9') { n = n * 10 + (*arg - '0'); arg++; }
            }
            /* Count total lines */
            int total = 0;
            for (int i = 0; i < capture_pos; i++)
                if (capture_buf[i] == '\n') total++;
            int skip = total - n;
            if (skip < 0) skip = 0;
            int lines = 0;
            for (int i = 0; i < capture_pos; i++) {
                if (lines >= skip) k_putc(capture_buf[i]);
                if (capture_buf[i] == '\n') lines++;
            }
        }
        else {
            /* Unknown pipe target — just dump the captured output and run right */
            for (int i = 0; i < capture_pos; i++) k_putc(capture_buf[i]);
            shell_exec_simple(right);
        }
        return;
    }

    /* ── Check for redirect append: cmd >> file ──────── */
    char *redir_append = find_unquoted(line, '>');
    if (redir_append && *(redir_append + 1) == '>') {
        *redir_append = '\0';
        char *left = trim_inplace(line);
        char *fname = trim_inplace(redir_append + 2);

        capture_start();
        shell_exec_simple(left);
        capture_stop();

        int node = redirect_open_file(fname);
        if (node >= 0) {
            ramfs_append(node, capture_buf, capture_pos);
            serial_puts("[redirect] >> ");
            serial_puts(fname);
            serial_puts(" (");
            char nbuf[16];
            uint_to_str(capture_pos, nbuf, sizeof(nbuf));
            serial_puts(nbuf);
            serial_puts(" bytes)\n");
        } else {
            k_set_color(0x0C, 0x00);
            k_print("ltlsh: cannot open file for redirect: ");
            k_print(fname);
            k_putc('\n');
            k_set_color(0x0F, 0x00);
        }
        return;
    }

    /* ── Check for redirect overwrite: cmd > file ────── */
    char *redir_pos = find_unquoted(line, '>');
    if (redir_pos) {
        *redir_pos = '\0';
        char *left = trim_inplace(line);
        char *fname = trim_inplace(redir_pos + 1);

        capture_start();
        shell_exec_simple(left);
        capture_stop();

        int node = redirect_open_file(fname);
        if (node >= 0) {
            ramfs_write(node, capture_buf, capture_pos);
            serial_puts("[redirect] > ");
            serial_puts(fname);
            serial_puts(" (");
            char nbuf[16];
            uint_to_str(capture_pos, nbuf, sizeof(nbuf));
            serial_puts(nbuf);
            serial_puts(" bytes)\n");
        } else {
            k_set_color(0x0C, 0x00);
            k_print("ltlsh: cannot open file for redirect: ");
            k_print(fname);
            k_putc('\n');
            k_set_color(0x0F, 0x00);
        }
        return;
    }

    /* ── No pipe/redirect — plain command ────────────── */
    shell_exec_simple(line);
}

/* ── Shell: VGA cursor ────────────────────────────────────────────────── */

static void vga_update_cursor(void) {
    uint16_t pos = cur_y * VGA_W + cur_x;
    outb(0x3D4, 14);
    outb(0x3D5, (uint8_t)(pos >> 8));
    outb(0x3D4, 15);
    outb(0x3D5, (uint8_t)(pos & 0xFF));
}

static void vga_enable_cursor(void) {
    outb(0x3D4, 0x0A);
    outb(0x3D5, (inb(0x3D5) & 0xC0) | 13);  /* cursor start line */
    outb(0x3D4, 0x0B);
    outb(0x3D5, (inb(0x3D5) & 0xE0) | 15);  /* cursor end line   */
}

/* ── Shell: backspace ─────────────────────────────────────────────────── */

static void k_backspace(void) {
    if (cur_x > 0) {
        cur_x--;
    } else if (cur_y > 0) {
        cur_y--;
        cur_x = VGA_W - 1;
    }
    VGA_BUF[cur_y * VGA_W + cur_x] = (uint16_t)' ' | ((uint16_t)cur_color << 8);
}

/* ── Shell: cursor-aware line redraw ──────────────────────────────────── */

/* Redraw the command line from the cursor position onward */
static void redraw_from_cursor(int prompt_x, int prompt_y) {
    /* Calculate the absolute screen position for cmd_cursor */
    int base_x = prompt_x;
    int base_y = prompt_y;
    /* Position cursor at cmd_cursor */
    int draw_x = base_x + cmd_cursor;
    int draw_y = base_y;
    while (draw_x >= VGA_W) { draw_x -= VGA_W; draw_y++; }

    /* Redraw from cmd_cursor to cmd_len */
    cur_x = draw_x;
    cur_y = draw_y;
    for (int i = cmd_cursor; i < cmd_len; i++) {
        k_putc(cmd_buf[i]);
    }
    /* Clear one extra char (in case of deletion) */
    k_putc(' ');

    /* Move cursor back to cmd_cursor position */
    cur_x = base_x + cmd_cursor;
    cur_y = base_y;
    while (cur_x >= VGA_W) { cur_x -= VGA_W; cur_y++; }
}

/* ── Shell: tab completion ────────────────────────────────────────────── */

static const char *all_commands[] = {
    "alias", "alloc", "arp", "cal", "cat", "cd", "clear", "cpuid", "date", "dhcp",
    "dmesg", "dns", "echo", "env", "export", "free", "gui", "halt", "head", "heap",
    "help", "history", "hostname", "ifconfig", "kill", "ls", "mkdir", "netstat",
    "nslookup", "ping", "ps", "pwd", "reboot", "rm", "sleep", "spawn", "stat", "sysinfo",
    "tail", "tcp", "ticks", "touch", "unalias", "uname", "unset", "uptime", "version",
    "wc", "wget", "whoami", "write", "xxd",
    (const char *)0
};

static void shell_tab_complete(void) {
    if (cmd_len == 0) return;

    /* Find matching commands */
    const char *matches[10];
    int match_count = 0;

    for (int i = 0; all_commands[i]; i++) {
        if (k_strncmp(cmd_buf, all_commands[i], cmd_len) == 0) {
            if (match_count < 10) matches[match_count++] = all_commands[i];
        }
    }

    if (match_count == 1) {
        /* Single match — complete it */
        const char *m = matches[0];
        int mlen = k_strlen(m);
        for (int i = cmd_len; i < mlen && i < CMD_BUF_SIZE - 2; i++) {
            cmd_buf[i] = m[i];
            k_putc(m[i]);
        }
        cmd_buf[mlen] = ' ';
        cmd_len = mlen + 1;
        cmd_cursor = cmd_len;
        k_putc(' ');
        vga_update_cursor();
    } else if (match_count > 1) {
        /* Multiple matches — show them */
        k_putc('\n');
        for (int i = 0; i < match_count; i++) {
            k_set_color(0x0B, 0x00);
            k_print(matches[i]);
            k_set_color(0x0F, 0x00);
            k_print("  ");
        }
        k_putc('\n');
        shell_prompt();
        /* Redraw current input */
        for (int i = 0; i < cmd_len; i++) k_putc(cmd_buf[i]);
        cmd_cursor = cmd_len;
        vga_update_cursor();
    }
}

/* ── Shell: main loop ─────────────────────────────────────────────────── */

static void shell_main(void) {
    serial_puts("[shell] ltlsh 0.3.0 interactive shell ready\n");

    /* Initialize environment */
    env_init();
    alias_init();

    vga_enable_cursor();
    shell_prompt();
    vga_update_cursor();

    cmd_len = 0;
    cmd_cursor = 0;
    uint8_t prev_sc = 0;
    int shift_held = 0;

    /* Remember prompt position for cursor-aware editing */
    int prompt_end_x = cur_x;
    int prompt_end_y = cur_y;

    while (1) {
        if (last_scancode != prev_sc && last_scancode != 0) {
            uint8_t sc = last_scancode;
            prev_sc = sc;

            /* Track shift state */
            if (sc == 0x2A || sc == 0x36) { shift_held = 1; continue; }
            if (sc == 0xAA || sc == 0xB6) { shift_held = 0; continue; }

            /* Only key-down events (bit 7 clear) */
            if (sc & 0x80) continue;

            if (sc == 0x48) {
                /* Up arrow — history previous */
                if (hist_pos > 0 && hist_count > 0) {
                    /* Erase current line on screen */
                    cur_x = prompt_end_x; cur_y = prompt_end_y;
                    for (int i = 0; i < cmd_len; i++) k_putc(' ');
                    cur_x = prompt_end_x; cur_y = prompt_end_y;
                    hist_pos--;
                    int idx = hist_pos % MAX_HISTORY;
                    int len = k_strlen(history[idx]);
                    for (int i = 0; i < len && i < CMD_BUF_SIZE - 1; i++) {
                        cmd_buf[i] = history[idx][i];
                        k_putc(history[idx][i]);
                    }
                    cmd_len = len;
                    cmd_cursor = len;
                    vga_update_cursor();
                }
                continue;
            }

            if (sc == 0x50) {
                /* Down arrow — history next */
                cur_x = prompt_end_x; cur_y = prompt_end_y;
                for (int i = 0; i < cmd_len; i++) k_putc(' ');
                cur_x = prompt_end_x; cur_y = prompt_end_y;
                if (hist_pos < hist_count - 1) {
                    hist_pos++;
                    int idx = hist_pos % MAX_HISTORY;
                    int len = k_strlen(history[idx]);
                    for (int i = 0; i < len && i < CMD_BUF_SIZE - 1; i++) {
                        cmd_buf[i] = history[idx][i];
                        k_putc(history[idx][i]);
                    }
                    cmd_len = len;
                    cmd_cursor = len;
                } else {
                    hist_pos = hist_count;
                    cmd_len = 0;
                    cmd_cursor = 0;
                }
                vga_update_cursor();
                continue;
            }

            if (sc == 0x4B) {
                /* Left arrow — move cursor left */
                if (cmd_cursor > 0) {
                    cmd_cursor--;
                    if (cur_x > 0) { cur_x--; }
                    else if (cur_y > 0) { cur_y--; cur_x = VGA_W - 1; }
                    vga_update_cursor();
                }
                continue;
            }

            if (sc == 0x4D) {
                /* Right arrow — move cursor right */
                if (cmd_cursor < cmd_len) {
                    cmd_cursor++;
                    cur_x++;
                    if (cur_x >= VGA_W) { cur_x = 0; cur_y++; }
                    vga_update_cursor();
                }
                continue;
            }

            if (sc == 0x47) {
                /* Home key — move to start of line */
                cmd_cursor = 0;
                cur_x = prompt_end_x;
                cur_y = prompt_end_y;
                vga_update_cursor();
                continue;
            }

            if (sc == 0x4F) {
                /* End key — move to end of line */
                cmd_cursor = cmd_len;
                cur_x = prompt_end_x + cmd_len;
                cur_y = prompt_end_y;
                while (cur_x >= VGA_W) { cur_x -= VGA_W; cur_y++; }
                vga_update_cursor();
                continue;
            }

            if (sc == 0x53) {
                /* Delete key — delete char at cursor */
                if (cmd_cursor < cmd_len) {
                    for (int i = cmd_cursor; i < cmd_len - 1; i++)
                        cmd_buf[i] = cmd_buf[i + 1];
                    cmd_len--;
                    redraw_from_cursor(prompt_end_x, prompt_end_y);
                    vga_update_cursor();
                }
                continue;
            }

            if (sc == 0x0F) {
                /* Tab — auto-complete */
                shell_tab_complete();
                continue;
            }

            if (sc < 128) {
                char c = scancode_ascii[sc];

                /* Handle shift for uppercase and symbols */
                if (shift_held && c >= 'a' && c <= 'z') c -= 32;

                if (c == '\n') {
                    /* Execute command */
                    cmd_buf[cmd_len] = '\0';
                    k_putc('\n');
                    shell_exec(cmd_buf);
                    cmd_len = 0;
                    cmd_cursor = 0;
                    shell_prompt();
                    prompt_end_x = cur_x;
                    prompt_end_y = cur_y;
                    vga_update_cursor();
                } else if (c == '\b') {
                    /* Backspace — delete char before cursor */
                    if (cmd_cursor > 0) {
                        for (int i = cmd_cursor - 1; i < cmd_len - 1; i++)
                            cmd_buf[i] = cmd_buf[i + 1];
                        cmd_len--;
                        cmd_cursor--;
                        /* Redraw from cursor */
                        if (cur_x > 0) cur_x--; else { cur_y--; cur_x = VGA_W - 1; }
                        redraw_from_cursor(prompt_end_x, prompt_end_y);
                        vga_update_cursor();
                    }
                } else if (c >= ' ' && cmd_len < CMD_BUF_SIZE - 1) {
                    /* Insert character at cursor position */
                    if (cmd_cursor < cmd_len) {
                        /* Shift chars right */
                        for (int i = cmd_len; i > cmd_cursor; i--)
                            cmd_buf[i] = cmd_buf[i - 1];
                    }
                    cmd_buf[cmd_cursor] = c;
                    cmd_len++;
                    cmd_cursor++;

                    if (cmd_cursor == cmd_len) {
                        /* Appending at end — just print the char */
                        k_putc(c);
                        serial_putc(c);
                    } else {
                        /* Inserted in middle — redraw rest of line */
                        k_putc(c);
                        int save_x = cur_x, save_y = cur_y;
                        for (int i = cmd_cursor; i < cmd_len; i++) k_putc(cmd_buf[i]);
                        cur_x = save_x; cur_y = save_y;
                    }
                    vga_update_cursor();
                }
            }
        }
        __asm__ volatile ("hlt");  /* wait for next interrupt */
    }
}

void kernel_main(void) {
    serial_puts("[kernel] LateralusOS kernel_main() entered\n");
    dmesg_add("[kernel] LateralusOS kernel_main() entered");

    /* Initialize environment variables early */
    env_init();
    alias_init();

    /* Phase 1: CPU */
    k_set_color(0x0A, 0x00);  /* green */
    k_print("[cpu]       ");
    k_set_color(0x0F, 0x00);
    k_print("x86_64 long mode active\n");
    serial_puts("[cpu] x86_64 long mode active\n");
    dmesg_add("[cpu] x86_64 long mode active");

    /* Phase 2: IDT + PIC */
    init_idt();
    k_set_color(0x0A, 0x00);
    k_print("[idt]       ");
    k_set_color(0x0F, 0x00);
    k_print("256 vectors, PIC remapped, IRQ 0-1 unmasked\n");
    serial_puts("[idt] IDT loaded, PIC remapped\n");
    dmesg_add("[idt] IDT loaded, PIC remapped");

    /* Phase 3: Memory + heap allocator */
    uint64_t mem = detect_memory();
    heap_init(mem);
    k_set_color(0x0A, 0x00);
    k_print("[memory]    ");
    k_set_color(0x0F, 0x00);
    k_print("4 GB identity-mapped, heap allocator active\n");
    serial_puts("[memory] 4 GB identity-mapped, heap active\n");
    dmesg_add("[memory] 4 GB identity-mapped, heap active");

    /* Phase 4: Timer */
    init_pit();
    k_set_color(0x0A, 0x00);
    k_print("[timer]     ");
    k_set_color(0x0F, 0x00);
    k_print("PIT @ 1000 Hz\n");
    serial_puts("[timer] PIT configured @ 1000 Hz\n");
    dmesg_add("[timer] PIT configured @ 1000 Hz");

    /* Phase 5: Keyboard */
    k_set_color(0x0A, 0x00);
    k_print("[keyboard]  ");
    k_set_color(0x0F, 0x00);
    k_print("PS/2 IRQ1 handler installed\n");
    serial_puts("[keyboard] PS/2 ready\n");
    dmesg_add("[keyboard] PS/2 ready");

    /* Phase 6: VGA */
    k_set_color(0x0A, 0x00);
    k_print("[vga]       ");
    k_set_color(0x0F, 0x00);
    k_print("80x25 text mode active\n");
    serial_puts("[vga] 80x25 text mode\n");
    dmesg_add("[vga] 80x25 text mode");

    /* Phase 6b: Framebuffer + Mouse */
    if (boot_info.fb_available) {
        char fbdim[32];
        k_set_color(0x0A, 0x00);
        k_print("[framebuf]  ");
        k_set_color(0x0F, 0x00);
        uint_to_str(boot_info.fb_width, fbdim, sizeof(fbdim));
        k_print(fbdim); k_print("x");
        uint_to_str(boot_info.fb_height, fbdim, sizeof(fbdim));
        k_print(fbdim); k_print("x");
        uint_to_str(boot_info.fb_bpp, fbdim, sizeof(fbdim));
        k_print(fbdim); k_print(" linear framebuffer at 0x");
        k_print_hex(boot_info.framebuffer_addr);
        k_print("\n");
        serial_puts("[framebuf] Framebuffer available\n");
        dmesg_add("[framebuf] Framebuffer available");

        k_set_color(0x0A, 0x00);
        k_print("[mouse]     ");
        k_set_color(0x0F, 0x00);
        k_print("PS/2 IRQ12 handler installed\n");
        serial_puts("[mouse] PS/2 mouse ready\n");
        dmesg_add("[mouse] PS/2 mouse ready");
    } else {
        k_set_color(0x0E, 0x00);
        k_print("[framebuf]  ");
        k_set_color(0x07, 0x00);
        k_print("Not available (text mode only)\n");
        serial_puts("[framebuf] Not available\n");
        dmesg_add("[framebuf] Not available (text mode)");
    }

    /* Phase 7: Disk (ATA PIO) */
    {
        int ndrives = ata_init();
        k_set_color(0x0A, 0x00);
        k_print("[disk]      ");
        k_set_color(0x0F, 0x00);
        if (ndrives > 0) {
            char nbuf[8];
            uint_to_str((uint64_t)ndrives, nbuf, sizeof(nbuf));
            k_print(nbuf);
            k_print(" ATA drive(s) detected\n");
            for (int d = 0; d < 2; d++) {
                const AtaDriveInfo *info = ata_get_drive(d);
                if (info) {
                    k_print("            ");
                    k_print(d == 0 ? "Master: " : "Slave:  ");
                    k_print(info->model);
                    k_print(" (");
                    char szbuf[16];
                    uint_to_str(info->size_mb, szbuf, sizeof(szbuf));
                    k_print(szbuf);
                    k_print(" MB)\n");
                }
            }
        } else {
            k_print("No ATA drives detected\n");
        }
    }

    /* Phase 8: Syscall dispatch table */
    {
        int nsys = syscall_init();
        char scbuf[8];
        uint_to_str((uint64_t)nsys, scbuf, sizeof(scbuf));
        k_set_color(0x0A, 0x00);
        k_print("[syscall]   ");
        k_set_color(0x0F, 0x00);
        k_print(scbuf);
        k_print(" syscalls registered\n");
        serial_puts("[syscall] table initialized, ");
        serial_puts(scbuf);
        serial_puts(" handlers\n");
        dmesg_add("[syscall] dispatch table initialized");
    }

    /* Phase 8b: Filesystems (ramfs + procfs + devfs) */
    ramfs_init();
    procfs_init();
    devfs_init();
    /* Create standard directories */
    {
        int root = ramfs_root();
        if (root >= 0) {
            ramfs_mkdir(root, "tmp");
            ramfs_mkdir(root, "var");
        }
    }
    k_set_color(0x0A, 0x00);
    k_print("[fs]        ");
    k_set_color(0x0F, 0x00);
    k_print("ramfs + procfs + devfs initialized\n");
    serial_puts("[fs] ramfs + procfs + devfs initialized\n");
    dmesg_add("[fs] ramfs + procfs + devfs initialized");

    /* Phase 9: Network (RTL8139 PCI NIC) */
    {
        int found = net_init();
        ip_init();  /* IPv4/ARP/UDP/ICMP stack */
        k_set_color(0x0A, 0x00);
        k_print("[net]       ");
        k_set_color(0x0F, 0x00);
        if (found) {
            const NetDeviceInfo *ni = net_get_info();
            char mac[18];
            net_mac_str(mac);
            k_print("RTL8139 MAC=");
            k_print(mac);
            k_print("\n");
            /* Try DHCP */
            k_set_color(0x0A, 0x00);
            k_print("[ip]        ");
            k_set_color(0x0F, 0x00);
            if (dhcp_discover()) {
                const NetConfig *nc = ip_get_config();
                char ipstr[16];
                ip_to_str(nc->ip, ipstr);
                k_print("DHCP ");
                k_print(ipstr);
                k_putc('\n');
            } else {
                ip_set_static(IP4(10,0,2,15), IP4(255,255,255,0), IP4(10,0,2,2));
                k_print("static 10.0.2.15\n");
            }
        } else {
            k_print("No NIC detected\n");
        }
        dns_init();  /* DNS resolver (uses UDP) */
        tcp_init();  /* TCP transport layer */
        http_init(); /* HTTP/1.1 client */
    }

    /* Phase 10: IPC */
    k_set_color(0x0A, 0x00);
    k_print("[ipc]       ");
    k_set_color(0x0F, 0x00);
    ipc_init();
    k_print("Message queues ready (16 slots)\n");
    dmesg_add("[ipc] Message queues ready");

    /* Phase 11: Preemptive Scheduler */
    k_set_color(0x0A, 0x00);
    k_print("[scheduler] ");
    k_set_color(0x0F, 0x00);
    sched_init();
    k_print("Preemptive round-robin, 4 priority levels\n");
    dmesg_add("[scheduler] Preemptive round-robin active");

    /* Phase 12: Spawn kernel daemon tasks */
    {
        int tid_net = sched_create("netpoll", task_net_poll, 0, PRIO_HIGH);
        if (tid_net >= 0) {
            k_set_color(0x0A, 0x00);
            k_print("[daemons]   ");
            k_set_color(0x0F, 0x00);
            k_print("netpoll (tid ");
            char nbuf[8]; uint_to_str((uint64_t)tid_net, nbuf, sizeof(nbuf));
            k_print(nbuf);
            k_print(") — network polling at 10 Hz\n");
            dmesg_add("[daemons] netpoll started");
        }
    }

    k_print("\n");

    /* ── Boot complete ───────────────────────────────────────────────── */
    k_set_color(0x0E, 0x00);  /* yellow */
    k_print("════════════════════════════════════════════════════\n");
    k_set_color(0x0A, 0x00);  /* green */
    k_print("  LateralusOS v0.3.0 boot complete!\n");
    k_set_color(0x0E, 0x00);
    k_print("════════════════════════════════════════════════════\n");
    k_set_color(0x0F, 0x00);
    if (boot_info.fb_available) {
        k_set_color(0x0B, 0x00);
        k_print("  Type 'gui' to launch the graphical desktop\n");
        k_set_color(0x0F, 0x00);
    }
    k_print("\n");
    serial_puts("[init] Boot sequence complete\n");
    dmesg_add("[init] Boot sequence complete — entering shell");

    /* ── Auto-GUI boot: check for "gui=auto" in GRUB command line ─────── */
    if (boot_info.fb_available && k_strstr(boot_info.boot_cmd, "gui=auto")) {
        serial_puts("[init] gui=auto detected — launching desktop\n");
        k_set_color(0x0B, 0x00);
        k_print("  Auto-launching graphical desktop...\n\n");
        k_set_color(0x0F, 0x00);
        /* Small delay so user can see the boot messages */
        {
            uint64_t wait_until = tick_count + 500;  /* 500ms */
            while (tick_count < wait_until)
                __asm__ volatile ("hlt");
        }
        cmd_gui();
    }

    /* ── Interactive Shell (ltlsh) ──────────────────────────────────────── */
    shell_main();
}
