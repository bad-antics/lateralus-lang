"""Verify the tutorial against compiled stdlib code and an independent small oracle."""

import itertools
from pathlib import Path
import subprocess
import sys
import unittest

from lateralus_lang import Compiler, Target

ROOT = Path(__file__).resolve().parents[1]


def reference_lcp(text: str, suffixes: list[int]) -> list[int]:
    """Compute adjacent common prefixes directly, without Kasai's algorithm."""
    result = [0] * len(suffixes)
    for index in range(1, len(suffixes)):
        left, right = text[suffixes[index - 1]:], text[suffixes[index]:]
        for a, b in zip(left, right):
            if a != b:
                break
            result[index] += 1
    return result


class TestSuffixArrayTutorial(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """Transpile the unchanged module and the example's actual helper once."""
        module = (ROOT / "stdlib/suffix_array.ltl").read_text(encoding="utf-8")
        example = (ROOT / "examples/suffix_array_demo.ltl").read_text(encoding="utf-8")
        helper = example.split("fn main()", 1)[0]
        compiled = Compiler().compile_source(module + "\n" + helper, target=Target.PYTHON)
        if not compiled.ok:
            raise AssertionError([str(error) for error in compiled.errors])
        cls.functions = {"__name__": "suffix_array_tutorial_test"}
        exec(compile(compiled.python_src, "<stdlib-suffix-array>", "exec"), cls.functions)

    def test_pinned_banana_vector(self) -> None:
        """Check every element of the worked example, not only its length."""
        self.assertEqual(self.functions["build"]("banana"), [5, 3, 1, 0, 4, 2])
        self.assertEqual(
            self.functions["lcp"]("banana", [5, 3, 1, 0, 4, 2]), [0, 1, 3, 0, 0, 2]
        )
        self.assertEqual(self.functions["longest_repeated"]("banana"), "ana")

    def test_small_strings_against_independent_oracle(self) -> None:
        """Cover every binary string through length six and selected other inputs."""
        texts = ["mississippi", "abcde", "aaaaa", "z", "a a a", "\u732b\u72ac\u732b"]
        for size in range(7):
            texts.extend("".join(chars) for chars in itertools.product("ab", repeat=size))
        for text in texts:
            with self.subTest(text=text):
                expected = sorted(range(len(text)), key=lambda index: text[index:])
                actual = self.functions["build"](text)
                self.assertEqual(actual, expected)
                common = reference_lcp(text, expected)
                self.assertEqual(self.functions["lcp"](text, actual), common)
                repeated = self.functions["longest_repeated"](text)
                self.assertEqual(len(repeated), max(common, default=0))
                if repeated:
                    starts = range(len(text) - len(repeated) + 1)
                    self.assertGreaterEqual(sum(text.startswith(repeated, i) for i in starts), 2)

    def test_documented_runner(self) -> None:
        """Run the exact documented command without relying on the caller's cwd."""
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_suffix_array_tutorial.py")],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "[5, 3, 1, 0, 4, 2]\n[0, 1, 3, 0, 0, 2]\nana\n")


if __name__ == "__main__":
    unittest.main()
