"""Run the numeric alignment helpers from stdlib/mem.ltl."""

from pathlib import Path

from lateralus_lang.ast_nodes import FnDecl
from lateralus_lang.codegen.python import transpile_to_python
from lateralus_lang.parser import parse


def main() -> None:
    module_path = Path(__file__).resolve().parents[1] / "stdlib" / "mem.ltl"
    program = parse(module_path.read_text(encoding="utf-8"), str(module_path))

    # The other functions in mem.ltl use native operations.
    names = {"align_down", "align_up", "is_aligned"}
    program.body = [
        statement
        for statement in program.body
        if isinstance(statement, FnDecl) and statement.name in names
    ]
    if {statement.name for statement in program.body} != names:
        raise RuntimeError("Missing alignment helpers in stdlib/mem.ltl")

    helpers = {"__name__": "mem_alignment_helpers"}
    exec(transpile_to_python(program), helpers)

    vectors = [
        (0, 8, (0, 0, True)),
        (13, 8, (8, 16, False)),
        (16, 8, (16, 16, True)),
        (17, 8, (16, 24, False)),
        (13, 1, (13, 13, True)),
    ]
    print("offset alignment down up aligned")
    for offset, alignment, expected in vectors:
        down = helpers["align_down"](offset, alignment)
        up = helpers["align_up"](offset, alignment)
        aligned = helpers["is_aligned"](offset, alignment)
        actual = (down, up, aligned)
        if actual != expected:
            raise AssertionError(f"{offset=}, {alignment=}: {actual!r} != {expected!r}")
        print(offset, alignment, down, up, str(aligned).lower())


if __name__ == "__main__":
    main()
