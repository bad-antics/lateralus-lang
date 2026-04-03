; ═══════════════════════════════════════════════════════════════════════════
; LateralusOS — Multiboot2 Boot Entry (x86_64)
; ═══════════════════════════════════════════════════════════════════════════
; Copyright (c) 2025 bad-antics. All rights reserved.
;
; This is the very first code that runs when the bootloader (GRUB) hands
; control to LateralusOS.  It sets up:
;   1. Multiboot2 header (so GRUB recognises us)
;   2. GDT (Global Descriptor Table) for 64-bit long mode
;   3. Page tables (identity-map first 4 GB)
;   4. Stack
;   5. Jump to the C bootstrap stub → kernel_main (Lateralus)
; ═══════════════════════════════════════════════════════════════════════════

BITS 32

; ── Multiboot2 Header ─────────────────────────────────────────────────────
section .multiboot
align 8

MULTIBOOT2_MAGIC    equ 0xE85250D6
ARCH_X86            equ 0            ; i386 protected mode
HEADER_LENGTH       equ multiboot_end - multiboot_start
CHECKSUM            equ -(MULTIBOOT2_MAGIC + ARCH_X86 + HEADER_LENGTH)

multiboot_start:
    dd MULTIBOOT2_MAGIC
    dd ARCH_X86
    dd HEADER_LENGTH
    dd CHECKSUM

    ; Framebuffer request tag (type 5)
    ; Requests 1024x768x32 linear framebuffer from GRUB
    align 8
    dw 5        ; type = framebuffer
    dw 0        ; flags (optional — GRUB can fall back)
    dd 20       ; size of this tag
    dd 1024     ; preferred width
    dd 768      ; preferred height
    dd 32       ; preferred bpp

    ; End tag
    align 8
    dw 0        ; type
    dw 0        ; flags
    dd 8        ; size
multiboot_end:


; ── BSS: Stack & Page Tables ──────────────────────────────────────────────
section .bss
align 4096

; Page tables for identity mapping (4 GB)
pml4_table:     resb 4096
pdpt_table:     resb 4096
pd_table:       resb 4096       ; PD 0: 0 – 1 GB
pd_table1:      resb 4096       ; PD 1: 1 – 2 GB
pd_table2:      resb 4096       ; PD 2: 2 – 3 GB
pd_table3:      resb 4096       ; PD 3: 3 – 4 GB
pt_table:       resb 4096

; Kernel stack (16 KB)
stack_bottom:
    resb 16384
stack_top:


; ── Boot Code ─────────────────────────────────────────────────────────────
section .text
global _start
extern boot_init            ; C bootstrap stub

_start:
    ; Save multiboot registers for boot_init(magic, mb_info_addr)
    mov edi, eax            ; multiboot magic  (arg 1)
    mov esi, ebx            ; multiboot info   (arg 2)

    ; Set up stack
    mov esp, stack_top

    ; ── Check for CPUID ──────────────────────────────────────────────────
    pushfd
    pop eax
    mov ecx, eax
    xor eax, 1 << 21       ; Flip CPUID bit
    push eax
    popfd
    pushfd
    pop eax
    push ecx
    popfd
    cmp eax, ecx
    je .no_cpuid

    ; ── Check for Long Mode ──────────────────────────────────────────────
    mov eax, 0x80000000
    cpuid
    cmp eax, 0x80000001
    jb .no_long_mode

    mov eax, 0x80000001
    cpuid
    test edx, 1 << 29      ; LM bit
    jz .no_long_mode

    ; ── Set up paging ────────────────────────────────────────────────────

    ; PML4[0] → PDPT
    mov eax, pdpt_table
    or eax, 0x03            ; present + writable
    mov [pml4_table], eax

    ; PDPT[0..3] → PD0..PD3 (maps 4 GB total)
    mov eax, pd_table
    or eax, 0x03
    mov [pdpt_table], eax

    mov eax, pd_table1
    or eax, 0x03
    mov [pdpt_table + 8], eax

    mov eax, pd_table2
    or eax, 0x03
    mov [pdpt_table + 16], eax

    mov eax, pd_table3
    or eax, 0x03
    mov [pdpt_table + 24], eax

    ; PD0: map 0x00000000 – 0x3FFFFFFF  (0 – 1 GB)
    mov ecx, 0
.map_pd0:
    mov eax, ecx
    shl eax, 21
    or eax, 0x83            ; present + writable + huge (2MB)
    mov [pd_table + ecx * 8], eax
    inc ecx
    cmp ecx, 512
    jne .map_pd0

    ; PD1: map 0x40000000 – 0x7FFFFFFF  (1 – 2 GB)
    mov ecx, 0
.map_pd1:
    mov eax, ecx
    add eax, 512
    shl eax, 21
    or eax, 0x83
    mov [pd_table1 + ecx * 8], eax
    inc ecx
    cmp ecx, 512
    jne .map_pd1

    ; PD2: map 0x80000000 – 0xBFFFFFFF  (2 – 3 GB)
    mov ecx, 0
.map_pd2:
    mov eax, ecx
    add eax, 1024
    shl eax, 21
    or eax, 0x83
    mov [pd_table2 + ecx * 8], eax
    inc ecx
    cmp ecx, 512
    jne .map_pd2

    ; PD3: map 0xC0000000 – 0xFFFFFFFF  (3 – 4 GB)
    mov ecx, 0
.map_pd3:
    mov eax, ecx
    add eax, 1536
    shl eax, 21
    or eax, 0x83
    mov [pd_table3 + ecx * 8], eax
    inc ecx
    cmp ecx, 512
    jne .map_pd3

    ; Load PML4 into CR3
    mov eax, pml4_table
    mov cr3, eax

    ; Enable PAE
    mov eax, cr4
    or eax, 1 << 5          ; PAE bit
    mov cr4, eax

    ; Enable Long Mode (EFER.LME)
    mov ecx, 0xC0000080     ; EFER MSR
    rdmsr
    or eax, 1 << 8          ; LME bit
    wrmsr

    ; Enable paging
    mov eax, cr0
    or eax, 1 << 31         ; PG bit
    mov cr0, eax

    ; ── Load 64-bit GDT and jump to long mode ───────────────────────────
    lgdt [gdt64.pointer]
    jmp gdt64.code_segment:long_mode_start

.no_cpuid:
    mov al, 'C'
    jmp .error

.no_long_mode:
    mov al, 'L'
    jmp .error

.error:
    ; Print error character to VGA
    mov dword [0xB8000], 0x4F524F45  ; "ER"
    mov dword [0xB8004], 0x4F3A4F52  ; "R:"
    mov byte  [0xB8008], al
    mov byte  [0xB8009], 0x4F
    hlt


; ── 64-bit Long Mode Entry ───────────────────────────────────────────────
BITS 64

long_mode_start:
    ; Clear segment registers
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Reload stack in 64-bit mode
    mov rsp, stack_top

    ; Pass multiboot info to C bootstrap
    ; edi already has multiboot info ptr from above
    ; esi already has multiboot magic

    ; Jump to C bootstrap → Lateralus kernel
    call boot_init

    ; Should never return, but just in case:
    cli
.halt:
    hlt
    jmp .halt


; ── GDT (64-bit) ─────────────────────────────────────────────────────────
section .rodata
align 16

gdt64:
    ; Null descriptor
    dq 0

.code_segment: equ $ - gdt64
    ; Code segment: executable, 64-bit, present
    dq (1 << 43) | (1 << 44) | (1 << 47) | (1 << 53)

.data_segment: equ $ - gdt64
    ; Data segment: writable, present
    dq (1 << 41) | (1 << 44) | (1 << 47)

.pointer:
    dw $ - gdt64 - 1        ; GDT limit
    dq gdt64                ; GDT base address
