"""
Tests for the LATERALUS formatter and linter.
"""
import pytest
from lateralus_lang.formatter import LateralusFormatter, FormatConfig
from lateralus_lang.linter import LateralusLinter, Severity


class TestFormatter:
    def setup_method(self):
        self.fmt = LateralusFormatter()

    def test_trailing_whitespace(self):
        result = self.fmt.format("let x = 42   \n")
        assert not any(line.endswith(" ") for line in result.split("\n") if line)

    def test_tab_to_spaces(self):
        result = self.fmt.format("\tfn hello() {\n\t\tprintln(42)\n\t}\n")
        assert "\t" not in result
        assert "    " in result

    def test_trailing_newline(self):
        result = self.fmt.format("let x = 42")
        assert result.endswith("\n")

    def test_no_trailing_newline(self):
        fmt = LateralusFormatter(FormatConfig(trailing_newline=False))
        result = fmt.format("let x = 42\n\n\n")
        assert not result.endswith("\n\n")

    def test_import_sorting(self):
        source = 'import "zebra"\nimport "alpha"\nimport "middle"\n'
        result = self.fmt.format(source)
        lines = [l for l in result.strip().split("\n") if l.startswith("import")]
        assert lines[0] == 'import "alpha"'
        assert lines[-1] == 'import "zebra"'

    def test_empty_source(self):
        result = self.fmt.format("")
        assert result == "\n"

    def test_comment_preserved(self):
        result = self.fmt.format("// This is a comment\nlet x = 42\n")
        assert "// This is a comment" in result

    def test_custom_indent(self):
        fmt = LateralusFormatter(FormatConfig(indent_size=2))
        result = fmt.format("fn hello() {\nprintln(42)\n}\n")
        # Should use 2-space indent
        lines = result.split("\n")
        # Find the println line
        for line in lines:
            if "println" in line:
                assert line.startswith("  ")
                assert not line.startswith("    ")

    def test_enum_block_spacing(self):
        """v1.5: Formatter should insert blank lines around enum blocks."""
        source = "let x = 1\nenum Color {\n    Red,\n}\nlet y = 2\n"
        result = self.fmt.format(source)
        lines = result.strip().split("\n")
        # There should be a blank line before 'enum'
        for i, line in enumerate(lines):
            if line.strip().startswith("enum"):
                if i > 0 and lines[i - 1].strip() != "":
                    assert lines[i - 1].strip() == "", "Expected blank line before enum"

    def test_struct_block_spacing(self):
        """v1.5: Formatter should insert blank lines around struct blocks."""
        source = "let x = 1\nstruct Point {\n    x: float\n}\nlet y = 2\n"
        result = self.fmt.format(source)
        lines = result.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("struct"):
                if i > 0 and lines[i - 1].strip() != "":
                    assert lines[i - 1].strip() == "", "Expected blank line before struct"

    def test_impl_block_spacing(self):
        """v1.5: Formatter should insert blank lines around impl blocks."""
        source = "let x = 1\nimpl Point {\n    fn distance(self) { }\n}\nlet y = 2\n"
        result = self.fmt.format(source)
        lines = result.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("impl"):
                if i > 0 and lines[i - 1].strip() != "":
                    assert lines[i - 1].strip() == "", "Expected blank line before impl"

    def test_trait_block_spacing(self):
        """v1.5: Formatter should insert blank lines around trait blocks."""
        source = "let x = 1\ntrait Printable {\n    fn to_str(self) -> str\n}\nlet y = 2\n"
        result = self.fmt.format(source)
        lines = result.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("trait"):
                if i > 0 and lines[i - 1].strip() != "":
                    assert lines[i - 1].strip() == "", "Expected blank line before trait"

    def test_pub_fn_spacing(self):
        """v1.5: pub fn should get blank line separation."""
        source = "let x = 1\npub fn greet() {\n    println(42)\n}\nlet y = 2\n"
        result = self.fmt.format(source)
        lines = result.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("pub fn"):
                if i > 0 and lines[i - 1].strip() != "":
                    assert lines[i - 1].strip() == "", "Expected blank line before pub fn"


class TestLinter:
    def setup_method(self):
        self.linter = LateralusLinter()

    def test_unused_variable(self):
        result = self.linter.lint("let unused = 42\nprintln(1)")
        unused_issues = [i for i in result.issues if i.rule == "unused-variable"]
        assert len(unused_issues) >= 1
        assert "unused" in unused_issues[0].message

    def test_underscore_prefix_ignored(self):
        result = self.linter.lint("let _unused = 42")
        unused_issues = [i for i in result.issues if i.rule == "unused-variable"]
        assert len(unused_issues) == 0

    def test_var_keyword_error(self):
        result = self.linter.lint("var x = 42")
        var_issues = [i for i in result.issues if i.rule == "use-let"]
        assert len(var_issues) == 1
        assert var_issues[0].severity == Severity.ERROR

    def test_semicolon_warning(self):
        result = self.linter.lint("let x = 42;")
        semi_issues = [i for i in result.issues if i.rule == "unnecessary-semicolon"]
        assert len(semi_issues) >= 1

    def test_none_comparison(self):
        result = self.linter.lint("if x == none { pass }")
        none_issues = [i for i in result.issues if i.rule == "none-comparison"]
        assert len(none_issues) >= 1

    def test_empty_block(self):
        result = self.linter.lint("if true {}")
        empty_issues = [i for i in result.issues if i.rule == "empty-block"]
        assert len(empty_issues) >= 1

    def test_naming_function_snake_case(self):
        result = self.linter.lint("fn myFunction() { pass }")
        naming_issues = [i for i in result.issues if i.rule == "naming-convention"
                         and "snake_case" in i.message]
        assert len(naming_issues) >= 1

    def test_naming_struct_pascal_case(self):
        result = self.linter.lint("struct myStruct { x: int }")
        naming_issues = [i for i in result.issues if i.rule == "naming-convention"
                         and "PascalCase" in i.message]
        assert len(naming_issues) >= 1

    def test_naming_const_upper(self):
        result = self.linter.lint("const myConst = 42")
        naming_issues = [i for i in result.issues if i.rule == "naming-convention"
                         and "UPPER_CASE" in i.message]
        assert len(naming_issues) >= 1

    def test_clean_code(self):
        source = """let x = 42
let y = x + 1
println(y)
"""
        result = self.linter.lint(source)
        assert not result.has_errors

    def test_strict_missing_types(self):
        linter = LateralusLinter(strict=True)
        result = linter.lint("fn add(a, b) { return a + b }")
        type_issues = [i for i in result.issues if i.rule == "missing-type-annotation"]
        assert len(type_issues) >= 1

    def test_issue_to_string(self):
        result = self.linter.lint("var x = 42")
        assert result.issues
        s = str(result.issues[0])
        assert "ERROR" in s or "error" in s.lower()

    def test_comment_not_linted(self):
        result = self.linter.lint("// var x = 42;\nlet y = 1\nprintln(y)")
        var_issues = [i for i in result.issues if i.rule == "use-let"]
        assert len(var_issues) == 0

    def test_used_variable_no_warning(self):
        source = "let x = 42\nprintln(x)"
        result = self.linter.lint(source)
        unused_issues = [i for i in result.issues if i.rule == "unused-variable"]
        assert len(unused_issues) == 0

    def test_test_function_not_unused(self):
        source = "fn test_something() { assert_eq(1, 1) }"
        result = self.linter.lint(source)
        unused_fn = [i for i in result.issues if i.rule == "unused-function"
                     and "test_something" in i.message]
        assert len(unused_fn) == 0
