/* =======================================================================
 * LateralusOS — RAM Filesystem (ramfs)
 * =======================================================================
 * In-memory inode-based filesystem with directories and files.
 * Provides ls, cat, touch, mkdir, rm, write operations.
 *
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ======================================================================= */

#ifndef LATERALUS_RAMFS_H
#define LATERALUS_RAMFS_H

#include "../gui/types.h"

/* -- Limits ------------------------------------------------------------- */

#define RAMFS_MAX_NODES     64
#define RAMFS_MAX_NAME      32
#define RAMFS_MAX_CONTENT 2048
#define RAMFS_MAX_CHILDREN  16

/* -- Node types --------------------------------------------------------- */

typedef enum { RAMFS_FILE = 0, RAMFS_DIR = 1 } RamfsType;

/* -- Filesystem node (inode) -------------------------------------------- */

typedef struct {
    char       name[RAMFS_MAX_NAME];
    RamfsType  type;
    uint8_t    in_use;

    /* File content */
    char       content[RAMFS_MAX_CONTENT];
    uint32_t   size;        /* bytes of content */

    /* Directory children (indices into node pool) */
    int        children[RAMFS_MAX_CHILDREN];
    int        child_count;

    /* Parent node index (-1 for root) */
    int        parent;
} RamfsNode;

/* -- Public API --------------------------------------------------------- */

/* Initialize the filesystem with root /, /home, /etc, default files */
void ramfs_init(void);

/* Create a file in parent directory. Returns node index or -1. */
int ramfs_create(int parent_idx, const char *name);

/* Create a directory in parent directory. Returns node index or -1. */
int ramfs_mkdir(int parent_idx, const char *name);

/* Write data to a file node. Returns bytes written or -1. */
int ramfs_write(int node_idx, const char *data, uint32_t len);

/* Append data to a file node. Returns bytes written or -1. */
int ramfs_append(int node_idx, const char *data, uint32_t len);

/* Read a file node's content into buf. Returns bytes read or -1. */
int ramfs_read(int node_idx, char *buf, uint32_t buflen);

/* Find a child by name within a directory. Returns node index or -1. */
int ramfs_find(int parent_idx, const char *name);

/* List directory contents into buf (newline-separated). Returns 0 or -1. */
int ramfs_list(int dir_idx, char *buf, uint32_t buflen);

/* Remove a node (file or empty directory). Returns 0 or -1. */
int ramfs_remove(int node_idx);

/* Resolve an absolute path like "/home/readme.txt" to node index.
   Returns -1 if not found. */
int ramfs_resolve_path(const char *path);

/* Get node info */
const char *ramfs_node_name(int idx);
RamfsType   ramfs_node_type(int idx);
uint32_t    ramfs_node_size(int idx);
int         ramfs_node_parent(int idx);
int         ramfs_node_child_count(int idx);

/* Get the root node index (always 0) */
int ramfs_root(void);

/* Build absolute path for a node into buf */
void ramfs_get_path(int idx, char *buf, uint32_t buflen);

#endif /* LATERALUS_RAMFS_H */
