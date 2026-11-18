import os
import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lateralus_lang.compiler import Compiler, Target

c = Compiler()

def load_yaml_runtime():
    yaml_path = REPO_ROOT / "stdlib" / "yaml.ltl"
    res = c.compile_file(str(yaml_path), target=Target.PYTHON)
    assert res.ok, f"Failed to compile stdlib/yaml.ltl: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)
    return ns

yaml_mod = load_yaml_runtime()

def test_parse_scalar_int():
    parsed = yaml_mod["parse"]("42")
    assert parsed == 42

def test_parse_scalar_bool_and_null():
    assert yaml_mod["parse"]("true") is True
    assert yaml_mod["parse"]("false") is False
    assert yaml_mod["parse"]("null") is None
    assert yaml_mod["parse"]("~") is None

def test_parse_scalar_strings():
    assert yaml_mod["parse"]("hello") == "hello"
    assert yaml_mod["parse"]('"quoted value"') == "quoted value"
    assert yaml_mod["parse"]("'single quoted'") == "single quoted"

def test_parse_sequence():
    raw = "- item1\n- item2\n- item3"
    parsed = yaml_mod["parse"](raw)
    assert parsed == ["item1", "item2", "item3"]

def test_parse_mapping():
    raw = "name: lateralus\nversion: 3\nstable: true"
    parsed = yaml_mod["parse"](raw)
    assert parsed["name"] == "lateralus"
    assert parsed["version"] == 3
    assert parsed["stable"] is True

def test_parse_nested_structures():
    raw = """server:
  host: 127.0.0.1
  port: 8080
  workers: 4"""
    parsed = yaml_mod["parse"](raw)
    assert parsed["server"]["host"] == "127.0.0.1"
    assert parsed["server"]["port"] == 8080
    assert parsed["server"]["workers"] == 4

def test_parse_comments():
    raw = """# Configuration
name: webapp # app name
# Port setting
port: 3000"""
    parsed = yaml_mod["parse"](raw)
    assert parsed["name"] == "webapp"
    assert parsed["port"] == 3000

def test_dump_scalars():
    assert yaml_mod["dump"](42).strip() == "42"
    assert yaml_mod["dump"](True).strip() == "true"
    assert yaml_mod["dump"](False).strip() == "false"
    assert yaml_mod["dump"](None).strip() == "null"
    assert yaml_mod["dump"]("hello").strip() == "hello"

def test_dump_sequence():
    items = ["red", "green", "blue"]
    out = yaml_mod["dump"](items)
    assert "- red" in out
    assert "- green" in out
    assert "- blue" in out

def test_dump_mapping():
    m = {"database": "postgres", "port": 5432}
    out = yaml_mod["dump"](m)
    assert "database: postgres" in out
    assert "port: 5432" in out

def test_roundtrip_equivalence():
    original = {
        "name": "production_cluster",
        "nodes": 3,
        "enabled": True,
    }
    emitted = yaml_mod["dump"](original)
    reloaded = yaml_mod["parse"](emitted)
    assert reloaded["name"] == original["name"]
    assert reloaded["nodes"] == original["nodes"]
    assert reloaded["enabled"] == original["enabled"]

def test_stringify_alias():
    val = {"service": "gateway"}
    out1 = yaml_mod["dump"](val)
    out2 = yaml_mod["stringify"](val)
    assert out1 == out2
