/* ═══════════════════════════════════════════════════════════════════════════
 * LateralusOS — Linker Script (ARM Cortex-M4)
 * ═══════════════════════════════════════════════════════════════════════════
 * Copyright (c) 2025 bad-antics. All rights reserved.
 *
 * Target: ARM Cortex-M4 (embedded/industrial edition)
 * Flash: 512 KB at 0x08000000
 * RAM:   128 KB at 0x20000000
 * ═══════════════════════════════════════════════════════════════════════════ */

ENTRY(Reset_Handler)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

_stack_size = 8K;
_heap_size  = 32K;

SECTIONS
{
    /* ── Vector table (must be at flash start) ─────────────────────────── */
    .isr_vector : {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } > FLASH

    /* ── Code ──────────────────────────────────────────────────────────── */
    .text : {
        . = ALIGN(4);
        _text_start = .;
        *(.text)
        *(.text.*)
        *(.glue_7)
        *(.glue_7t)
        KEEP(*(.init))
        KEEP(*(.fini))
        . = ALIGN(4);
        _text_end = .;
    } > FLASH

    /* ── Read-only data ────────────────────────────────────────────────── */
    .rodata : {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata.*)
        . = ALIGN(4);
    } > FLASH

    /* ── ARM exception tables ──────────────────────────────────────────── */
    .ARM.extab : {
        *(.ARM.extab*)
    } > FLASH

    .ARM.exidx : {
        __exidx_start = .;
        *(.ARM.exidx*)
        __exidx_end = .;
    } > FLASH

    _sidata = LOADADDR(.data);

    /* ── Initialized data (loaded from flash, copied to RAM) ───────────── */
    .data : {
        . = ALIGN(4);
        _data_start = .;
        *(.data)
        *(.data.*)
        . = ALIGN(4);
        _data_end = .;
    } > RAM AT> FLASH

    /* ── BSS (zeroed) ──────────────────────────────────────────────────── */
    .bss : {
        . = ALIGN(4);
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        *(COMMON)
        . = ALIGN(4);
        _bss_end = .;
    } > RAM

    /* ── Heap ──────────────────────────────────────────────────────────── */
    .heap : {
        . = ALIGN(8);
        _heap_start = .;
        . = . + _heap_size;
        _heap_end = .;
    } > RAM

    /* ── Stack (grows downward) ────────────────────────────────────────── */
    .stack : {
        . = ALIGN(8);
        _stack_end = .;
        . = . + _stack_size;
        _stack_start = .;
    } > RAM

    _end = .;

    /* ── Assertions ────────────────────────────────────────────────────── */
    ASSERT(_end <= ORIGIN(RAM) + LENGTH(RAM), "ERROR: Not enough RAM")
    ASSERT(_text_end <= ORIGIN(FLASH) + LENGTH(FLASH), "ERROR: Not enough FLASH")

    /DISCARD/ : {
        *(.comment)
        *(.note.*)
        *(.ARM.attributes)
    }
}
