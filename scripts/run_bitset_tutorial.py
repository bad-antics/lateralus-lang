#!/usr/bin/env python3
"""Compile and run examples/bitset_rbac.ltl against stdlib/bitset.ltl."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lateralus_lang.compiler import Compiler, Target

def main() -> int:
    stdlib_src = (ROOT / "stdlib/bitset.ltl").read_text(encoding="utf-8")
    example_src = (ROOT / "examples/bitset_rbac.ltl").read_text(encoding="utf-8")
    res = Compiler().compile_source(stdlib_src + chr(10)*2 + example_src, target=Target.PYTHON)
    if not res.ok:
        for err in res.errors:
            print(err, file=sys.stderr)
        return 1
    ns = {"__name__": "__main__"}
    exec(res.python_src, ns)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
