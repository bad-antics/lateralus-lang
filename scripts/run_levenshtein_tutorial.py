"""Run the tutorial against the checked-out stdlib, without copying its algorithm."""

from pathlib import Path

from lateralus_lang.compiler import Compiler

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    """Combine the module and example until stdlib imports are supported."""
    module = REPO_ROOT / "stdlib" / "levenshtein.ltl"
    example = REPO_ROOT / "examples" / "levenshtein_tutorial.ltl"
    source = module.read_text(encoding="utf-8") + "\n" + example.read_text(encoding="utf-8")
    result = Compiler().run_source(source, filename="<levenshtein-tutorial-combined>")
    if not result.ok:
        for error in result.errors:
            print(error.message)
        return result.exit_code or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
