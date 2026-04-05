/* =======================================================================
 * LateralusOS — /proc Virtual Filesystem Implementation
 * =======================================================================
 * Generates dynamic text content from live kernel state and writes it
 * into ramfs files under /proc/.  All files are read-only and refreshed
 * on demand before reading.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ======================================================================= */

#include "procfs.h"
#include "ramfs.h"
#include "../kernel/heap.h"
#include "../kernel/sched.h"
#include "../net/ip.h"

/* -- Externals from kernel_stub.c / boot ---------------------------- */
extern volatile uint64_t tick_count;

/* -- Forward declarations for kernel helpers ------------------------ */
/* (defined in kernel_stub.c — we redefine minimal helpers locally) */

static int pf_strlen(const char *s) {
    int n = 0;
    while (s[n]) n++;
    return n;
}

static void pf_strcpy(char *dst, const char *src) {
    while (*src) *dst++ = *src++;
    *dst = '\0';
}

static void pf_strcat(char *dst, const char *src) {
    while (*dst) dst++;
    while (*src) *dst++ = *src++;
    *dst = '\0';
}

static void pf_uint_to_str(uint64_t val, char *buf, int buflen) {
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char tmp[24];
    int i = 0;
    while (val > 0 && i < 22) {
        tmp[i++] = '0' + (val % 10);
        val /= 10;
    }
    int j = 0;
    while (i > 0 && j < buflen - 1) buf[j++] = tmp[--i];
    buf[j] = '\0';
}

static void pf_hex32(uint32_t val, char *buf) {
    const char *hex = "0123456789abcdef";
    for (int i = 7; i >= 0; i--) {
        buf[7 - i] = hex[(val >> (i * 4)) & 0xf];
    }
    buf[8] = '\0';
}

/* Strip leading zeros from hex string (keep at least 1 char) */
static void pf_hex_strip(char *buf) {
    char *p = buf;
    while (*p == '0' && *(p + 1)) p++;
    if (p != buf) {
        char *d = buf;
        while (*p) *d++ = *p++;
        *d = '\0';
    }
}

/* -- /proc directory index in ramfs --------------------------------- */
static int proc_dir_idx = -1;

/* -- Proc file ramfs indices ---------------------------------------- */
static int pf_version_idx  = -1;
static int pf_uptime_idx   = -1;
static int pf_meminfo_idx  = -1;
static int pf_cpuinfo_idx  = -1;
static int pf_loadavg_idx  = -1;
static int pf_tasks_idx    = -1;
static int pf_net_idx      = -1;
static int pf_mounts_idx   = -1;
static int pf_cmdline_idx  = -1;

/* =======================================================================
 * Content Generators
 * ======================================================================= */

static void gen_version(void) {
    char buf[256];
    pf_strcpy(buf, "LateralusOS v0.3.0 (x86_64)\n");
    pf_strcat(buf, "Built with: gcc (freestanding, -O2)\n");
    pf_strcat(buf, "Kernel:     lateralus.elf\n");
    pf_strcat(buf, "Bootloader: GRUB2 Multiboot2\n");
    ramfs_write(pf_version_idx, buf, pf_strlen(buf));
}

static void gen_uptime(void) {
    char buf[128];
    char num[24];
    uint64_t secs = tick_count / 1000;
    uint64_t mins = secs / 60;
    uint64_t hours = mins / 60;
    uint64_t days = hours / 24;

    pf_uint_to_str(secs, num, sizeof(num));
    pf_strcpy(buf, num);
    pf_strcat(buf, " seconds (");

    if (days > 0) {
        pf_uint_to_str(days, num, sizeof(num));
        pf_strcat(buf, num);
        pf_strcat(buf, "d ");
    }
    pf_uint_to_str(hours % 24, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, "h ");
    pf_uint_to_str(mins % 60, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, "m ");
    pf_uint_to_str(secs % 60, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, "s)\n");

    ramfs_write(pf_uptime_idx, buf, pf_strlen(buf));
}

static void gen_meminfo(void) {
    char buf[512];
    char num[24];
    HeapStats hs = heap_get_stats();

    uint64_t total_kb = (hs.end - hs.start) / 1024;
    uint64_t used_kb  = hs.allocated / 1024;
    uint64_t free_kb  = total_kb > used_kb ? total_kb - used_kb : 0;

    pf_strcpy(buf, "HeapTotal:    ");
    pf_uint_to_str(total_kb, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " kB\n");

    pf_strcat(buf, "HeapUsed:     ");
    pf_uint_to_str(used_kb, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " kB\n");

    pf_strcat(buf, "HeapFree:     ");
    pf_uint_to_str(free_kb, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " kB\n");

    pf_strcat(buf, "Allocations:  ");
    pf_uint_to_str(hs.alloc_count, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, "\n");

    pf_strcat(buf, "Frees:        ");
    pf_uint_to_str(hs.free_count, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, "\n");

    pf_strcat(buf, "HeapStart:    0x");
    pf_hex32((uint32_t)hs.start, num);
    pf_hex_strip(num);
    pf_strcat(buf, num);
    pf_strcat(buf, "\n");

    pf_strcat(buf, "HeapEnd:      0x");
    pf_hex32((uint32_t)hs.end, num);
    pf_hex_strip(num);
    pf_strcat(buf, num);
    pf_strcat(buf, "\n");

    ramfs_write(pf_meminfo_idx, buf, pf_strlen(buf));
}

static void gen_cpuinfo(void) {
    char buf[512];
    char vendor[13];
    uint32_t eax, ebx, ecx, edx;

    /* Get vendor string */
    __asm__ volatile ("cpuid" : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx) : "a"(0));
    *(uint32_t*)&vendor[0] = ebx;
    *(uint32_t*)&vendor[4] = edx;
    *(uint32_t*)&vendor[8] = ecx;
    vendor[12] = '\0';

    pf_strcpy(buf, "vendor_id:    ");
    pf_strcat(buf, vendor);
    pf_strcat(buf, "\n");

    /* Feature flags */
    __asm__ volatile ("cpuid" : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx) : "a"(1));
    pf_strcat(buf, "features:     ");
    if (edx & (1 << 0))  pf_strcat(buf, "fpu ");
    if (edx & (1 << 4))  pf_strcat(buf, "tsc ");
    if (edx & (1 << 23)) pf_strcat(buf, "mmx ");
    if (edx & (1 << 25)) pf_strcat(buf, "sse ");
    if (edx & (1 << 26)) pf_strcat(buf, "sse2 ");
    if (ecx & (1 << 0))  pf_strcat(buf, "sse3 ");
    if (ecx & (1 << 19)) pf_strcat(buf, "sse4_1 ");
    if (ecx & (1 << 20)) pf_strcat(buf, "sse4_2 ");
    if (ecx & (1 << 28)) pf_strcat(buf, "avx ");
    pf_strcat(buf, "\n");

    /* Model / stepping from EAX */
    uint32_t stepping = eax & 0xF;
    uint32_t model    = (eax >> 4) & 0xF;
    uint32_t family   = (eax >> 8) & 0xF;
    char nbuf[24];
    pf_strcat(buf, "family:       ");
    pf_uint_to_str(family, nbuf, sizeof(nbuf));
    pf_strcat(buf, nbuf);
    pf_strcat(buf, "\nmodel:        ");
    pf_uint_to_str(model, nbuf, sizeof(nbuf));
    pf_strcat(buf, nbuf);
    pf_strcat(buf, "\nstepping:     ");
    pf_uint_to_str(stepping, nbuf, sizeof(nbuf));
    pf_strcat(buf, nbuf);
    pf_strcat(buf, "\n");

    ramfs_write(pf_cpuinfo_idx, buf, pf_strlen(buf));
}

static void gen_loadavg(void) {
    char buf[128];
    char num[24];
    int l1, l5, l15;
    sched_load_avg(&l1, &l5, &l15);

    /* Format as X.XX X.XX X.XX */
    pf_uint_to_str((uint64_t)(l1 / 100), num, sizeof(num));
    pf_strcpy(buf, num);
    pf_strcat(buf, ".");
    int frac = l1 % 100;
    if (frac < 10) pf_strcat(buf, "0");
    pf_uint_to_str((uint64_t)frac, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " ");

    pf_uint_to_str((uint64_t)(l5 / 100), num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, ".");
    frac = l5 % 100;
    if (frac < 10) pf_strcat(buf, "0");
    pf_uint_to_str((uint64_t)frac, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " ");

    pf_uint_to_str((uint64_t)(l15 / 100), num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, ".");
    frac = l15 % 100;
    if (frac < 10) pf_strcat(buf, "0");
    pf_uint_to_str((uint64_t)frac, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, "\n");

    /* Also append task counts */
    int ready, blocked, sleeping, total;
    sched_stats(&ready, &blocked, &sleeping, &total);
    pf_strcat(buf, "tasks: ");
    pf_uint_to_str((uint64_t)total, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " total, ");
    pf_uint_to_str((uint64_t)ready, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " ready, ");
    pf_uint_to_str((uint64_t)blocked, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " blocked, ");
    pf_uint_to_str((uint64_t)sleeping, num, sizeof(num));
    pf_strcat(buf, num);
    pf_strcat(buf, " sleeping\n");

    ramfs_write(pf_loadavg_idx, buf, pf_strlen(buf));
}

static void gen_tasks(void) {
    char buf[PROCFS_MAX_BUF];
    char num[24];
    static const char *state_names[] = {
        "FREE", "READY", "RUNNING", "BLOCKED", "SLEEPING", "DEAD"
    };

    pf_strcpy(buf, "TID  STATE     PRIO  NAME\n");
    pf_strcat(buf, "---  --------  ----  ----\n");

    for (int i = 0; i < SCHED_MAX_TASKS; i++) {
        const SchedTask *t = sched_get_task(i);
        if (!t || t->state == TASK_FREE) continue;

        /* TID */
        pf_uint_to_str((uint64_t)t->tid, num, sizeof(num));
        /* Right-pad TID to 5 chars */
        int tidlen = pf_strlen(num);
        pf_strcat(buf, num);
        for (int p = tidlen; p < 5; p++) pf_strcat(buf, " ");

        /* State */
        const char *sn = (t->state >= 0 && t->state <= 5) ? state_names[t->state] : "?";
        pf_strcat(buf, sn);
        int snlen = pf_strlen(sn);
        for (int p = snlen; p < 10; p++) pf_strcat(buf, " ");

        /* Priority */
        pf_uint_to_str((uint64_t)t->priority, num, sizeof(num));
        pf_strcat(buf, num);
        int prilen = pf_strlen(num);
        for (int p = prilen; p < 6; p++) pf_strcat(buf, " ");

        /* Name */
        pf_strcat(buf, t->name);
        pf_strcat(buf, "\n");

        /* Safety: don't overflow buf */
        if (pf_strlen(buf) > PROCFS_MAX_BUF - 100) break;
    }

    ramfs_write(pf_tasks_idx, buf, pf_strlen(buf));
}

static void gen_net(void) {
    char buf[1024];
    char num[24];
    char hex[12];
    const NetConfig *cfg = ip_get_config();

    pf_strcpy(buf, "Interface: eth0\n");

    if (cfg->configured) {
        /* IP address */
        pf_strcat(buf, "  IPv4:    ");
        pf_uint_to_str((cfg->ip >> 24) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->ip >> 16) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->ip >> 8) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str(cfg->ip & 0xFF, num, sizeof(num));
        pf_strcat(buf, num);
        pf_strcat(buf, "\n");

        /* Netmask */
        pf_strcat(buf, "  Netmask: ");
        pf_uint_to_str((cfg->netmask >> 24) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->netmask >> 16) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->netmask >> 8) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str(cfg->netmask & 0xFF, num, sizeof(num));
        pf_strcat(buf, num);
        pf_strcat(buf, "\n");

        /* Gateway */
        pf_strcat(buf, "  Gateway: ");
        pf_uint_to_str((cfg->gateway >> 24) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->gateway >> 16) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->gateway >> 8) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str(cfg->gateway & 0xFF, num, sizeof(num));
        pf_strcat(buf, num);
        pf_strcat(buf, "\n");

        /* DNS */
        pf_strcat(buf, "  DNS:     ");
        pf_uint_to_str((cfg->dns >> 24) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->dns >> 16) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str((cfg->dns >> 8) & 0xFF, num, sizeof(num));
        pf_strcat(buf, num); pf_strcat(buf, ".");
        pf_uint_to_str(cfg->dns & 0xFF, num, sizeof(num));
        pf_strcat(buf, num);
        pf_strcat(buf, "\n");
    } else {
        pf_strcat(buf, "  Status:  not configured\n");
    }

    (void)hex;  /* suppress unused warning */

    ramfs_write(pf_net_idx, buf, pf_strlen(buf));
}

static void gen_mounts(void) {
    char buf[256];
    pf_strcpy(buf, "ramfs    /         ramfs   rw  0 0\n");
    pf_strcat(buf, "procfs   /proc     procfs  ro  0 0\n");
    pf_strcat(buf, "devfs    /dev      devfs   rw  0 0\n");
    ramfs_write(pf_mounts_idx, buf, pf_strlen(buf));
}

static void gen_cmdline(void) {
    char buf[128];
    pf_strcpy(buf, "multiboot2 /boot/lateralus.elf\n");
    ramfs_write(pf_cmdline_idx, buf, pf_strlen(buf));
}

/* =======================================================================
 * Public API
 * ======================================================================= */

void procfs_init(void) {
    /* Create /proc directory under root (ramfs index 0) */
    proc_dir_idx = ramfs_mkdir(0, "proc");
    if (proc_dir_idx < 0) return;

    /* Create virtual files */
    pf_version_idx = ramfs_create(proc_dir_idx, "version");
    pf_uptime_idx  = ramfs_create(proc_dir_idx, "uptime");
    pf_meminfo_idx = ramfs_create(proc_dir_idx, "meminfo");
    pf_cpuinfo_idx = ramfs_create(proc_dir_idx, "cpuinfo");
    pf_loadavg_idx = ramfs_create(proc_dir_idx, "loadavg");
    pf_tasks_idx   = ramfs_create(proc_dir_idx, "tasks");
    pf_net_idx     = ramfs_create(proc_dir_idx, "net");
    pf_mounts_idx  = ramfs_create(proc_dir_idx, "mounts");
    pf_cmdline_idx = ramfs_create(proc_dir_idx, "cmdline");

    /* Generate initial content */
    procfs_refresh();
}

void procfs_refresh(void) {
    if (proc_dir_idx < 0) return;
    gen_version();
    gen_uptime();
    gen_meminfo();
    gen_cpuinfo();
    gen_loadavg();
    gen_tasks();
    gen_net();
    gen_mounts();
    gen_cmdline();
}

int procfs_refresh_file(const char *name) {
    if (!name) return -1;

    /* Simple name matching */
    if (pf_strlen(name) == 0) return -1;

    /* Compare and regenerate the specific file */
    const char *n = name;
    /* Skip leading "/proc/" if present */
    if (n[0] == '/') {
        n++;
        if (n[0] == 'p' && n[1] == 'r' && n[2] == 'o' && n[3] == 'c' && n[4] == '/') {
            n += 5;
        }
    }

    if (n[0] == 'v' && n[1] == 'e') { gen_version();  return 0; }
    if (n[0] == 'u' && n[1] == 'p') { gen_uptime();   return 0; }
    if (n[0] == 'm' && n[1] == 'e') { gen_meminfo();  return 0; }
    if (n[0] == 'c' && n[1] == 'p') { gen_cpuinfo();  return 0; }
    if (n[0] == 'l' && n[1] == 'o') { gen_loadavg();  return 0; }
    if (n[0] == 't' && n[1] == 'a') { gen_tasks();    return 0; }
    if (n[0] == 'n' && n[1] == 'e') { gen_net();      return 0; }
    if (n[0] == 'm' && n[1] == 'o') { gen_mounts();   return 0; }
    if (n[0] == 'c' && n[1] == 'm') { gen_cmdline();  return 0; }

    return -1;  /* unknown /proc file */
}
