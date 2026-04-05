/* ===========================================================================
 * LateralusOS — Linker Script (RISC-V 64)
 * ===========================================================================
 * Copyright (c) 2025 bad-antics. All rights reserved.
 *
 * Target: RISC-V RV64IMAC (QEMU virt machine)
 * RAM starts at 0x80000000
 * =========================================================================== */

ENTRY(_start)

BASE_ADDRESS = 0x80000000;

SECTIONS
{
    . = BASE_ADDRESS;

    /* -- Code ------------------------------------------------------------ */
    .text ALIGN(4096) : {
        _text_start = .;
        KEEP(*(.text.entry))
        *(.text)
        *(.text.*)
        _text_end = .;
    }

    /* -- Read-only data -------------------------------------------------- */
    .rodata ALIGN(4096) : {
        _rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        *(.srodata)
        *(.srodata.*)
        _rodata_end = .;
    }

    /* -- Initialized data ------------------------------------------------ */
    .data ALIGN(4096) : {
        _data_start = .;
        *(.data)
        *(.data.*)
        *(.sdata)
        *(.sdata.*)
        _data_end = .;
    }

    /* -- BSS ------------------------------------------------------------- */
    .bss ALIGN(4096) : {
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        *(.sbss)
        *(.sbss.*)
        *(COMMON)
        _bss_end = .;
    }

    /* -- Stack (64 KB) --------------------------------------------------- */
    . = ALIGN(16);
    . = . + 64K;
    _stack_top = .;

    _kernel_end = .;

    /DISCARD/ : {
        *(.comment)
        *(.note.*)
        *(.eh_frame)
    }
}
