/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Boot Info (shared between boot_stub and kernel)
 * ═══════════════════════════════════════════════════════════════════════ */
#ifndef LTL_BOOTINFO_H
#define LTL_BOOTINFO_H

#include "types.h"

typedef struct {
    uint64_t total_memory_kb;
    uint64_t available_memory_kb;
    uint64_t framebuffer_addr;
    uint32_t fb_width;
    uint32_t fb_height;
    uint32_t fb_pitch;
    uint8_t  fb_bpp;
    uint8_t  fb_available;
    char     boot_cmd[256];
} BootInfo;

#endif /* LTL_BOOTINFO_H */
