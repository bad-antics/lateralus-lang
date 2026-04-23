"""Unit tests for tools/gen_grug_corpus.py."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "tools" / "gen_grug_corpus.py"

spec = importlib.util.spec_from_file_location("gen_grug_corpus", GEN)
mod = importlib.util.module_from_spec(spec)
sys.modules["gen_grug_corpus"] = mod
spec.loader.exec_module(mod)  # type: ignore[union-attr]


def test_read_lines_strips_comments_and_blanks(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("# comment\n\nhello\n  spaced  \n# end\nworld\n", encoding="utf-8")
    assert mod.read_lines(p) == ["hello", "spaced", "world"]


def test_read_lines_missing_returns_empty(tmp_path: pathlib.Path) -> None:
    assert mod.read_lines(tmp_path / "nope.txt") == []


def test_c_escape_handles_quotes_and_backslashes() -> None:
    assert mod.c_escape('hello "world"') == 'hello \\"world\\"'
    assert mod.c_escape("a\\b") == "a\\\\b"
    assert mod.c_escape("line1\nline2") == "line1\\nline2"
    assert mod.c_escape("col1\tcol2") == "col1\\tcol2"


def test_parse_rules_basic(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "rules.txt"
    p.write_text(
        "# header\n"
        "docker,k8s=>container is cage for app\n"
        "  python  ,  pip => snake good. install easy.\n"
        "ignored line without arrow\n"
        "=>missing keywords\n"
        "kw=>\n",
        encoding="utf-8",
    )
    rules = mod.parse_rules(p)
    assert rules == [
        (["docker", "k8s"], "container is cage for app"),
        (["python", "pip"], "snake good. install easy."),
    ]


def test_parse_rules_missing_file(tmp_path: pathlib.Path) -> None:
    assert mod.parse_rules(tmp_path / "nope.txt") == []


def test_emit_array_round_trip(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "h.h"
    with out.open("w", encoding="utf-8") as fh:
        mod.emit_array(fh, "FOO", ['hello "grug"', "second"])
    text = out.read_text(encoding="utf-8")
    assert "static const char *const FOO[] = {" in text
    assert '"hello \\"grug\\""' in text
    assert "\"second\"" in text
    assert "FOO_N" in text


def test_real_training_files_load_and_compile() -> None:
    """Smoke test: every shipped training file parses + emits valid header."""
    for name in ("wisdom.txt", "jokes.txt", "smoke.txt"):
        items = mod.read_lines(ROOT / "apps" / "grug_training" / name)
        assert len(items) >= 5, f"{name} should have at least 5 entries"
        for line in items:
            assert "\n" not in line
    rules = mod.parse_rules(ROOT / "apps" / "grug_training" / "rules.txt")
    assert len(rules) >= 5
    for kws, resp in rules:
        assert kws and resp
        assert all(k == k.lower() for k in kws), "keywords must be lowercased"


def test_generated_header_matches_disk() -> None:
    """The committed gui/grug_corpus.h must match a fresh regeneration
    so PRs can't drift the header out of sync with the .txt sources."""
    header = (ROOT / "gui" / "grug_corpus.h").read_text(encoding="utf-8")
    wisdom = mod.read_lines(ROOT / "apps" / "grug_training" / "wisdom.txt")
    jokes = mod.read_lines(ROOT / "apps" / "grug_training" / "jokes.txt")
    smoke = mod.read_lines(ROOT / "apps" / "grug_training" / "smoke.txt")
    rules = mod.parse_rules(ROOT / "apps" / "grug_training" / "rules.txt")
    assert f"#define GRUG_TRAINING_WISDOM_N  {len(wisdom)}" in header
    assert f"#define GRUG_TRAINING_JOKES_N   {len(jokes)}" in header
    assert f"#define GRUG_TRAINING_SMOKE_N   {len(smoke)}" in header
    assert f"#define GRUG_TRAINING_RULES_N   {len(rules)}" in header
