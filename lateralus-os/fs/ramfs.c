/* =======================================================================
 * LateralusOS — RAM Filesystem Implementation
 * =======================================================================
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ======================================================================= */

#include "ramfs.h"

/* -- Static node pool --------------------------------------------------- */

static RamfsNode nodes[RAMFS_MAX_NODES];
static int node_count = 0;

/* -- Tiny string helpers ------------------------------------------------ */

static int _rlen(const char *s) { int n = 0; while (s[n]) n++; return n; }

static void _rcpy(char *dst, const char *src, int max) {
    int i = 0;
    while (src[i] && i < max - 1) { dst[i] = src[i]; i++; }
    dst[i] = 0;
}

static void _rcat(char *dst, const char *src, int max) {
    int n = _rlen(dst);
    int i = 0;
    while (src[i] && n + i < max - 1) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

static int _rcmp(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return (int)(unsigned char)*a - (int)(unsigned char)*b;
}

/* -- Allocate a new node ------------------------------------------------ */

static int alloc_node(void) {
    for (int i = 0; i < RAMFS_MAX_NODES; i++) {
        if (!nodes[i].in_use) {
            nodes[i].in_use     = 1;
            nodes[i].size       = 0;
            nodes[i].child_count = 0;
            nodes[i].parent     = -1;
            nodes[i].content[0] = 0;
            nodes[i].name[0]    = 0;
            node_count++;
            return i;
        }
    }
    return -1;  /* pool exhausted */
}

/* -- Initialize filesystem ---------------------------------------------- */

void ramfs_init(void) {
    /* Clear all nodes */
    for (int i = 0; i < RAMFS_MAX_NODES; i++) {
        nodes[i].in_use = 0;
    }
    node_count = 0;

    /* Create root directory "/" */
    int root = alloc_node();
    _rcpy(nodes[root].name, "/", RAMFS_MAX_NAME);
    nodes[root].type   = RAMFS_DIR;
    nodes[root].parent = -1;

    /* Create /home directory */
    int home = ramfs_mkdir(root, "home");

    /* Create /etc directory */
    int etc = ramfs_mkdir(root, "etc");

    /* Create /tmp directory */
    ramfs_mkdir(root, "tmp");

    /* Create /etc/hostname */
    int hostname = ramfs_create(etc, "hostname");
    if (hostname >= 0) {
        ramfs_write(hostname, "lateralus", 9);
    }

    /* Create /etc/motd */
    int motd = ramfs_create(etc, "motd");
    if (motd >= 0) {
        const char *msg = "Welcome to LateralusOS v0.2.0\n"
                          "Spiral Out, Keep Going\n";
        ramfs_write(motd, msg, _rlen(msg));
    }

    /* Create /home/readme.txt */
    int readme = ramfs_create(home, "readme.txt");
    if (readme >= 0) {
        const char *txt =
            "LateralusOS — README\n"
            "====================\n"
            "\n"
            "A bare-metal operating system built\n"
            "with the Lateralus language.\n"
            "\n"
            "Features:\n"
            "  - x86_64 long mode\n"
            "  - RAM filesystem (ramfs)\n"
            "  - Framebuffer GUI (1024x768)\n"
            "  - Interactive terminal\n"
            "  - Catppuccin color theme\n"
            "\n"
            "Commands: ls, cat, touch, mkdir,\n"
            "          rm, echo, cd, pwd\n"
            "\n"
            "Copyright (c) 2025 bad-antics\n";
        ramfs_write(readme, txt, _rlen(txt));
    }

    /* Create /home/hello.ltl */
    int hello = ramfs_create(home, "hello.ltl");
    if (hello >= 0) {
        const char *src =
            "// Hello World in Lateralus\n"
            "fn main() {\n"
            "    println(\"Hello from LateralusOS!\")\n"
            "    let x = 42\n"
            "    println(\"The answer is: {x}\")\n"
            "}\n";
        ramfs_write(hello, src, _rlen(src));
    }

    /* Create /home/spiral.txt */
    int spiral = ramfs_create(home, "spiral.txt");
    if (spiral >= 0) {
        const char *art =
            "    *\n"
            "   * *\n"
            "  *   *\n"
            " *     *\n"
            "  *   *\n"
            "   * *\n"
            "    *\n"
            "\n"
            "Spiral Out, Keep Going\n";
        ramfs_write(spiral, art, _rlen(art));
    }
}

/* -- Create a file ------------------------------------------------------ */

int ramfs_create(int parent_idx, const char *name) {
    if (parent_idx < 0 || parent_idx >= RAMFS_MAX_NODES) return -1;
    if (!nodes[parent_idx].in_use || nodes[parent_idx].type != RAMFS_DIR) return -1;
    if (nodes[parent_idx].child_count >= RAMFS_MAX_CHILDREN) return -1;

    /* Check for duplicate name */
    if (ramfs_find(parent_idx, name) >= 0) return -1;

    int idx = alloc_node();
    if (idx < 0) return -1;

    _rcpy(nodes[idx].name, name, RAMFS_MAX_NAME);
    nodes[idx].type   = RAMFS_FILE;
    nodes[idx].parent = parent_idx;

    /* Add to parent's children */
    nodes[parent_idx].children[nodes[parent_idx].child_count++] = idx;

    return idx;
}

/* -- Create a directory ------------------------------------------------- */

int ramfs_mkdir(int parent_idx, const char *name) {
    if (parent_idx < 0 || parent_idx >= RAMFS_MAX_NODES) return -1;
    if (!nodes[parent_idx].in_use || nodes[parent_idx].type != RAMFS_DIR) return -1;
    if (nodes[parent_idx].child_count >= RAMFS_MAX_CHILDREN) return -1;

    /* Check for duplicate name */
    if (ramfs_find(parent_idx, name) >= 0) return -1;

    int idx = alloc_node();
    if (idx < 0) return -1;

    _rcpy(nodes[idx].name, name, RAMFS_MAX_NAME);
    nodes[idx].type   = RAMFS_DIR;
    nodes[idx].parent = parent_idx;

    /* Add to parent's children */
    nodes[parent_idx].children[nodes[parent_idx].child_count++] = idx;

    return idx;
}

/* -- Write to file ------------------------------------------------------ */

int ramfs_write(int node_idx, const char *data, uint32_t len) {
    if (node_idx < 0 || node_idx >= RAMFS_MAX_NODES) return -1;
    if (!nodes[node_idx].in_use || nodes[node_idx].type != RAMFS_FILE) return -1;
    if (len > RAMFS_MAX_CONTENT - 1) len = RAMFS_MAX_CONTENT - 1;

    for (uint32_t i = 0; i < len; i++)
        nodes[node_idx].content[i] = data[i];
    nodes[node_idx].content[len] = 0;
    nodes[node_idx].size = len;

    return (int)len;
}

/* -- Append to file ----------------------------------------------------- */

int ramfs_append(int node_idx, const char *data, uint32_t len) {
    if (node_idx < 0 || node_idx >= RAMFS_MAX_NODES) return -1;
    if (!nodes[node_idx].in_use || nodes[node_idx].type != RAMFS_FILE) return -1;

    uint32_t cur = nodes[node_idx].size;
    uint32_t avail = RAMFS_MAX_CONTENT - 1 - cur;
    if (len > avail) len = avail;

    for (uint32_t i = 0; i < len; i++)
        nodes[node_idx].content[cur + i] = data[i];
    nodes[node_idx].content[cur + len] = 0;
    nodes[node_idx].size = cur + len;

    return (int)len;
}

/* -- Read from file ----------------------------------------------------- */

int ramfs_read(int node_idx, char *buf, uint32_t buflen) {
    if (node_idx < 0 || node_idx >= RAMFS_MAX_NODES) return -1;
    if (!nodes[node_idx].in_use || nodes[node_idx].type != RAMFS_FILE) return -1;

    uint32_t len = nodes[node_idx].size;
    if (len > buflen - 1) len = buflen - 1;

    for (uint32_t i = 0; i < len; i++)
        buf[i] = nodes[node_idx].content[i];
    buf[len] = 0;

    return (int)len;
}

/* -- Find child by name ------------------------------------------------ */

int ramfs_find(int parent_idx, const char *name) {
    if (parent_idx < 0 || parent_idx >= RAMFS_MAX_NODES) return -1;
    if (!nodes[parent_idx].in_use || nodes[parent_idx].type != RAMFS_DIR) return -1;

    for (int i = 0; i < nodes[parent_idx].child_count; i++) {
        int c = nodes[parent_idx].children[i];
        if (nodes[c].in_use && _rcmp(nodes[c].name, name) == 0)
            return c;
    }
    return -1;
}

/* -- List directory ----------------------------------------------------- */

int ramfs_list(int dir_idx, char *buf, uint32_t buflen) {
    if (dir_idx < 0 || dir_idx >= RAMFS_MAX_NODES) return -1;
    if (!nodes[dir_idx].in_use || nodes[dir_idx].type != RAMFS_DIR) return -1;

    buf[0] = 0;
    for (int i = 0; i < nodes[dir_idx].child_count; i++) {
        int c = nodes[dir_idx].children[i];
        if (!nodes[c].in_use) continue;

        if (nodes[c].type == RAMFS_DIR) {
            _rcat(buf, nodes[c].name, (int)buflen);
            _rcat(buf, "/", (int)buflen);
        } else {
            _rcat(buf, nodes[c].name, (int)buflen);
        }
        _rcat(buf, "\n", (int)buflen);
    }
    return 0;
}

/* -- Remove node -------------------------------------------------------- */

int ramfs_remove(int node_idx) {
    if (node_idx <= 0 || node_idx >= RAMFS_MAX_NODES) return -1;  /* can't remove root */
    if (!nodes[node_idx].in_use) return -1;

    /* Can't remove non-empty directory */
    if (nodes[node_idx].type == RAMFS_DIR && nodes[node_idx].child_count > 0)
        return -1;

    /* Remove from parent's children list */
    int parent = nodes[node_idx].parent;
    if (parent >= 0 && parent < RAMFS_MAX_NODES && nodes[parent].in_use) {
        for (int i = 0; i < nodes[parent].child_count; i++) {
            if (nodes[parent].children[i] == node_idx) {
                /* Shift remaining children down */
                for (int j = i; j < nodes[parent].child_count - 1; j++)
                    nodes[parent].children[j] = nodes[parent].children[j + 1];
                nodes[parent].child_count--;
                break;
            }
        }
    }

    nodes[node_idx].in_use = 0;
    node_count--;
    return 0;
}

/* -- Resolve absolute path ---------------------------------------------- */

int ramfs_resolve_path(const char *path) {
    if (!path || path[0] != '/') return -1;
    if (path[0] == '/' && path[1] == '\0') return 0;  /* root */

    int current = 0;  /* start at root */
    char component[RAMFS_MAX_NAME];
    int ci = 0;

    const char *p = path + 1;  /* skip leading '/' */
    while (1) {
        if (*p == '/' || *p == '\0') {
            component[ci] = 0;
            if (ci > 0) {
                if (_rcmp(component, "..") == 0) {
                    /* Go to parent */
                    if (nodes[current].parent >= 0)
                        current = nodes[current].parent;
                } else if (_rcmp(component, ".") != 0) {
                    /* Find child */
                    int child = ramfs_find(current, component);
                    if (child < 0) return -1;
                    current = child;
                }
            }
            ci = 0;
            if (*p == '\0') break;
            p++;
        } else {
            if (ci < RAMFS_MAX_NAME - 1)
                component[ci++] = *p;
            p++;
        }
    }

    return current;
}

/* -- Node info accessors ------------------------------------------------ */

const char *ramfs_node_name(int idx) {
    if (idx < 0 || idx >= RAMFS_MAX_NODES || !nodes[idx].in_use) return "";
    return nodes[idx].name;
}

RamfsType ramfs_node_type(int idx) {
    if (idx < 0 || idx >= RAMFS_MAX_NODES || !nodes[idx].in_use) return RAMFS_FILE;
    return nodes[idx].type;
}

uint32_t ramfs_node_size(int idx) {
    if (idx < 0 || idx >= RAMFS_MAX_NODES || !nodes[idx].in_use) return 0;
    return nodes[idx].size;
}

int ramfs_node_parent(int idx) {
    if (idx < 0 || idx >= RAMFS_MAX_NODES || !nodes[idx].in_use) return -1;
    return nodes[idx].parent;
}

int ramfs_node_child_count(int idx) {
    if (idx < 0 || idx >= RAMFS_MAX_NODES || !nodes[idx].in_use) return 0;
    return nodes[idx].child_count;
}

int ramfs_root(void) {
    return 0;
}

/* -- Build absolute path ------------------------------------------------ */

void ramfs_get_path(int idx, char *buf, uint32_t buflen) {
    if (idx < 0 || idx >= RAMFS_MAX_NODES || !nodes[idx].in_use) {
        buf[0] = '/'; buf[1] = 0;
        return;
    }

    /* Build path by traversing parents */
    char parts[8][RAMFS_MAX_NAME];
    int depth = 0;
    int cur = idx;
    while (cur >= 0 && depth < 8) {
        _rcpy(parts[depth], nodes[cur].name, RAMFS_MAX_NAME);
        depth++;
        cur = nodes[cur].parent;
    }

    buf[0] = 0;
    if (depth <= 1) {
        _rcpy(buf, "/", (int)buflen);
        return;
    }

    /* Reverse order (skip root's "/" since we add separators) */
    for (int i = depth - 2; i >= 0; i--) {
        _rcat(buf, "/", (int)buflen);
        _rcat(buf, parts[i], (int)buflen);
    }
}
