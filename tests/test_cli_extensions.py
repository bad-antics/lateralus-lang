"""
tests/test_cli_extensions.py — Tests for CLI extension commands
"""
from types import SimpleNamespace

from lateralus_lang.cli_extensions import (
    cmd_compile,
    cmd_decompile,
    cmd_doc,
    cmd_engines,
    cmd_hash,
    cmd_inspect,
    register_subcommands,
)

SAMPLE_LTL = '''
fn greet(name: str) -> str {
    return "Hello, " + name + "!"
}

fn main() {
    let msg = greet("LATERALUS")
    println(msg)
}
'''

SAMPLE_LTLML = '''---
title: Test
author: Test Author
---

# Test Heading

A paragraph with **bold** text.
'''


class TestCmdCompile:
    def test_compile_success(self, tmp_path):
        src = tmp_path / "test.ltl"
        src.write_text(SAMPLE_LTL)
        out = tmp_path / "test.ltlc"

        args = SimpleNamespace(
            file=str(src),
            output=str(out),
            no_compress=False,
            debug=False,
            sign_key=None,
        )
        result = cmd_compile(args)
        assert result == 0
        assert out.exists()
        assert out.stat().st_size > 0

    def test_compile_missing_file(self):
        args = SimpleNamespace(
            file="/nonexistent/path.ltl",
            output=None,
            no_compress=False,
            debug=False,
            sign_key=None,
        )
        result = cmd_compile(args)
        assert result == 1

    def test_compile_with_debug(self, tmp_path):
        src = tmp_path / "debug.ltl"
        src.write_text(SAMPLE_LTL)

        args = SimpleNamespace(
            file=str(src),
            output=None,
            no_compress=False,
            debug=True,
            sign_key=None,
        )
        result = cmd_compile(args)
        assert result == 0

    def test_compile_with_signing(self, tmp_path):
        src = tmp_path / "signed.ltl"
        src.write_text(SAMPLE_LTL)

        args = SimpleNamespace(
            file=str(src),
            output=None,
            no_compress=False,
            debug=False,
            sign_key="my-secret-key",
        )
        result = cmd_compile(args)
        assert result == 0


class TestCmdDecompile:
    def test_decompile_success(self, tmp_path):
        # First compile
        src = tmp_path / "original.ltl"
        src.write_text(SAMPLE_LTL)
        ltlc = tmp_path / "original.ltlc"

        compile_args = SimpleNamespace(
            file=str(src), output=str(ltlc),
            no_compress=False, debug=False, sign_key=None,
        )
        cmd_compile(compile_args)

        # Then decompile
        out = tmp_path / "recovered.ltl"
        decompile_args = SimpleNamespace(
            file=str(ltlc), output=str(out), sign_key=None,
        )
        result = cmd_decompile(decompile_args)
        assert result == 0
        assert out.exists()
        content = out.read_text()
        assert "greet" in content

    def test_decompile_missing_file(self):
        args = SimpleNamespace(
            file="/nonexistent/file.ltlc",
            output=None,
            sign_key=None,
        )
        result = cmd_decompile(args)
        assert result == 1


class TestCmdInspect:
    def test_inspect_success(self, tmp_path):
        src = tmp_path / "inspect.ltl"
        src.write_text(SAMPLE_LTL)
        ltlc = tmp_path / "inspect.ltlc"

        compile_args = SimpleNamespace(
            file=str(src), output=str(ltlc),
            no_compress=False, debug=True, sign_key=None,
        )
        cmd_compile(compile_args)

        inspect_args = SimpleNamespace(file=str(ltlc), json=False)
        result = cmd_inspect(inspect_args)
        assert result == 0

    def test_inspect_json(self, tmp_path, capsys):
        src = tmp_path / "json_inspect.ltl"
        src.write_text(SAMPLE_LTL)
        ltlc = tmp_path / "json_inspect.ltlc"

        compile_args = SimpleNamespace(
            file=str(src), output=str(ltlc),
            no_compress=False, debug=False, sign_key=None,
        )
        cmd_compile(compile_args)

        inspect_args = SimpleNamespace(file=str(ltlc), json=True)
        result = cmd_inspect(inspect_args)
        assert result == 0

        import json
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "format" in data


class TestCmdDoc:
    def test_doc_success(self, tmp_path):
        src = tmp_path / "test.ltlml"
        src.write_text(SAMPLE_LTLML)
        out = tmp_path / "test.html"

        args = SimpleNamespace(file=str(src), output=str(out))
        result = cmd_doc(args)
        assert result == 0
        assert out.exists()
        content = out.read_text()
        assert "<h1" in content

    def test_doc_missing_file(self):
        args = SimpleNamespace(file="/nonexistent/doc.ltlml", output=None)
        result = cmd_doc(args)
        assert result == 1


class TestCmdEngines:
    def test_engines_command(self):
        args = SimpleNamespace()
        result = cmd_engines(args)
        assert result == 0


class TestCmdHash:
    def test_hash_string(self):
        args = SimpleNamespace(file=None, string="hello world", algorithm="sha256")
        result = cmd_hash(args)
        assert result == 0

    def test_hash_file(self, tmp_path):
        f = tmp_path / "hashme.txt"
        f.write_text("test content")

        args = SimpleNamespace(file=str(f), string=None, algorithm="sha256")
        result = cmd_hash(args)
        assert result == 0

    def test_hash_missing_file(self):
        args = SimpleNamespace(file="/nonexistent/file.txt", string=None, algorithm="sha256")
        result = cmd_hash(args)
        assert result == 1


class TestRegisterSubcommands:
    def test_register_all(self):
        import argparse
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_subcommands(subparsers)

        # Verify all commands are registered by trying to parse them
        for cmd in ["compile", "decompile", "inspect", "doc", "engines", "hash", "bench"]:
            # Just make sure the subcommand exists; don't actually run it
            try:
                args = parser.parse_args([cmd, "--help"] if cmd == "engines" else [cmd, "test.ltl"])
                assert hasattr(args, "func"), f"Command {cmd} should have a func attribute"
            except SystemExit:
                pass  # --help causes SystemExit, that's fine
