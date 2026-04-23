"""Tests for docs/linguist/scripts/update_badge.py."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "docs" / "linguist" / "scripts" / "update_badge.py"

spec = importlib.util.spec_from_file_location("update_badge", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["update_badge"] = mod
spec.loader.exec_module(mod)  # type: ignore[union-attr]


def _patch_paths(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(mod, "JSONL", tmp_path / "repo-count.jsonl")
    monkeypatch.setattr(mod, "OUT", tmp_path / "repo-count-badge.json")


def test_no_data(tmp_path, monkeypatch, capsys):
    _patch_paths(tmp_path, monkeypatch)
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "no data" in out


def test_orange_when_low(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    mod.JSONL.write_text(
        json.dumps({"ts": "x", "total": 50, "community": 5, "threshold": 200}) + "\n"
    )
    mod.main()
    payload = json.loads(mod.OUT.read_text())
    assert payload["color"] == "orange"
    assert payload["message"].startswith("50 / 200")


def test_brightgreen_when_eligible(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    mod.JSONL.write_text(
        json.dumps({"ts": "x", "total": 250, "community": 100, "threshold": 200}) + "\n"
    )
    mod.main()
    payload = json.loads(mod.OUT.read_text())
    assert payload["color"] == "brightgreen"
    assert "✅" in payload["message"]


def test_uses_latest_line(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    mod.JSONL.write_text(
        "\n".join(
            [
                json.dumps({"ts": "1", "total": 10, "community": 0, "threshold": 200}),
                json.dumps({"ts": "2", "total": 199, "community": 50, "threshold": 200}),
                "",  # trailing blank
            ]
        )
    )
    mod.main()
    payload = json.loads(mod.OUT.read_text())
    assert payload["message"].startswith("199 / 200")
    assert payload["color"] == "green"  # 199/200 = 99% >= 75%
