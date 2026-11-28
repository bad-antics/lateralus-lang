import pytest
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def load_stdlib_module(name: str):
    path = Path("stdlib") / f"{name}.ltl"
    compiled = Compiler().compile_source(
        path.read_text(encoding="utf-8"), filename=str(path), target=Target.PYTHON
    )
    assert compiled.ok, [e.message for e in compiled.errors]
    ns = {}
    exec(compiled.python_src, ns)
    return ns

def test_csv_generate_parse_preserves_spaces():
    csv_mod = load_stdlib_module("csv")
    generate = csv_mod["generate"]
    parse = csv_mod["parse"]
    rows = [["plain", "value"], [" 001", "400 "]]
    csv_text = generate(rows, ",")
    parsed = parse(csv_text, ",")
    assert parsed == rows, f"Spaces were stripped: expected {rows}, got {parsed}"
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target


def test_csv_parse_preserves_edge_spaces():
    ns = {"__name__": "csv_repro"}
    for name in ("strings", "csv"):
        path = Path("stdlib") / (name + ".ltl")
        compiled = Compiler().compile_source(
            path.read_text(encoding="utf-8"), filename=str(path), target=Target.PYTHON
        )
        assert compiled.ok, [e.message for e in compiled.errors]
        exec(compiled.python_src, ns)

    rows = [["plain", "value"], [" 001", "400 "]]
    encoded = ns["generate"](rows, ",")
    parsed_generated = ns["parse"](encoded, ",")
    parsed_unquoted = ns["parse"]("plain,value\n 001,400 \n", ",")
    parsed_quoted = ns["parse"]('plain,value\n" 001","400 "\n', ",")

    assert parsed_generated == rows
    assert parsed_unquoted == rows
    assert parsed_quoted == rows
