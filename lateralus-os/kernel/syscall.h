/* =======================================================================
 * LateralusOS — System Call Interface
 * =======================================================================
 * Syscall dispatch table and handler. In the current stub kernel all
 * calls execute in ring 0 (no privilege separation yet), so these are
 * really internal kernel services exposed via a numbered table.
 *
 * Syscall convention (x86_64, when user-mode lands):
 *   rax = syscall number
 *   rdi = arg1, rsi = arg2, rdx = arg3
 *   Return value in rax
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ======================================================================= */

#ifndef LATERALUS_SYSCALL_H
#define LATERALUS_SYSCALL_H

#include "../gui/types.h"

/* -- Syscall numbers --------------------------------------------------- */

#define SYS_EXIT         0
#define SYS_READ         1
#define SYS_WRITE        2
#define SYS_OPEN         3
#define SYS_CLOSE        4
#define SYS_FORK         5
#define SYS_EXEC         6
#define SYS_WAIT         7
#define SYS_GETPID       8
#define SYS_SLEEP        9
#define SYS_YIELD       10
#define SYS_MMAP        11
#define SYS_MUNMAP      12
#define SYS_BRK         13
#define SYS_IOCTL       14
#define SYS_STAT        15
#define SYS_MKDIR       16
#define SYS_RMDIR       17
#define SYS_UNLINK      18
#define SYS_RENAME      19
#define SYS_PIPE        20
#define SYS_DUP         21
#define SYS_KILL        22
#define SYS_SIGNAL      23
#define SYS_TIME        24
#define SYS_SPAWN       25
#define SYS_CHAN_CREATE  26
#define SYS_CHAN_SEND    27
#define SYS_CHAN_RECV    28
#define SYS_CHAN_CLOSE   29
#define SYS_SHM_CREATE  30
#define SYS_SHM_ATTACH  31
#define SYS_SHM_DETACH  32
#define SYS_DISK_READ   33
#define SYS_DISK_WRITE  34
#define SYS_DISK_INFO   35
#define SYS_UPTIME      36
#define SYS_REBOOT      37
#define SYS_NET_SEND    38
#define SYS_NET_RECV    39
#define SYS_NET_INFO    40
#define MAX_SYSCALLS     64

/* -- Syscall handler type ---------------------------------------------- */

typedef int64_t (*SyscallFn)(uint64_t arg1, uint64_t arg2, uint64_t arg3);

/* -- Public API -------------------------------------------------------- */

/* Initialize the syscall dispatch table. Returns number of registered calls. */
int  syscall_init(void);

/* Dispatch a syscall by number. Returns result or -1 on error. */
int64_t syscall_dispatch(uint64_t num, uint64_t a1, uint64_t a2, uint64_t a3);

/* Get count of registered (non-NULL) syscalls */
int  syscall_count(void);

/* Get the kernel task id (for VFS fd table access). */
int  syscall_kernel_task_id(void);

#endif /* LATERALUS_SYSCALL_H */
