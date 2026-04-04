/* LateralusOS — Multiboot2 C Bootstrap
 * Copyright (c) 2025 bad-antics. All rights reserved.
 */

#include <stdint.h>
#include <stddef.h>

#define MULTIBOOT2_MAGIC 0xE85250D6
#define MULTIBOOT2_ARCH  0

/* Forward declarations for Lateralus-compiled code */
extern void kernel_main(void);
extern void ltl_runtime_init(void);

/* Multiboot2 header (must be in first 32KB of binary) */
__attribute__((section(".multiboot")))
static const struct {
    uint32_t magic;
    uint32_t architecture;
    uint32_t header_length;
    uint32_t checksum;
    /* end tag */
    uint16_t end_type;
    uint16_t end_flags;
    uint32_t end_size;
} mb2_header = {
    .magic         = MULTIBOOT2_MAGIC,
    .architecture  = MULTIBOOT2_ARCH,
    .header_length = sizeof(mb2_header),
    .checksum      = -(MULTIBOOT2_MAGIC + MULTIBOOT2_ARCH + sizeof(mb2_header)),
    .end_type      = 0,
    .end_flags     = 0,
    .end_size      = 8,
};

/* Called from entry.asm after setting up stack and GDT */
void boot_main(uint32_t magic, void *mbi) {
    (void)magic;
    (void)mbi;
    ltl_runtime_init();
    kernel_main();
    /* Should never return */
    for (;;) { __asm__ volatile("hlt"); }
}
