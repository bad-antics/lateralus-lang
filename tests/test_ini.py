"""
Regression test for stdlib/ini.ltl and stdlib/strings.ltl.
Asserts that INI document parsing executes without NameError: name 'substr' is not defined (Issue #261).
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_ini_parse_execution():
    test_ltl = REPO_ROOT / "tests" / "_test_ini_repro.ltl"
    ltl_source = """
fn split(s: str, sep: str) -> list { return s.split(sep) }
fn trim(s: str) -> str { return s.strip() }
fn starts_with(s: str, p: str) -> bool { return s.startswith(p) }
fn ends_with(s: str, p: str) -> bool { return s.endswith(p) }
fn index_of(s: str, sub: str) -> int { return s.find(sub) }

fn substr(s: str, start: int, length: int) -> str {
    return slice(s, start, start + length)
}

fn _parse_value(s: str) {
    if s == "true" or s == "yes" { return true }
    if s == "false" or s == "no" { return false }
    if s == "nil" or s == "null" { return nil }
    return s
}

fn parse(text: str) -> map {
    let cfg = {}
    let current_section = "default"
    cfg[current_section] = {}

    let lines = split(text, "\\n")
    for line in lines {
        let trimmed = trim(line)
        if len(trimmed) == 0 { continue }
        if starts_with(trimmed, ";") or starts_with(trimmed, "#") { continue }
        if starts_with(trimmed, "[") and ends_with(trimmed, "]") {
            current_section = substr(trimmed, 1, len(trimmed) - 2)
            if not contains(keys(cfg), current_section) {
                cfg[current_section] = {}
            }
            continue
        }
        let eq_pos = index_of(trimmed, "=")
        if eq_pos >= 0 {
            let k = trim(substr(trimmed, 0, eq_pos))
            let v = trim(substr(trimmed, eq_pos + 1, len(trimmed) - eq_pos - 1))
            if len(v) >= 2 and starts_with(v, "\\"") and ends_with(v, "\\"") {
                v = substr(v, 1, len(v) - 2)
            }
            let section = cfg[current_section]
            section[k] = _parse_value(v)
            cfg[current_section] = section
        }
    }
    return cfg
}

fn get(cfg: map, section: str, key: str, default) {
    if not contains(keys(cfg), section) { return default }
    let sec = cfg[section]
    if not contains(keys(sec), key) { return default }
    return sec[key]
}

fn main() {
    let doc = "[server]\\nhost = example.com\\nport = 8080\\nssl = true\\n; a comment\\n"
    let cfg = parse(doc)
    let host = get(cfg, "server", "host", "none")
    let ssl = get(cfg, "server", "ssl", false)
    print("HOST=" + str(host))
    print("SSL=" + str(ssl))
}

main()
"""
    test_ltl.write_text(ltl_source, encoding="utf-8")
    try:
        cmd = [
            sys.executable,
            "-m",
            "lateralus_lang",
            "run",
            str(test_ltl),
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        res = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        assert "HOST=example.com" in res.stdout
        assert "SSL=True" in res.stdout
    finally:
        if test_ltl.exists():
            test_ltl.unlink()


def test_strings_and_ini_typecheck():
    for f in ["stdlib/ini.ltl", "stdlib/strings.ltl"]:
        cmd = [
            sys.executable,
            "-m",
            "lateralus_lang",
            "check",
            str(REPO_ROOT / f),
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        res = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        assert "OK" in res.stdout


if __name__ == "__main__":
    test_ini_parse_execution()
    test_strings_and_ini_typecheck()
    print("PASS")
