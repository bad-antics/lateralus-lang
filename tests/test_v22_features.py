"""
tests/test_v22_features.py  ─  v2.2 Feature Test Suite
═══════════════════════════════════════════════════════════════════════════
Tests for LATERALUS v2.2 features:
  · New linter rules: unreachable-code, duplicate-import, shadowed-variable, todo-comment
  · New stdlib modules: fmt, encoding, csv, logging, filepath
  · v22 showcase compilation
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.compiler import Compiler, Target
from lateralus_lang.linter import LateralusLinter, Severity

# ─── Helpers ─────────────────────────────────────────────────────────────────

ROOT = pathlib.Path(__file__).parent.parent


def compile_ok(src, target=Target.PYTHON, filename="<test>"):
    """Return True if source compiles without errors."""
    r = Compiler().compile_source(src, target=target, filename=filename)
    return r.ok


def compile_result(src, target=Target.PYTHON, filename="<test>"):
    return Compiler().compile_source(src, target=target, filename=filename)


def python_src(src, filename="<test>"):
    """Compile LTL source and return the Python transpilation."""
    r = Compiler().compile_source(src, target=Target.PYTHON, filename=filename)
    assert r.ok, f"Compile failed: {r.errors}"
    return r.python_src


def run_ltl(src):
    """Compile and execute LTL source, return captured stdout."""
    import io
    import contextlib
    py = python_src(src)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(py, {"__builtins__": __builtins__})
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════
# LINTER: Unreachable Code Detection
# ═══════════════════════════════════════════════════════════════════════

class TestUnreachableCode:
    def setup_method(self):
        self.linter = LateralusLinter()

    def test_code_after_return(self):
        """Code after return should be flagged."""
        src = "fn foo() {\n    return 42\n    let x = 5\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "unreachable-code"]
        assert len(issues) >= 1
        assert issues[0].line == 3

    def test_code_after_break(self):
        """Code after break should be flagged."""
        src = "fn main() {\n    for i in range(10) {\n        break\n        println(i)\n    }\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "unreachable-code"]
        assert len(issues) >= 1

    def test_code_after_continue(self):
        """Code after continue should be flagged."""
        src = "fn main() {\n    for i in range(10) {\n        continue\n        println(i)\n    }\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "unreachable-code"]
        assert len(issues) >= 1

    def test_no_false_positive_return_in_if(self):
        """Return inside if block should not flag else clause as unreachable."""
        src = "fn foo(x: int) {\n    if x > 0 {\n        return 1\n    }\n    return 0\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "unreachable-code"]
        assert len(issues) == 0

    def test_normal_code_no_flag(self):
        """Normal code without unreachable paths should be clean."""
        src = "fn add(a: int, b: int) -> int {\n    let result = a + b\n    return result\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "unreachable-code"]
        assert len(issues) == 0

    def test_severity_is_warning(self):
        """Unreachable code should be a WARNING."""
        src = "fn foo() {\n    return 42\n    println(1)\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "unreachable-code"]
        assert len(issues) >= 1
        assert issues[0].severity == Severity.WARNING


# ═══════════════════════════════════════════════════════════════════════
# LINTER: Duplicate Import Detection
# ═══════════════════════════════════════════════════════════════════════

class TestDuplicateImport:
    def setup_method(self):
        self.linter = LateralusLinter()

    def test_duplicate_import(self):
        """Importing the same module twice should be flagged."""
        src = "import math\nimport strings\nimport math"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "duplicate-import"]
        assert len(issues) == 1
        assert "math" in issues[0].message
        assert "line 1" in issues[0].message

    def test_no_duplicate(self):
        """Different imports should not be flagged."""
        src = "import math\nimport strings\nimport io"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "duplicate-import"]
        assert len(issues) == 0

    def test_multiple_duplicates(self):
        """Multiple duplicate imports should each be flagged."""
        src = "import math\nimport io\nimport math\nimport io"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "duplicate-import"]
        assert len(issues) == 2

    def test_severity_is_warning(self):
        """Duplicate import should be a WARNING."""
        src = "import math\nimport math"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "duplicate-import"]
        assert len(issues) >= 1
        assert issues[0].severity == Severity.WARNING

    def test_suggestion_provided(self):
        """Duplicate import should have a suggestion."""
        src = "import math\nimport math"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "duplicate-import"]
        assert issues[0].suggestion is not None
        assert "Remove" in issues[0].suggestion


# ═══════════════════════════════════════════════════════════════════════
# LINTER: Shadowed Variable Detection
# ═══════════════════════════════════════════════════════════════════════

class TestShadowedVariable:
    def setup_method(self):
        self.linter = LateralusLinter()

    def test_shadowed_variable(self):
        """Redefining a variable many lines later should be flagged."""
        src = "let x = 10\nfn a() {\n    println(1)\n    println(2)\n    let x = 20\n    println(x)\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "shadowed-variable"]
        assert len(issues) >= 1
        assert "x" in issues[0].message

    def test_underscore_ignored(self):
        """Variables named _ should never trigger shadow warning."""
        src = "let _ = 10\nfn a() {\n    println(1)\n    println(2)\n    let _ = 20\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "shadowed-variable"]
        assert len(issues) == 0

    def test_no_shadow_close_lines(self):
        """Redefinition within 3 lines is not flagged (likely reassignment)."""
        src = "let x = 10\nlet x = 20\nprintln(x)"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "shadowed-variable"]
        assert len(issues) == 0

    def test_severity_is_info(self):
        """Shadowed variable should be INFO severity."""
        src = "let x = 10\nfn a() {\n    println(1)\n    println(2)\n    let x = 20\n    println(x)\n}"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "shadowed-variable"]
        assert len(issues) >= 1
        assert issues[0].severity == Severity.INFO


# ═══════════════════════════════════════════════════════════════════════
# LINTER: TODO/FIXME Comment Detection
# ═══════════════════════════════════════════════════════════════════════

class TestTodoComment:
    def setup_method(self):
        self.linter = LateralusLinter()

    def test_todo_detected(self):
        """TODO comments should be flagged."""
        src = "// TODO: fix this later\nfn main() { println(42) }"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) == 1
        assert "TODO" in issues[0].message

    def test_fixme_detected(self):
        """FIXME comments should be flagged."""
        src = "// FIXME: broken function\nfn main() { println(42) }"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) == 1
        assert "FIXME" in issues[0].message

    def test_hack_detected(self):
        """HACK comments should be flagged."""
        src = "// HACK: workaround for now\nfn main() { println(42) }"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) == 1

    def test_xxx_detected(self):
        """XXX comments should be flagged."""
        src = "// XXX: needs review\nfn main() { println(42) }"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) == 1

    def test_inline_todo(self):
        """TODO in inline comment should be detected."""
        src = "let x = 42  // TODO: refactor"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) == 1

    def test_severity_is_hint(self):
        """TODO comments should be HINT severity."""
        src = "// TODO: fix\nfn main() { println(42) }"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) >= 1
        assert issues[0].severity == Severity.HINT

    def test_no_false_positive(self):
        """Normal comments without TODO/FIXME/HACK/XXX should not be flagged."""
        src = "// This is a normal comment\nfn main() { println(42) }"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) == 0

    def test_multiple_per_file(self):
        """Multiple TODO-style comments should each be flagged."""
        src = "// TODO: first\n// FIXME: second\n// HACK: third\nfn main() { println(42) }"
        result = self.linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "todo-comment"]
        assert len(issues) == 3


# ═══════════════════════════════════════════════════════════════════════
# STDLIB: Module Compilation Tests
# ═══════════════════════════════════════════════════════════════════════

class TestStdlibCompilation:
    """Verify that all new stdlib modules compile cleanly."""

    @pytest.mark.parametrize("module", [
        "fmt",
        "encoding",
        "csv",
        "logging",
        "filepath",
    ])
    def test_stdlib_module_compiles(self, module):
        """Each new stdlib module should compile without errors."""
        path = ROOT / "stdlib" / f"{module}.ltl"
        assert path.exists(), f"stdlib/{module}.ltl not found"
        src = path.read_text()
        r = Compiler().compile_source(src, target=Target.PYTHON, filename=f"{module}.ltl")
        assert r.ok, f"stdlib/{module}.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_fmt_has_format_function(self):
        """fmt.ltl should define a format() function."""
        path = ROOT / "stdlib" / "fmt.ltl"
        src = path.read_text()
        assert "fn format(" in src

    def test_encoding_has_hex_encode(self):
        """encoding.ltl should define hex_encode()."""
        path = ROOT / "stdlib" / "encoding.ltl"
        src = path.read_text()
        assert "fn hex_encode(" in src

    def test_csv_has_parse(self):
        """csv.ltl should define parse()."""
        path = ROOT / "stdlib" / "csv.ltl"
        src = path.read_text()
        assert "fn parse(" in src

    def test_logging_has_levels(self):
        """logging.ltl should define severity level constants."""
        path = ROOT / "stdlib" / "logging.ltl"
        src = path.read_text()
        for level in ["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"]:
            assert level in src, f"Missing log level: {level}"

    def test_filepath_has_dirname(self):
        """filepath.ltl should define dirname()."""
        path = ROOT / "stdlib" / "filepath.ltl"
        src = path.read_text()
        assert "fn dirname(" in src


# ═══════════════════════════════════════════════════════════════════════
# STDLIB: Functional Tests (via Python transpilation)
# ═══════════════════════════════════════════════════════════════════════

class TestStdlibFunctionality:
    """Test stdlib module behavior via compiled execution."""

    def test_import_fmt(self):
        """Importing fmt should compile."""
        assert compile_ok("import fmt")

    def test_import_encoding(self):
        """Importing encoding should compile."""
        assert compile_ok("import encoding")

    def test_import_csv(self):
        """Importing csv should compile."""
        assert compile_ok("import csv")

    def test_import_logging(self):
        """Importing logging should compile."""
        assert compile_ok("import logging")

    def test_import_filepath(self):
        """Importing filepath should compile."""
        assert compile_ok("import filepath")


# ═══════════════════════════════════════════════════════════════════════
# LINTER: Integration with existing rules
# ═══════════════════════════════════════════════════════════════════════

class TestLinterIntegration:
    """Ensure new rules integrate well with existing ones."""

    def test_combined_issues(self):
        """Multiple new rule violations in one file should all be detected."""
        src = (
            "import math\n"
            "// TODO: cleanup\n"
            "import math\n"
            "let x = 10\n"
            "fn foo() {\n"
            "    println(1)\n"
            "    println(2)\n"
            "    println(3)\n"
            "    let x = 20\n"
            "    return x\n"
            "    println(99)\n"
            "}\n"
        )
        linter = LateralusLinter()
        result = linter.lint(src, "test.ltl")
        rules_found = {i.rule for i in result.issues}
        assert "duplicate-import" in rules_found
        assert "todo-comment" in rules_found
        assert "shadowed-variable" in rules_found
        assert "unreachable-code" in rules_found

    def test_clean_file_no_new_issues(self):
        """A clean, well-written file should not trigger new rules."""
        src = (
            "import math\n"
            "import strings\n"
            "\n"
            "fn add(a: int, b: int) -> int {\n"
            "    return a + b\n"
            "}\n"
            "\n"
            "fn main() {\n"
            "    let result = add(1, 2)\n"
            "    println(result)\n"
            "}\n"
        )
        linter = LateralusLinter()
        result = linter.lint(src, "test.ltl")
        new_rules = {"unreachable-code", "duplicate-import", "shadowed-variable", "todo-comment"}
        new_issues = [i for i in result.issues if i.rule in new_rules]
        assert len(new_issues) == 0

    def test_linter_issue_string_format(self):
        """New rule issues should have proper string formatting."""
        src = "import math\nimport math"
        linter = LateralusLinter()
        result = linter.lint(src, "test.ltl")
        issues = [i for i in result.issues if i.rule == "duplicate-import"]
        assert len(issues) >= 1
        s = str(issues[0])
        assert "WARNING" in s
        assert "duplicate-import" in s

    def test_existing_rules_still_work(self):
        """Ensure existing rules still function after adding new ones."""
        linter = LateralusLinter()

        # unused variable
        r = linter.lint("let unused = 42\nprintln(1)")
        assert any(i.rule == "unused-variable" for i in r.issues)

        # semicolon
        linter2 = LateralusLinter()
        r2 = linter2.lint("let x = 42;")
        assert any(i.rule == "unnecessary-semicolon" for i in r2.issues)

        # var keyword
        linter3 = LateralusLinter()
        r3 = linter3.lint("var x = 42")
        assert any(i.rule == "use-let" for i in r3.issues)


# ═══════════════════════════════════════════════════════════════════════
# SHOWCASE: v22 showcase file compilation
# ═══════════════════════════════════════════════════════════════════════

class TestV22Showcase:
    def test_v22_showcase_exists_and_compiles(self):
        """v22 showcase should exist and compile."""
        path = ROOT / "examples" / "v22_showcase.ltl"
        if path.exists():
            src = path.read_text()
            r = Compiler().compile_source(src, target=Target.PYTHON, filename="v22_showcase.ltl")
            assert r.ok, f"v22_showcase.ltl failed: {[e.message for e in r.errors[:3]]}"
        else:
            pytest.skip("v22_showcase.ltl not yet created")


# ═══════════════════════════════════════════════════════════════════════
# STDLIB: New stdlib module compilation tests
# ═══════════════════════════════════════════════════════════════════════

class TestStdlibUUID:
    """Tests for stdlib/uuid.ltl."""

    def test_uuid_module_compiles(self):
        path = ROOT / "stdlib" / "uuid.ltl"
        assert path.exists(), "stdlib/uuid.ltl not found"
        src = path.read_text()
        r = Compiler().compile_source(src, target=Target.PYTHON, filename="uuid.ltl")
        assert r.ok, f"uuid.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_uuid_has_core_functions(self):
        src = (ROOT / "stdlib" / "uuid.ltl").read_text()
        assert "fn uuid4(" in src
        assert "fn nil_uuid(" in src
        assert "fn is_valid(" in src
        assert "fn version(" in src

    def test_uuid_constants(self):
        src = (ROOT / "stdlib" / "uuid.ltl").read_text()
        assert "NAMESPACE_DNS" in src
        assert "NAMESPACE_URL" in src


class TestStdlibHash:
    """Tests for stdlib/hash.ltl."""

    def test_hash_module_compiles(self):
        path = ROOT / "stdlib" / "hash.ltl"
        assert path.exists(), "stdlib/hash.ltl not found"
        src = path.read_text()
        r = Compiler().compile_source(src, target=Target.PYTHON, filename="hash.ltl")
        assert r.ok, f"hash.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_hash_has_core_functions(self):
        src = (ROOT / "stdlib" / "hash.ltl").read_text()
        assert "fn fnv1a_32(" in src
        assert "fn djb2(" in src
        assert "fn sdbm(" in src
        assert "fn adler32(" in src

    def test_hash_has_utility_functions(self):
        src = (ROOT / "stdlib" / "hash.ltl").read_text()
        assert "fn combine(" in src
        assert "fn bucket(" in src
        assert "fn hash_list(" in src


class TestStdlibColor:
    """Tests for stdlib/color.ltl."""

    def test_color_module_compiles(self):
        path = ROOT / "stdlib" / "color.ltl"
        assert path.exists(), "stdlib/color.ltl not found"
        src = path.read_text()
        r = Compiler().compile_source(src, target=Target.PYTHON, filename="color.ltl")
        assert r.ok, f"color.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_color_has_core_functions(self):
        src = (ROOT / "stdlib" / "color.ltl").read_text()
        assert "fn rgb(" in src
        assert "fn rgba(" in src
        assert "fn lighten(" in src
        assert "fn darken(" in src
        assert "fn mix(" in src

    def test_color_has_named_colors(self):
        src = (ROOT / "stdlib" / "color.ltl").read_text()
        assert "BLACK" in src
        assert "WHITE" in src
        assert "LTL_ACCENT" in src

    def test_color_has_manipulation(self):
        src = (ROOT / "stdlib" / "color.ltl").read_text()
        assert "fn invert(" in src
        assert "fn grayscale(" in src
        assert "fn to_hex(" in src


class TestStdlibQueue:
    """Tests for stdlib/queue.ltl."""

    def test_queue_module_compiles(self):
        path = ROOT / "stdlib" / "queue.ltl"
        assert path.exists(), "stdlib/queue.ltl not found"
        r = Compiler().compile_source(path.read_text(), target=Target.PYTHON, filename="queue.ltl")
        assert r.ok, f"queue.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_queue_has_core_ops(self):
        src = (ROOT / "stdlib" / "queue.ltl").read_text()
        assert "fn push_back(" in src
        assert "fn push_front(" in src
        assert "fn pop_front(" in src
        assert "fn pop_back(" in src
        assert "fn front(" in src
        assert "fn drain(" in src


class TestStdlibStack:
    """Tests for stdlib/stack.ltl."""

    def test_stack_module_compiles(self):
        path = ROOT / "stdlib" / "stack.ltl"
        assert path.exists(), "stdlib/stack.ltl not found"
        r = Compiler().compile_source(path.read_text(), target=Target.PYTHON, filename="stack.ltl")
        assert r.ok, f"stack.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_stack_has_core_ops(self):
        src = (ROOT / "stdlib" / "stack.ltl").read_text()
        assert "fn push(" in src
        assert "fn pop(" in src
        assert "fn peek(" in src
        assert "fn swap_top(" in src
        assert "fn dup(" in src
        assert "fn fold(" in src


class TestStdlibBase64:
    """Tests for stdlib/base64.ltl."""

    def test_base64_module_compiles(self):
        path = ROOT / "stdlib" / "base64.ltl"
        assert path.exists(), "stdlib/base64.ltl not found"
        r = Compiler().compile_source(path.read_text(), target=Target.PYTHON, filename="base64.ltl")
        assert r.ok, f"base64.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_base64_has_core_functions(self):
        src = (ROOT / "stdlib" / "base64.ltl").read_text()
        assert "fn encode(" in src
        assert "fn decode(" in src
        assert "fn encode_url(" in src
        assert "fn decode_url(" in src
        assert "fn is_valid(" in src


class TestStdlibBitset:
    """Tests for stdlib/bitset.ltl."""

    def test_bitset_module_compiles(self):
        path = ROOT / "stdlib" / "bitset.ltl"
        assert path.exists(), "stdlib/bitset.ltl not found"
        r = Compiler().compile_source(path.read_text(), target=Target.PYTHON, filename="bitset.ltl")
        assert r.ok, f"bitset.ltl failed: {[e.message for e in r.errors[:3]]}"

    def test_bitset_has_core_ops(self):
        src = (ROOT / "stdlib" / "bitset.ltl").read_text()
        assert "fn set(" in src
        assert "fn clear(" in src
        assert "fn test(" in src
        assert "fn toggle(" in src

    def test_bitset_has_set_operations(self):
        src = (ROOT / "stdlib" / "bitset.ltl").read_text()
        assert "fn union(" in src
        assert "fn intersection(" in src
        assert "fn difference(" in src
        assert "fn is_subset(" in src
