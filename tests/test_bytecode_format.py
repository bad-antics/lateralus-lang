"""
tests/test_bytecode_format.py — Tests for the LATERALUS .ltlc binary format
"""
import pytest
from lateralus_lang.bytecode_format import (
    LTLCCompiler, LTLCDecompiler, LTLCInspector,
    LTLCFile, LTLCMetadata, Symbol,
    LTLC_MAGIC, LTLC_VERSION,
)


SAMPLE_SOURCE = '''
fn greet(name: str) -> str {
    return "Hello, {name}!"
}

fn main() {
    let message = greet("World")
    println(message)
}

let PI = 3.14159
let greeting = "Welcome"
'''


class TestLTLCCompiler:
    def test_compile_produces_bytes(self):
        compiler = LTLCCompiler()
        result = compiler.compile_source(SAMPLE_SOURCE, "test.ltl")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_magic_bytes(self):
        compiler = LTLCCompiler()
        result = compiler.compile_source(SAMPLE_SOURCE)
        assert result[:4] == LTLC_MAGIC

    def test_version_encoded(self):
        compiler = LTLCCompiler()
        result = compiler.compile_source(SAMPLE_SOURCE)
        import struct
        version = struct.unpack(">H", result[4:6])[0]
        assert version == LTLC_VERSION

    def test_extract_symbols(self):
        compiler = LTLCCompiler()
        symbols = compiler._extract_symbols(SAMPLE_SOURCE)
        names = [s.name for s in symbols]
        assert "greet" in names
        assert "main" in names
        assert "PI" in names

    def test_extract_constants(self):
        compiler = LTLCCompiler()
        constants = compiler._extract_constants(SAMPLE_SOURCE)
        str_consts = [c for c in constants if isinstance(c, str)]
        num_consts = [c for c in constants if isinstance(c, (int, float))]
        assert any("Hello" in s for s in str_consts)
        assert any(abs(n - 3.14159) < 0.001 for n in num_consts)

    def test_compressed(self):
        compiler_c = LTLCCompiler(compress=True)
        compiler_u = LTLCCompiler(compress=False)
        compressed = compiler_c.compile_source(SAMPLE_SOURCE)
        uncompressed = compiler_u.compile_source(SAMPLE_SOURCE)
        # Compressed should generally be smaller for non-trivial input
        assert isinstance(compressed, bytes)
        assert isinstance(uncompressed, bytes)

    def test_with_debug(self):
        compiler = LTLCCompiler(include_debug=True)
        data = compiler.compile_source(SAMPLE_SOURCE, "test.ltl")
        decompiler = LTLCDecompiler()
        ltlc = decompiler.decompile(data)
        assert len(ltlc.debug_lines) > 0

    def test_without_debug(self):
        compiler = LTLCCompiler(include_debug=False)
        data = compiler.compile_source(SAMPLE_SOURCE, "test.ltl")
        decompiler = LTLCDecompiler()
        ltlc = decompiler.decompile(data)
        assert len(ltlc.debug_lines) == 0


class TestLTLCDecompiler:
    def test_roundtrip(self):
        compiler = LTLCCompiler(compress=True)
        data = compiler.compile_source(SAMPLE_SOURCE, "test.ltl")

        decompiler = LTLCDecompiler()
        ltlc = decompiler.decompile(data)

        assert ltlc.metadata.source_file == "test.ltl"
        assert ltlc.metadata.language_version == "1.5.0"
        assert len(ltlc.symbols) > 0
        assert len(ltlc.constants) > 0
        assert ltlc.source_hash

    def test_decompile_to_source(self):
        compiler = LTLCCompiler()
        data = compiler.compile_source(SAMPLE_SOURCE, "demo.ltl")

        decompiler = LTLCDecompiler()
        source = decompiler.decompile_to_source(data)

        assert "Decompiled from: demo.ltl" in source
        assert "fn greet" in source
        assert "fn main" in source

    def test_invalid_magic(self):
        with pytest.raises(ValueError, match="Not a valid"):
            LTLCDecompiler().decompile(b"INVALID_DATA_HERE")

    def test_metadata_flags(self):
        compiler = LTLCCompiler(compress=True, include_debug=True)
        data = compiler.compile_source(SAMPLE_SOURCE)
        ltlc = LTLCDecompiler().decompile(data)
        assert ltlc.metadata.is_compressed
        assert ltlc.metadata.has_debug

    def test_source_hash_integrity(self):
        import hashlib
        compiler = LTLCCompiler()
        data = compiler.compile_source(SAMPLE_SOURCE)
        ltlc = LTLCDecompiler().decompile(data)
        expected_hash = hashlib.sha256(SAMPLE_SOURCE.encode()).hexdigest()
        assert ltlc.source_hash == expected_hash


class TestLTLCInspector:
    def test_inspect(self):
        compiler = LTLCCompiler()
        data = compiler.compile_source(SAMPLE_SOURCE, "inspect_test.ltl")

        inspector = LTLCInspector()
        report = inspector.inspect(data)

        assert report["format"] == "LATERALUS Compiled Binary"
        assert report["source_file"] == "inspect_test.ltl"
        assert report["symbols_count"] > 0
        assert report["constants_count"] > 0
        assert isinstance(report["symbols"], list)

    def test_inspect_symbols(self):
        compiler = LTLCCompiler()
        data = compiler.compile_source(SAMPLE_SOURCE)
        report = LTLCInspector().inspect(data)

        sym_names = [s["name"] for s in report["symbols"]]
        assert "greet" in sym_names
        assert "main" in sym_names


class TestSignedCompilation:
    def test_signed_roundtrip(self):
        key = "test-signing-key"
        compiler = LTLCCompiler(signing_key=key)
        data = compiler.compile_source(SAMPLE_SOURCE, "signed.ltl")

        decompiler = LTLCDecompiler(signing_key=key)
        ltlc = decompiler.decompile(data)

        assert ltlc.metadata.is_signed
        assert ltlc.signature
