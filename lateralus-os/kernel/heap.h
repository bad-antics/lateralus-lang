/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Kernel Heap Allocator
 * ═══════════════════════════════════════════════════════════════════════
 * Free-list + bump allocator with split/coalesce, double-free detection,
 * and allocation statistics. All allocations are 16-byte aligned.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_HEAP_H
#define LATERALUS_HEAP_H

#include "../gui/types.h"

/* ── Allocation header (placed before every returned pointer) ──────── */

typedef struct {
    uint64_t size;     /* total allocation size (includes header) */
    uint64_t magic;    /* 0xDEADBEEF — for validation             */
} AllocHeader;

#define ALLOC_MAGIC  0xDEADBEEFULL
#define MIN_SPLIT    64  /* don't split free blocks smaller than this */

/* ── Heap statistics (read-only access) ───────────────────────────── */

typedef struct {
    uint64_t start;        /* heap start address                    */
    uint64_t end;          /* heap end address                      */
    uint64_t next;         /* next bump-alloc address               */
    uint64_t allocated;    /* currently allocated bytes              */
    uint64_t alloc_count;  /* lifetime allocation count              */
    uint64_t free_count;   /* lifetime free count                   */
} HeapStats;

/* ── Public API ──────────────────────────────────────────────────── */

/* Initialise the heap. Called once at boot.
   `total_mem` = end of identity-mapped memory (typically RAM size). */
void  heap_init(uint64_t total_mem);

/* Allocate `size` bytes. Returns NULL on failure.
   All allocations are 16-byte aligned. */
void *kmalloc(uint64_t size);

/* Allocate `size` bytes, zero-initialised. */
void *kcalloc(uint64_t count, uint64_t elem_size);

/* Reallocate a previously allocated block. */
void *krealloc(void *ptr, uint64_t new_size);

/* Free a previously allocated block. Safe to call with NULL. */
void  kfree(void *ptr);

/* Get a snapshot of heap statistics. */
HeapStats heap_get_stats(void);

/* Print heap stats to the serial port (for debugging). */
void  heap_dump_stats(void);

#endif /* LATERALUS_HEAP_H */
