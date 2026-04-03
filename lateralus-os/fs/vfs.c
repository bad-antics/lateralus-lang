/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Virtual File System Layer
 * ═══════════════════════════════════════════════════════════════════════
 * Per-task file descriptor table connecting syscalls to the ramfs
 * backend. Provides POSIX-like open/read/write/close/dup/pipe semantics.
 *
 * fd 0 = stdin (console read)
 * fd 1 = stdout (VGA + serial write)
 * fd 2 = stderr (serial write)
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "vfs.h"
#include "ramfs.h"

/* ── External services ────────────────────────────────────────────────── */

extern void serial_puts(const char *s);

/* ── Internal state ───────────────────────────────────────────────────── */

static FdTable  fd_tables[VFS_MAX_TASKS];
static PipeState pipes[VFS_MAX_PIPES];
static int       pipe_count = 0;

/* ── Helpers ──────────────────────────────────────────────────────────── */

static int _str_eq(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return *a == *b;
}

static int _str_len(const char *s) {
    int n = 0; while (s[n]) n++;
    return n;
}

static int _find_free_fd(FdTable *ft) {
    for (int i = 0; i < VFS_MAX_FD; i++) {
        if (ft->fds[i].type == FD_NONE) return i;
    }
    return -1;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Initialization
 * ═══════════════════════════════════════════════════════════════════════ */

void vfs_init(void) {
    for (int t = 0; t < VFS_MAX_TASKS; t++) {
        fd_tables[t].in_use = 0;
        fd_tables[t].cwd = ramfs_root();
        for (int f = 0; f < VFS_MAX_FD; f++)
            fd_tables[t].fds[f].type = FD_NONE;
    }
    for (int p = 0; p < VFS_MAX_PIPES; p++) {
        pipes[p].read_pos   = 0;
        pipes[p].write_pos  = 0;
        pipes[p].count      = 0;
        pipes[p].read_open  = 0;
        pipes[p].write_open = 0;
    }
    pipe_count = 0;
    serial_puts("[vfs] initialized\n");
}

int vfs_alloc_task(void) {
    for (int t = 0; t < VFS_MAX_TASKS; t++) {
        if (!fd_tables[t].in_use) {
            fd_tables[t].in_use = 1;
            fd_tables[t].cwd = ramfs_root();
            for (int f = 0; f < VFS_MAX_FD; f++)
                fd_tables[t].fds[f].type = FD_NONE;

            /* Set up stdin / stdout / stderr */
            fd_tables[t].fds[0].type  = FD_CONSOLE;
            fd_tables[t].fds[0].flags = O_RDONLY;
            fd_tables[t].fds[1].type  = FD_CONSOLE;
            fd_tables[t].fds[1].flags = O_WRONLY;
            fd_tables[t].fds[2].type  = FD_CONSOLE;
            fd_tables[t].fds[2].flags = O_WRONLY;

            return t;
        }
    }
    return -1;
}

void vfs_free_task(int task_id) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return;
    FdTable *ft = &fd_tables[task_id];

    /* Close all open fds */
    for (int f = 0; f < VFS_MAX_FD; f++) {
        if (ft->fds[f].type != FD_NONE) {
            vfs_close(task_id, f);
        }
    }
    ft->in_use = 0;
}

/* ═══════════════════════════════════════════════════════════════════════
 * File operations
 * ═══════════════════════════════════════════════════════════════════════ */

int vfs_open(int task_id, const char *path, uint32_t flags) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (!fd_tables[task_id].in_use) return -1;

    FdTable *ft = &fd_tables[task_id];

    /* Special paths */
    if (_str_eq(path, "/dev/null")) {
        int fd = _find_free_fd(ft);
        if (fd < 0) return -1;
        ft->fds[fd].type     = FD_NULL;
        ft->fds[fd].flags    = flags;
        ft->fds[fd].offset   = 0;
        ft->fds[fd].node_idx = -1;
        ft->fds[fd].pipe_idx = -1;
        return fd;
    }

    /* Resolve path in ramfs */
    int node = ramfs_resolve_path(path);

    /* If not found and O_CREAT is set, create the file */
    if (node < 0 && (flags & O_CREAT)) {
        /* Find parent directory and filename */
        int parent = ft->cwd;

        /* Find last '/' to split dir from filename */
        const char *last_slash = path;
        const char *p = path;
        while (*p) { if (*p == '/') last_slash = p; p++; }

        if (path[0] == '/') {
            /* Absolute path */
            if (last_slash > path) {
                /* Resolve parent directory */
                char dir_path[128];
                int dlen = (int)(last_slash - path);
                if (dlen >= 127) dlen = 127;
                for (int i = 0; i < dlen; i++) dir_path[i] = path[i];
                dir_path[dlen] = '\0';
                parent = ramfs_resolve_path(dir_path);
                if (parent < 0) return -1;
            } else {
                parent = ramfs_root();
            }
            last_slash++;  /* skip the slash to get filename */
        } else {
            /* Relative path — use cwd as parent */
            parent = ft->cwd;
            last_slash = path;  /* the whole thing is the filename */
        }

        node = ramfs_create(parent, last_slash);
        if (node < 0) return -1;
    }

    if (node < 0) return -1;

    /* Don't open directories as files */
    if (ramfs_node_type(node) == RAMFS_DIR) return -1;

    int fd = _find_free_fd(ft);
    if (fd < 0) return -1;

    ft->fds[fd].type     = FD_FILE;
    ft->fds[fd].node_idx = node;
    ft->fds[fd].flags    = flags;
    ft->fds[fd].pipe_idx = -1;

    if (flags & O_TRUNC) {
        ramfs_write(node, "", 0);
        ft->fds[fd].offset = 0;
    } else if (flags & O_APPEND) {
        ft->fds[fd].offset = ramfs_node_size(node);
    } else {
        ft->fds[fd].offset = 0;
    }

    return fd;
}

int32_t vfs_read(int task_id, int fd, void *buf, uint32_t count) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (fd < 0 || fd >= VFS_MAX_FD) return -1;

    FdTable *ft = &fd_tables[task_id];
    FdEntry *fe = &ft->fds[fd];

    if (fe->type == FD_NONE) return -1;

    switch (fe->type) {
    case FD_FILE: {
        char file_buf[RAMFS_MAX_CONTENT];
        int file_len = ramfs_read(fe->node_idx, file_buf, sizeof(file_buf));
        if (file_len < 0) return -1;

        /* Calculate how much we can read from current offset */
        if (fe->offset >= (uint32_t)file_len) return 0;  /* EOF */
        uint32_t available = (uint32_t)file_len - fe->offset;
        if (count > available) count = available;

        uint8_t *dst = (uint8_t*)buf;
        for (uint32_t i = 0; i < count; i++)
            dst[i] = (uint8_t)file_buf[fe->offset + i];

        fe->offset += count;
        return (int32_t)count;
    }
    case FD_CONSOLE:
        /* Console read — currently no buffered input. Returns 0 (no data). */
        return 0;

    case FD_PIPE_READ: {
        if (fe->pipe_idx < 0 || fe->pipe_idx >= VFS_MAX_PIPES) return -1;
        PipeState *ps = &pipes[fe->pipe_idx];

        if (ps->count == 0) {
            /* No data — if write end is closed, return EOF */
            if (!ps->write_open) return 0;
            return 0;  /* would block, but we're non-blocking for now */
        }

        uint32_t to_read = count;
        if (to_read > ps->count) to_read = ps->count;

        uint8_t *dst = (uint8_t*)buf;
        for (uint32_t i = 0; i < to_read; i++) {
            dst[i] = ps->buf[ps->read_pos];
            ps->read_pos = (ps->read_pos + 1) % VFS_PIPE_BUF;
        }
        ps->count -= (uint16_t)to_read;
        return (int32_t)to_read;
    }
    case FD_NULL:
        return 0;  /* always EOF */

    default:
        return -1;
    }
}

int32_t vfs_write(int task_id, int fd, const void *buf, uint32_t count) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (fd < 0 || fd >= VFS_MAX_FD) return -1;

    FdTable *ft = &fd_tables[task_id];
    FdEntry *fe = &ft->fds[fd];

    if (fe->type == FD_NONE) return -1;

    switch (fe->type) {
    case FD_FILE: {
        /* Read existing content, write at offset */
        char file_buf[RAMFS_MAX_CONTENT];
        int existing = ramfs_read(fe->node_idx, file_buf, sizeof(file_buf));
        if (existing < 0) existing = 0;

        const uint8_t *src = (const uint8_t*)buf;

        if (fe->flags & O_APPEND) {
            /* Append mode */
            if ((uint32_t)existing + count > RAMFS_MAX_CONTENT)
                count = RAMFS_MAX_CONTENT - (uint32_t)existing;
            return ramfs_append(fe->node_idx, (const char*)src, count);
        }

        /* Write at offset */
        uint32_t new_size = fe->offset + count;
        if (new_size > RAMFS_MAX_CONTENT) {
            count = RAMFS_MAX_CONTENT - fe->offset;
            new_size = RAMFS_MAX_CONTENT;
        }

        /* Extend file if needed (fill gap with zeros) */
        if (fe->offset > (uint32_t)existing) {
            for (uint32_t i = (uint32_t)existing; i < fe->offset; i++)
                file_buf[i] = '\0';
        }

        /* Copy new data */
        for (uint32_t i = 0; i < count; i++)
            file_buf[fe->offset + i] = (char)src[i];

        /* Update total size */
        if (new_size > (uint32_t)existing)
            existing = (int)new_size;

        /* Write the whole file back */
        ramfs_write(fe->node_idx, file_buf, (uint32_t)existing);
        fe->offset += count;
        return (int32_t)count;
    }
    case FD_CONSOLE: {
        /* fd 1 (stdout) → VGA + serial, fd 2 (stderr) → serial only */
        const char *src = (const char*)buf;
        for (uint32_t i = 0; i < count; i++) {
            char tmp[2] = { src[i], '\0' };
            serial_puts(tmp);
        }
        return (int32_t)count;
    }
    case FD_PIPE_WRITE: {
        if (fe->pipe_idx < 0 || fe->pipe_idx >= VFS_MAX_PIPES) return -1;
        PipeState *ps = &pipes[fe->pipe_idx];

        if (!ps->read_open) return -1;  /* broken pipe */

        uint32_t space = VFS_PIPE_BUF - ps->count;
        uint32_t to_write = count;
        if (to_write > space) to_write = space;

        const uint8_t *src = (const uint8_t*)buf;
        for (uint32_t i = 0; i < to_write; i++) {
            ps->buf[ps->write_pos] = src[i];
            ps->write_pos = (ps->write_pos + 1) % VFS_PIPE_BUF;
        }
        ps->count += (uint16_t)to_write;
        return (int32_t)to_write;
    }
    case FD_NULL:
        return (int32_t)count;  /* /dev/null: accept and discard */

    default:
        return -1;
    }
}

int vfs_close(int task_id, int fd) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (fd < 0 || fd >= VFS_MAX_FD) return -1;

    FdTable *ft = &fd_tables[task_id];
    FdEntry *fe = &ft->fds[fd];

    if (fe->type == FD_NONE) return -1;

    /* Handle pipe cleanup */
    if (fe->type == FD_PIPE_READ && fe->pipe_idx >= 0) {
        pipes[fe->pipe_idx].read_open = 0;
    } else if (fe->type == FD_PIPE_WRITE && fe->pipe_idx >= 0) {
        pipes[fe->pipe_idx].write_open = 0;
    }

    fe->type     = FD_NONE;
    fe->node_idx = -1;
    fe->offset   = 0;
    fe->flags    = 0;
    fe->pipe_idx = -1;
    return 0;
}

int32_t vfs_seek(int task_id, int fd, int32_t offset, int whence) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (fd < 0 || fd >= VFS_MAX_FD) return -1;

    FdEntry *fe = &fd_tables[task_id].fds[fd];
    if (fe->type != FD_FILE) return -1;

    uint32_t file_size = ramfs_node_size(fe->node_idx);
    int32_t new_pos;

    switch (whence) {
    case SEEK_SET: new_pos = offset; break;
    case SEEK_CUR: new_pos = (int32_t)fe->offset + offset; break;
    case SEEK_END: new_pos = (int32_t)file_size + offset; break;
    default: return -1;
    }

    if (new_pos < 0) new_pos = 0;
    fe->offset = (uint32_t)new_pos;
    return new_pos;
}

int vfs_dup(int task_id, int fd) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (fd < 0 || fd >= VFS_MAX_FD) return -1;

    FdTable *ft = &fd_tables[task_id];
    FdEntry *src = &ft->fds[fd];
    if (src->type == FD_NONE) return -1;

    int new_fd = _find_free_fd(ft);
    if (new_fd < 0) return -1;

    ft->fds[new_fd] = *src;  /* copy the entry */

    /* If pipe, keep the open ref count */
    if (src->type == FD_PIPE_READ && src->pipe_idx >= 0) {
        pipes[src->pipe_idx].read_open = 1;
    } else if (src->type == FD_PIPE_WRITE && src->pipe_idx >= 0) {
        pipes[src->pipe_idx].write_open = 1;
    }

    return new_fd;
}

int vfs_dup2(int task_id, int old_fd, int new_fd) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (old_fd < 0 || old_fd >= VFS_MAX_FD) return -1;
    if (new_fd < 0 || new_fd >= VFS_MAX_FD) return -1;

    FdTable *ft = &fd_tables[task_id];
    if (ft->fds[old_fd].type == FD_NONE) return -1;

    /* Close existing fd at new_fd */
    if (ft->fds[new_fd].type != FD_NONE) {
        vfs_close(task_id, new_fd);
    }

    ft->fds[new_fd] = ft->fds[old_fd];
    return new_fd;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Pipe
 * ═══════════════════════════════════════════════════════════════════════ */

int vfs_pipe(int task_id, int *read_fd, int *write_fd) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    if (pipe_count >= VFS_MAX_PIPES) return -1;

    FdTable *ft = &fd_tables[task_id];

    int rfd = _find_free_fd(ft);
    if (rfd < 0) return -1;
    ft->fds[rfd].type = FD_PIPE_READ;  /* reserve it */

    /* Find another free fd */
    int wfd = _find_free_fd(ft);
    if (wfd < 0) {
        ft->fds[rfd].type = FD_NONE;  /* undo */
        return -1;
    }

    int pi = pipe_count++;
    pipes[pi].read_pos   = 0;
    pipes[pi].write_pos  = 0;
    pipes[pi].count      = 0;
    pipes[pi].read_open  = 1;
    pipes[pi].write_open = 1;

    ft->fds[rfd].type     = FD_PIPE_READ;
    ft->fds[rfd].pipe_idx = pi;
    ft->fds[rfd].offset   = 0;
    ft->fds[rfd].flags    = O_RDONLY;
    ft->fds[rfd].node_idx = -1;

    ft->fds[wfd].type     = FD_PIPE_WRITE;
    ft->fds[wfd].pipe_idx = pi;
    ft->fds[wfd].offset   = 0;
    ft->fds[wfd].flags    = O_WRONLY;
    ft->fds[wfd].node_idx = -1;

    *read_fd  = rfd;
    *write_fd = wfd;

    serial_puts("[vfs] pipe created\n");
    return 0;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Directory
 * ═══════════════════════════════════════════════════════════════════════ */

int vfs_getcwd(int task_id) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;
    return fd_tables[task_id].cwd;
}

int vfs_chdir(int task_id, const char *path) {
    if (task_id < 0 || task_id >= VFS_MAX_TASKS) return -1;

    int node = ramfs_resolve_path(path);
    if (node < 0) return -1;
    if (ramfs_node_type(node) != RAMFS_DIR) return -1;

    fd_tables[task_id].cwd = node;
    return 0;
}
