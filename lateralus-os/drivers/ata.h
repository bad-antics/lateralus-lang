/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — ATA PIO Disk Driver
 * ═══════════════════════════════════════════════════════════════════════
 * PIO-mode ATA disk I/O for the primary IDE controller.
 * Supports 28-bit LBA read/write, identify, and flush.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_ATA_H
#define LATERALUS_ATA_H

#include "../gui/types.h"

/* ── Constants ────────────────────────────────────────────────────────── */

#define ATA_SECTOR_SIZE   512

/* Drive selection */
#define ATA_DRIVE_MASTER  0xE0
#define ATA_DRIVE_SLAVE   0xF0

/* ── Drive info ───────────────────────────────────────────────────────── */

typedef struct {
    uint8_t  present;         /* 1 if drive detected */
    uint8_t  drive_select;    /* ATA_DRIVE_MASTER or ATA_DRIVE_SLAVE */
    char     model[41];       /* Null-terminated model string */
    char     serial[21];      /* Null-terminated serial number */
    uint32_t sectors;         /* Total 28-bit LBA sectors */
    uint32_t size_mb;         /* Size in megabytes */
} AtaDriveInfo;

/* ── API ──────────────────────────────────────────────────────────────── */

/* Initialize the ATA controller, detect drives on primary bus.
   Returns number of drives found (0, 1, or 2). */
int ata_init(void);

/* Get drive info for drive 0 (master) or 1 (slave).
   Returns NULL if drive not present. */
const AtaDriveInfo *ata_get_drive(int drive);

/* Read `count` sectors starting at `lba` into `buf`.
   `drive` is 0 (master) or 1 (slave).
   Returns 0 on success, -1 on error. */
int ata_read_sectors(int drive, uint32_t lba, uint8_t count, void *buf);

/* Write `count` sectors starting at `lba` from `buf`.
   Returns 0 on success, -1 on error. */
int ata_write_sectors(int drive, uint32_t lba, uint8_t count, const void *buf);

/* Flush the drive's write cache.
   Returns 0 on success, -1 on error. */
int ata_flush(int drive);

#endif /* LATERALUS_ATA_H */
