#!/usr/bin/env python3
"""Render 'Polyglot Bridge Internals' in canonical Lateralus style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "polyglot-bridge-internals.pdf"

render_paper(
    out_path=str(OUT),
    title="Polyglot Bridge Internals",
    subtitle="Calling C, Python, and Rust from Lateralus without wrapper boilerplate",
    meta="bad-antics &middot; July 2024 &middot; Lateralus Language Research",
    abstract=(
        "Lateralus's polyglot bridge enables calling functions in C, Python, and Rust "
        "from Lateralus code with zero hand-written wrapper code. The bridge uses "
        "a three-layer architecture: a compile-time interface extractor that reads "
        "foreign headers or type stubs, a type-mapping layer that converts between "
        "Lateralus and foreign types, and a runtime ABI adaptor that handles calling "
        "convention differences. This paper describes each layer, explains the type-"
        "safety guarantees and their limits, and benchmarks the overhead versus "
        "hand-written FFI bindings."
    ),
    sections=[
        ("1. Motivation: FFI Without Wrappers", [
            "Foreign Function Interfaces (FFI) in most languages require the programmer "
            "to write explicit binding code: a C header declaration in Rust, a "
            "<code>ctypes</code> structure in Python, or a <code>foreign import</code> "
            "declaration in Haskell. For large C libraries (libc, OpenSSL, SQLite), "
            "the binding code can exceed 10,000 lines and must be maintained in sync "
            "with the upstream headers.",
            "Lateralus's polyglot bridge eliminates wrapper code for the common case: "
            "when the foreign function's types map cleanly to Lateralus types, the "
            "bridge generates the binding automatically from the foreign header or "
            "type stub. The programmer writes one import declaration:",
            ("code",
             "// Import from a C library\n"
             "import foreign::c { header: \"<sqlite3.h>\", lib: \"sqlite3\" }\n\n"
             "// All sqlite3_* functions are now callable directly\n"
             "let db = sqlite3_open(\"data.db\")?"),
            "When types do not map cleanly (e.g., C unions, variadic functions, "
            "pointer-to-pointer patterns), the programmer writes a thin adapter "
            "in a separate file and the bridge wraps the adapter instead of the "
            "original function.",
        ]),
        ("2. Layer 1: Interface Extraction", [
            "The interface extractor runs at compile time. For C headers, it uses a "
            "minimal C preprocessor and parser to extract function declarations, "
            "typedef'd struct definitions, and enum values. It does not evaluate "
            "preprocessor macros that expand to expressions (those require manual "
            "binding).",
            ("code",
             "// Extracted from sqlite3.h (simplified)\n"
             "foreign_fn sqlite3_open(filename: *const u8, db: **sqlite3) -> i32\n"
             "foreign_fn sqlite3_close(db: *sqlite3) -> i32\n"
             "foreign_fn sqlite3_exec(db: *sqlite3, sql: *const u8,\n"
             "                        cb: *fn, arg: *void, errmsg: **u8) -> i32"),
            "For Python modules, the extractor reads <code>.pyi</code> stub files "
            "(PEP 484) and maps Python type annotations to Lateralus types. For Rust "
            "crates, it reads the crate's <code>cbindgen.toml</code> and generated "
            "C header to extract the public ABI.",
            ("h3", "2.1 Extraction Limits"),
            "The extractor handles: function pointers as callback types, "
            "null-terminated string conventions (<code>*const u8</code> → "
            "<code>CStr</code>), fixed-size arrays, and opaque handle types. "
            "It does not handle: C++ classes, variadic arguments, setjmp/longjmp "
            "exception models, or platform-specific ABI extensions.",
        ]),
        ("3. Layer 2: Type Mapping", [
            "The type mapper converts foreign types to Lateralus types and back. "
            "The mapping is injective on the safe subset: every safe Lateralus type "
            "has a unique foreign representation, but not every foreign type has a "
            "safe Lateralus equivalent.",
            ("code",
             "Foreign Type         Lateralus Type      Safety\n"
             "---------------------------------------------------\n"
             "i8, i16, i32, i64   i8, i16, i32, i64   safe\n"
             "u8, u16, u32, u64   u8, u16, u32, u64   safe\n"
             "f32, f64            f32, f64             safe\n"
             "bool (C _Bool)      bool                 safe\n"
             "*const T            &T (borrow)          safe (no null)\n"
             "*mut T              &mut T               safe (no null)\n"
             "*const u8 (NUL-term) CStr                safe\n"
             "struct { fields }   record { fields }    safe\n"
             "void*               unsafe::RawPtr       unsafe\n"
             "union { ... }       unsafe::ForeignUnion unsafe\n"
             "int (*)(...)        unsafe::FnPtr        unsafe"),
            "When the mapper encounters an unsafe type, it wraps the foreign function "
            "in an <code>unsafe</code> block in the generated binding. The programmer "
            "must explicitly call the function within an <code>unsafe { }</code> scope, "
            "acknowledging the invariants they are responsible for maintaining.",
        ]),
        ("4. Layer 3: ABI Adaptor", [
            "The ABI adaptor handles calling convention differences at runtime. "
            "On x86-64 Linux, C uses the System V AMD64 ABI; on Windows, C uses "
            "the Microsoft x64 ABI. Lateralus uses the System V ABI for its native "
            "calls and generates a thunk when calling Windows binaries on Linux "
            "or vice versa.",
            "For Python, the bridge calls the CPython C API directly: arguments are "
            "converted from Lateralus values to <code>PyObject*</code> via the "
            "type mapping layer, the Python function is called via "
            "<code>PyObject_Call</code>, and the return value is converted back. "
            "The GIL is acquired before the call and released after if the call is "
            "marked <code>blocking</code>.",
            ("code",
             "// Calling a Python function from Lateralus\n"
             "import foreign::python { module: \"numpy\" }\n\n"
             "let array = numpy::array([1.0, 2.0, 3.0, 4.0])\n"
             "let mean = numpy::mean(array)  // returns f64"),
            ("h3", "4.1 Error Convention Mapping"),
            "C functions signal errors via return codes; Python via exceptions; "
            "Rust via <code>Result</code>. The bridge maps each convention to "
            "Lateralus's <code>Result</code>. For C, the programmer annotates "
            "the expected success code in the import declaration; for Python, "
            "any raised exception is caught and converted to <code>Err</code>; "
            "for Rust, the <code>Result</code> is passed through directly.",
        ]),
        ("5. Pipeline Integration", [
            "Foreign functions that pass through the type mapper become usable "
            "as pipeline stages without any additional adapter code. A C function "
            "<code>process(data: *const u8, len: usize) -> i32</code> becomes "
            "a Lateralus function <code>process(data: &[u8]) -> Result&lt;i32, i32&gt;</code> "
            "and can be used in a pipeline:",
            ("code",
             "let result = raw_bytes\n"
             "    |> compress\n"
             "    |?> process        // foreign C function, error-propagating\n"
             "    |>  format_result"),
            "The bridge generates the type conversion code at each call site so that "
            "the pipeline form is ergonomic. The overhead of the conversion is "
            "measured in the benchmarks section.",
        ]),
        ("6. Safety Guarantees and Their Limits", [
            "The bridge provides the following guarantees for the safe-type subset:",
            ("list", [
                "No null pointer dereferences: safe pointer types in Lateralus "
                "are non-null by construction; the bridge verifies at the call site "
                "that no null is passed to a non-nullable foreign parameter.",
                "No buffer overflows: slice types carry length metadata; the bridge "
                "passes both the pointer and the length to foreign functions that "
                "expect separate pointer/length arguments.",
                "No use-after-free: the lifetime system ensures that borrows passed "
                "to foreign functions do not outlive the owning value.",
            ]),
            "The bridge does NOT guarantee memory safety for foreign code itself: "
            "if the C function has an internal buffer overflow, Lateralus cannot "
            "detect it. The bridge only guarantees that the Lateralus side of "
            "the call is safe.",
        ]),
        ("7. Performance Benchmarks", [
            "We compared the polyglot bridge overhead against hand-written FFI "
            "bindings for three scenarios: calling a simple C math function, "
            "calling a struct-taking C library function, and calling a Python "
            "function via CPython API.",
            ("code",
             "Scenario                  Bridge overhead vs hand-written FFI\n"
             "--------------------------------------------------------------\n"
             "C scalar function             < 1 ns      (zero overhead, inlined)\n"
             "C struct-passing function     ~3 ns       (struct copy, unavoidable)\n"
             "C callback registration       ~5 ns       (function pointer wrap)\n"
             "Python function call          ~800 ns     (GIL + PyObject overhead)"),
            "The C overhead is negligible: the bridge generates the same code as "
            "a hand-written binding after inlining. The Python overhead is "
            "inherent to the CPython API and is no worse than calling from C "
            "via the same API.",
        ]),
        ("8. Future Work", [
            "Planned improvements to the polyglot bridge: automatic binding "
            "generation for gRPC and Cap'n Proto schemas (treating RPC as a "
            "foreign call layer), support for WASM modules as a language-neutral "
            "foreign runtime, and a bridge-aware fuzzer that generates valid "
            "inputs for foreign functions based on their extracted type signatures.",
            "The type-mapping layer will be extended to handle C++ templates "
            "via libclang integration, enabling direct calls into modern C++ "
            "libraries without an intermediate C wrapper layer.",
        ]),
    ],
)

print(f"wrote {OUT}")
