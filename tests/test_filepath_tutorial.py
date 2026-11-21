"""
tests/test_filepath_tutorial.py - Tests for stdlib/filepath.ltl
Verifies path component extraction, canonical joining, normalization, and extension swapping.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_filepath_component_extraction():
    fp_src = Path("stdlib/filepath.ltl").read_text(encoding="utf-8")
    driver = """
let d1 = dirname("/home/user/documents/report.pdf")
let d2 = dirname("report.pdf")
let d3 = dirname("/root")

let b1 = basename("/home/user/documents/report.pdf")
let b2 = basename("report.pdf")

let ext1 = extension("archive.tar.gz")
let ext2 = extension("script.ltl")
let ext3 = extension("Makefile")

let stem1 = stem("archive.tar.gz")
let stem2 = stem("script.ltl")
let stem3 = stem("Makefile")
"""
    c = Compiler()
    res = c.compile_source(fp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["d1"] == "/home/user/documents"
    assert ns["d2"] == "."
    assert ns["d3"] == "/"

    assert ns["b1"] == "report.pdf"
    assert ns["b2"] == "report.pdf"

    assert ns["ext1"] == ".gz"
    assert ns["ext2"] == ".ltl"
    assert ns["ext3"] == ""

    assert ns["stem1"] == "archive.tar"
    assert ns["stem2"] == "script"
    assert ns["stem3"] == "Makefile"

def test_filepath_joining_and_normalization():
    fp_src = Path("stdlib/filepath.ltl").read_text(encoding="utf-8")
    driver = """
let joined = join_path(["/srv", "data", "storage", "users.json"])
let norm1 = normalize("/app/backend/../frontend/./build")
let norm2 = normalize("a/b/../../c")
let norm_root = normalize("/a/../../")

let abs1 = is_absolute("/etc/hosts")
let abs2 = is_absolute("relative/path")

let rel1 = is_relative("local/data")
let rel2 = is_relative("/root")

let swapped = with_extension("src/main.ltl", ".py")
let has_ext = has_extension(swapped, ".py")
"""
    c = Compiler()
    res = c.compile_source(fp_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["joined"] == "/srv/data/storage/users.json"
    assert ns["norm1"] == "/app/frontend/build"
    assert ns["norm2"] == "c"
    assert ns["norm_root"] == "/"

    assert ns["abs1"] is True
    assert ns["abs2"] is False

    assert ns["rel1"] is True
    assert ns["rel2"] is False

    assert ns["swapped"] == "src/main.py"
    assert ns["has_ext"] is True
