/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Virtual File System Layer
 * ═══════════════════════════════════════════════════════════════════════
 * Per-task file descriptor table, connecting syscalls to the ramfs
 * backend. Provides POSIX-like open/read/write/close/dup/pipe semantics.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_VFS_H
#define LATERALUS_VFS_H

#include "../gui/types.h"

/* ── Limits ───────────────────────────────────────────────────────────── */

#define VFS_MAX_FD       32    /* max open fds per task               */
#define VFS_MAX_TASKS    32    /* max tasks with fd tables            */
#define VFS_PIPE_BUF    512    /* pipe buffer size                    */

/* ── Open flags (compatible subset of POSIX) ──────────────────────── */

#define O_RDONLY    0x0000
#define O_WRONLY    0x0001
#define O_RDWR      0x0002
#define O_CREAT     0x0040
#define O_TRUNC     0x0200
#define O_APPEND    0x0400

/* ── File descriptor types ────────────────────────────────────────── */

typedef enum {
    FD_NONE = 0,      /* unused slot                              */
    FD_FILE,           /* regular file backed by ramfs             */
    FD_CONSOLE,        /* stdin/stdout/stderr (VGA + serial)       */
    FD_PIPE_READ,      /* read end of a pipe                      */
    FD_PIPE_WRITE,     /* write end of a pipe                     */
    FD_NULL,           /* /dev/null                                */
} FdType;

/* ── Pipe state ───────────────────────────────────────────────────── */

typedef struct {
    uint8_t  buf[VFS_PIPE_BUF];
    uint16_t read_pos;
    uint16_t write_pos;
    uint16_t count;        /* bytes in buffer                      */
    uint8_t  read_open;    /* read end still open?                 */
    uint8_t  write_open;   /* write end still open?                */
} PipeState;

#define VFS_MAX_PIPES    16

/* ── File descriptor entry ────────────────────────────────────────── */

typedef struct {
    FdType   type;
    int      node_idx;     /* ramfs node index (for FD_FILE)        */
    uint32_t offset;       /* current read/write position           */
    uint32_t flags;        /* O_RDONLY, O_WRONLY, O_RDWR, etc.      */
    int      pipe_idx;     /* index into pipe table (for FD_PIPE)   */
} FdEntry;

/* ── Per-task fd table ────────────────────────────────────────────── */

typedef struct {
    FdEntry  fds[VFS_MAX_FD];
    int      cwd;          /* current working directory (ramfs idx) */
    uint8_t  in_use;       /* table in use?                        */
} FdTable;

/* ═══════════════════════════════════════════════════════════════════════
 * Public API
 * ═══════════════════════════════════════════════════════════════════════ */

/* Initialize the VFS subsystem. Called once at boot. */
void     vfs_init(void);

/* Allocate a fd table for a task. Returns task_id for the table, or -1. */
int      vfs_alloc_task(void);

/* Free a task's fd table, closing all open fds. */
void     vfs_free_task(int task_id);

/* ── File operations (all take task_id to identify the fd table) ──── */

/* Open a file by path. Returns fd (>= 0) or -1 on error. */
int      vfs_open(int task_id, const char *path, uint32_t flags);

/* Read up to `count` bytes from fd into buf. Returns bytes read, 0 on EOF, -1 on error. */
int32_t  vfs_read(int task_id, int fd, void *buf, uint32_t count);

/* Write `count` bytes from buf to fd. Returns bytes written, or -1 on error. */
int32_t  vfs_write(int task_id, int fd, const void *buf, uint32_t count);

/* Close a file descriptor. Returns 0 on success, -1 on error. */
int      vfs_close(int task_id, int fd);

/* Seek to a position in a file. Returns new position, or -1 on error. */
int32_t  vfs_seek(int task_id, int fd, int32_t offset, int whence);

/* Duplicate a file descriptor. Returns new fd, or -1 on error. */
int      vfs_dup(int task_id, int fd);

/* Duplicate fd to a specific target fd. Returns new_fd or -1. */
int      vfs_dup2(int task_id, int old_fd, int new_fd);

/* ── Pipe ─────────────────────────────────────────────────────────── */

/* Create a pipe. read_fd and write_fd are filled on success. Returns 0 or -1. */
int      vfs_pipe(int task_id, int *read_fd, int *write_fd);

/* ── Directory ────────────────────────────────────────────────────── */

/* Get the current working directory node index for a task. */
int      vfs_getcwd(int task_id);

/* Set the current working directory for a task. Returns 0 or -1. */
int      vfs_chdir(int task_id, const char *path);

/* ── Seek whence constants ────────────────────────────────────────── */

#define SEEK_SET  0
#define SEEK_CUR  1
#define SEEK_END  2

#endif /* LATERALUS_VFS_H */
