#!/usr/bin/env python3
"""
LATERALUS Source Map Generator

Creates source maps that map compiled/transpiled output back to
original .ltl source lines. Essential for debugging and error reporting.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceMapping:
    """Maps a generated line/column to a source line/column."""
    gen_line: int
    gen_col: int
    src_line: int
    src_col: int
    source_file: str
    name: str | None = None


@dataclass
class SourceMap:
    """
    Source map following a simplified version of the Source Map v3 spec.
    Maps generated code positions back to original LATERALUS source.
    """
    version: int = 3
    file: str = ""
    source_root: str = ""
    sources: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    mappings: list[SourceMapping] = field(default_factory=list)

    def add_mapping(self, gen_line: int, gen_col: int,
                    src_line: int, src_col: int,
                    source_file: str, name: str | None = None):
        """Add a mapping entry."""
        if source_file not in self.sources:
            self.sources.append(source_file)

        if name and name not in self.names:
            self.names.append(name)

        self.mappings.append(SourceMapping(
            gen_line=gen_line,
            gen_col=gen_col,
            src_line=src_line,
            src_col=src_col,
            source_file=source_file,
            name=name,
        ))

    def find_source(self, gen_line: int, gen_col: int = 0) -> SourceMapping | None:
        """Find the source mapping for a generated position."""
        best = None
        for m in self.mappings:
            if m.gen_line == gen_line:
                if gen_col == 0 or m.gen_col <= gen_col:
                    if best is None or m.gen_col > best.gen_col:
                        best = m
        return best

    def find_generated(self, src_file: str, src_line: int) -> list[SourceMapping]:
        """Find all generated positions for a source line."""
        return [
            m for m in self.mappings
            if m.source_file == src_file and m.src_line == src_line
        ]

    def to_json(self) -> str:
        """Serialize to JSON format."""
        data = {
            "version": self.version,
            "file": self.file,
            "sourceRoot": self.source_root,
            "sources": self.sources,
            "names": self.names,
            "mappings": [
                {
                    "generatedLine": m.gen_line,
                    "generatedColumn": m.gen_col,
                    "originalLine": m.src_line,
                    "originalColumn": m.src_col,
                    "source": m.source_file,
                    "name": m.name,
                }
                for m in self.mappings
            ],
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, data: str) -> SourceMap:
        """Deserialize from JSON."""
        obj = json.loads(data)
        smap = cls(
            version=obj.get("version", 3),
            file=obj.get("file", ""),
            source_root=obj.get("sourceRoot", ""),
            sources=obj.get("sources", []),
            names=obj.get("names", []),
        )
        for m in obj.get("mappings", []):
            smap.mappings.append(SourceMapping(
                gen_line=m["generatedLine"],
                gen_col=m["generatedColumn"],
                src_line=m["originalLine"],
                src_col=m["originalColumn"],
                source_file=m["source"],
                name=m.get("name"),
            ))
        return smap

    def save(self, path: str | Path):
        """Save source map to file."""
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> SourceMap:
        """Load source map from file."""
        data = Path(path).read_text(encoding="utf-8")
        return cls.from_json(data)


class SourceMapBuilder:
    """Builder for constructing source maps during compilation."""

    def __init__(self, output_file: str, source_file: str):
        self.source_map = SourceMap(file=output_file)
        self.default_source = source_file
        self._gen_line = 1
        self._gen_col = 0

    def set_position(self, gen_line: int, gen_col: int = 0):
        """Set the current generated code position."""
        self._gen_line = gen_line
        self._gen_col = gen_col

    def map_line(self, src_line: int, src_col: int = 0,
                 name: str | None = None,
                 source_file: str | None = None):
        """Map current generated position to a source position."""
        self.source_map.add_mapping(
            gen_line=self._gen_line,
            gen_col=self._gen_col,
            src_line=src_line,
            src_col=src_col,
            source_file=source_file or self.default_source,
            name=name,
        )

    def advance_line(self):
        """Advance to the next generated line."""
        self._gen_line += 1
        self._gen_col = 0

    def build(self) -> SourceMap:
        """Return the completed source map."""
        return self.source_map


def enhance_error_with_source_map(error_line: int, source_map: SourceMap,
                                   source_content: dict[str, list[str]]) -> str:
    """
    Given an error in generated code, produce a helpful error message
    pointing to the original LATERALUS source.
    """
    mapping = source_map.find_source(error_line)
    if not mapping:
        return f"Error at generated line {error_line} (no source map entry)"

    src_file = mapping.source_file
    src_line = mapping.src_line

    lines = [
        f"Error in {src_file}, line {src_line}:",
    ]

    if src_file in source_content:
        src_lines = source_content[src_file]
        # Show context
        start = max(0, src_line - 3)
        end = min(len(src_lines), src_line + 2)

        for i in range(start, end):
            marker = " >> " if i == src_line - 1 else "    "
            lines.append(f"{marker}{i+1:4d} | {src_lines[i]}")

    if mapping.name:
        lines.append(f"  in function: {mapping.name}")

    return "\n".join(lines)
