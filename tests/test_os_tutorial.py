"""
tests/test_os_tutorial.py - Comprehensive verification for stdlib/os.ltl
Verifies cross-platform path manipulation (joining, normalization, basename,
dirname, extension extraction), environment variable access, and operating
system process metadata primitives.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target


def run_os_snippet(driver: str) -> dict:
    os_src = Path("stdlib/os.ltl").read_text(encoding="utf-8")
    c = Compiler()
    res = c.compile_source(os_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation to Python failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    return ns


def test_os_path_join_and_separators():
    driver = r"""
let sep = path_separator()
let joined = path_join(["usr", "local", "bin"])
let expected = "usr" + sep + "local" + sep + "bin"
"""
    ns = run_os_snippet(driver)
    assert ns["joined"] == ns["expected"], f"Path join mismatch: {ns['joined']}"
    assert ns["sep"] in ("/", "\\"), f"Unexpected path separator: {ns['sep']}"


def test_os_basename_and_dirname():
    driver = r"""
let sep = path_separator()
let full = "var" + sep + "log" + sep + "audit.log"
let base = basename(full)
let dir = dirname(full)
let empty_base = basename("")
let single_dir = dirname("file.txt")
"""
    ns = run_os_snippet(driver)
    assert ns["base"] == "audit.log"
    assert ns["dir"] == "var" + ns["sep"] + "log"
    assert ns["empty_base"] == ""
    assert ns["single_dir"] == "."


def test_os_extension_and_stripping():
    driver = r"""
let ext1 = extension("archive.tar.gz")
let strip1 = strip_extension("archive.tar.gz")
let ext2 = extension("plain_file")
let strip2 = strip_extension("plain_file")
let ext3 = extension("script.ltl")
let strip3 = strip_extension("script.ltl")
"""
    ns = run_os_snippet(driver)
    assert ns["ext1"] == ".gz"
    assert ns["strip1"] == "archive.tar"
    assert ns["ext2"] == ""
    assert ns["strip2"] == "plain_file"
    assert ns["ext3"] == ".ltl"
    assert ns["strip3"] == "script"


def test_os_normalize_path():
    driver = r"""
let sep = path_separator()
let dirty = "a" + sep + "b" + sep + ".." + sep + "c" + sep + "." + sep + "d"
let norm = normalize_path(dirty)
let expected = "a" + sep + "c" + sep + "d"
let dot_path = normalize_path("." + sep + "." + sep + ".")
"""
    ns = run_os_snippet(driver)
    assert ns["norm"] == ns["expected"], f"Path normalization mismatch: {ns['norm']}"
    assert ns["dot_path"] == "."


def test_os_environment_lifecycle():
    driver = r"""
setenv("LATERALUS_TEST_KEY", "alpha_omega_99")
let val = getenv("LATERALUS_TEST_KEY")
let missing = getenv("NON_EXISTENT_VAR_xyz123")
"""
    ns = run_os_snippet(driver)
    assert ns["val"] == "alpha_omega_99"
    assert ns["missing"] == ""


def test_os_system_metadata():
    driver = r"""
let plat = platform()
let p_arch = arch()
let p_id = pid()
"""
    ns = run_os_snippet(driver)
    assert len(ns["plat"]) > 0, "Platform identifier must not be empty"
    assert len(ns["p_arch"]) > 0, "Architecture string must not be empty"
    assert isinstance(ns["p_id"], int) and ns["p_id"] > 0, f"Invalid PID: {ns['p_id']}"
