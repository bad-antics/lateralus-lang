/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — ATA PIO Disk Driver
 * ═══════════════════════════════════════════════════════════════════════
 * PIO-mode ATA disk I/O for the primary IDE controller.
 * Supports 28-bit LBA read/write, identify, and flush.
 *
 * This driver uses polling (PIO) mode, not DMA, which is slower but
 * simpler and works on all ATA controllers without PRDT setup.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "ata.h"

/* Port I/O (defined in kernel_stub.c) */
extern void    outb(uint16_t port, uint8_t val);
extern uint8_t inb(uint16_t port);
extern void serial_puts(const char *s);

/* ── I/O Ports (Primary ATA Controller) ──────────────────────────────── */

#define ATA_DATA        0x1F0
#define ATA_ERROR       0x1F1
#define ATA_SECT_COUNT  0x1F2
#define ATA_LBA_LO      0x1F3
#define ATA_LBA_MID     0x1F4
#define ATA_LBA_HI      0x1F5
#define ATA_DRIVE_HEAD  0x1F6
#define ATA_STATUS      0x1F7
#define ATA_COMMAND     0x1F7
#define ATA_ALT_STATUS  0x3F6
#define ATA_DEV_CTRL    0x3F6

/* ── ATA Commands ────────────────────────────────────────────────────── */

#define ATA_CMD_READ_PIO     0x20
#define ATA_CMD_WRITE_PIO    0x30
#define ATA_CMD_IDENTIFY     0xEC
#define ATA_CMD_CACHE_FLUSH  0xE7

/* ── Status bits ─────────────────────────────────────────────────────── */

#define ATA_SR_BSY   0x80  /* Busy */
#define ATA_SR_DRDY  0x40  /* Drive ready */
#define ATA_SR_DF    0x20  /* Drive fault */
#define ATA_SR_DSC   0x10  /* Drive seek complete */
#define ATA_SR_DRQ   0x08  /* Data request */
#define ATA_SR_CORR  0x04  /* Corrected data */
#define ATA_SR_IDX   0x02  /* Index */
#define ATA_SR_ERR   0x01  /* Error */

/* ── Internal state ──────────────────────────────────────────────────── */

static AtaDriveInfo drives[2];
static int num_drives = 0;

/* ── Utility ─────────────────────────────────────────────────────────── */

static void ata_400ns_delay(void) {
    /* Read alternate status 4 times (~400ns on ISA bus) */
    inb(ATA_ALT_STATUS);
    inb(ATA_ALT_STATUS);
    inb(ATA_ALT_STATUS);
    inb(ATA_ALT_STATUS);
}

static int ata_wait_bsy(void) {
    /* Wait for BSY to clear, with timeout */
    for (int i = 0; i < 100000; i++) {
        uint8_t status = inb(ATA_STATUS);
        if (!(status & ATA_SR_BSY))
            return 0;
    }
    return -1;  /* Timeout */
}

static int ata_wait_drq(void) {
    /* Wait for DRQ to set (data ready) */
    for (int i = 0; i < 100000; i++) {
        uint8_t status = inb(ATA_STATUS);
        if (status & ATA_SR_ERR) return -1;
        if (status & ATA_SR_DF)  return -1;
        if (status & ATA_SR_DRQ) return 0;
    }
    return -1;  /* Timeout */
}

/* ── Read a 16-bit word from the data port ───────────────────────────── */

static inline uint16_t ata_read_word(void) {
    uint16_t val;
    __asm__ volatile ("inw %1, %0" : "=a"(val) : "Nd"((uint16_t)ATA_DATA));
    return val;
}

/* ── Write a 16-bit word to the data port ────────────────────────────── */

static inline void ata_write_word(uint16_t val) {
    __asm__ volatile ("outw %0, %1" : : "a"(val), "Nd"((uint16_t)ATA_DATA));
}

/* ── Copy ATA identify string (byte-swapped pairs) ───────────────────── */

static void ata_copy_string(char *dst, const uint16_t *src, int words) {
    for (int i = 0; i < words; i++) {
        dst[i * 2]     = (char)(src[i] >> 8);
        dst[i * 2 + 1] = (char)(src[i] & 0xFF);
    }
    dst[words * 2] = '\0';

    /* Trim trailing spaces */
    int len = words * 2;
    while (len > 0 && dst[len - 1] == ' ')
        dst[--len] = '\0';
}

/* ── Software reset ──────────────────────────────────────────────────── */

static void ata_soft_reset(void) {
    outb(ATA_DEV_CTRL, 0x04);  /* Set SRST */
    ata_400ns_delay();
    outb(ATA_DEV_CTRL, 0x00);  /* Clear SRST */
    ata_400ns_delay();
    ata_wait_bsy();
}

/* ── Identify a drive ────────────────────────────────────────────────── */

static int ata_identify_drive(int drive_idx) {
    uint8_t drive_sel = (drive_idx == 0) ? ATA_DRIVE_MASTER : ATA_DRIVE_SLAVE;
    AtaDriveInfo *info = &drives[drive_idx];

    info->present = 0;
    info->drive_select = drive_sel;

    /* Select drive */
    outb(ATA_DRIVE_HEAD, drive_sel);
    ata_400ns_delay();

    /* Clear sector count and LBA registers */
    outb(ATA_SECT_COUNT, 0);
    outb(ATA_LBA_LO, 0);
    outb(ATA_LBA_MID, 0);
    outb(ATA_LBA_HI, 0);

    /* Send IDENTIFY command */
    outb(ATA_COMMAND, ATA_CMD_IDENTIFY);
    ata_400ns_delay();

    /* Check if drive exists */
    uint8_t status = inb(ATA_STATUS);
    if (status == 0) return 0;  /* No drive */

    /* Wait for BSY to clear */
    if (ata_wait_bsy() < 0) return 0;

    /* Check for ATAPI (not supported) */
    if (inb(ATA_LBA_MID) != 0 || inb(ATA_LBA_HI) != 0)
        return 0;  /* ATAPI or SATA — not a PATA disk */

    /* Wait for DRQ */
    if (ata_wait_drq() < 0) return 0;

    /* Read 256 words of identify data */
    uint16_t ident[256];
    for (int i = 0; i < 256; i++)
        ident[i] = ata_read_word();

    /* Parse identify data */
    ata_copy_string(info->serial, &ident[10], 10);   /* Words 10-19: serial */
    ata_copy_string(info->model,  &ident[27], 20);   /* Words 27-46: model */

    /* Total LBA28 sectors at word 60-61 */
    info->sectors = (uint32_t)ident[60] | ((uint32_t)ident[61] << 16);
    info->size_mb = info->sectors / 2048;

    info->present = 1;
    return 1;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Public API
 * ═══════════════════════════════════════════════════════════════════════ */

int ata_init(void) {
    serial_puts("[ata] Initializing ATA PIO driver...\n");

    /* Software reset both drives */
    ata_soft_reset();

    num_drives = 0;

    /* Detect master */
    if (ata_identify_drive(0)) {
        serial_puts("[ata] Master: ");
        serial_puts(drives[0].model);
        serial_puts("\n");
        num_drives++;
    }

    /* Detect slave */
    if (ata_identify_drive(1)) {
        serial_puts("[ata] Slave: ");
        serial_puts(drives[1].model);
        serial_puts("\n");
        num_drives++;
    }

    if (num_drives == 0) {
        serial_puts("[ata] No ATA drives detected\n");
    }

    return num_drives;
}

const AtaDriveInfo *ata_get_drive(int drive) {
    if (drive < 0 || drive > 1) return (const AtaDriveInfo *)0;
    if (!drives[drive].present) return (const AtaDriveInfo *)0;
    return &drives[drive];
}

int ata_read_sectors(int drive, uint32_t lba, uint8_t count, void *buf) {
    if (drive < 0 || drive > 1 || !drives[drive].present)
        return -1;
    if (count == 0) return -1;
    if (lba + count > drives[drive].sectors)
        return -1;

    uint8_t drive_sel = drives[drive].drive_select;
    uint16_t *wbuf = (uint16_t *)buf;

    /* Wait for controller */
    ata_wait_bsy();

    /* Select drive + set top 4 bits of LBA */
    outb(ATA_DRIVE_HEAD, drive_sel | ((lba >> 24) & 0x0F));
    ata_400ns_delay();

    /* Set sector count and LBA */
    outb(ATA_SECT_COUNT, count);
    outb(ATA_LBA_LO, lba & 0xFF);
    outb(ATA_LBA_MID, (lba >> 8) & 0xFF);
    outb(ATA_LBA_HI, (lba >> 16) & 0xFF);

    /* Send read command */
    outb(ATA_COMMAND, ATA_CMD_READ_PIO);

    /* Read each sector */
    for (int s = 0; s < count; s++) {
        if (ata_wait_drq() < 0) return -1;

        /* Read 256 words (512 bytes) */
        for (int i = 0; i < 256; i++)
            *wbuf++ = ata_read_word();

        ata_400ns_delay();
    }

    return 0;
}

int ata_write_sectors(int drive, uint32_t lba, uint8_t count, const void *buf) {
    if (drive < 0 || drive > 1 || !drives[drive].present)
        return -1;
    if (count == 0) return -1;
    if (lba + count > drives[drive].sectors)
        return -1;

    uint8_t drive_sel = drives[drive].drive_select;
    const uint16_t *wbuf = (const uint16_t *)buf;

    /* Wait for controller */
    ata_wait_bsy();

    /* Select drive + set top 4 bits of LBA */
    outb(ATA_DRIVE_HEAD, drive_sel | ((lba >> 24) & 0x0F));
    ata_400ns_delay();

    /* Set sector count and LBA */
    outb(ATA_SECT_COUNT, count);
    outb(ATA_LBA_LO, lba & 0xFF);
    outb(ATA_LBA_MID, (lba >> 8) & 0xFF);
    outb(ATA_LBA_HI, (lba >> 16) & 0xFF);

    /* Send write command */
    outb(ATA_COMMAND, ATA_CMD_WRITE_PIO);

    /* Write each sector */
    for (int s = 0; s < count; s++) {
        if (ata_wait_drq() < 0) return -1;

        /* Write 256 words (512 bytes) */
        for (int i = 0; i < 256; i++)
            ata_write_word(*wbuf++);

        ata_400ns_delay();
    }

    /* Flush cache */
    outb(ATA_COMMAND, ATA_CMD_CACHE_FLUSH);
    ata_wait_bsy();

    return 0;
}

int ata_flush(int drive) {
    if (drive < 0 || drive > 1 || !drives[drive].present)
        return -1;

    outb(ATA_DRIVE_HEAD, drives[drive].drive_select);
    ata_400ns_delay();
    outb(ATA_COMMAND, ATA_CMD_CACHE_FLUSH);

    return ata_wait_bsy();
}
