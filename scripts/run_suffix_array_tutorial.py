"""Run the suffix-array example against the repository's actual stdlib source."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lateralus_lang import Compiler, Target  # noqa: E402


def main() -> int:
    """Compile and execute the documented example without an import shim or install."""
    source = (ROOT / "stdlib/suffix_array.ltl").read_text(encoding="utf-8")
    source += "\n" + (ROOT / "examples/suffix_array_demo.ltl").read_text(encoding="utf-8")
    result = Compiler().compile_source(source, "suffix_array_demo.ltl", Target.PYTHON)
    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1
    # This executes the compiler's output, including its generated call to main().
    exec(compile(result.python_src, "<suffix-array-demo>", "exec"), {"__name__": "__main__"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
