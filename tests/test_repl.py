"""
tests/test_repl.py — Tests for LATERALUS REPL (basic + enhanced)
====================================================================
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from io import StringIO

from lateralus_lang.repl import REPL, start_repl
from lateralus_lang.repl_enhanced import (
    REPLSession, start_repl as start_repl_enhanced,
    highlight_line, KEYWORDS, BUILTINS, SPECIAL_COMMANDS, _BUILTIN_DOCS,
)


# -----------------------------------------------------------------------------
# Basic REPL tests
# -----------------------------------------------------------------------------

class TestBasicREPL:
    def test_repl_construction(self):
        repl = REPL()
        assert repl._mode == "ltl"
        assert repl._session_errors == []
        assert repl._history == []
        assert repl._last_source == ""

    def test_repl_mode_switch(self):
        repl = REPL()
        assert repl._mode == "ltl"
        # Simulate :mode asm
        repl._handle_command(":mode asm")
        assert repl._mode == "asm"
        # And back
        repl._handle_command(":mode ltl")
        assert repl._mode == "ltl"

    def test_repl_mode_invalid(self):
        repl = REPL()
        repl._handle_command(":mode invalid")
        assert repl._mode == "ltl"

    def test_repl_target_switch(self, capsys):
        repl = REPL()
        repl._handle_command(":target py")
        from lateralus_lang.compiler import Target
        assert repl._target == Target.PYTHON

        repl._handle_command(":target vm")
        assert repl._target == Target.BYTECODE

        repl._handle_command(":target check")
        assert repl._target == Target.CHECK

    def test_repl_reset(self):
        repl = REPL()
        repl._session_errors.append("test error")
        repl._handle_command(":reset")
        assert repl._session_errors == []

    def test_repl_errors_empty(self, capsys):
        repl = REPL()
        repl._handle_command(":errors")
        out = capsys.readouterr().out
        assert "No errors" in out or "no error" in out.lower()

    def test_repl_ver(self, capsys):
        repl = REPL()
        repl._handle_command(":ver")
        out = capsys.readouterr().out
        assert "LATERALUS" in out

    def test_repl_unknown_command(self, capsys):
        repl = REPL()
        repl._handle_command(":nonexistent")
        out = capsys.readouterr().out
        assert "Unknown" in out or "unknown" in out.lower()

    def test_repl_help(self, capsys):
        repl = REPL()
        repl._handle_command(":help")
        out = capsys.readouterr().out
        assert ":quit" in out
        assert ":mode" in out
        assert ":target" in out

    def test_repl_load_missing(self, capsys):
        repl = REPL()
        repl._handle_command(":load /nonexistent/path.ltl")
        out = capsys.readouterr().out
        assert "not found" in out.lower() or "Not found" in out

    def test_repl_dump_ast(self, capsys):
        repl = REPL()
        repl._last_source = "let x = 42"
        repl._dump_ast("let x = 42")
        out = capsys.readouterr().out
        # Should produce some AST output
        assert len(out) > 0

    def test_repl_dump_ir(self, capsys):
        repl = REPL()
        repl._dump_ir("fn main() { let x = 1 }")
        out = capsys.readouterr().out
        assert len(out) > 0


# -----------------------------------------------------------------------------
# Enhanced REPL — REPLSession tests
# -----------------------------------------------------------------------------

class TestEnhancedREPLSession:
    def test_construction(self):
        session = REPLSession(color=False, timing=False)
        assert session.color is False
        assert session.timing is False
        assert session.history == []
        assert session.env == {}
        assert session.last_result is None
        assert session._counter == 0
        assert session._profile_next is False

    def test_banner_contains_version(self):
        session = REPLSession(color=False)
        banner = session.banner()
        # Banner uses interpunct dots: L·A·T·E·R·A·L·U·S
        assert "L\xb7A\xb7T\xb7E\xb7R" in banner
        assert "INTERACTIVE" in banner

    def test_prompt_increments_counter(self):
        session = REPLSession(color=False)
        p1 = session.prompt()
        p2 = session.prompt()
        assert "1" in p1
        assert "2" in p2
        assert session._counter == 2

    def test_continuation_prompt(self):
        session = REPLSession(color=False)
        cp = session.continuation_prompt()
        assert "..." in cp

    def test_needs_continuation(self):
        session = REPLSession(color=False)
        assert session.needs_continuation("fn foo() {") is True
        assert session.needs_continuation("fn foo() { }") is False
        assert session.needs_continuation("fn foo() { return [") is True
        assert session.needs_continuation("let x = (1 +") is True
        assert session.needs_continuation("let x = 42") is False


# -----------------------------------------------------------------------------
# Enhanced REPL — Special commands
# -----------------------------------------------------------------------------

class TestEnhancedCommands:
    def test_help(self):
        session = REPLSession(color=False)
        result = session.handle_special(":help")
        assert "REPL Commands" in result
        assert ":save" in result
        assert ":doc" in result

    def test_clear(self, capsys):
        session = REPLSession(color=False)
        result = session.handle_special(":clear")
        assert result == ""

    def test_reset(self):
        session = REPLSession(color=False)
        session.env["x"] = 42
        session.history.append("let x = 42")
        result = session.handle_special(":reset")
        assert "reset" in result.lower()
        assert session.env == {}
        assert session.history == []

    def test_time_toggle(self):
        session = REPLSession(color=False, timing=False)
        result = session.handle_special(":time")
        assert session.timing is True
        assert "on" in result.lower()

        result = session.handle_special(":time")
        assert session.timing is False
        assert "off" in result.lower()

    def test_env_empty(self):
        session = REPLSession(color=False)
        result = session.handle_special(":env")
        assert "no variables" in result.lower()

    def test_env_with_values(self):
        session = REPLSession(color=False)
        session.env["x"] = 42
        session.env["name"] = "test"
        result = session.handle_special(":env")
        assert "x" in result
        assert "42" in result
        assert "name" in result
        assert "test" in result

    def test_version(self):
        session = REPLSession(color=False)
        result = session.handle_special(":version")
        assert "LATERALUS" in result

    def test_history_empty(self):
        session = REPLSession(color=False)
        result = session.handle_special(":history")
        assert "no history" in result.lower()

    def test_history_with_entries(self):
        session = REPLSession(color=False)
        session.history = ["let x = 1", "println(x)"]
        result = session.handle_special(":history")
        assert "let x = 1" in result
        assert "println(x)" in result

    def test_type_with_variable(self):
        session = REPLSession(color=False)
        session.env["count"] = 42
        result = session.handle_special(":type count")
        assert "int" in result

    def test_type_unknown(self):
        session = REPLSession(color=False)
        result = session.handle_special(":type unknown_var")
        assert "Unknown" in result or "unknown" in result.lower()

    def test_type_no_arg(self):
        session = REPLSession(color=False)
        result = session.handle_special(":type")
        # With no last result
        assert "none" in result.lower()

    def test_unknown_command(self):
        session = REPLSession(color=False)
        result = session.handle_special(":foobar")
        assert "Unknown" in result or "unknown" in result.lower()


# -----------------------------------------------------------------------------
# Enhanced REPL — New v2.4 commands
# -----------------------------------------------------------------------------

class TestV24Commands:
    def test_save_no_args(self):
        session = REPLSession(color=False)
        result = session.handle_special(":save")
        assert "Usage" in result

    def test_save_no_history(self):
        session = REPLSession(color=False)
        result = session.handle_special(":save /tmp/test.ltl")
        assert "no history" in result.lower()

    def test_save_writes_file(self, tmp_path):
        session = REPLSession(color=False)
        session.history = ["let x = 42", ":help", "println(x)"]
        out_path = str(tmp_path / "session.ltl")
        result = session.handle_special(f":save {out_path}")
        assert "Saved" in result
        assert "2 expressions" in result  # :help is filtered out

        content = open(out_path).read()
        assert "let x = 42" in content
        assert "println(x)" in content
        assert ":help" not in content

    def test_doc_no_args(self):
        session = REPLSession(color=False)
        result = session.handle_special(":doc")
        assert "Usage" in result

    def test_doc_known_builtin(self):
        session = REPLSession(color=False)
        result = session._lookup_doc("map")
        assert "map" in result
        assert "fn" in result.lower()

    def test_doc_unknown(self):
        session = REPLSession(color=False)
        result = session._lookup_doc("nonexistent_function")
        assert "No doc" in result or "not found" in result.lower()

    def test_doc_fuzzy_match(self):
        session = REPLSession(color=False)
        result = session._lookup_doc("prin")
        assert "Did you mean" in result or "No doc" in result

    def test_profile_sets_flag(self):
        session = REPLSession(color=False)
        assert session._profile_next is False
        result = session.handle_special(":profile")
        assert session._profile_next is True
        assert "enabled" in result.lower()

    def test_profile_execution(self, capsys):
        session = REPLSession(color=False)
        session._run_profiled("let x = 42")
        out = capsys.readouterr().out
        assert "Lex" in out
        assert "Parse" in out
        assert "Compile" in out
        assert "ms" in out


# -----------------------------------------------------------------------------
# Enhanced REPL — Syntax highlighting
# -----------------------------------------------------------------------------

class TestSyntaxHighlighting:
    def test_highlight_keyword(self):
        result = highlight_line("fn main() {")
        assert "fn" in result
        assert "main" in result

    def test_highlight_string(self):
        result = highlight_line('"hello world"')
        assert "hello world" in result

    def test_highlight_number(self):
        result = highlight_line("let x = 42")
        assert "42" in result

    def test_highlight_comment(self):
        result = highlight_line("// this is a comment")
        assert "comment" in result

    def test_highlight_pipeline(self):
        result = highlight_line("data |> map(fn)")
        assert "|>" in result

    def test_highlight_empty(self):
        result = highlight_line("")
        assert result == ""


# -----------------------------------------------------------------------------
# Enhanced REPL — Completions
# -----------------------------------------------------------------------------

class TestCompletions:
    def test_completions_keyword(self):
        session = REPLSession(color=False)
        comps = session.get_completions("fn")
        assert "fn" in comps or "filter" in comps

    def test_completions_builtin(self):
        session = REPLSession(color=False)
        comps = session.get_completions("print")
        assert "println" in comps
        assert "print" in comps

    def test_completions_command(self):
        session = REPLSession(color=False)
        comps = session.get_completions(":h")
        assert ":help" in comps or ":history" in comps

    def test_completions_empty(self):
        session = REPLSession(color=False)
        comps = session.get_completions("")
        assert comps == []

    def test_completions_env_variable(self):
        session = REPLSession(color=False)
        session.env["my_variable"] = 42
        comps = session.get_completions("my_")
        assert "my_variable" in comps


# -----------------------------------------------------------------------------
# Enhanced REPL — Format results
# -----------------------------------------------------------------------------

class TestFormatResult:
    def test_format_none(self):
        session = REPLSession(color=False)
        assert session.format_result(None) == ""

    def test_format_int(self):
        session = REPLSession(color=False)
        result = session.format_result(42)
        assert "42" in result

    def test_format_string(self):
        session = REPLSession(color=False)
        result = session.format_result("hello")
        assert "hello" in result

    def test_format_bool(self):
        session = REPLSession(color=False)
        result = session.format_result(True)
        assert "True" in result

    def test_format_list(self):
        session = REPLSession(color=False)
        result = session.format_result([1, 2, 3])
        assert "[1, 2, 3]" in result

    def test_format_dict(self):
        session = REPLSession(color=False)
        result = session.format_result({"a": 1})
        assert "a" in result
        assert "1" in result

    def test_format_sets_last_result(self):
        session = REPLSession(color=False)
        session.format_result(99)
        assert session.last_result == 99


# -----------------------------------------------------------------------------
# Builtin docs
# -----------------------------------------------------------------------------

class TestBuiltinDocs:
    def test_all_builtins_documented(self):
        """Verify that common builtins have doc entries."""
        for name in ["println", "map", "filter", "reduce", "len", "str",
                      "int", "float", "sum", "sorted", "reversed",
                      "sha256", "join", "split", "sqrt", "abs"]:
            assert name in _BUILTIN_DOCS, f"Missing doc for {name}"

    def test_doc_format(self):
        """All doc entries should have the function name and parentheses."""
        for name, doc in _BUILTIN_DOCS.items():
            assert name in doc, f"Doc for {name} doesn't mention its own name"
            assert "(" in doc, f"Doc for {name} missing parentheses"


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

class TestConstants:
    def test_keywords_set(self):
        assert "fn" in KEYWORDS
        assert "let" in KEYWORDS
        assert "match" in KEYWORDS
        assert "struct" in KEYWORDS
        assert "return" in KEYWORDS

    def test_builtins_set(self):
        assert "println" in BUILTINS
        assert "map" in BUILTINS
        assert "filter" in BUILTINS
        assert "sha256" in BUILTINS

    def test_special_commands_set(self):
        assert ":help" in SPECIAL_COMMANDS
        assert ":quit" in SPECIAL_COMMANDS
        assert ":save" in SPECIAL_COMMANDS
        assert ":doc" in SPECIAL_COMMANDS
        assert ":profile" in SPECIAL_COMMANDS
