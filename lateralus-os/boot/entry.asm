; LateralusOS — x86_64 entry point (NASM)
; Copyright (c) 2025 bad-antics. All rights reserved.

bits 32
section .text

global _start
extern boot_main

; Initial stack
section .bss
align 16
stack_bottom:
    resb 65536        ; 64 KB initial stack
stack_top:

_start:
    ; Set up stack
    mov  esp, stack_top

    ; Clear EFLAGS
    push 0
    popf

    ; Push multiboot info for C bootstrap
    push ebx          ; multiboot info pointer
    push eax          ; multiboot magic

    ; Call C bootstrap (which calls Lateralus kernel_main)
    call boot_main

    ; Halt if kernel returns
.halt:
    cli
    hlt
    jmp .halt
