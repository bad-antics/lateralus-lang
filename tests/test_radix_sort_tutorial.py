"""Exercise the tutorial through the CLI using unchanged combined stdlib source."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RadixSortTutorialTests(unittest.TestCase):
    """Check literal examples and independent integer-order expectations."""

    def run_program(self, example: str) -> str:
        """Run actual Lateralus source and require a successful, quiet CLI."""
        source = (ROOT / "stdlib/radix_sort.ltl").read_text(encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "radix_sort_tutorial.ltl"
            program.write_text(source + "\n" + example, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "lateralus_lang", "run", str(program)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_example_pinned_vectors(self) -> None:
        """Keep the published example tied to literal expected boundary vectors."""
        example = (ROOT / "examples/radix_sort_tutorial.ltl").read_text(encoding="utf-8")
        self.assertEqual(
            self.run_program(example),
            "[0, 1, 3, 3, 4294967295]\n"
            "[0, 4294967296, 18446744073709551615]\n"
            "[-2147483648, -1, 0, 2147483647]\n",
        )

    def test_empty_and_singleton(self) -> None:
        """All three integer APIs handle empty lists and one valid key."""
        self.assertEqual(
            self.run_program("""fn main() {
                print(radix_sort_u32([]))
                print(radix_sort_u32([4294967295]))
                print(radix_sort_u64([]))
                print(radix_sort_u64([18446744073709551615]))
                print(radix_sort_i32([]))
                print(radix_sort_i32([-2147483648]))
            }"""),
            "[]\n[4294967295]\n[]\n[18446744073709551615]\n[]\n[-2147483648]\n",
        )

    def test_duplicate_negatives(self) -> None:
        """Sign restoration preserves repeated negative keys and their count."""
        self.assertEqual(
            self.run_program("""fn main() {
                print(radix_sort_i32([-1, -2147483648, -1, 0, -7, -7, -2147483648]))
            }"""),
            "[-2147483648, -2147483648, -7, -7, -1, -1, 0]\n",
        )

    def test_against_sorted_oracle(self) -> None:
        """Compare byte-boundary and mixed-order lists with Python integer sorting."""
        cases = {
            "radix_sort_u32": [
                4294967295, 0, 256, 255, 65536, 65535, 16777216, 16777215,
                2147483648, 2147483647, 1, 256,
            ],
            "radix_sort_u64": [
                18446744073709551615, 0, 4294967296, 4294967295, 256, 255,
                65536, 65535, 16777216, 16777215, 1099511627776, 1099511627775,
                281474976710656, 281474976710655, 72057594037927936,
                72057594037927935, 9223372036854775808, 1, 4294967296,
            ],
            "radix_sort_i32": [
                -2147483648, 2147483647, -1, 0, -256, -255, -65536, -65535,
                -16777216, -16777215, 16777216, 65536, 256, 1, -1,
            ],
        }
        for function, values in cases.items():
            with self.subTest(function=function):
                vectors = [values, list(reversed(values)), sorted(values)]
                calls = "\n".join(f"print({function}({vector!r}))" for vector in vectors)
                expected = "".join(f"{sorted(vector)}\n" for vector in vectors)
                self.assertEqual(self.run_program("fn main() {\n" + calls + "\n}"), expected)


if __name__ == "__main__":
    unittest.main()
