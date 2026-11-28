"""Unsupported stdlib imports must fail before Python execution."""
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from lateralus_lang.__main__ import main
from lateralus_lang.compiler import Compiler, Target


class TestPythonStdlibImports(unittest.TestCase):
    def test_unsupported_import_forms_report_the_module(self):
        sources = [
            "import stdlib.regex as regex",
            "import stdlib.regex",
            "from stdlib.regex import find_first",
            "import stdlib.not_a_module as missing",
        ]
        for source in sources:
            with self.subTest(source=source):
                result = Compiler().compile_source(source, target=Target.PYTHON)
                self.assertFalse(result.ok)
                self.assertIsNone(result.python_src)
                expected_path = "stdlib.not_a_module" if "not_a_module" in source else "stdlib.regex"
                self.assertTrue(any(
                    "Python backend does not support stdlib import" in error.message
                    and expected_path in error.message
                    for error in result.errors
                ))

    def test_math_alias_still_executes(self):
        result = Compiler().compile_source(
            "import stdlib.math as math\nlet result = math.sqrt(81)",
            target=Target.PYTHON,
        )
        self.assertTrue(result.ok, result.errors)
        namespace = {}
        exec(result.python_src, namespace)
        self.assertEqual(namespace["result"], 9.0)

    def test_supported_preamble_modules_still_compile(self):
        for name in ["io", "math", "strings", "collections", "time", "random"]:
            with self.subTest(module=name):
                result = Compiler().compile_source(
                    f"import stdlib.{name} as supported", target=Target.PYTHON,
                )
                self.assertTrue(result.ok, result.errors)

    def test_regular_python_import_still_executes(self):
        result = Compiler().compile_source(
            "import fractions as fractions", target=Target.PYTHON,
        )
        self.assertTrue(result.ok, result.errors)
        namespace = {}
        exec(result.python_src, namespace)
        self.assertEqual(str(namespace["fractions"].Fraction(1, 2)), "1/2")

    def test_check_target_does_not_claim_backend_support(self):
        result = Compiler().compile_source(
            "import stdlib.regex as regex", target=Target.CHECK,
        )
        self.assertTrue(result.ok, result.errors)

    def test_cli_run_fails_before_executing_unsupported_import(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "repro.ltl"
            source.write_text("import stdlib.regex as regex", encoding="utf-8")
            error_output = StringIO()
            with redirect_stderr(error_output):
                self.assertEqual(main(["run", str(source)]), 1)
            self.assertIn("Python backend does not support stdlib import", error_output.getvalue())

    def test_cli_py_does_not_write_broken_output(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "repro.ltl"
            output = Path(directory) / "repro.py"
            source.write_text("import stdlib.regex as regex", encoding="utf-8")
            with redirect_stderr(StringIO()):
                self.assertEqual(main(["py", str(source), "-o", str(output)]), 1)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
