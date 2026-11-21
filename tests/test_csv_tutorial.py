"""
tests/test_csv_tutorial.py - Comprehensive tests for stdlib/csv.ltl
Verifies CSV row parsing, header-based dictionary extraction, RFC 4180 escaping,
custom delimiter support, and generation round-trips.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_csv_parsing_and_dict_extraction():
    csv_src = Path("stdlib/csv.ltl").read_text(encoding="utf-8")
    driver = r"""
let sample = "id,name,city\n1,Alice,\"New York, NY\"\n2,Bob,\"San \"\"Francisco\"\", CA\"\n"
let rows = parse(sample, ",")

let row0 = rows[0]
let row1 = rows[1]
let row2 = rows[2]

let dicts = parse_dict(sample, ",")
let d0 = dicts[0]
let d1 = dicts[1]
let d0_city = d0["city"]
let d1_city = d1["city"]
let d1_name = d1["name"]
"""
    c = Compiler()
    res = c.compile_source(csv_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["row0"] == ["id", "name", "city"]
    assert ns["row1"] == ["1", "Alice", "New York, NY"]
    assert ns["row2"] == ["2", "Bob", 'San "Francisco", CA']

    assert len(ns["dicts"]) == 2
    assert ns["d0_city"] == "New York, NY"
    assert ns["d1_city"] == 'San "Francisco", CA'
    assert ns["d1_name"] == "Bob"

def test_csv_generation_and_custom_delimiters():
    csv_src = Path("stdlib/csv.ltl").read_text(encoding="utf-8")
    driver = r"""
// Generation from list of rows
let raw_rows = [["col1", "col2"], ["data1", "data with, comma"]]
let generated_csv = generate(raw_rows, ",")

// Generation from list of records
let mut r1 = map_new()
r1["product"] = "Laptop"
r1["price"] = "1200"

let mut r2 = map_new()
r2["product"] = "Mouse, Wireless"
r2["price"] = "25"

let records = [r1, r2]
let headers = ["product", "price"]
let generated_records = generate_dict(records, headers, ",")

// Parsing with custom semicolon delimiter
let tsv_sample = "alpha;beta;gamma\n10;20;30\n"
let semi_rows = parse(tsv_sample, ";")
let semi_r1 = semi_rows[1]
"""
    c = Compiler()
    res = c.compile_source(csv_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert '"data with, comma"' in ns["generated_csv"]
    assert '"Mouse, Wireless"' in ns["generated_records"]
    assert ns["semi_r1"] == ["10", "20", "30"]
