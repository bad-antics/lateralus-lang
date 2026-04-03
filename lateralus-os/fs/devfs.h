/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — /dev Virtual Device Filesystem
 * ═══════════════════════════════════════════════════════════════════════
 * Provides pseudo-devices under /dev/:
 *   /dev/null    — discards all writes, reads return empty
 *   /dev/zero    — infinite stream of zero bytes
 *   /dev/random  — pseudo-random bytes (LFSR)
 *   /dev/serial  — serial port access (COM1)
 *   /dev/fb0     — framebuffer info (read-only)
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_DEVFS_H
#define LATERALUS_DEVFS_H

#include "../gui/types.h"

#define DEVFS_MAX_DEVICES   8
#define DEVFS_BUF_SIZE    512

/* Initialize /dev directory and register device nodes.
   Must be called after ramfs_init(). */
void devfs_init(void);

/* Refresh a specific device file's content (e.g. before `cat`).
   Returns 0 on success, -1 if name not found. */
int devfs_refresh_file(const char *name);

#endif /* LATERALUS_DEVFS_H */
