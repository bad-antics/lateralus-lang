"""
lateralus_lang/codegen/c.py  ─  LTL → C99 Transpiler
═══════════════════════════════════════════════════════════════════════════
Converts a Lateralus (.ltl) AST to C99 source code suitable for bare-metal
compilation (kernel, embedded, OS components) or hosted userspace programs.

This backend is the foundation for LateralusOS — enabling Lateralus programs
to be compiled with GCC/Clang for any target architecture (x86_64, ARM,
RISC-V, etc.).

Modes
─────
  · HOSTED   — links against libc, includes main() wrapper, runtime GC
  · FREESTANDING — no libc, no runtime, static alloc only (OS kernel mode)

Output
──────
  · Single .c file with all definitions (header-free for simplicity)
  · Optional companion .h file for public symbols
  · Build command hints in comments

v1.5.0 — 2026-03-30
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Dict, List, Optional, Set

from ..ast_nodes import (
    # v1.6 — low-level / OS-dev
    AddrOfExpr,
    AlignofExpr,
    AssignStmt,
    ASTVisitor,
    # v1.6 — async / concurrency
    AsyncForStmt,
    AwaitExpr,
    BindingPattern,
    BinOp,
    BlockStmt,
    CallExpr,
    CancelExpr,
    CastExpr,
    # v1.7 — conditional compilation
    CfgAttr,
    CfgExpr,
    ChainExpr,
    ChannelExpr,
    ComprehensionExpr,
    # v1.8 — metaprogramming
    CompTimeBlock,
    ConstFnDecl,
    DerefExpr,
    DeriveAttr,
    EmitStmt,
    EnumDecl,
    ExprStmt,
    ExternDecl,
    FieldExpr,
    FnDecl,
    ForeignBlock,
    ForeignParam,
    ForStmt,
    GuardExpr,
    Ident,
    IfStmt,
    ImplBlock,
    ImportStmt,
    IndexExpr,
    InlineAsm,
    InterfaceDecl,
    InterpolatedStr,
    LambdaExpr,
    LetDecl,
    ListExpr,
    Literal,
    LiteralPattern,
    LoopStmt,
    MacroDecl,
    MacroInvocation,
    MapExpr,
    MatchStmt,
    MeasureBlock,
    Node,
    NurseryBlock,
    OffsetofExpr,
    OptionExpr,
    Param,
    PipelineAssign,
    ProbeExpr,
    Program,
    PropagateExpr,
    QuoteExpr,
    RangeExpr,
    ReflectExpr,
    ResultExpr,
    ReturnStmt,
    SpawnExpr,
    SpreadExpr,
    StaticDecl,
    StructDecl,
    StructLiteral,
    TernaryExpr,
    ThrowStmt,
    TryExpr,
    TryStmt,
    TupleExpr,
    TypeAlias,
    TypeMatchExpr,
    TypeRef,
    UnaryOp,
    UnsafeBlock,
    VolatileExpr,
    WhereClause,
    WhileStmt,
    WildcardPattern,
    YieldExpr,
)

# ─────────────────────────────────────────────────────────────────────────────
# Build mode
# ─────────────────────────────────────────────────────────────────────────────

class CMode(Enum):
    HOSTED       = auto()  # Standard userspace (links libc)
    FREESTANDING = auto()  # Bare-metal / kernel (no libc, no runtime)


# ─────────────────────────────────────────────────────────────────────────────
# Code writer
# ─────────────────────────────────────────────────────────────────────────────

class _W:
    """Indented C code writer."""

    def __init__(self):
        self._lines: List[str] = []
        self._indent: int = 0

    def line(self, text: str = ""):
        if text:
            self._lines.append("    " * self._indent + text)
        else:
            self._lines.append("")

    def indent(self):
        self._indent += 1

    def dedent(self):
        self._indent = max(0, self._indent - 1)

    def block_open(self, header: str = ""):
        if header:
            self.line(f"{header} {{")
        else:
            self.line("{")
        self.indent()

    def block_close(self, suffix: str = ""):
        self.dedent()
        self.line("}" + suffix)

    def comment(self, text: str):
        self.line(f"/* {text} */")

    def raw(self, text: str):
        for ln in text.splitlines():
            self._lines.append(ln)

    def result(self) -> str:
        return "\n".join(self._lines) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# Type mapping  (Lateralus type annotations → C types)
# ─────────────────────────────────────────────────────────────────────────────

_TYPE_MAP: Dict[str, str] = {
    "int":    "int64_t",
    "float":  "double",
    "str":    "ltl_string_t*",
    "bool":   "bool",
    "byte":   "uint8_t",
    "none":   "void",
    "nil":    "void",
    "any":    "ltl_value_t",
    "void":   "void",
    # v1.6 fixed-width integer types
    "u8":     "uint8_t",
    "u16":    "uint16_t",
    "u32":    "uint32_t",
    "u64":    "uint64_t",
    "i8":     "int8_t",
    "i16":    "int16_t",
    "i32":    "int32_t",
    "i64":    "int64_t",
    "usize":  "size_t",
    "isize":  "int64_t",
    # Function type → function pointer (generic)
    "fn":     "void*",
    "Fn":     "void*",
}


def _c_type(type_ref: Optional[TypeRef], default: str = "ltl_value_t") -> str:
    """Convert a Lateralus TypeRef to C type string."""
    if type_ref is None:
        return default
    name = getattr(type_ref, "name", None)
    if isinstance(name, str):
        # Handle Ptr<T> → T*
        if name == "Ptr" and hasattr(type_ref, "params") and type_ref.params:
            inner = _c_type(type_ref.params[0], "void")
            return f"{inner}*"
        return _TYPE_MAP.get(name, name)
    return default


# ─────────────────────────────────────────────────────────────────────────────
# Preamble templates
# ─────────────────────────────────────────────────────────────────────────────

_HOSTED_PREAMBLE = '''\
/* ═══════════════════════════════════════════════════════════════════════
 * Generated by LATERALUS C Transpiler v1.5.0
 * Mode: HOSTED (userspace, libc linked)
 *
 * Build:
 *   gcc -O2 -std=c99 -o program program.c -lm
 *   clang -O2 -std=c99 -o program program.c -lm
 * ═══════════════════════════════════════════════════════════════════════ */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <assert.h>

/* ── Lateralus Runtime Types ─────────────────────────────────────────── */

typedef struct ltl_string {
    int64_t len;
    int64_t cap;
    char    data[];
} ltl_string_t;

typedef enum {
    LTL_NIL = 0, LTL_INT, LTL_FLOAT, LTL_BOOL, LTL_STRING,
    LTL_LIST, LTL_MAP, LTL_STRUCT, LTL_FN, LTL_RESULT, LTL_OPTION,
} ltl_type_tag;

typedef struct ltl_value {
    ltl_type_tag tag;
    union {
        int64_t       i;
        double        f;
        bool          b;
        ltl_string_t *s;
        void         *ptr;
    };
} ltl_value_t;

/* ── Result / Option ADTs ────────────────────────────────────────────── */

typedef struct {
    bool    is_ok;
    ltl_value_t value;
    ltl_value_t error;
} ltl_result_t;

typedef struct {
    bool    is_some;
    ltl_value_t value;
} ltl_option_t;

/* ── String helpers ──────────────────────────────────────────────────── */

static ltl_string_t* ltl_str_new(const char *s) {
    int64_t len = (int64_t)strlen(s);
    ltl_string_t *r = (ltl_string_t*)malloc(sizeof(ltl_string_t) + len + 1);
    r->len = len;
    r->cap = len + 1;
    memcpy(r->data, s, len + 1);
    return r;
}

static ltl_string_t* ltl_str_concat(ltl_string_t *a, ltl_string_t *b) {
    int64_t len = a->len + b->len;
    ltl_string_t *r = (ltl_string_t*)malloc(sizeof(ltl_string_t) + len + 1);
    r->len = len;
    r->cap = len + 1;
    memcpy(r->data, a->data, a->len);
    memcpy(r->data + a->len, b->data, b->len + 1);
    return r;
}

/* ── I/O & Lateralus stdlib bindings ────────────────────────────────── */

static void println(const char *s)         { puts(s ? s : ""); }
static void print_int(int64_t v)           { printf("%lld", (long long)v); }
static void print_float(double v)          { printf("%g", v); }

/* io module */
static void ltl_io_println(ltl_string_t *s)  { puts(s && s->len ? s->data : ""); }
static void ltl_io_print(ltl_string_t *s)    { if (s) fputs(s->data, stdout); }
static void ltl_io_eprintln(ltl_string_t *s) { if (s) { fputs(s->data, stderr); fputc('\\n', stderr); } else fputs("\\n", stderr); }
static ltl_string_t* ltl_io_readline(void) {
    char buf[4096]; if (!fgets(buf, sizeof(buf), stdin)) return ltl_str_new("");
    size_t n = strlen(buf); if (n && buf[n-1] == '\\n') buf[n-1] = '\\0';
    return ltl_str_new(buf);
}

/* Type-to-string helpers */
static ltl_string_t* ltl_int_to_str(int64_t v) {
    char buf[32]; snprintf(buf, sizeof(buf), "%lld", (long long)v);
    return ltl_str_new(buf);
}
static ltl_string_t* ltl_float_to_str(double v) {
    char buf[64]; snprintf(buf, sizeof(buf), "%g", v);
    return ltl_str_new(buf);
}
static ltl_string_t* ltl_bool_to_str(bool v) { return ltl_str_new(v ? "true" : "false"); }
static ltl_string_t* ltl_value_to_str(ltl_value_t v) {
    switch (v.tag) {
        case LTL_STRING: return v.s;
        case LTL_INT:    return ltl_int_to_str(v.i);
        case LTL_FLOAT:  return ltl_float_to_str(v.f);
        case LTL_BOOL:   return ltl_bool_to_str(v.b);
        default:         return ltl_str_new("nil");
    }
}
/* Generic println for any value */
static void ltl_println_any(ltl_value_t v) {
    switch (v.tag) {
        case LTL_STRING: puts(v.s ? v.s->data : ""); break;
        case LTL_INT:    printf("%lld\\n", (long long)v.i); break;
        case LTL_FLOAT:  printf("%g\\n", v.f); break;
        case LTL_BOOL:   puts(v.b ? "true" : "false"); break;
        default:         puts("nil"); break;
    }
}

/* ── Dynamic list (growable array) ───────────────────────────────────── */

typedef struct {
    ltl_value_t *items;
    int64_t      len;
    int64_t      cap;
} ltl_list_t;

static ltl_list_t* ltl_list_new(int64_t cap) {
    ltl_list_t *l = (ltl_list_t*)malloc(sizeof(ltl_list_t));
    l->cap = cap > 4 ? cap : 4;
    l->len = 0;
    l->items = (ltl_value_t*)malloc(sizeof(ltl_value_t) * l->cap);
    return l;
}

static void ltl_list_push(ltl_list_t *l, ltl_value_t v) {
    if (l->len >= l->cap) {
        l->cap *= 2;
        l->items = (ltl_value_t*)realloc(l->items, sizeof(ltl_value_t) * l->cap);
    }
    l->items[l->len++] = v;
}

'''

_FREESTANDING_PREAMBLE = '''\
/* ═══════════════════════════════════════════════════════════════════════
 * Generated by LATERALUS C Transpiler v1.5.0
 * Mode: FREESTANDING (bare-metal / OS kernel)
 *
 * Build (x86_64):
 *   x86_64-elf-gcc -ffreestanding -nostdlib -O2 -c kernel.c -o kernel.o
 *   x86_64-elf-ld -T linker.ld kernel.o -o kernel.elf
 *
 * Build (ARM Cortex-M):
 *   arm-none-eabi-gcc -ffreestanding -nostdlib -mcpu=cortex-m4 -c kernel.c
 * ═══════════════════════════════════════════════════════════════════════ */

/* No libc — provide our own primitives */

typedef unsigned char      uint8_t;
typedef unsigned short     uint16_t;
typedef unsigned int       uint32_t;
typedef unsigned long long uint64_t;
typedef signed long long   int64_t;
typedef uint64_t           size_t;
typedef _Bool              bool;
#define true  1
#define false 0
#define NULL  ((void*)0)

/* ── Freestanding memory primitives ──────────────────────────────────── */

static void* ltl_memcpy(void *dst, const void *src, size_t n) {
    uint8_t *d = (uint8_t*)dst;
    const uint8_t *s = (const uint8_t*)src;
    while (n--) *d++ = *s++;
    return dst;
}

static void* ltl_memset(void *dst, int val, size_t n) {
    uint8_t *d = (uint8_t*)dst;
    while (n--) *d++ = (uint8_t)val;
    return dst;
}

static size_t ltl_strlen(const char *s) {
    size_t n = 0;
    while (*s++) n++;
    return n;
}

/* ── Kernel memory allocator (bump allocator) ────────────────────────── */

static uint8_t _heap[1048576];  /* 1 MB static heap */
static size_t  _heap_offset = 0;

static void* ltl_alloc(size_t size) {
    /* Align to 8 bytes */
    size = (size + 7) & ~7;
    if (_heap_offset + size > sizeof(_heap)) return NULL;
    void *ptr = &_heap[_heap_offset];
    _heap_offset += size;
    return ptr;
}

static void ltl_free(void *ptr) {
    /* Bump allocator: free is a no-op (reclaimed on reset) */
    (void)ptr;
}

static void ltl_heap_reset(void) {
    _heap_offset = 0;
}

/* ── Freestanding types (same layout as hosted) ──────────────────────── */

typedef struct ltl_string {
    int64_t len;
    int64_t cap;
    char    data[];
} ltl_string_t;

typedef enum {
    LTL_NIL = 0, LTL_INT, LTL_FLOAT, LTL_BOOL, LTL_STRING,
    LTL_LIST, LTL_MAP, LTL_STRUCT, LTL_FN, LTL_RESULT, LTL_OPTION,
} ltl_type_tag;

typedef struct ltl_value {
    ltl_type_tag tag;
    union {
        int64_t       i;
        double        f;
        bool          b;
        ltl_string_t *s;
        void         *ptr;
    };
} ltl_value_t;

typedef struct {
    bool        is_ok;
    ltl_value_t value;
    ltl_value_t error;
} ltl_result_t;

typedef struct {
    bool        is_some;
    ltl_value_t value;
} ltl_option_t;

/* ── Port I/O (x86) ─────────────────────────────────────────────────── */

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

/* ── VGA text mode (0xB8000) ─────────────────────────────────────────── */

static volatile uint16_t *const VGA_BUFFER = (volatile uint16_t*)0xB8000;
static int vga_row = 0, vga_col = 0;

static void vga_putchar(char c, uint8_t color) {
    if (c == \'\\n\') { vga_row++; vga_col = 0; return; }
    if (vga_row >= 25) vga_row = 0;
    VGA_BUFFER[vga_row * 80 + vga_col] = (uint16_t)c | ((uint16_t)color << 8);
    if (++vga_col >= 80) { vga_col = 0; vga_row++; }
}

static void println(const char *s) {
    while (*s) vga_putchar(*s++, 0x0F);
    vga_putchar(\'\\n\', 0x0F);
}

'''


# ─────────────────────────────────────────────────────────────────────────────
# C Transpiler
# ─────────────────────────────────────────────────────────────────────────────

class CTranspiler(ASTVisitor):
    """
    Walk a Lateralus AST and emit C99 source code.

    Supports both hosted (libc-linked userspace) and freestanding
    (bare-metal kernel) modes.
    """

    def __init__(self, mode: CMode = CMode.HOSTED, *, target_arch: str = "x86_64"):
        self.mode = mode
        self.target_arch = target_arch
        self._w = _W()
        self._structs: List[str] = []        # forward declarations
        self._functions: List[str] = []      # forward declarations
        self._globals: Dict[str, str] = {}
        self._local_vars: Set[str] = set()
        self._indent = 0
        self._temp_counter = 0
        self._in_fn = False
        self._local_types: Dict[str, str] = {}    # name → C type for current fn
        self._fn_return_types: Dict[str, str] = {}  # fn name → C return type

    # ── helpers ───────────────────────────────────────────────────────────

    def _temp(self, prefix: str = "_t") -> str:
        self._temp_counter += 1
        return f"{prefix}{self._temp_counter}"

    def _mangle(self, name: str) -> str:
        """Mangle identifiers to avoid C keyword collisions."""
        C_KEYWORDS = {
            "auto", "break", "case", "char", "const", "continue", "default",
            "do", "double", "else", "enum", "extern", "float", "for", "goto",
            "if", "int", "long", "register", "return", "short", "signed",
            "sizeof", "static", "struct", "switch", "typedef", "union",
            "unsigned", "void", "volatile", "while",
            "main",  # avoid C entry point conflict
        }
        if name in C_KEYWORDS:
            return f"ltl_{name}"
        return name.replace("::", "_")

    # ── main entry ────────────────────────────────────────────────────────

    def transpile(self, ast: Program) -> str:
        """Transpile a complete Program AST to C source."""
        w = self._w

        # Preamble
        if self.mode == CMode.FREESTANDING:
            w.raw(_FREESTANDING_PREAMBLE)
        else:
            w.raw(_HOSTED_PREAMBLE)

        w.comment("═══ Forward Declarations ═══")
        w.line()

        # First pass: collect enum/struct/fn forward declarations
        for node in ast.body:
            if isinstance(node, EnumDecl):
                self._w.comment(f"enum {node.name} (defined below)")
                self._w.line(f"typedef struct ltl_enum_{self._mangle(node.name)} {self._mangle(node.name)};")
            elif isinstance(node, StructDecl):
                self._emit_struct_forward(node)
            elif isinstance(node, FnDecl):
                self._emit_fn_forward(node)

        w.line()
        w.comment("═══ Struct Definitions ═══")
        w.line()

        # Second pass: emit structs
        for node in ast.body:
            if isinstance(node, StructDecl):
                self._emit_struct(node)

        w.line()
        w.comment("═══ Function Definitions ═══")
        w.line()

        # Third pass: emit everything else
        for node in ast.body:
            if isinstance(node, StructDecl):
                continue  # already emitted
            if isinstance(node, ExprStmt):
                # Bare expression statements at file scope are invalid C
                # (e.g. top-level function calls). Skip them — main() handles entry.
                w.comment("top-level expr (skipped in C — handled by main)")
                continue
            self._visit(node)
            w.line()

        # main() wrapper
        if self.mode == CMode.HOSTED:
            self._emit_main_wrapper()
        elif self.mode == CMode.FREESTANDING:
            self._emit_kernel_entry()

        return w.result()

    # ── visit dispatch ────────────────────────────────────────────────────

    # ── type inference helpers ────────────────────────────────────────────

    def _infer_ctype_from_expr(self, node) -> str:
        """Heuristically infer a C type from an AST expression node."""
        if node is None:
            return "ltl_value_t"
        if isinstance(node, Literal):
            if isinstance(node.value, bool):  return "bool"
            if isinstance(node.value, int):   return "int64_t"
            if isinstance(node.value, float): return "double"
            if isinstance(node.value, str):   return "ltl_string_t*"
            return "ltl_value_t"
        if isinstance(node, (InterpolatedStr,)):
            return "ltl_string_t*"
        if isinstance(node, Ident):
            # Look up known local variable types
            nm = self._mangle(node.name)
            if nm in self._local_types:
                return self._local_types[nm]
            # Look up known function return types
            if nm in self._fn_return_types:
                return self._fn_return_types[nm]
        if isinstance(node, BinOp):
            op = getattr(node, "op", "+")
            if op in ("+", "-", "*", "/", "%"):
                lt = self._infer_ctype_from_expr(node.left)
                rt = self._infer_ctype_from_expr(node.right)
                if "ltl_string_t*" in (lt, rt): return "ltl_string_t*"
                if "double" in (lt, rt):         return "double"
                if lt == "int64_t" and rt == "int64_t": return "int64_t"
            if op in ("==", "!=", "<", ">", "<=", ">=", "and", "or", "not"):
                return "bool"
        if isinstance(node, CastExpr):
            tname = getattr(node.target, "name", None) if node.target else None
            if tname == "str":   return "ltl_string_t*"
            if tname == "int":   return "int64_t"
            if tname == "float": return "double"
            if tname == "bool":  return "bool"
            return _c_type(node.target, "ltl_value_t")
        if isinstance(node, CallExpr):
            if isinstance(node.callee, Ident):
                nm = self._mangle(node.callee.name)
                if nm in ("ltl_int_to_str", "ltl_float_to_str",
                          "ltl_bool_to_str", "ltl_str_new", "ltl_str_concat"):
                    return "ltl_string_t*"
                # Look up fn return type
                if nm in self._fn_return_types:
                    return self._fn_return_types[nm]
        return "ltl_value_t"

    # ── stdlib module call mapping ─────────────────────────────────────────

    _IO_MATH = {
        "sqrt": "sqrt", "cbrt": "cbrt", "abs": "fabs", "fabs": "fabs",
        "floor": "floor", "ceil": "ceil", "round": "round",
        "pow": "pow", "exp": "exp", "log": "log", "log2": "log2",
        "log10": "log10", "sin": "sin", "cos": "cos", "tan": "tan",
        "asin": "asin", "acos": "acos", "atan": "atan", "atan2": "atan2",
        "min": "fmin", "max": "fmax",
    }

    def _map_stdlib_call(self, mod: str, method: str, args: "List[str]") -> "Optional[str]":
        """Map a Lateralus module.method call to a C expression."""
        a0 = args[0] if args else 'ltl_str_new("")'
        all_args = ", ".join(args)
        # io module
        if mod == "io":
            if method == "println":  return f"ltl_io_println({a0})"
            if method == "print":    return f"ltl_io_print({a0})"
            if method == "eprintln": return f"ltl_io_eprintln({a0})"
            if method == "readline": return "ltl_io_readline()"
            if method in ("println_int",):
                return f"printf(\"%%lld\\n\", (long long){a0})"
        # fmt module
        if mod == "fmt":
            if method in ("println", "writeln"): return f"ltl_io_println({a0})"
            if method in ("print", "write"):     return f"ltl_io_print({a0})"
        # math module
        if mod == "math":
            if method in self._IO_MATH:
                cfn = self._IO_MATH[method]
                return f"{cfn}({all_args})"
            if method == "pi": return "M_PI"
            if method == "tau": return "(2.0 * M_PI)"
            if method == "inf": return "INFINITY"
        # mem module
        if mod == "mem":
            if method == "alloc": return f"malloc({a0})"
            if method == "free":  return f"free({a0}), 0"
            if method == "realloc": return f"realloc({all_args})"
            if method == "copy": return f"memcpy({all_args})"
            if method == "set":  return f"memset({all_args})"
        # sys / os module
        if mod in ("sys", "os"):
            if method == "exit": return f"exit({a0})"
            if method == "abort": return "abort()"
            if method == "panic": return f"(puts({a0}->data), abort(), 0)"
        # str / strings module
        if mod in ("str", "strings"):
            if method == "len": return f"({a0}->len)"
            if method == "concat": return f"ltl_str_concat({all_args})"
        # process
        if mod == "process":
            if method == "exit": return f"exit({a0})"
        return None

    def _visit(self, node: Node):
        method = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method, None)
        if visitor:
            return visitor(node)
        else:
            self._w.comment(f"unsupported: {type(node).__name__} (skipped)")

    def _visit_expr(self, node: Node) -> str:
        """Visit an expression and return a C expression string."""
        method = f"_expr_{type(node).__name__}"
        visitor = getattr(self, method, None)
        if visitor:
            return visitor(node)
        return f"/* unsupported: {type(node).__name__} */ 0"

    # ── struct emission ───────────────────────────────────────────────────

    def _emit_struct_forward(self, node: StructDecl):
        name = self._mangle(node.name)
        self._w.line(f"typedef struct {name} {name};")
        self._structs.append(name)

    def _emit_struct(self, node: StructDecl):
        w = self._w
        name = self._mangle(node.name)
        w.block_open(f"struct {name}")
        for f in node.fields:
            ftype = _c_type(getattr(f, "type_", None), "ltl_value_t")
            fname = self._mangle(f.name)
            w.line(f"{ftype} {fname};")
        w.block_close(";")
        w.line()

    # ── function forward declaration ──────────────────────────────────────

    def _emit_fn_forward(self, node: FnDecl):
        ret = _c_type(node.ret_type, "ltl_value_t")
        name = self._mangle(node.name)
        params = self._format_params(node.params)
        self._w.line(f"static {ret} {name}({params});")
        self._functions.append(name)
        self._fn_return_types[name] = ret  # track for type inference

    def _format_params(self, params: List[Param]) -> str:
        if not params:
            return "void"
        parts = []
        for p in params:
            ptype = _c_type(getattr(p, "type_", None), "ltl_value_t")
            pname = self._mangle(p.name)
            parts.append(f"{ptype} {pname}")
        return ", ".join(parts)

    # ── function definition ───────────────────────────────────────────────

    def _visit_FnDecl(self, node: FnDecl):
        w = self._w
        ret = _c_type(node.ret_type, "ltl_value_t")
        name = self._mangle(node.name)
        params = self._format_params(node.params)

        self._in_fn = True
        self._local_vars = set()
        self._local_types = {}

        w.block_open(f"static {ret} {name}({params})")
        if node.body:
            self._visit_block(node.body)
        w.block_close()
        w.line()
        self._in_fn = False

    def _visit_block(self, block):
        if isinstance(block, BlockStmt):
            for stmt in block.stmts:
                self._visit(stmt)
        elif isinstance(block, list):
            for stmt in block:
                self._visit(stmt)
        elif isinstance(block, Node):
            self._visit(block)

    # ── statements ────────────────────────────────────────────────────────

    def _visit_LetDecl(self, node: LetDecl):
        explicit = _c_type(getattr(node, "type_", None), None)
        if explicit is not None:
            ctype = explicit
        elif node.value is not None:
            ctype = self._infer_ctype_from_expr(node.value)
        else:
            ctype = "ltl_value_t"
        name = self._mangle(node.name)
        val  = self._visit_expr(node.value) if node.value else "/* uninitialized */ {0}"
        self._w.line(f"{ctype} {name} = {val};")
        self._local_types[name] = ctype
        self._local_vars.add(name)

    def _visit_AssignStmt(self, node: AssignStmt):
        target = self._visit_expr(node.target)
        value  = self._visit_expr(node.value)
        op     = getattr(node, "op", "=") or "="
        # Compound assignment operators
        compound_map = {
            "+=": "+=", "-=": "-=", "*=": "*=", "/=": "/=", "%=": "%=",
            "&=": "&=", "|=": "|=", "^=": "^=", "<<=": "<<=", ">>=": ">>=",
            "|>=": "= /* |>= */ ",  # pipeline assign
        }
        if op in compound_map:
            self._w.line(f"{target} {compound_map[op]} {value};")
        else:
            self._w.line(f"{target} = {value};")

    def _visit_ReturnStmt(self, node: ReturnStmt):
        if node.value:
            val = self._visit_expr(node.value)
            self._w.line(f"return {val};")
        else:
            self._w.line("return;")

    def _visit_IfStmt(self, node: IfStmt):
        w = self._w
        cond = self._visit_expr(node.condition)
        w.block_open(f"if ({cond})")
        self._visit_block(node.then_block)
        w.block_close()
        for elif_cond, elif_block in (node.elif_arms or []):
            ec = self._visit_expr(elif_cond)
            w.block_open(f"else if ({ec})")
            self._visit_block(elif_block)
            w.block_close()
        if node.else_block:
            w.block_open("else")
            self._visit_block(node.else_block)
            w.block_close()

    def _visit_WhileStmt(self, node: WhileStmt):
        cond = self._visit_expr(node.condition)
        self._w.block_open(f"while ({cond})")
        self._visit_block(node.body)
        self._w.block_close()

    def _visit_ForStmt(self, node: ForStmt):
        w = self._w
        iter_expr = self._visit_expr(node.iter)
        var = self._mangle(node.var)
        tmp = self._temp()
        # Emit as a C for-loop over a list
        w.line(f"ltl_list_t *{tmp} = {iter_expr};")
        w.block_open(f"for (int64_t _i = 0; _i < {tmp}->len; _i++)")
        w.line(f"ltl_value_t {var} = {tmp}->items[_i];")
        self._visit_block(node.body)
        w.block_close()

    def _visit_LoopStmt(self, node: LoopStmt):
        self._w.block_open("for (;;)")
        self._visit_block(node.body)
        self._w.block_close()

    def _visit_BreakStmt(self, _):
        self._w.line("break;")

    def _visit_ContinueStmt(self, _):
        self._w.line("continue;")

    def _visit_ExprStmt(self, node: ExprStmt):
        expr = self._visit_expr(node.expr)
        self._w.line(f"{expr};")

    def _visit_ImportStmt(self, node: ImportStmt):
        # C has no module system — emit a comment noting the import
        w = self._w
        if node.items:
            items = ", ".join(node.items)
            w.comment(f"import {{ {items} }} from {node.path}")
        elif node.alias:
            w.comment(f"import {node.path} as {node.alias}")
        else:
            w.comment(f"import {node.path}")

    def _visit_EnumDecl(self, node: EnumDecl):
        w = self._w
        name = self._mangle(node.name)

        # Check if this is a simple C-style enum (no fields on any variant)
        is_simple = all(not v.fields for v in node.variants)

        if is_simple:
            # Simple enum → C enum
            w.block_open(f"typedef enum {name}")
            for i, v in enumerate(node.variants):
                vname = f"{name}_{self._mangle(v.name)}"
                if v.value:
                    val = self._visit_expr(v.value)
                    w.line(f"{vname} = {val},")
                else:
                    w.line(f"{vname} = {i},")
            w.block_close(f" {name};")
        else:
            # Tagged union → struct with tag + union
            w.line(f"typedef enum {{ /* {name} tags */ ")
            for i, v in enumerate(node.variants):
                w.line(f"    {name}_TAG_{self._mangle(v.name)} = {i},")
            w.line(f"}} {name}_tag_t;")
            w.line()
            w.block_open(f"typedef struct {name}")
            w.line(f"{name}_tag_t tag;")
            w.block_open("union")
            for v in node.variants:
                if v.fields:
                    w.block_open("struct")
                    for f in v.fields:
                        ftype = _c_type(getattr(f, "type_", None), "ltl_value_t")
                        w.line(f"{ftype} {self._mangle(f.name)};")
                    w.block_close(f" {self._mangle(v.name)};")
                else:
                    w.line(f"char _{self._mangle(v.name)};  /* unit variant */")
            w.block_close(";")  # union
            w.block_close(f" {name};")
        w.line()

    def _visit_ImplBlock(self, node: ImplBlock):
        # Methods become free functions with an explicit self parameter
        w = self._w
        type_name = self._mangle(node.type_name)
        w.comment(f"impl {type_name}")
        for method in node.methods:
            # Prefix method name with type name for namespacing
            mangled_name = f"{type_name}_{self._mangle(method.name)}"
            ret = _c_type(method.ret_type, "ltl_value_t")

            # Build params: prepend self pointer
            param_parts = [f"{type_name}* self"]
            for p in method.params:
                ptype = _c_type(getattr(p, "type_", None), "ltl_value_t")
                pname = self._mangle(p.name)
                param_parts.append(f"{ptype} {pname}")
            params_str = ", ".join(param_parts)

            self._in_fn = True
            self._local_vars = set()
            w.block_open(f"static {ret} {mangled_name}({params_str})")
            if method.body:
                self._visit_block(method.body)
            w.block_close()
            w.line()
            self._in_fn = False

    def _visit_TypeAlias(self, node: TypeAlias):
        target = _c_type(node.target, "ltl_value_t")
        name = self._mangle(node.name)
        self._w.line(f"typedef {target} {name};")

    def _visit_MatchStmt(self, node: MatchStmt):
        w = self._w
        subject = self._visit_expr(node.subject)
        tmp = self._temp()
        w.line(f"ltl_value_t {tmp} = {subject};")
        first = True
        for arm in node.arms:
            kw = "if" if first else "else if"
            pattern_cond = self._pattern_cond(tmp, arm.pattern)
            w.block_open(f"{kw} ({pattern_cond})")
            if arm.body:
                self._visit_block(arm.body)
            w.block_close()
            first = False

    def _visit_ForeignBlock(self, node: ForeignBlock):
        w = self._w
        lang = getattr(node, "language", "C") or "C"
        w.comment(f"foreign({lang}) block")
        for item in getattr(node, "items", []):
            if isinstance(item, FnDecl):
                ret = _c_type(item.ret_type, "ltl_value_t")
                name = self._mangle(item.name)
                params = self._format_params(item.params)
                w.line(f"extern {ret} {name}({params});")
            elif isinstance(item, ForeignParam):
                ptype = _c_type(getattr(item, "type_", None), "ltl_value_t")
                pname = self._mangle(item.name)
                w.line(f"extern {ptype} {pname};")
            else:
                w.comment(f"unsupported foreign item: {type(item).__name__}")

    def _visit_TryStmt(self, node: TryStmt):
        w = self._w
        w.comment("try/recover → C error-handling via goto")
        label_ok = self._temp("ok")
        w.block_open("/* try */")
        if hasattr(node, "body") and node.body:
            self._visit_block(node.body)
        w.line(f"goto {label_ok};")
        w.block_close()
        for clause in getattr(node, "recover_clauses", []) or getattr(node, "handlers", []) or []:
            w.block_open("/* recover */")
            body = getattr(clause, "body", None)
            if body:
                self._visit_block(body)
            w.block_close()
        w.line(f"{label_ok}:;")

    def _visit_ThrowStmt(self, node: ThrowStmt):
        expr = self._visit_expr(node.value) if hasattr(node, "value") and node.value else "1"
        self._w.comment("throw → return error")
        self._w.line(f"return {expr}; /* throw */")

    def _visit_InterfaceDecl(self, node: InterfaceDecl):
        w = self._w
        name = self._mangle(node.name)
        w.comment(f"interface {node.name} → vtable struct")
        w.block_open(f"typedef struct {name}_vtable")
        for method in getattr(node, "methods", []):
            ret = _c_type(getattr(method, "ret_type", None), "ltl_value_t")
            mname = self._mangle(method.name)
            params = self._format_params(getattr(method, "params", []))
            w.line(f"{ret} (*{mname})({params});")
        w.block_close(f" {name}_vtable;")
        w.line()

    # ── expressions ───────────────────────────────────────────────────────

    def _expr_Literal(self, node: Literal) -> str:
        if isinstance(node.value, str):
            escaped = node.value.replace("\\", "\\\\").replace('"', '\\"')
            if self.mode == CMode.FREESTANDING:
                return f'"{escaped}"'
            return f'ltl_str_new("{escaped}")'
        if isinstance(node.value, bool):
            return "true" if node.value else "false"
        if isinstance(node.value, float):
            return repr(node.value)
        if node.value is None:
            return "(ltl_value_t){.tag = LTL_NIL}"
        return str(node.value)

    def _expr_Ident(self, node: Ident) -> str:
        return self._mangle(node.name)

    def _expr_BinOp(self, node: BinOp) -> str:
        op = getattr(node, "op", "+")
        if op == "|>":
            right = self._visit_expr(node.right)
            left  = self._visit_expr(node.left)
            return f"{right}({left})"
        if op == "**":
            left  = self._visit_expr(node.left)
            right = self._visit_expr(node.right)
            return f"pow({left}, {right})"
        # Detect string concatenation before visiting (needs type info)
        if op == "+":
            lt = self._infer_ctype_from_expr(node.left)
            rt = self._infer_ctype_from_expr(node.right)
            left  = self._visit_expr(node.left)
            right = self._visit_expr(node.right)
            if lt == "ltl_string_t*" or rt == "ltl_string_t*":
                # Coerce non-string side if needed
                if lt != "ltl_string_t*":
                    if lt == "int64_t":   left  = f"ltl_int_to_str({left})"
                    elif lt == "double":  left  = f"ltl_float_to_str({left})"
                    elif lt == "bool":    left  = f"ltl_bool_to_str({left})"
                    elif lt == "ltl_value_t": left = f"ltl_value_to_str({left})"
                if rt != "ltl_string_t*":
                    if rt == "int64_t":   right = f"ltl_int_to_str({right})"
                    elif rt == "double":  right = f"ltl_float_to_str({right})"
                    elif rt == "bool":    right = f"ltl_bool_to_str({right})"
                    elif rt == "ltl_value_t": right = f"ltl_value_to_str({right})"
                return f"ltl_str_concat({left}, {right})"
        left  = self._visit_expr(node.left)
        right = self._visit_expr(node.right)
        op_map = {
            "+": "+", "-": "-", "*": "*", "/": "/", "%": "%",
            "==": "==", "!=": "!=",
            "<": "<", ">": ">", "<=": "<=", ">=": ">=",
            "and": "&&", "or": "||",
            "&": "&", "|": "|", "^": "^", "<<": "<<", ">>": ">>",
        }
        c_op = op_map.get(op, op)
        return f"({left} {c_op} {right})"

    def _expr_UnaryOp(self, node: UnaryOp) -> str:
        operand = self._visit_expr(node.operand)
        op = getattr(node, "op", "-")
        if op == "not":
            return f"(!{operand})"
        return f"({op}{operand})"

    def _expr_CallExpr(self, node: CallExpr) -> str:
        # Intercept stdlib module calls: io.println(...), math.sqrt(...), etc.
        if isinstance(node.callee, FieldExpr) and isinstance(node.callee.obj, Ident):
            mod    = node.callee.obj.name
            method = node.callee.field
            args   = [self._visit_expr(a) for a in node.args]
            mapped = self._map_stdlib_call(mod, method, args)
            if mapped is not None:
                return mapped
        func = self._visit_expr(node.callee)
        args = ", ".join(self._visit_expr(a) for a in node.args)
        return f"{func}({args})"

    def _expr_IndexExpr(self, node: IndexExpr) -> str:
        obj = self._visit_expr(node.obj)
        idx = self._visit_expr(node.index)
        return f"{obj}->items[{idx}]"

    def _expr_FieldExpr(self, node: FieldExpr) -> str:
        # Handle module constant access: math.PI, sys.STDOUT, etc.
        if isinstance(node.obj, Ident):
            mod = node.obj.name
            field = node.field
            if mod == "math":
                consts = {"PI": "M_PI", "E": "M_E", "INF": "INFINITY",
                          "NAN": "NAN", "TAU": "(2.0*M_PI)"}
                if field in consts:
                    return consts[field]
        obj = self._visit_expr(node.obj)
        # Use -> for pointer types, . for value types
        return f"{obj}->{self._mangle(node.field)}" if obj.endswith("*") or "ltl_" in obj else f"{obj}.{self._mangle(node.field)}"

    def _expr_ListExpr(self, node: ListExpr) -> str:
        # Build a list from elements
        parts = [self._visit_expr(e) for e in node.elements]
        tmp = self._temp()
        # This is an expression — we'll use a compound literal / helper
        return f"/* list[{len(parts)}] */ ltl_list_new({len(parts)})"

    def _expr_TernaryExpr(self, node: TernaryExpr) -> str:
        cond = self._visit_expr(node.condition)
        then = self._visit_expr(node.true_expr)
        els = self._visit_expr(node.false_expr)
        return f"({cond} ? {then} : {els})"

    def _expr_ResultExpr(self, node: ResultExpr) -> str:
        if node.variant == "Ok":
            val = self._visit_expr(node.value)
            return f"((ltl_result_t){{.is_ok = true, .value = {val}}})"
        else:
            err = self._visit_expr(node.value)
            return f"((ltl_result_t){{.is_ok = false, .error = {err}}})"

    def _expr_OptionExpr(self, node: OptionExpr) -> str:
        if node.variant == "Some":
            val = self._visit_expr(node.value)
            return f"((ltl_option_t){{.is_some = true, .value = {val}}})"
        return "((ltl_option_t){.is_some = false})"

    def _expr_LambdaExpr(self, node: LambdaExpr) -> str:
        # C doesn't have first-class closures — emit function pointer
        return "/* lambda (requires hoisting) */ NULL"

    def _expr_SelfExpr(self, _) -> str:
        return "self"

    def _expr_StructLiteral(self, node: StructLiteral) -> str:
        name = self._mangle(node.name)
        fields = ", ".join(
            f".{self._mangle(fname)} = {self._visit_expr(fval)}"
            for fname, fval in node.fields
        )
        return f"(({name}){{{fields}}})"

    def _expr_InterpolatedStr(self, node: InterpolatedStr) -> str:
        if self.mode == CMode.FREESTANDING:
            # Freestanding: concatenate literals, skip expressions
            parts = []
            for p in node.parts:
                if isinstance(p, str):
                    parts.append(p.replace("\\", "\\\\").replace('"', '\\"'))
            return f'"{"".join(parts)}"'
        else:
            # Hosted: build with snprintf pattern
            fmt_parts = []
            args = []
            for p in node.parts:
                if isinstance(p, str):
                    fmt_parts.append(p.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"'))
                else:
                    expr = self._visit_expr(p)
                    fmt_parts.append("%s")
                    args.append(expr)
            fmt = "".join(fmt_parts)
            if args:
                tmp = self._temp()
                # Use a compound expression
                arg_str = ", ".join(args)
                return f'/* interpolated */ "{fmt}" /* args: {arg_str} */'
            return f'ltl_str_new("{fmt}")'

    def _expr_CastExpr(self, node: CastExpr) -> str:
        val = self._visit_expr(node.value)
        src_type = self._infer_ctype_from_expr(node.value)
        tname = getattr(node.target, "name", None) if node.target else None
        # Smart cast: value-to-string
        if tname == "str":
            if src_type == "int64_t":    return f"ltl_int_to_str({val})"
            if src_type == "double":     return f"ltl_float_to_str({val})"
            if src_type == "bool":       return f"ltl_bool_to_str({val})"
            if src_type == "ltl_value_t": return f"ltl_value_to_str({val})"
            return f"ltl_value_to_str((ltl_value_t){{.tag=LTL_STRING,.s=(ltl_string_t*){val}}})"
        # String-to-int/float
        if tname == "int":   return f"(int64_t)({val})"
        if tname == "float": return f"(double)({val})"
        if tname == "bool":  return f"(bool)({val})"
        target = _c_type(node.target, "ltl_value_t")
        return f"(({target}){val})"

    def _expr_TupleExpr(self, node: TupleExpr) -> str:
        # Tuples → anonymous struct compound literal
        fields = ", ".join(
            f"._{i} = {self._visit_expr(e)}"
            for i, e in enumerate(node.elements)
        )
        n = len(node.elements)
        # Generate a typedef name based on arity
        return f"/* tuple({n}) */ (struct {{ {'; '.join(f'ltl_value_t _{i}' for i in range(n))}; }}){{{fields}}}"

    def _expr_MapExpr(self, node: MapExpr) -> str:
        # Maps → placeholder (would need hash table runtime)
        n = len(node.pairs)
        self._w.comment(f"Map literal with {n} entries")
        if self.mode == CMode.HOSTED:
            return f"/* map[{n}] */ NULL"
        return f"/* map[{n}] (freestanding) */ NULL"

    def _expr_SpawnExpr(self, node: SpawnExpr) -> str:
        inner = self._visit_expr(node.expr) if hasattr(node, "expr") and node.expr else "0"
        return f"/* spawn */ {inner}"

    def _expr_AwaitExpr(self, node: AwaitExpr) -> str:
        inner = self._visit_expr(node.expr) if hasattr(node, "expr") and node.expr else "0"
        return f"/* await */ {inner}"

    def _expr_YieldExpr(self, node: YieldExpr) -> str:
        inner = self._visit_expr(node.value) if hasattr(node, "value") and node.value else "0"
        return f"/* yield */ {inner}"

    def _expr_TypeMatchExpr(self, node: TypeMatchExpr) -> str:
        subject = self._visit_expr(node.subject) if hasattr(node, "subject") else "0"
        tmp = self._temp()
        # Type match as expression → nested ternary chain
        parts = []
        for arm in getattr(node, "arms", []):
            body_expr = self._visit_expr(arm.body) if hasattr(arm, "body") else "0"
            parts.append(body_expr)
        if parts:
            return parts[0]  # simplified: return first arm
        return f"/* type_match */ {subject}"

    def _expr_RangeExpr(self, node: RangeExpr) -> str:
        start = self._visit_expr(node.start) if hasattr(node, "start") and node.start else "0"
        end = self._visit_expr(node.end) if hasattr(node, "end") and node.end else "0"
        return f"/* range */ {start} /* .. */ /* {end} */"

    def _expr_ChainExpr(self, node: ChainExpr) -> str:
        expr = self._visit_expr(node.expr) if hasattr(node, "expr") and node.expr else "0"
        return f"/* ?-chain */ {expr}"

    def _expr_ComprehensionExpr(self, node: ComprehensionExpr) -> str:
        return "/* list comprehension */ NULL"

    def _expr_PropagateExpr(self, node: PropagateExpr) -> str:
        inner = self._visit_expr(node.expr) if hasattr(node, "expr") and node.expr else "0"
        return f"/* propagate */ {inner}"

    # ── v1.5 completeness: previously-missing visitors ────────────────────

    def _visit_EmitStmt(self, node: EmitStmt):
        w = self._w
        event = getattr(node, "event", None) or getattr(node, "name", "event")
        w.comment(f'emit "{event}" → telemetry (no-op in C)')
        if hasattr(node, "body") and node.body:
            self._visit_block(node.body)

    def _visit_MeasureBlock(self, node: MeasureBlock):
        w = self._w
        label = getattr(node, "label", None) or getattr(node, "name", "block")
        if isinstance(label, Node):
            label = self._visit_expr(label)
        start_var = self._temp("measure_start")
        w.comment(f'measure "{label}"')
        w.line(f"/* clock_t {start_var} = clock(); */")
        w.block_open("")
        if hasattr(node, "body") and node.body:
            self._visit_block(node.body)
        w.block_close()
        w.line(f'/* elapsed = clock() - {start_var}; */')

    def _visit_PipelineAssign(self, node: PipelineAssign):
        w = self._w
        target = self._visit_expr(node.target) if hasattr(node, "target") else "x"
        value = self._visit_expr(node.value) if hasattr(node, "value") else "0"
        w.line(f"{target} = {value};  /* |>= */")

    def _expr_GuardExpr(self, node: GuardExpr) -> str:
        cond = self._visit_expr(node.condition) if hasattr(node, "condition") else "1"
        return f"/* guard */ ({cond})"

    def _expr_WhereClause(self, node: WhereClause) -> str:
        value = self._visit_expr(node.value) if hasattr(node, "value") else "0"
        # Emit bindings as a block, return value
        return f"/* where */ {value}"

    def _expr_SpreadExpr(self, node: SpreadExpr) -> str:
        inner = self._visit_expr(node.expr) if hasattr(node, "expr") else "NULL"
        return f"/* ...spread */ {inner}"

    def _expr_TryExpr(self, node: TryExpr) -> str:
        inner = self._visit_expr(node.expr) if hasattr(node, "expr") and node.expr else "0"
        return f"/* try-expr */ {inner}"

    def _expr_ProbeExpr(self, node: ProbeExpr) -> str:
        label = getattr(node, "label", None) or getattr(node, "name", "probe")
        return f'/* probe "{label}" */ 0'

    # ── v1.6 low-level statement visitors ─────────────────────────────────

    def _visit_UnsafeBlock(self, node: UnsafeBlock):
        w = self._w
        w.comment("unsafe block — unchecked operations")
        w.block_open("/* unsafe */")
        self._visit_block(node.body)
        w.block_close()

    def _visit_ExternDecl(self, node: ExternDecl):
        w = self._w
        ret = node.return_type or "void"
        c_ret = _TYPE_MAP.get(ret, ret)
        name = self._mangle(node.name)
        if node.params:
            parts = []
            for p in node.params:
                ptype = _c_type(getattr(p, "type_", None), "void")
                pname = self._mangle(p.name)
                parts.append(f"{ptype} {pname}")
            params_str = ", ".join(parts)
        else:
            params_str = "void"
        w.line(f"extern {c_ret} {name}({params_str});")

    def _visit_StaticDecl(self, node: StaticDecl):
        w = self._w
        ctype = _TYPE_MAP.get(node.type_ann, "ltl_value_t") if node.type_ann else "ltl_value_t"
        name = self._mangle(node.name)
        qual = "" if not node.mutable else "/* mut */ "
        if node.value:
            val = self._visit_expr(node.value)
            w.line(f"static {qual}{ctype} {name} = {val};")
        else:
            w.line(f"static {qual}{ctype} {name};")

    # ── v1.6 low-level expression visitors ────────────────────────────────

    def _expr_InlineAsm(self, node: InlineAsm) -> str:
        escaped = node.template.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'__asm__ volatile ("{escaped}")'

    def _expr_VolatileExpr(self, node: VolatileExpr) -> str:
        operand = self._visit_expr(node.operand)
        return f"(*(volatile __typeof__({operand})*)&({operand}))"

    def _expr_AddrOfExpr(self, node: AddrOfExpr) -> str:
        operand = self._visit_expr(node.operand)
        return f"(&({operand}))"

    def _expr_DerefExpr(self, node: DerefExpr) -> str:
        operand = self._visit_expr(node.operand)
        return f"(*({operand}))"

    def _expr_AlignofExpr(self, node: AlignofExpr) -> str:
        ctype = _TYPE_MAP.get(node.type_name, node.type_name)
        return f"_Alignof({ctype})"

    def _expr_OffsetofExpr(self, node: OffsetofExpr) -> str:
        sname = self._mangle(node.struct_name)
        fname = self._mangle(node.field_name)
        return f"__builtin_offsetof({sname}, {fname})"

    # ── v1.6 async / concurrency visitors ────────────────────────────────

    def _visit_NurseryBlock(self, node: NurseryBlock):
        w = self._w
        name = getattr(node, "name", None) or "_nursery"
        w.comment("nursery { ... } → sequential fallback in C (no green threads)")
        w.block_open(f"/* nursery: {name} */")
        if node.body:
            self._visit_block(node.body)
        w.block_close()

    def _visit_AsyncForStmt(self, node: AsyncForStmt):
        w = self._w
        var = self._mangle(node.var)
        iter_expr = self._visit_expr(node.iter)
        w.comment(f"async for {node.var} in ... → synchronous for-loop in C")
        tmp = self._temp()
        w.line(f"ltl_list_t *{tmp} = {iter_expr};")
        w.block_open(f"for (int64_t _i = 0; _i < {tmp}->len; _i++)")
        w.line(f"ltl_value_t {var} = {tmp}->items[_i];")
        self._visit_block(node.body)
        w.block_close()

    def _expr_ChannelExpr(self, node: ChannelExpr) -> str:
        cap = getattr(node, "capacity", 0) or 0
        return f"/* channel(cap={cap}) */ NULL"

    def _expr_CancelExpr(self, node: CancelExpr) -> str:
        scope = getattr(node, "scope", None)
        return f'/* cancel("{scope}") */ 0'

    # ── v1.7 — conditional compilation visitors ───────────────────────────

    def _visit_CfgAttr(self, node: CfgAttr):
        w = self._w
        w.line(f'#if defined(LTL_CFG_{node.key.upper()}_{node.value.upper()})')
        w.comment(f'@cfg({node.key} = "{node.value}")')

    def _expr_CfgExpr(self, node: CfgExpr) -> str:
        macro = f"LTL_CFG_{node.key.upper()}_{node.value.upper()}"
        return f"(defined({macro}) ? 1 : 0)"

    # ── v1.8 — metaprogramming visitors ───────────────────────────────────

    def _visit_ConstFnDecl(self, node: ConstFnDecl):
        w = self._w
        ret = _c_type(getattr(node, "ret_type", None), "ltl_value_t")
        name = self._mangle(node.name)
        params = self._format_params(node.params)

        w.comment(f"const fn {node.name} — compile-time evaluable")
        self._in_fn = True
        self._local_vars = set()

        # In C, const fn emits as a static inline with const attributes
        w.block_open(f"static inline {ret} {name}({params})")
        if node.body:
            self._visit_block(node.body)
        w.block_close()
        w.line()
        self._in_fn = False
        self._functions.append(name)

    def _visit_MacroDecl(self, node: MacroDecl):
        w = self._w
        name = node.name
        params = node.params or []

        w.comment(f"macro {name}! — syntactic macro (expanded at compile time)")
        if params:
            param_str = ", ".join(params)
            w.line(f"#define {name}({param_str})  \\")
            w.line("    /* macro body — expand at call site */")
        else:
            w.line(f"#define {name}()  \\")
            w.line("    /* macro body — expand at call site */")
        w.line()

    def _visit_MacroInvocation(self, node: MacroInvocation):
        # As a statement
        args = ", ".join(self._visit_expr(a) for a in node.args)
        self._w.line(f"{node.name}({args});  /* macro invocation */")

    def _expr_MacroInvocation(self, node: MacroInvocation) -> str:
        args = ", ".join(self._visit_expr(a) for a in node.args)
        return f"{node.name}({args})"

    def _visit_CompTimeBlock(self, node: CompTimeBlock):
        w = self._w
        w.comment("comptime { ... } — compile-time evaluated block")
        w.block_open("/* comptime */")
        if node.body:
            self._visit_block(node.body)
        w.block_close()

    def _visit_DeriveAttr(self, node: DeriveAttr):
        w = self._w
        traits = ", ".join(node.traits)
        w.comment(f"@derive({traits}) — auto-generated trait implementations")

    def _expr_ReflectExpr(self, node: ReflectExpr) -> str:
        # In C, reflect produces a struct literal with type info
        return (f'((ltl_value_t){{.tag = LTL_STRING, '
                f'.s = ltl_str_new("{node.target}")}})')

    def _expr_QuoteExpr(self, node: QuoteExpr) -> str:
        return '/* quote { ... } */ ((ltl_value_t){.tag = LTL_NIL})'

    def _expr_UnquoteExpr(self, node) -> str:
        if hasattr(node, "expr") and node.expr:
            return self._visit_expr(node.expr)
        return "0"

    # ── pattern matching helpers ──────────────────────────────────────────

    def _pattern_cond(self, subject: str, pattern) -> str:
        """Generate a C boolean expression for pattern matching."""
        if isinstance(pattern, WildcardPattern):
            return "1"
        if isinstance(pattern, LiteralPattern):
            val = self._expr_Literal(Literal(value=pattern.value))
            return f"{subject}.i == {val}"
        if isinstance(pattern, BindingPattern):
            return "1"  # always matches, binding handled separately
        return "1"

    # ── main / kernel entry ───────────────────────────────────────────────

    def _emit_main_wrapper(self):
        w = self._w
        w.line()
        w.comment("═══ Entry Point ═══")
        w.block_open("int main(int argc, char *argv[])")
        if "main" in self._functions or "ltl_main" in [
                self._mangle("main")]:
            w.line("ltl_main();")
        else:
            w.comment("No main() found — nothing to run")
        w.line("return 0;")
        w.block_close()

    def _emit_kernel_entry(self):
        w = self._w
        w.line()
        w.comment("═══ Kernel Entry Point ═══")
        w.block_open("void _start(void)")
        w.comment("Clear BSS")
        w.line("ltl_heap_reset();")
        w.line()
        if "kernel_main" in self._functions:
            w.line("kernel_main();")
        elif "main" in self._functions or "ltl_main" in self._functions:
            w.line("ltl_main();")
        else:
            w.line('println("LateralusOS — No kernel_main() found");')
        w.line()
        w.comment("Halt CPU")
        w.block_open("for (;;)")
        w.line('__asm__ volatile ("hlt");')
        w.block_close()
        w.block_close()


# ─────────────────────────────────────────────────────────────────────────────
# Public API (matches python.py pattern)
# ─────────────────────────────────────────────────────────────────────────────

def transpile_to_c(ast: Program, mode: CMode = CMode.HOSTED,
                   target_arch: str = "x86_64") -> str:
    """Transpile a Lateralus AST to C99 source code."""
    return CTranspiler(mode=mode, target_arch=target_arch).transpile(ast)
