"""Exercise the tutorial and real stdlib LRU behavior through the Python backend."""

import subprocess
import sys
from pathlib import Path

import pytest

from lateralus_lang.compiler import Compiler, Target


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def lru():
    source = (ROOT / "stdlib/lru.ltl").read_text(encoding="utf-8")
    result = Compiler().compile_source(source, target=Target.PYTHON)
    assert result.ok, result.errors
    namespace = {"__name__": "lru_tutorial_test"}
    exec(result.python_src, namespace)
    return namespace


def test_catalog_example_matches_pinned_vector():
    result = subprocess.run(
        [sys.executable, "scripts/run_lru_tutorial.py"],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == (ROOT / "examples/lru_catalog.expected.txt").read_text()


def test_get_refreshes_recency_before_eviction(lru):
    cache = lru["from_pairs"]([["a", 1], ["b", 2]], 2)
    cache, value = lru["get"](cache, "a")
    assert value == 1
    cache = lru["put"](cache, "c", 3)
    assert lru["all_keys"](cache) == ["a", "c"]
    assert not lru["has"](cache, "b")
    assert lru["hits"](cache) == 1


def test_has_does_not_refresh_or_count_as_hit(lru):
    cache = lru["from_pairs"]([["a", 1], ["b", 2]], 2)
    assert lru["has"](cache, "a")
    cache = lru["put"](cache, "c", 3)
    assert lru["all_keys"](cache) == ["b", "c"]
    assert lru["hits"](cache) == 0


def test_update_refreshes_without_growing(lru):
    cache = lru["from_pairs"]([["a", 1], ["b", 2]], 2)
    cache = lru["put"](cache, "a", 9)
    assert lru["size"](cache) == 2
    assert lru["all_keys"](cache) == ["b", "a"]
    cache = lru["put"](cache, "c", 3)
    assert lru["get"](cache, "a")[1] == 9
    assert not lru["has"](cache, "b")


def test_miss_preserves_order(lru):
    cache = lru["from_pairs"]([["a", 1]], 2)
    cache, value = lru["get"](cache, "missing")
    assert value is None
    assert lru["all_keys"](cache) == ["a"]
    assert lru["misses"](cache) == 1
    assert lru["hits"](cache) == 0


def test_nil_value_is_distinct_from_absent_key_with_has(lru):
    cache = lru["put"](lru["new"](2), "a", None)
    cache, value = lru["get"](cache, "a")
    assert value is None
    assert lru["has"](cache, "a")
    assert lru["hits"](cache) == 1


def test_resize_and_clear(lru):
    cache = lru["from_pairs"]([["a", 1], ["b", 2], ["c", 3]], 3)
    cache = lru["resize"](cache, 1)
    assert lru["all_keys"](cache) == ["c"]
    cache, _ = lru["get"](cache, "c")
    cache = lru["clear"](cache)
    assert lru["is_empty"](cache)
    assert lru["hits"](cache) == lru["misses"](cache) == 0
    assert lru["capacity"](cache) == 1


def test_zero_capacity_does_not_disable_storage(lru):
    cache = lru["new"](0)
    for key in ["a", "b", "c"]:
        cache = lru["put"](cache, key, key)
    assert lru["all_keys"](cache) == ["a", "b", "c"]
