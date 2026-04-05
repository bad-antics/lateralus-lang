/* =======================================================================
 * LateralusOS — System Call Dispatch Table
 * =======================================================================
 * Provides kernel services through a numbered dispatch table.
 * Currently all calls execute in ring 0 (kernel mode).
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ======================================================================= */

#include "syscall.h"
#include "../drivers/ata.h"
#include "../drivers/net.h"
#include "../fs/vfs.h"
#include "sched.h"

/* External kernel services */
extern void    serial_puts(const char *s);
extern void   *kmalloc(uint64_t size);
extern uint64_t tick_count;   /* PIT tick counter from kernel_stub.c */

/* -- Global kernel task id for the shell/initial process ------------ */

static int kernel_task_id = -1;

/* -- Syscall table ----------------------------------------------------- */

static SyscallFn syscall_table[MAX_SYSCALLS];
static int       registered_count = 0;

/* -- Helpers ----------------------------------------------------------- */

static void _itoa(int64_t val, char *buf, int max) {
    if (val < 0) { buf[0] = '-'; _itoa(-val, buf + 1, max - 1); return; }
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    char rev[24]; int rp = 0;
    uint64_t v = (uint64_t)val;
    while (v > 0 && rp < 23) { rev[rp++] = '0' + (v % 10); v /= 10; }
    int pos = 0;
    while (rp > 0 && pos < max - 1) buf[pos++] = rev[--rp];
    buf[pos] = '\0';
}

/* =======================================================================
 * Syscall implementations
 * ======================================================================= */

/* SYS_EXIT (0): exit current process */
static int64_t sys_exit(uint64_t code, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    serial_puts("[syscall] exit(");
    char buf[24]; _itoa((int64_t)code, buf, sizeof(buf));
    serial_puts(buf);
    serial_puts(")\n");
    /* In a real OS this would terminate the process.
       For now just halt. */
    __asm__ volatile ("cli; hlt");
    return 0;  /* unreachable */
}

/* SYS_READ (1): read from fd. Returns bytes read or -1. */
static int64_t sys_read(uint64_t fd, uint64_t buf_addr, uint64_t count) {
    if (kernel_task_id < 0) return -1;
    return (int64_t)vfs_read(kernel_task_id, (int)fd, (void*)buf_addr, (uint32_t)count);
}

/* SYS_WRITE (2): write to fd. fd=1 => stdout, fd=2 => stderr. */
static int64_t sys_write(uint64_t fd, uint64_t buf_addr, uint64_t count) {
    if (kernel_task_id < 0) {
        /* Fallback: write to serial directly */
        if (fd == 1 || fd == 2) {
            const char *p = (const char *)buf_addr;
            for (uint64_t i = 0; i < count; i++) {
                char tmp[2] = { p[i], '\0' };
                serial_puts(tmp);
            }
            return (int64_t)count;
        }
        return -1;
    }
    return (int64_t)vfs_write(kernel_task_id, (int)fd, (const void*)buf_addr, (uint32_t)count);
}

/* SYS_OPEN (3): open a file. Returns fd or -1. */
static int64_t sys_open(uint64_t path_addr, uint64_t flags, uint64_t mode) {
    (void)mode;
    if (kernel_task_id < 0) return -1;
    return (int64_t)vfs_open(kernel_task_id, (const char*)path_addr, (uint32_t)flags);
}

/* SYS_CLOSE (4): close fd */
static int64_t sys_close(uint64_t fd, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    if (kernel_task_id < 0) return -1;
    return (int64_t)vfs_close(kernel_task_id, (int)fd);
}

/* SYS_GETPID (8): return current process ID */
static int64_t sys_getpid(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a1; (void)a2; (void)a3;
    return (int64_t)sched_current_tid();
}

/* SYS_SLEEP (9): sleep for N milliseconds */
static int64_t sys_sleep(uint64_t ms, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    sched_sleep((uint32_t)ms);
    return 0;
}

/* SYS_YIELD (10): yield execution */
static int64_t sys_yield(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a1; (void)a2; (void)a3;
    sched_yield();
    return 0;
}

/* SYS_BRK (13): adjust heap break. Returns new break or -1. */
static int64_t sys_brk(uint64_t new_brk, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    if (new_brk == 0) {
        /* Query: just return something reasonable */
        return 0x400000;
    }
    /* In a real OS this adjusts the process heap.
       For now just accept anything. */
    return (int64_t)new_brk;
}

/* SYS_TIME (24): get system uptime in milliseconds */
static int64_t sys_time(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a1; (void)a2; (void)a3;
    return (int64_t)tick_count;
}

/* SYS_DISK_READ (33): read disk sectors.
   arg1 = drive | (count << 8), arg2 = LBA, arg3 = buffer address */
static int64_t sys_disk_read(uint64_t drv_count, uint64_t lba, uint64_t buf) {
    int drive = drv_count & 0xFF;
    int count = (drv_count >> 8) & 0xFF;
    if (count == 0) count = 1;
    return ata_read_sectors(drive, (uint32_t)lba, (uint8_t)count, (void *)buf);
}

/* SYS_DISK_WRITE (34): write disk sectors.
   arg1 = drive | (count << 8), arg2 = LBA, arg3 = buffer address */
static int64_t sys_disk_write(uint64_t drv_count, uint64_t lba, uint64_t buf) {
    int drive = drv_count & 0xFF;
    int count = (drv_count >> 8) & 0xFF;
    if (count == 0) count = 1;
    return ata_write_sectors(drive, (uint32_t)lba, (uint8_t)count, (const void *)buf);
}

/* SYS_DISK_INFO (35): get disk info.
   arg1 = drive, returns 1 if present, 0 if not.
   If arg2 != 0, writes size_mb there. */
static int64_t sys_disk_info(uint64_t drive, uint64_t out_size, uint64_t a3) {
    (void)a3;
    const AtaDriveInfo *info = ata_get_drive((int)drive);
    if (!info) return 0;
    if (out_size) {
        uint32_t *p = (uint32_t *)out_size;
        *p = info->size_mb;
    }
    return 1;
}

/* SYS_UPTIME (36): alias for SYS_TIME */
static int64_t sys_uptime(uint64_t a1, uint64_t a2, uint64_t a3) {
    return sys_time(a1, a2, a3);
}

/* SYS_REBOOT (37): reboot the system */
static int64_t sys_reboot(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a1; (void)a2; (void)a3;
    serial_puts("[syscall] reboot requested\n");
    /* Triple fault → reboot */
    __asm__ volatile (
        "lidt (%%rax)"
        : : "a"(0)
    );
    return 0;  /* unreachable */
}

/* SYS_NET_SEND (38): send a raw Ethernet frame
   a1 = pointer to frame data, a2 = length */
static int64_t sys_net_send(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a3;
    return (int64_t)net_send((const void *)a1, (uint16_t)a2);
}

/* SYS_NET_RECV (39): poll for received packet
   a1 = pointer to buffer, a2 = buffer size */
static int64_t sys_net_recv(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a3;
    return (int64_t)net_recv((void *)a1, (uint16_t)a2);
}

/* SYS_NET_INFO (40): get NIC info
   Returns 1 if NIC present, 0 otherwise.
   If a1 != 0, copies MAC (6 bytes) to that address. */
static int64_t sys_net_info(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    const NetDeviceInfo *ni = net_get_info();
    if (!ni) return 0;
    if (a1) {
        uint8_t *dst = (uint8_t *)a1;
        for (int i = 0; i < 6; i++) dst[i] = ni->mac[i];
    }
    return 1;
}

/* SYS_PIPE (20): create a pipe.
   a1 = pointer to int[2] (read_fd, write_fd). Returns 0 or -1. */
static int64_t sys_pipe(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    if (kernel_task_id < 0) return -1;
    int *fds = (int *)a1;
    return (int64_t)vfs_pipe(kernel_task_id, &fds[0], &fds[1]);
}

/* SYS_DUP (21): duplicate a file descriptor.
   a1 = fd to dup. Returns new fd or -1. */
static int64_t sys_dup(uint64_t a1, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    if (kernel_task_id < 0) return -1;
    return (int64_t)vfs_dup(kernel_task_id, (int)a1);
}

/* SYS_SPAWN (25): create a new task.
   a1 = pointer to TaskEntry function, a2 = arg pointer,
   a3 = priority (0-3). Returns tid or -1. */
static int64_t sys_spawn(uint64_t entry, uint64_t arg, uint64_t priority) {
    if (!entry) return -1;
    uint8_t prio = (uint8_t)(priority & 0x3);
    return (int64_t)sched_create("user-task",
                                 (TaskEntry)(void *)entry,
                                 (void *)arg, prio);
}

/* SYS_WAIT (7): wait for a child task to exit.
   a1 = child tid. Returns exit code or -1. */
static int64_t sys_wait(uint64_t child_tid, uint64_t a2, uint64_t a3) {
    (void)a2; (void)a3;
    return (int64_t)sched_wait((int)child_tid);
}

/* SYS_KILL (22): send signal to a task.
   a1 = tid, a2 = signum (0 = SIG_TERM default). Returns 0 on success, -1 on failure. */
static int64_t sys_kill_task(uint64_t tid, uint64_t a2, uint64_t a3) {
    (void)a3;
    int signum = (a2 == 0) ? SIG_TERM : (int)a2;
    if (signum <= 0 || signum >= SIG_MAX) return -1;
    return (int64_t)sched_signal((int)tid, signum);
}

/* =======================================================================
 * Public API
 * ======================================================================= */

int syscall_init(void) {
    /* Initialize VFS and allocate kernel task fd table */
    vfs_init();
    kernel_task_id = vfs_alloc_task();

    /* Clear table */
    for (int i = 0; i < MAX_SYSCALLS; i++)
        syscall_table[i] = (SyscallFn)0;

    /* Register handlers */
    syscall_table[SYS_EXIT]       = sys_exit;
    syscall_table[SYS_READ]       = sys_read;
    syscall_table[SYS_WRITE]      = sys_write;
    syscall_table[SYS_OPEN]       = sys_open;
    syscall_table[SYS_CLOSE]      = sys_close;
    syscall_table[SYS_GETPID]     = sys_getpid;
    syscall_table[SYS_SLEEP]      = sys_sleep;
    syscall_table[SYS_YIELD]      = sys_yield;
    syscall_table[SYS_BRK]        = sys_brk;
    syscall_table[SYS_TIME]       = sys_time;
    syscall_table[SYS_DISK_READ]  = sys_disk_read;
    syscall_table[SYS_DISK_WRITE] = sys_disk_write;
    syscall_table[SYS_DISK_INFO]  = sys_disk_info;
    syscall_table[SYS_UPTIME]     = sys_uptime;
    syscall_table[SYS_REBOOT]     = sys_reboot;
    syscall_table[SYS_NET_SEND]   = sys_net_send;
    syscall_table[SYS_NET_RECV]   = sys_net_recv;
    syscall_table[SYS_NET_INFO]   = sys_net_info;
    syscall_table[SYS_PIPE]       = sys_pipe;
    syscall_table[SYS_DUP]        = sys_dup;
    syscall_table[SYS_KILL]       = sys_kill_task;
    syscall_table[SYS_SPAWN]      = sys_spawn;
    syscall_table[SYS_WAIT]       = sys_wait;

    /* Count registered */
    registered_count = 0;
    for (int i = 0; i < MAX_SYSCALLS; i++) {
        if (syscall_table[i]) registered_count++;
    }

    return registered_count;
}

int64_t syscall_dispatch(uint64_t num, uint64_t a1, uint64_t a2, uint64_t a3) {
    if (num >= MAX_SYSCALLS || !syscall_table[num]) {
        serial_puts("[syscall] invalid syscall #");
        char buf[12]; _itoa((int64_t)num, buf, sizeof(buf));
        serial_puts(buf);
        serial_puts("\n");
        return -1;
    }
    return syscall_table[num](a1, a2, a3);
}

int syscall_count(void) {
    return registered_count;
}

int syscall_kernel_task_id(void) {
    return kernel_task_id;
}
