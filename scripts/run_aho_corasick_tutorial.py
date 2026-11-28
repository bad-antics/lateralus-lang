"""Run the tutorial against the repository's actual Aho-Corasick module.

The Python backend does not load this .ltl module via `import aho_corasick`.
Join the two sources explicitly and supply the missing char_at helper, without
reimplementing the matching algorithm. Assertions propagate as a nonzero exit.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lateralus_lang import parse, transpile_to_python  # noqa: E402


def run_tutorial() -> None:
    """Transpile and execute the module and its companion example together."""
    module = REPO_ROOT / "stdlib" / "aho_corasick.ltl"
    example = REPO_ROOT / "examples" / "tutorials" / "aho_corasick_log_scan.ltl"
    source = module.read_text(encoding="utf-8") + "\n" + example.read_text(encoding="utf-8")
    generated = transpile_to_python(parse(source, filename=str(example)))
    namespace = {"__name__": "__main__", "char_at": lambda text, index: text[index]}
    exec(compile(generated, str(example), "exec"), namespace)


if __name__ == "__main__":
    run_tutorial()
