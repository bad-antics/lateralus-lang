/* ===========================================================================
 * LateralusOS — Linker Script (x86_64)
 * ===========================================================================
 * Copyright (c) 2025 bad-antics. All rights reserved.
 *
 * Kernel linked at virtual address 0xFFFFFFFF80000000 (higher-half)
 * Physical load address 0x100000 (1 MB mark, above real-mode memory)
 * =========================================================================== */

ENTRY(_start)

KERNEL_VMA = 0xFFFFFFFF80000000;
KERNEL_LMA = 0x100000;

SECTIONS
{
    . = KERNEL_LMA;

    /* -- Multiboot2 header (must be in first 32 KB) ---------------------- */
    .multiboot2 ALIGN(8) : {
        KEEP(*(.multiboot2))
    }

    /* -- Boot code (runs before paging is set up) ------------------------ */
    .boot ALIGN(4096) : {
        *(.boot)
        *(.boot.*)
    }

    /* -- Page tables (16 KB aligned, identity-mapped) -------------------- */
    .page_tables ALIGN(4096) : {
        *(.page_tables)
    }

    /* -- Higher-half kernel ---------------------------------------------- */
    . = KERNEL_VMA + ALIGN(. - KERNEL_LMA, 4096);

    .text ALIGN(4096) : AT(ADDR(.text) - KERNEL_VMA + KERNEL_LMA) {
        _text_start = .;
        *(.text)
        *(.text.*)
        _text_end = .;
    }

    .rodata ALIGN(4096) : AT(ADDR(.rodata) - KERNEL_VMA + KERNEL_LMA) {
        _rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        _rodata_end = .;
    }

    .data ALIGN(4096) : AT(ADDR(.data) - KERNEL_VMA + KERNEL_LMA) {
        _data_start = .;
        *(.data)
        *(.data.*)
        _data_end = .;
    }

    .bss ALIGN(4096) : AT(ADDR(.bss) - KERNEL_VMA + KERNEL_LMA) {
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        *(COMMON)
        _bss_end = .;
    }

    _kernel_end = .;
    _kernel_phys_end = _kernel_end - KERNEL_VMA + KERNEL_LMA;

    /* -- Debug info (stripped in release) --------------------------------- */
    .debug_info     0 : { *(.debug_info)     }
    .debug_abbrev   0 : { *(.debug_abbrev)   }
    .debug_line     0 : { *(.debug_line)     }
    .debug_str      0 : { *(.debug_str)      }
    .debug_ranges   0 : { *(.debug_ranges)   }
    .debug_loc      0 : { *(.debug_loc)      }
    .debug_frame    0 : { *(.debug_frame)    }

    /DISCARD/ : {
        *(.comment)
        *(.note.*)
        *(.eh_frame)
        *(.eh_frame_hdr)
    }
}
