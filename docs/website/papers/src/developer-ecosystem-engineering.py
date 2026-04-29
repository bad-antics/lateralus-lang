#!/usr/bin/env python3
"""Render 'Developer Ecosystem Engineering' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "developer-ecosystem-engineering.pdf"

render_paper(
    out_path=str(OUT),
    title="Developer Ecosystem Engineering",
    subtitle="Package registry, toolchain distribution, IDE integration, and community tooling for Lateralus",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "A programming language is adopted through its ecosystem, not its specification. "
        "This paper describes the engineering decisions behind the Lateralus developer "
        "ecosystem: the package registry design, toolchain distribution and versioning, "
        "IDE integration via the Language Server Protocol, and community tooling such "
        "as the playground and documentation generator. Each component is motivated "
        "by concrete adoption goals and compared to analogous systems in Rust, "
        "Elixir, and Python."
    ),
    sections=[
        ("1. The Package Registry", [
            "The Lateralus package registry (registry.lateralus.dev) is a "
            "content-addressed store of signed package archives. The design "
            "principles are:",
            ("list", [
                "<b>Immutability</b>: published packages are never deleted or "
                "overwritten. The content hash is the canonical identifier.",
                "<b>Reproducibility</b>: given a version string, the registry "
                "always returns the same bytes. No floating tags.",
                "<b>Namespace isolation</b>: packages are namespaced by author "
                "(<code>bad-antics/nullsec</code>) preventing name squatting.",
                "<b>Signed archives</b>: every package is signed by the publisher's "
                "Ed25519 key; the public key is pinned in the registry.",
            ]),
            "Package resolution uses Pubgrub (the Dart/Flutter algorithm) which "
            "provides SAT-complete version solving with informative error messages "
            "when resolution fails.",
        ]),
        ("2. Toolchain Distribution with ltlup", [
            "<code>ltlup</code> is the Lateralus toolchain manager, analogous "
            "to Rust's <code>rustup</code>. It manages parallel installation of "
            "Lateralus compiler versions and components:",
            ("code",
             "# Install stable toolchain\n"
             "ltlup install stable\n\n"
             "# Install specific version\n"
             "ltlup install 1.4.2\n\n"
             "# Switch project to a specific version\n"
             "ltlup override set 1.3.1\n\n"
             "# Install components\n"
             "ltlup component add ltl-fmt ltl-check ltl-doc"),
            "Toolchain binaries are distributed as static musl-linked binaries "
            "for Linux (x86-64, AArch64, RISC-V) and macOS (x86-64, Apple Silicon). "
            "Each binary is SHA-256 verified against the registry manifest before "
            "installation.",
        ]),
        ("3. Build System: ltl build", [
            "The Lateralus build system is integrated into the <code>ltl</code> "
            "binary. It reads a <code>Lateralus.toml</code> workspace manifest "
            "and compiles the dependency graph in parallel:",
            ("code",
             "# Lateralus.toml\n"
             "[package]\n"
             "name    = \"nullsec\"\n"
             "version = \"0.9.0\"\n"
             "authors = [\"bad-antics\"]\n\n"
             "[dependencies]\n"
             "lateralus-net  = \"2.1\"\n"
             "lateralus-tls  = \"1.4\"\n"
             "lateralus-crypto = \"3.0\"\n\n"
             "[targets]\n"
             "x86_64-linux-musl  = {}\n"
             "riscv64gc-linux    = {}"),
            "Incremental compilation is based on content hashes: a compilation "
            "unit is re-compiled only if its content or any dependency's content "
            "has changed. Build artifacts are cached in <code>~/.ltl/cache</code>.",
        ]),
        ("4. Language Server Protocol Integration", [
            "The Lateralus Language Server (<code>ltl-lsp</code>) implements LSP 3.17 "
            "and provides IDE features for VS Code, Neovim, Emacs, and any "
            "LSP-compatible editor.",
            "Key features and their implementation strategy:",
            ("code",
             "Feature                  Implementation\n"
             "-----------------------------------------------\n"
             "Completion               Type-driven, scope-aware\n"
             "Hover types              Full type with effect annotations\n"
             "Go-to-definition         Symbol resolution from module graph\n"
             "Find references          Reverse index maintained incrementally\n"
             "Inline diagnostics       Error propagation from type checker\n"
             "Pipeline inlay hints     Stage types shown between |> operators\n"
             "Rename symbol            Cross-crate safe rename"),
            "Pipeline inlay hints are the most Lateralus-specific feature: "
            "the type at each pipeline stage is displayed inline, making "
            "complex pipelines self-documenting in the editor.",
        ]),
        ("5. Documentation Generator: ltl doc", [
            "<code>ltl doc</code> generates HTML documentation from Lateralus "
            "source files. Documentation is written as structured doc comments "
            "that attach to type, function, and module definitions:",
            ("code",
             "--- Applies f to the value and returns the result.\n"
             "--- If the value is an error, propagates it without calling f.\n"
             "---\n"
             "--- ## Example\n"
             "--- ```\n"
             "--- Ok(5) |?> double == Ok(10)\n"
             "--- Err(\"x\") |?> double == Err(\"x\")\n"
             "--- ```\n"
             "fn pipe_fallible<T, U, E>(val: Result<T,E>, f: T -> Result<U,E>)\n"
             "    -> Result<U,E>"),
            "The documentation site is generated as static HTML with a full-text "
            "search index. The pipeline operator table and type system reference "
            "are automatically cross-linked from every usage.",
        ]),
        ("6. The Online Playground", [
            "The Lateralus Playground (play.lateralus.dev) runs the compiler in "
            "the browser via WebAssembly. Architecture:",
            ("code",
             "Browser → WASM ltl compiler → LBC bytecode\n"
             "       → WASM LBC interpreter → stdout\n\n"
             "Latency: compile + run < 200ms for programs under 500 lines\n"
             "Sandboxing: WASM memory isolation; no filesystem or network access"),
            "The playground supports sharing via URL-encoded program text "
            "(compressed with DEFLATE). Shared programs are not stored server-side; "
            "the URL is the entire state. This eliminates privacy concerns "
            "and the need for a persistence backend.",
        ]),
        ("7. ltl-fmt: the Formatter", [
            "<code>ltl-fmt</code> is an opinionated code formatter in the "
            "style of gofmt: there is one correct formatting and the tool "
            "enforces it without configuration options. The design goals:",
            ("list", [
                "<b>Idempotent</b>: formatting a formatted file produces no changes.",
                "<b>Stable</b>: formatting output is stable across compiler versions "
                "for the same program.",
                "<b>Pipeline-aware</b>: pipeline chains are always formatted with one "
                "stage per line, with consistent indentation for the operator.",
            ]),
            ("code",
             "// ltl-fmt output: pipeline always vertical\n"
             "let result = input\n"
             "    |>  stage_one\n"
             "    |>  stage_two\n"
             "    |?> stage_three\n"
             "    |>  stage_four;"),
        ]),
        ("8. Community and Growth Strategy", [
            "Lateralus ecosystem growth is driven by three initiatives:",
            ("list", [
                "<b>Nullsec as flagship application</b>: nullsec demonstrates "
                "that a production-quality security tool can be built on Lateralus, "
                "providing a concrete example for security-focused adopters.",
                "<b>Academic engagement</b>: the formal semantics papers and "
                "the educational FRISC OS project provide entry points for "
                "researchers and students.",
                "<b>Compatibility bridge</b>: the C/Rust polyglot bridge allows "
                "incremental adoption — teams can use Lateralus for new pipeline "
                "code while retaining their existing C or Rust libraries.",
            ]),
        ]),
    ],
)

print(f"wrote {OUT}")
