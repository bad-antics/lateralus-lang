#!/usr/bin/env python3
"""Render 'The Lateralus Module System' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-module-system.pdf"

render_paper(
    out_path=str(OUT),
    title="The Lateralus Module System",
    subtitle="Namespacing, visibility, package management, and the module import graph",
    meta="bad-antics &middot; March 2025 &middot; Lateralus Language Research",
    abstract=(
        "The Lateralus module system provides namespacing for definitions, visibility "
        "control for APIs, and a package manager interface for external dependencies. "
        "Each source file is a module; modules are organized into packages; packages "
        "are versioned and distributed via the Lateralus package registry. This paper "
        "describes the module declaration syntax, the import graph model, visibility "
        "rules, and the package manifest format. We pay special attention to the "
        "module system's interaction with the pipeline type system: a module can export "
        "pipeline stages as typed values, enabling modular composition of pipeline "
        "libraries."
    ),
    sections=[
        ("1. Modules and Files", [
            "In Lateralus, every source file is a module. The module name is derived "
            "from the file path relative to the package root: a file at "
            "<code>src/data/parser.lt</code> in package <code>my_app</code> has "
            "module path <code>my_app::data::parser</code>.",
            "A module may contain declarations in any order: the compiler resolves "
            "all names in a two-pass process that first scans top-level declarations "
            "and then resolves references. Forward references within a module are "
            "permitted.",
            ("code",
             "// src/data/parser.lt\n"
             "module my_app::data::parser\n\n"
             "pub use crate::types::ParsedDoc\n\n"
             "pub fn parse(input: &[u8]) -> Result<ParsedDoc, ParseError> {\n"
             "    // ...\n"
             "}\n\n"
             "// Private helper — not exported\n"
             "fn read_header(bytes: &[u8]) -> Header { ... }"),
        ]),
        ("2. Visibility: pub, pub(crate), and private", [
            "Lateralus has three visibility levels:",
            ("list", [
                "<b>private</b> (default): the item is visible only within the "
                "declaring module.",
                "<b><code>pub(crate)</code></b>: the item is visible within the "
                "current package but not to external packages.",
                "<b><code>pub</code></b>: the item is visible to any importer, "
                "including external packages.",
            ]),
            ("code",
             "pub fn exported_to_everyone() { }\n"
             "pub(crate) fn exported_within_package() { }\n"
             "fn private_to_this_module() { }"),
            "The visibility system prevents accidental exposure of internal "
            "implementation details. A package's public API is exactly its "
            "set of <code>pub</code>-marked items at any visibility-boundary "
            "module path.",
        ]),
        ("3. Importing Modules", [
            "The <code>import</code> keyword brings names from another module "
            "into scope:",
            ("code",
             "// Absolute import\n"
             "import std::data::Vec\n\n"
             "// Multiple names from one module\n"
             "import std::math::{ sin, cos, pi }\n\n"
             "// Rename on import\n"
             "import std::data::HashMap as Map\n\n"
             "// Glob import (use sparingly)\n"
             "import std::prelude::*"),
            "Imports are resolved at compile time. Cyclic imports are permitted "
            "as long as they do not create a cycle in the type definition graph "
            "(value cycles are resolved at link time, type cycles cause a compile "
            "error).",
            ("h3", "3.1 The Import Graph"),
            "The compiler builds an import graph before type-checking: a directed "
            "acyclic graph where nodes are modules and edges are import relationships. "
            "The topological order of the graph determines the compilation order: "
            "a module is compiled only after all its imports are compiled.",
        ]),
        ("4. The Package Manifest", [
            "A package is a directory containing a <code>Package.toml</code> "
            "manifest and a <code>src/</code> directory of Lateralus source files. "
            "The manifest declares the package name, version, and dependencies:",
            ("code",
             "[package]\n"
             "name    = \"my_app\"\n"
             "version = \"1.2.0\"\n"
             "edition = \"2025\"\n\n"
             "[dependencies]\n"
             "std          = { version = \">=1.0\" }  # always implicit\n"
             "http_client  = { version = \"~0.8\" }\n"
             "json         = { version = \"^2.1\", features = [\"streaming\"] }\n\n"
             "[dev-dependencies]\n"
             "test_helpers = { version = \"0.3\" }"),
            "Version constraints follow SemVer: <code>^</code> allows any compatible "
            "version (same major), <code>~</code> allows patch-level changes only, "
            "and <code>&gt;=</code> imposes a lower bound.",
        ]),
        ("5. Pipeline Stages as Module Exports", [
            "One of the module system's distinctive features is the ability to "
            "export pipeline stage values as typed library items. A module can "
            "define a pipeline value and export it:",
            ("code",
             "// Exporting a pipeline as a library value\n"
             "pub let request_pipeline : Pipeline<RawBytes, HttpResponse> = pipe {\n"
             "    |>  parse_http_request\n"
             "    |?> authenticate\n"
             "    |?> route_to_handler\n"
             "    |>  serialize_response\n"
             "}"),
            "External code imports and composes the pipeline:",
            ("code",
             "import my_framework::request_pipeline\n\n"
             "// Extend with additional middleware\n"
             "let extended = logging_stage >> request_pipeline >> metrics_stage"),
            "This model enables pipeline library authors to ship composable "
            "stage values rather than just functions, giving users a richer "
            "vocabulary for building complex pipelines from trusted components.",
        ]),
        ("6. Package Registry", [
            "The Lateralus package registry (<code>pkg.lateralus.dev</code>) "
            "hosts published packages. To publish a package:",
            ("code",
             "ltl package build       # verify package, run tests\n"
             "ltl package publish     # upload to registry\n"
             "                         # requires API token from pkg.lateralus.dev"),
            "The registry enforces package name uniqueness per author, SemVer "
            "compliance, and a checksum manifest for every uploaded artifact. "
            "Package downloads are verified against the checksum before use.",
        ]),
        ("7. Workspace Mode", [
            "Multiple packages that are developed together (a monorepo) are "
            "organized as a workspace. A workspace <code>Workspace.toml</code> "
            "at the repository root lists the packages:",
            ("code",
             "[workspace]\n"
             "members = [\n"
             "    \"packages/core\",\n"
             "    \"packages/http\",\n"
             "    \"packages/cli\",\n"
             "]"),
            "Workspace builds compile all members together, resolving "
            "cross-member imports as if they were internal modules. Path "
            "dependencies between workspace members do not require a "
            "registry round-trip.",
        ]),
        ("8. Stability and Semver Checking", [
            "The Lateralus toolchain includes a semver checker that compares "
            "the public API of a new version against the previous version and "
            "determines the minimum version bump required (major, minor, patch). "
            "The check is based on the published API surface: added public items "
            "require a minor bump; removed or changed public items require a major "
            "bump; no public API changes allow a patch bump.",
            ("code",
             "ltl package semver-check\n"
             "# Comparing v1.2.0 API against published v1.1.3...\n"
             "# Added: pub fn new_helper() [minor change: +1 minor version]\n"
             "# Removed: none\n"
             "# Changed: none\n"
             "# Minimum required bump: 1.2.0 → 1.3.0"),
            "The semver checker integrates with the CI pipeline to block "
            "releases that would break the semver contract.",
        ]),
    ],
)

print(f"wrote {OUT}")
