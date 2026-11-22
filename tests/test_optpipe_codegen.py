"""
Regression tests for issue #166: `|?` optional pipeline must preserve
falsy return values (0, false, "", [], 0.0) instead of emitting
`and ... or None`, which collapses them to None.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from tests.test_compiler import check

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_optpipe_preserves_falsy_returns():
    src = (
        "fn zero(x: int) -> int { return 0 }\n"
        "fn falsy(x: int) -> bool { return false }\n"
        "fn main() {\n"
        "    let a = 5 |? zero\n"
        "    let b = 5 |? falsy\n"
        "}\n"
    )
    r = check(src)
    assert r.ok
    # generated code must use a conditional, not `and ... or None`
    assert "or None" not in r.python_src
    assert "is None else" in r.python_src


def test_optpipe_call_expr_branch():
    src = "fn add(x: int, y: int) -> int { return x + y }\nfn main() { let r = 5 |? add(10) }"
    r = check(src)
    assert r.ok
    assert "is None else" in r.python_src
    assert "or None" not in r.python_src


def test_optpipe_runtime_values():
    prog = (
        "module examples.optpipe_rt\n"
        "fn zero(x: int) -> int { return 0 }\n"
        "fn falsy(x: int) -> bool { return false }\n"
        "fn empty(x: int) -> str { return \"\" }\n"
        "fn inc(x: int) -> int { return x + 1 }\n"
        "fn main() {\n"
        "    print(5 |? zero)\n"
        "    print(5 |? falsy)\n"
        "    print(5 |? empty)\n"
        "    print(nil |? zero)\n"
        "    print(7 |? inc)\n"
        "}\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".ltl", delete=False) as f:
        f.write(prog)
        path = f.name
    try:
        res = subprocess.run(
            [sys.executable, "-m", "lateralus_lang", "run", path],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    lines = res.stdout.strip().splitlines()
    assert lines == ["0", "False", "", "None", "8"]
