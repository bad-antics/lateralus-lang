"""
LATERALUS Standard Library Indexer
Indexes stdlib/*.ltl files for LSP hover signatures and completions.
"""
from __future__ import annotations

import re
import os
from dataclasses import dataclass
from typing import Any, Optional
from pathlib import Path


@dataclass
class StdlibFunction:
    """A function signature from the standard library."""
    name: str
    params: str
    return_type: str
    doc: str
    module: str


# Regex patterns for parsing stdlib functions
_RE_FN_SIGNATURE = re.compile(
    r"^\s*--\s*(.+?)\s*\n"  # doc comment before fn
    r"(?:pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^\s{]+))?\s*{",
    re.MULTILINE
)

_RE_MODULE = re.compile(r"^\s*module\s+(\w+)", re.MULTILINE)


def parse_stdlib_file(filepath: Path) -> list[StdlibFunction]:
    """Parse a single stdlib .ltl file and extract function signatures."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    # Extract module name
    module_match = _RE_MODULE.search(content)
    module = module_match.group(1) if module_match else filepath.stem

    functions = []
    for match in _RE_FN_SIGNATURE.finditer(content):
        doc, name, params, return_type = match.groups()
        doc = doc.strip().lstrip("--").strip() if doc else ""
        return_type = return_type.strip() if return_type else "any"
        params = params.strip()

        functions.append(StdlibFunction(
            name=name,
            params=params,
            return_type=return_type,
            doc=doc,
            module=module,
        ))

    return functions


def index_stdlib(stdlib_dir: Path) -> dict[str, StdlibFunction]:
    """Index all stdlib functions from stdlib directory."""
    functions = {}

    for ltl_file in stdlib_dir.glob("*.ltl"):
        if ltl_file.name.startswith(".") or ltl_file.name == "core.ltl":
            # Skip core.ltl (builtins) - handled separately
            continue

        try:
            funcs = parse_stdlib_file(ltl_file)
            for fn in funcs:
                # Store with lowercase module for case-insensitive lookup
                key = f"{fn.module.lower()}.{fn.name}"
                functions[key] = fn
        except Exception:
            # Skip files that can't be parsed
            continue

    return functions


def get_stdlib_root() -> Path:
    """Get the stdlib directory path."""
    # Try multiple locations
    candidates = [
        Path(__file__).parent / "stdlib",
        Path.cwd() / "stdlib",
        Path(__file__).parent.parent / "stdlib",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback
    return Path.cwd() / "stdlib"


# Global cache
_STDLIB_CACHE: Optional[dict[str, StdlibFunction]] = None


def get_stdlib_functions() -> dict[str, StdlibFunction]:
    """Get all indexed stdlib functions (cached)."""
    global _STDLIB_CACHE
    if _STDLIB_CACHE is None:
        stdlib_dir = get_stdlib_root()
        _STDLIB_CACHE = index_stdlib(stdlib_dir)
    return _STDLIB_CACHE


def get_stdlib_function(name: str) -> Optional[StdlibFunction]:
    """Get a specific stdlib function by qualified name (module.name)."""
    functions = get_stdlib_functions()
    return functions.get(name)


def get_stdlib_hover(name: str) -> Optional[dict]:
    """Get hover info for a stdlib function."""
    fn = get_stdlib_function(name)
    if not fn:
        return None

    # Build signature
    sig = f"fn {fn.name}({fn.params}) -> {fn.return_type}"
    doc = fn.doc if fn.doc else "No documentation available."

    return {
        "contents": {
            "kind": "markdown",
            "value": f"```lateralus\n{sig}\n```\n\n{fn.doc}",
        },
    }


def get_stdlib_completions(prefix: str = "") -> list[dict]:
    """Get completion items for stdlib functions."""
    functions = get_stdlib_functions()
    items = []
    prefix_lower = prefix.lower()

    for key, fn in functions.items():
        if not prefix_lower or fn.name.lower().startswith(prefix_lower):
            items.append({
                "label": f"{fn.module}.{fn.name}",
                "kind": 3,  # Function
                "detail": f"{fn.module}.{fn.name}({fn.params}) -> {fn.return_type}",
                "documentation": fn.doc or "Standard library function",
            })

    return items


def get_all_stdlib_names() -> list[str]:
    """Get all stdlib function qualified names."""
    return list(get_stdlib_functions().keys())