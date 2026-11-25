"""Index of the LATERALUS standard library surface.

The language server answers ``textDocument/hover`` for builtins from a static
table.  Stdlib functions, however, live in ``stdlib/*.ltl`` and change with the
library.  This module parses those sources once, on first use, and exposes a
name → signature + first docstring line lookup so hover stays in sync with the
shipped stdlib without a second data file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_STDLIB_DIR = Path(__file__).resolve().parent.parent / "stdlib"

_MODULE_RE = re.compile(r"^\s*module\s+(?P<name>[\w.]+)")
_FN_RE = re.compile(
    r"^(?P<indent>\s*)(?P<pub>pub\s+)?(?P<async>async\s+)?fn\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*\((?P<params>.*)$"
)
_RET_RE = re.compile(r"^\s*\)?\s*(?:->\s*(?P<ret>[^\{]+?))?\s*\{?\s*$")
_DOC_PREFIX = "///"


def _clean_doc_line(line: str, prefix: str) -> str:
    return line.strip()[len(prefix):].strip()


def _is_separator(text: str) -> bool:
    """True for banner/section rules and generic headers, not documentation."""
    stripped = text.strip()
    if not stripped:
        return True
    # Lines made only of punctuation (banners, box-drawing rules, ellipses).
    if not any(ch.isalnum() for ch in stripped):
        return True
    if set(stripped) <= set("-=*_#~ \t"):
        return True
    # Section rules such as "-- Helpers ---" / "== Encoding ==". If the cleaned
    # text begins with a rule character it is a banner/heading, not prose.
    if stripped[:1] in ("-", "="):
        return True
    # File banner lines such as "LATERALUS Standard Library — weird.ltl".
    # File banner lines such as "LATERALUS Standard Library — weird.ltl".
    if re.match(r"^lateralus", stripped, re.I):
        return True
    # Generic boilerplate headers such as "Exported Function: encode".
    if re.match(r"^(exported\s+)?(function|fn|method)\s*:", stripped, re.I):
        return True
    return False


def _clean_plain(line: str) -> str:
    """Strip a plain ``//`` comment of the comment marker."""
    return line.strip()[2:].strip()


def _extract_doc(lines: list[str], def_index: int) -> tuple[str, str]:
    """Return ``(first docstring line, style)`` for a definition.

    ``style`` is ``"doc"`` for a ``///`` comment, ``"line"`` for a plain ``//``
    comment block, and ``""`` when the function is undocumented.
    """
    # 1. Contiguous /// block
    i = def_index - 1
    block: list[str] = []
    while i >= 0 and lines[i].strip().startswith(_DOC_PREFIX):
        block.append(_clean_doc_line(lines[i], _DOC_PREFIX))
        i -= 1
    for text in reversed(block):
        if not _is_separator(text):
            return text, "doc"

    # 2. Contiguous // block (never crosses a blank line)
    i = def_index - 1
    plain: list[str] = []
    while i >= 0 and lines[i].strip().startswith("//"):
        plain.append(_clean_plain(lines[i]))
        i -= 1
    for text in reversed(plain):  # nearest comment first
        if not _is_separator(text):
            return text, "line"
    return "", ""


def _join_signature(name: str, params: str, ret: str, is_async: bool) -> str:
    params = " ".join(params.split())
    prefix = "async fn" if is_async else "fn"
    signature = f"{prefix} {name}({params})"
    if ret:
        signature += f" -> {ret.strip()}"
    return signature


@dataclass(frozen=True)
class StdlibFunction:
    """One public stdlib function as seen by the editor."""

    name: str
    signature: str
    doc: str
    module: str
    path: str
    is_public: bool
    doc_style: str = ""

    def hover_markdown(self, related: Optional[list[str]] = None) -> str:
        body = f"```lateralus\n{self.signature}\n```\n\n`{self.module}`"
        if self.doc:
            body += f"\n\n{self.doc}"
        if related:
            body += "\n\nAlso defined in: " + ", ".join(related)
        return body


class StdlibIndex:
    """Lazily built index of stdlib functions."""

    def __init__(self, stdlib_dir: Optional[Path | str] = None):
        self.stdlib_dir = Path(stdlib_dir) if stdlib_dir is not None else DEFAULT_STDLIB_DIR
        self._by_name: Optional[dict[str, list[StdlibFunction]]] = None

    # -- building -------------------------------------------------------
    def _ensure_built(self) -> dict[str, list[StdlibFunction]]:
        if self._by_name is None:
            self._by_name = self._build()
        return self._by_name

    def _build(self) -> dict[str, list[StdlibFunction]]:
        index: dict[str, list[StdlibFunction]] = {}
        try:
            files = sorted(self.stdlib_dir.glob("*.ltl"))
        except OSError:
            return index
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:          # pragma: no cover – unreadable file
                continue
            for fn in self._parse_file(path, text):
                index.setdefault(fn.name, []).append(fn)
        return index

    @staticmethod
    def _parse_file(path: Path, text: str) -> list[StdlibFunction]:
        lines = text.split("\n")
        module = path.stem
        for line in lines:
            m = _MODULE_RE.match(line)
            if m:
                module = m.group("name")
                break

        functions: list[StdlibFunction] = []
        for i, line in enumerate(lines):
            m = _FN_RE.match(line)
            if not m:
                continue
            params = m.group("params")
            ret = ""
            if ")" not in params:
                # Multi-line parameter list: join until the closing paren.
                parts = [params]
                j = i + 1
                while j < len(lines) and j < i + 40:
                    parts.append(lines[j].strip())
                    if ")" in lines[j]:
                        break
                    j += 1
                joined = " ".join(parts)
                params, sep, rest = joined.partition(")")
                ret_m = re.match(r"\s*->\s*([^\{]+)", rest)
                ret = ret_m.group(1) if ret_m else ""
            else:
                params, _sep, rest = params.partition(")")
                ret_m = re.match(r"\s*->\s*([^\{]+)", rest)
                ret = ret_m.group(1) if ret_m else ""

            name = m.group("name")
            doc, doc_style = _extract_doc(lines, i)
            functions.append(StdlibFunction(
                name=name,
                signature=_join_signature(
                    name, params, ret, bool(m.group("async"))),
                doc=doc,
                module=module,
                path=str(path),
                is_public=bool(m.group("pub")),
                doc_style=doc_style,
            ))
        return functions

    # -- querying -------------------------------------------------------
    def candidates(self, name: str) -> list[StdlibFunction]:
        return list(self._ensure_built().get(name, ()))

    @staticmethod
    def _rank(fn: StdlibFunction, context: str) -> tuple:
        imported = bool(fn.module) and (fn.module in context
                                        or fn.module.split(".")[-1] in context)
        doc_rank = {"doc": 0, "line": 1}.get(fn.doc_style, 2)
        return (
            0 if imported else 1,       # imported modules first
            doc_rank,                   # /// docstring over // comment over none
            0 if fn.is_public else 1,   # `pub fn` over bare `fn`
            fn.module,                  # stable, deterministic tie-break
            fn.signature,
        )

    def lookup(self, name: str, context: str = "") -> Optional[StdlibFunction]:
        """Best match for ``name`` given the surrounding document text."""
        found = self.candidates(name)
        if not found:
            return None
        return min(found, key=lambda fn: self._rank(fn, context))

    def lookup_with_related(self, name: str,
                            context: str = "") -> tuple[Optional[StdlibFunction], list[str]]:
        """Best match plus the other modules that define the same name."""
        found = self.candidates(name)
        if not found:
            return None, []
        best = min(found, key=lambda fn: self._rank(fn, context))
        related = sorted({fn.module for fn in found if fn.module != best.module})
        return best, related

    def __len__(self) -> int:
        return sum(len(v) for v in self._ensure_built().values())


_DEFAULT_INDEX = StdlibIndex()


def get_stdlib_index() -> StdlibIndex:
    """Process-wide index used by the language server."""
    return _DEFAULT_INDEX


def lookup_stdlib_function(name: str, context: str = "") -> Optional[StdlibFunction]:
    """Return the stdlib function called ``name``, or ``None``."""
    return _DEFAULT_INDEX.lookup(name, context)


def lookup_stdlib_hover(name: str, context: str = "") -> Optional[str]:
    """Return the hover markdown for a stdlib function, or ``None``."""
    fn, related = _DEFAULT_INDEX.lookup_with_related(name, context)
    if fn is None:
        return None
    return fn.hover_markdown(related)
