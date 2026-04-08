#!/usr/bin/env python3
"""
Tests for the LATERALUS source map module.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lateralus_lang.source_map import (
    SourceMap,
    SourceMapBuilder,
    SourceMapping,
    enhance_error_with_source_map,
)


class TestSourceMapping:
    def test_basic_mapping(self):
        m = SourceMapping(
            gen_line=10, gen_col=0,
            src_line=5, src_col=0,
            source_file="test.ltl"
        )
        assert m.gen_line == 10
        assert m.src_line == 5
        assert m.source_file == "test.ltl"
        assert m.name is None

    def test_named_mapping(self):
        m = SourceMapping(
            gen_line=1, gen_col=4,
            src_line=1, src_col=0,
            source_file="test.ltl",
            name="main"
        )
        assert m.name == "main"


class TestSourceMap:
    def test_add_mapping(self):
        smap = SourceMap(file="output.py")
        smap.add_mapping(1, 0, 1, 0, "input.ltl")
        assert len(smap.mappings) == 1
        assert "input.ltl" in smap.sources

    def test_add_named_mapping(self):
        smap = SourceMap()
        smap.add_mapping(1, 0, 1, 0, "test.ltl", name="greet")
        assert "greet" in smap.names
        assert smap.mappings[0].name == "greet"

    def test_find_source(self):
        smap = SourceMap()
        smap.add_mapping(5, 0, 10, 0, "test.ltl")
        smap.add_mapping(6, 0, 11, 0, "test.ltl")

        result = smap.find_source(5)
        assert result is not None
        assert result.src_line == 10

    def test_find_source_miss(self):
        smap = SourceMap()
        smap.add_mapping(5, 0, 10, 0, "test.ltl")
        assert smap.find_source(99) is None

    def test_find_generated(self):
        smap = SourceMap()
        smap.add_mapping(1, 0, 5, 0, "test.ltl")
        smap.add_mapping(2, 0, 5, 4, "test.ltl")
        smap.add_mapping(3, 0, 6, 0, "test.ltl")

        results = smap.find_generated("test.ltl", 5)
        assert len(results) == 2

    def test_json_roundtrip(self):
        smap = SourceMap(file="out.py")
        smap.add_mapping(1, 0, 1, 0, "in.ltl", name="main")
        smap.add_mapping(5, 4, 3, 0, "in.ltl")

        json_str = smap.to_json()
        loaded = SourceMap.from_json(json_str)

        assert loaded.version == 3
        assert loaded.file == "out.py"
        assert len(loaded.mappings) == 2
        assert loaded.mappings[0].name == "main"
        assert loaded.mappings[1].src_line == 3

    def test_save_and_load(self, tmp_path):
        smap = SourceMap(file="test.py")
        smap.add_mapping(1, 0, 1, 0, "test.ltl")

        path = tmp_path / "test.map"
        smap.save(path)
        loaded = SourceMap.load(path)

        assert len(loaded.mappings) == 1
        assert loaded.file == "test.py"

    def test_multiple_sources(self):
        smap = SourceMap()
        smap.add_mapping(1, 0, 1, 0, "main.ltl")
        smap.add_mapping(2, 0, 5, 0, "utils.ltl")
        smap.add_mapping(3, 0, 10, 0, "main.ltl")

        assert len(smap.sources) == 2
        assert "main.ltl" in smap.sources
        assert "utils.ltl" in smap.sources


class TestSourceMapBuilder:
    def test_basic_builder(self):
        builder = SourceMapBuilder("output.py", "input.ltl")
        builder.set_position(1, 0)
        builder.map_line(1)
        builder.advance_line()
        builder.map_line(2)

        smap = builder.build()
        assert len(smap.mappings) == 2
        assert smap.file == "output.py"

    def test_builder_with_names(self):
        builder = SourceMapBuilder("out.py", "in.ltl")
        builder.set_position(1)
        builder.map_line(1, name="main")

        smap = builder.build()
        assert smap.mappings[0].name == "main"

    def test_builder_multiple_sources(self):
        builder = SourceMapBuilder("out.py", "main.ltl")
        builder.set_position(1)
        builder.map_line(1)
        builder.set_position(5)
        builder.map_line(10, source_file="utils.ltl")

        smap = builder.build()
        assert len(smap.sources) == 2


class TestErrorEnhancement:
    def test_basic_error(self):
        smap = SourceMap()
        smap.add_mapping(10, 0, 5, 0, "test.ltl")

        source = {
            "test.ltl": [
                "fn main() {",
                "    let x = 1",
                "    let y = 2",
                "    let z = x / 0",  # line 4 (src_line 5 is 1-indexed)
                "    println(z)",
                "}",
            ]
        }

        msg = enhance_error_with_source_map(10, smap, source)
        assert "test.ltl" in msg
        assert "line 5" in msg

    def test_error_no_mapping(self):
        smap = SourceMap()
        msg = enhance_error_with_source_map(99, smap, {})
        assert "no source map entry" in msg

    def test_error_with_name(self):
        smap = SourceMap()
        smap.add_mapping(10, 0, 5, 0, "test.ltl", name="divide")

        msg = enhance_error_with_source_map(10, smap, {})
        assert "divide" in msg
