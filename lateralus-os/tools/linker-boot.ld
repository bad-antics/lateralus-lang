/* ===========================================================================
 * LateralusOS — Flat Boot Linker Script (initial testing)
 * ===========================================================================
 * Simple identity-mapped layout for first boot testing.
 * Physical load at 1 MB.  No higher-half mapping yet.
 * =========================================================================== */

ENTRY(_start)

SECTIONS
{
    . = 1M;

    .multiboot ALIGN(8) : {
        KEEP(*(.multiboot))
    }

    .text ALIGN(4096) : {
        *(.text)
        *(.text.*)
    }

    .rodata ALIGN(4096) : {
        *(.rodata)
        *(.rodata.*)
    }

    .data ALIGN(4096) : {
        *(.data)
        *(.data.*)
    }

    .bss ALIGN(4096) : {
        *(COMMON)
        *(.bss)
        *(.bss.*)
    }

    /* End-of-kernel marker — used by heap allocator */
    . = ALIGN(4096);
    _end = .;

    /DISCARD/ : {
        *(.comment)
        *(.note.*)
        *(.eh_frame)
        *(.eh_frame_hdr)
    }
}
