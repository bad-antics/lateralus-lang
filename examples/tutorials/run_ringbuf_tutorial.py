"""Run the ringbuf tutorial and verify pinned vectors on the Python backend.

Python 3.10+, no third-party dependencies. Run from any working directory.
This compiles the repository's actual stdlib/ringbuf.ltl, not a substitute.
"""
from __future__ import annotations
import argparse
import contextlib
import io
import sys
from pathlib import Path

EXPECTED_OUTPUT = "[21, 19, 23]\n21\n23\n21\n[19, 23]\n[19, 23, 24]\n0\n3\n"

def compile_code(root: Path, source: str) -> str:
    sys.path.insert(0, str(root))
    from lateralus_lang.compiler import Compiler, Target
    result = Compiler().compile_source(source, filename="ringbuf_tutorial.ltl", target=Target.PYTHON)
    if not result.ok:
        raise RuntimeError("Compilation failed: " + "; ".join(e.message for e in result.errors))
    return result.python_src

def verify(root: Path, example: Path) -> tuple[str, int]:
    source = (root / "stdlib/ringbuf.ltl").read_text(encoding="utf-8")
    namespace = {"__name__": "ringbuf_tutorial_module"}
    exec(compile_code(root, source), namespace)
    checked = 0

    def equal(actual: object, expected: object, label: str) -> None:
        nonlocal checked
        if actual != expected:
            raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
        checked += 1

    fresh = namespace["new"](3)
    equal(namespace["to_list"](fresh), [], "empty contents")
    equal(namespace["pop"](fresh), [None, fresh], "empty pop")
    equal(namespace["count"](fresh), 0, "empty count")
    buf = fresh
    for value in [18, 21, 19, 23]:
        buf = namespace["push"](buf, value)
    equal(namespace["to_list"](buf), [21, 19, 23], "overwrite oldest")
    equal(namespace["to_list"](fresh), [], "prior buffer remains unchanged")
    equal(namespace["is_full"](buf), True, "full after overwrite")
    equal(namespace["peek_front"](buf), 21, "oldest item")
    equal(namespace["peek_back"](buf), 23, "newest item")
    value, remaining = namespace["pop"](buf)
    equal(value, 21, "popped item")
    equal(namespace["to_list"](remaining), [19, 23], "remaining items")
    remaining = namespace["push"](remaining, 24)
    equal(namespace["to_list"](remaining), [19, 23, 24], "wrap after pop")
    cleared = namespace["clear"](remaining)
    equal(namespace["to_list"](cleared), [], "clear contents")
    equal(namespace["capacity"](cleared), 3, "clear preserves capacity")
    one = namespace["push"](namespace["push"](namespace["new"](1), 7), 9)
    equal(namespace["to_list"](one), [9], "capacity one")
    equal(namespace["at"](one, 1), None, "out of range")
    # The current implementation returns a list but does not empty buf.
    equal(namespace["drain"](buf), [21, 19, 23], "drain returns snapshot")
    equal(namespace["count"](buf), 3, "drain does not clear buffer")

    output = io.StringIO()
    combined = source + "\n" + example.read_text(encoding="utf-8")
    with contextlib.redirect_stdout(output):
        exec(compile_code(root, combined), {"__name__": "ringbuf_tutorial_example"})
    equal(output.getvalue(), EXPECTED_OUTPUT, "complete tutorial stdout")
    return output.getvalue(), checked

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--example", type=Path, default=Path(__file__).with_name("ringbuf_tutorial.ltl"))
    args = parser.parse_args()
    output, count = verify(args.repository.resolve(), args.example.resolve())
    print(output, end="")
    print(f"Verified {count} pinned checks against stdlib/ringbuf.ltl (Python backend).")

if __name__ == "__main__":
    main()
