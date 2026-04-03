/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — /proc Virtual Filesystem
 * ═══════════════════════════════════════════════════════════════════════
 * Read-only virtual filesystem exposing kernel state as text files.
 * Content is generated dynamically from live kernel data structures.
 *
 * Virtual files:
 *   /proc/version   — OS version string
 *   /proc/uptime    — System uptime in seconds
 *   /proc/meminfo   — Heap usage statistics
 *   /proc/cpuinfo   — CPU vendor and feature info
 *   /proc/loadavg   — 1/5/15 min load averages
 *   /proc/tasks     — Task list (TID, state, priority, name)
 *   /proc/net       — Network interface and ARP/DNS cache info
 *   /proc/mounts    — Mounted filesystems
 *   /proc/cmdline   — Kernel command line (boot params)
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_PROCFS_H
#define LATERALUS_PROCFS_H

#include "../gui/types.h"

/* Maximum size of a generated /proc file content */
#define PROCFS_MAX_BUF   4096

/* Number of known /proc entries */
#define PROCFS_NUM_FILES  9

/* ── Public API ───────────────────────────────────────────────────────── */

/* Initialize procfs — creates /proc directory and virtual entries in ramfs */
void procfs_init(void);

/* Refresh all /proc file contents from live kernel state.
 * Called periodically or on-demand (e.g. before `cat /proc/xxx`). */
void procfs_refresh(void);

/* Refresh a single proc file by name. Returns 0 on success, -1 if unknown. */
int  procfs_refresh_file(const char *name);

#endif /* LATERALUS_PROCFS_H */
