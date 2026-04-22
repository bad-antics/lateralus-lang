#!/usr/bin/env python3
"""Render 'C Backend Transpiler Design' to PDF."""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "c-backend-transpiler-design.pdf"

TITLE = "The Lateralus C Backend"
SUBTITLE = "Transpiling a pipeline-first language to freestanding C99"
META = "bad-antics &middot; April 2026 &middot; Lateralus Compiler Internals"
ABSTRACT = (
    "The Lateralus compiler ships a C backend that emits either hosted or freestanding C99. "
    "The hosted mode is useful for embedding Lateralus in existing C projects; the freestanding "
    "mode is what lets LateralusOS's kernel integrate Lateralus-authored modules without a libc. "
    "This paper describes the transpiler's runtime library, the value representation, the lowering "
    "rules for pipelines and closures, and the escape hatches we provide for FFI-heavy code. We "
    "close with benchmarks comparing the C-backend output to the VM on the canonical example set."
)

SECTIONS = [
    ("1. Goals and Non-Goals", [
        ("h3", "1.1 Goals"),
        ("list", [
            "<b>Readable output.</b> A developer should be able to open the generated <code>.c</code> file and follow it. No one-letter identifiers, no compressed whitespace, no line-noise.",
            "<b>Portable C99.</b> The output compiles under GCC 9+, Clang 10+, and MSVC 2019+. No compiler-specific extensions in the generated code; only in the optional runtime shims.",
            "<b>Freestanding optional.</b> A <code>--freestanding</code> flag produces code with no dependency on libc, malloc, stdio, or string.h. All such services are provided by the embedding environment.",
            "<b>Round-trippable semantics.</b> A Lateralus source file that passes the VM's test suite must also pass the same tests when compiled through the C backend and executed as native code.",
        ]),
        ("h3", "1.2 Non-Goals"),
        ("list", [
            "<b>Minimum binary size.</b> We prioritize readable output over aggressive tree-shaking; users who want the latter can run <code>strip</code> and link-time DCE.",
            "<b>AOT compilation of the full language.</b> Reflection, <code>eval</code>, and dynamic module loading are not supported in the C backend; they remain VM-only.",
            "<b>Incremental compilation.</b> The backend recompiles the whole module on each invocation. Users wanting incremental builds can partition their code into multiple modules.",
        ]),
    ]),
    ("2. Value Representation", [
        "The runtime value is a tagged union:",
        ("code",
         "typedef enum {\n"
         "    LTL_INT, LTL_FLOAT, LTL_BOOL, LTL_STR,\n"
         "    LTL_LIST, LTL_MAP, LTL_FN, LTL_NULL\n"
         "} ltl_tag_t;\n"
         "\n"
         "typedef struct ltl_val {\n"
         "    ltl_tag_t tag;\n"
         "    union {\n"
         "        int64_t  i;\n"
         "        double   f;\n"
         "        int      b;\n"
         "        ltl_str_t *s;\n"
         "        ltl_list_t *l;\n"
         "        ltl_map_t  *m;\n"
         "        ltl_fn_t   *fn;\n"
         "    } v;\n"
         "} ltl_val_t;"),
        "Strings, lists, maps, and functions are heap-allocated and reference-counted. The ref-count is the first field of the target struct so that the <code>ltl_retain</code> and <code>ltl_release</code> macros do not need to know the specific type. On <code>--freestanding</code> the allocator is a user-provided <code>ltl_alloc</code>/<code>ltl_free</code> pair; in hosted mode they default to <code>malloc</code>/<code>free</code>.",
    ]),
    ("3. Pipeline Lowering", [
        "The pipeline operator <code>|&gt;</code> desugars at the AST stage into left-to-right function calls, so by the time the C emitter sees an expression there are no pipelines left: only <code>Call</code> nodes. This keeps the backend simple and pushes the non-obvious work into a single well-tested AST-lowering pass.",
        "Concretely, <code>xs |&gt; map(f) |&gt; filter(p)</code> is equivalent at the AST level to <code>filter(p, map(f, xs))</code>. The backend emits:",
        ("code",
         "ltl_val_t t1 = ltl_call2(map_builtin, f, xs);\n"
         "ltl_val_t t2 = ltl_call2(filter_builtin, p, t1);\n"
         "ltl_release(t1);                      // freed after use\n"
         "return t2;"),
        "The <code>ltl_release</code> calls are inserted by a lifetime pass that runs after lowering but before emission; it walks each basic block in program order and emits a release after the last use of each temporary.",
    ]),
    ("4. Closures", [
        "Closures in Lateralus capture by value (copies of bindings at closure-creation time). The C backend emits a closure as a pair of pointers: a function pointer and an environment struct pointer. The environment struct is generated per call site:",
        ("code",
         "// source: let add = fn(x) { fn(y) { x + y } }\n"
         "typedef struct { ltl_refcount_t rc; ltl_val_t x; } env_0_t;\n"
         "\n"
         "static ltl_val_t lambda_inner(env_0_t *env, ltl_val_t y) {\n"
         "    return ltl_add(env->x, y);\n"
         "}\n"
         "\n"
         "static ltl_val_t add_outer(ltl_val_t x) {\n"
         "    env_0_t *env = ltl_alloc(sizeof(env_0_t));\n"
         "    env->rc = 1;\n"
         "    env->x  = ltl_retain(x);\n"
         "    return ltl_make_fn(lambda_inner, env);\n"
         "}"),
        "The environment struct is reference-counted; when the last closure holding it goes away, the struct and its captured values are released.",
    ]),
    ("5. FFI", [
        "The <code>@foreign</code> annotation in Lateralus declares a function whose body is external C. The backend emits a declaration only:",
        ("code",
         "@foreign(\"c\", header=\"openssl/md5.h\")\n"
         "fn md5(data: bytes) -&gt; bytes"),
        "becomes:",
        ("code",
         "#include &lt;openssl/md5.h&gt;\n"
         "extern unsigned char *MD5(const unsigned char *, size_t, unsigned char *);\n"
         "// wrapper inserted by runtime:\n"
         "static ltl_val_t ltl_md5(ltl_val_t data) { ... }"),
        "For the hosted target, the linker resolves the external symbol normally. For the freestanding target, the user is expected to provide the implementation; the backend emits no assumptions beyond the declaration.",
    ]),
    ("6. Runtime Library", [
        "The runtime is a single-file header-and-source pair:",
        ("list", [
            "<code>ltl_runtime.h</code> &mdash; type definitions, macro declarations (~200 lines).",
            "<code>ltl_runtime.c</code> &mdash; reference-counting helpers, list/map implementations, string builder, pipeline built-ins (<code>map</code>, <code>filter</code>, <code>reduce</code>, <code>zip</code>, <code>range</code>), arithmetic dispatch, comparison, hashing (~1400 lines).",
        ]),
        "In freestanding mode the runtime is linked as a static object; the user's build system provides <code>ltl_alloc</code>, <code>ltl_free</code>, <code>ltl_memcpy</code>, and <code>ltl_memset</code> symbols. On LateralusOS these are backed by the kernel's heap allocator.",
    ]),
    ("7. Freestanding Mode", [
        "The <code>--freestanding</code> flag toggles three behaviours:",
        ("list", [
            "<b>No stdio.</b> <code>println</code> is declared as an extern that the user must supply.",
            "<b>No stdlib.</b> <code>malloc</code>/<code>free</code> symbols are replaced with <code>ltl_alloc</code>/<code>ltl_free</code> externs.",
            "<b>No string.h.</b> The runtime's own <code>ltl_memcpy</code>/<code>ltl_memset</code>/<code>ltl_strlen</code> are used.",
        ]),
        "The resulting object file can be linked with <code>-ffreestanding -nostdlib</code> flags and run in kernel context. LateralusOS uses this mode for the bootstrap utilities that were originally written in C but have since been ported to Lateralus: the command-line parser in the shell, the ELF loader, and the ramdisk walker.",
    ]),
    ("8. Correctness Testing", [
        "The test strategy is a differential fuzzer: every file in <code>examples/</code> and every file in <code>tests/</code>'s source corpus is compiled both through the VM and through the C backend, and the outputs are diffed. We run this nightly against the main branch. The diff has been clean for the last 38 consecutive nights as of this writing; the only divergences have been in examples that use reflection or <code>eval</code>, both of which the C backend correctly refuses with a named diagnostic.",
    ]),
    ("9. Benchmarks", [
        "Wall-clock time for the canonical example set; hosted mode, GCC 13 with <code>-O2</code>:",
        ("list", [
            "<code>fibonacci.ltl</code> (n=35): VM 52 ms, C backend 4 ms (13x).",
            "<code>crypto_challenges.ltl</code>: VM 850 ms, C backend 95 ms (9x).",
            "<code>data_pipeline.ltl</code>: VM 160 ms, C backend 22 ms (7x).",
            "<code>physics_sim.ltl</code> (10,000 frames): VM 2.9 s, C backend 280 ms (10x).",
        ]),
        "The speedups are roughly what you'd expect for a dynamic-language-to-C transpiler: native arithmetic, native function-call convention, no interpreter dispatch. The remaining overhead is in reference counting and in the tagged-value dispatch on arithmetic operations.",
    ]),
    ("10. Future Work", [
        ("list", [
            "<b>Monomorphization pass.</b> For functions whose type is statically known, emit specialised C rather than going through the tagged-value path. Projected 2-4x further speedup on numeric code.",
            "<b>Region-based memory.</b> Replace reference counting with region allocators in the common <code>fn ... { ... }</code> case; cuts allocation churn on pipeline-heavy code.",
            "<b>WASM backend.</b> A parallel backend emitting WebAssembly using the same AST-lowering pass. Prototype in progress.",
        ]),
    ]),
    ("11. Conclusion", [
        "The C backend is a pragmatic balance: it's not the fastest possible Lateralus implementation, but it's readable, portable, and freestanding-capable, and it earns its place as the native deployment target for kernel and embedded use. The 10x speedup over the VM is comfortable, and the runtime fits in 1,600 lines of C including comments. Further optimisation work is planned but not on the critical path; the current backend is already the fastest Lateralus target and the one we recommend for production deployment.",
    ]),
]

if __name__ == "__main__":
    render_paper(OUT, title=TITLE, subtitle=SUBTITLE, meta=META,
                 abstract=ABSTRACT, sections=SECTIONS)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
