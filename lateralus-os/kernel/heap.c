/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Kernel Heap Allocator
 * ═══════════════════════════════════════════════════════════════════════
 * Free-list + bump allocator with split/coalesce, double-free detection,
 * and allocation statistics. Extracted from the monolithic kernel_stub.c
 * into its own module for maintainability.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "heap.h"

/* ── External symbols ─────────────────────────────────────────────────── */

extern char _end;              /* defined by linker script — end of kernel image */
extern void serial_puts(const char *s);

/* ── Internal state ───────────────────────────────────────────────────── */

static uint64_t heap_start;
static uint64_t heap_end;
static uint64_t heap_next;
static uint64_t heap_allocated;
static uint64_t heap_alloc_count;
static uint64_t heap_free_count;

/* Free-list node */
typedef struct FreeBlock {
    uint64_t             size;
    struct FreeBlock    *next;
} FreeBlock;

static FreeBlock *free_list = (FreeBlock*)0;

/* ── Helpers ──────────────────────────────────────────────────────────── */

static void _heap_serial_hex(uint64_t val) {
    const char *hex = "0123456789ABCDEF";
    char buf[19] = "0x0000000000000000";
    for (int i = 17; i >= 2; i--) {
        buf[i] = hex[val & 0xF];
        val >>= 4;
    }
    serial_puts(buf);
}

static void _heap_serial_dec(uint64_t val) {
    if (val == 0) { serial_puts("0"); return; }
    char buf[24];
    int pos = 0;
    while (val > 0 && pos < 23) {
        buf[pos++] = '0' + (val % 10);
        val /= 10;
    }
    /* reverse */
    for (int i = pos - 1; i >= 0; i--) {
        char tmp[2] = { buf[i], '\0' };
        serial_puts(tmp);
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Public API
 * ═══════════════════════════════════════════════════════════════════════ */

void heap_init(uint64_t total_mem) {
    /* Place heap right after the kernel image, aligned to 4096 */
    heap_start = ((uint64_t)&_end + 0xFFF) & ~0xFFFULL;
    heap_end   = total_mem;          /* up to end of identity-mapped RAM */
    heap_next  = heap_start;
    heap_allocated   = 0;
    heap_alloc_count = 0;
    heap_free_count  = 0;
    free_list = (FreeBlock*)0;
}

void *kmalloc(uint64_t size) {
    if (size == 0) return (void*)0;

    /* Align to 16 bytes, add room for header */
    uint64_t total = ((size + sizeof(AllocHeader) + 15) & ~15ULL);

    /* First: try to find a block in the free list (first-fit) */
    FreeBlock **prev = &free_list;
    FreeBlock  *cur  = free_list;
    while (cur) {
        if (cur->size >= total) {
            /* Found a suitable free block */
            if (cur->size >= total + MIN_SPLIT) {
                /* Split: create a new free block after our allocation */
                FreeBlock *remainder = (FreeBlock*)((uint8_t*)cur + total);
                remainder->size = cur->size - total;
                remainder->next = cur->next;
                *prev = remainder;
            } else {
                /* Use the whole block */
                total = cur->size;
                *prev = cur->next;
            }
            AllocHeader *hdr = (AllocHeader*)cur;
            hdr->size  = total;
            hdr->magic = ALLOC_MAGIC;
            heap_allocated += total;
            heap_alloc_count++;
            return (void*)((uint8_t*)hdr + sizeof(AllocHeader));
        }
        prev = &cur->next;
        cur  = cur->next;
    }

    /* No free block found — bump allocate */
    if (heap_next + total > heap_end) return (void*)0;
    AllocHeader *hdr = (AllocHeader*)heap_next;
    hdr->size  = total;
    hdr->magic = ALLOC_MAGIC;
    heap_next += total;
    heap_allocated += total;
    heap_alloc_count++;
    return (void*)((uint8_t*)hdr + sizeof(AllocHeader));
}

void *kcalloc(uint64_t count, uint64_t elem_size) {
    uint64_t total = count * elem_size;
    void *ptr = kmalloc(total);
    if (ptr) {
        uint8_t *p = (uint8_t*)ptr;
        for (uint64_t i = 0; i < total; i++) p[i] = 0;
    }
    return ptr;
}

void *krealloc(void *ptr, uint64_t new_size) {
    if (!ptr) return kmalloc(new_size);
    if (new_size == 0) { kfree(ptr); return (void*)0; }

    AllocHeader *hdr = (AllocHeader*)((uint8_t*)ptr - sizeof(AllocHeader));
    if (hdr->magic != ALLOC_MAGIC) {
        serial_puts("[heap] krealloc: invalid pointer!\n");
        return (void*)0;
    }

    uint64_t old_usable = hdr->size - sizeof(AllocHeader);
    if (new_size <= old_usable) return ptr;  /* fits in existing block */

    /* Allocate new block, copy, free old */
    void *new_ptr = kmalloc(new_size);
    if (!new_ptr) return (void*)0;

    uint8_t *src = (uint8_t*)ptr;
    uint8_t *dst = (uint8_t*)new_ptr;
    for (uint64_t i = 0; i < old_usable; i++) dst[i] = src[i];

    kfree(ptr);
    return new_ptr;
}

void kfree(void *ptr) {
    if (!ptr) return;
    AllocHeader *hdr = (AllocHeader*)((uint8_t*)ptr - sizeof(AllocHeader));
    if (hdr->magic != ALLOC_MAGIC) {
        serial_puts("[heap] kfree: invalid pointer or double-free!\n");
        return;
    }
    hdr->magic = 0;  /* invalidate to catch double-free */
    heap_allocated -= hdr->size;
    heap_free_count++;

    /* Add to free list (insert at head — simple and fast) */
    FreeBlock *blk = (FreeBlock*)hdr;
    blk->size = hdr->size;
    blk->next = free_list;
    free_list = blk;
}

HeapStats heap_get_stats(void) {
    HeapStats s;
    s.start       = heap_start;
    s.end         = heap_end;
    s.next        = heap_next;
    s.allocated   = heap_allocated;
    s.alloc_count = heap_alloc_count;
    s.free_count  = heap_free_count;
    return s;
}

void heap_dump_stats(void) {
    serial_puts("[heap] start=");
    _heap_serial_hex(heap_start);
    serial_puts(" end=");
    _heap_serial_hex(heap_end);
    serial_puts(" next=");
    _heap_serial_hex(heap_next);
    serial_puts(" alloc=");
    _heap_serial_dec(heap_allocated);
    serial_puts(" count=");
    _heap_serial_dec(heap_alloc_count);
    serial_puts(" frees=");
    _heap_serial_dec(heap_free_count);
    serial_puts("\n");
}
