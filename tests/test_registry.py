"""
tests/test_registry.py — static package registry: determinism, integrity, safety.

The properties worth guarding here are not "does publish write a file". They are:

  * two publishes of the same tree produce byte-identical archives, so the
    digest in index.json means something across machines;
  * a tampered archive is rejected before it reaches the filesystem;
  * an archive containing a traversal path or a symlink is rejected.

Everything else is bookkeeping.
"""
import http.server
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import threading
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lateralus_lang.package_manager import ProjectManifest  # noqa: E402
from lateralus_lang.registry import (  # noqa: E402
    INDEX_FILE,
    IntegrityError,
    RegistryError,
    RegistryIndex,
    RegistryLocation,
    build_tarball,
    collect_files,
    digest_of,
    fetch_package,
    parse_semver,
    publish_package,
    rebuild_index,
    resolve_version,
    satisfies,
    tarball_path,
    unpack_tarball,
)

MANIFEST_TOML = """[package]
name = "hello"
version = "0.1.0"
description = "A test package"
license = "MIT"
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project(tmp_path):
    """A minimal but realistic package: manifest at the root, sources in src/."""
    root = tmp_path / "hello"
    root.mkdir()
    (root / "lateralus.toml").write_text(MANIFEST_TOML, encoding="utf-8")
    (root / "main.ltl").write_text('fn main() { println("hi") }\n', encoding="utf-8")
    (root / "README.md").write_text("# hello\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "util.ltl").write_text(
        "fn add(a: int, b: int) -> int { return a + b }\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# guide\n", encoding="utf-8")
    # Things that must never be published.
    (root / "vendor").mkdir()
    (root / "vendor" / "stale.ltl").write_text("nope\n", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "junk.pyc").write_bytes(b"\x00\x01")
    return root


@pytest.fixture
def manifest(project):
    return ProjectManifest.from_file(project / "lateralus.toml")


@pytest.fixture
def registry_dir(tmp_path):
    path = tmp_path / "registry"
    path.mkdir()
    return path


def _location(path):
    return RegistryLocation(path=path)


# ---------------------------------------------------------------------------
# collect_files
# ---------------------------------------------------------------------------

class TestCollectFiles:
    def test_includes_root_manifest_and_sources(self, project):
        files = collect_files(project)
        assert "lateralus.toml" in files
        assert "README.md" in files
        assert "main.ltl" in files          # template puts the entry point at the root
        assert "src/util.ltl" in files
        assert "docs/guide.md" in files

    def test_excludes_vendor_and_caches(self, project):
        files = collect_files(project)
        assert not any(f.startswith("vendor/") for f in files)
        assert not any(f.startswith("__pycache__/") for f in files)
        assert not any(f.endswith(".pyc") for f in files)

    def test_output_is_sorted_and_unique(self, project):
        files = collect_files(project)
        assert files == sorted(files)
        assert len(files) == len(set(files))


# ---------------------------------------------------------------------------
# Determinism — the whole point of the index digest
# ---------------------------------------------------------------------------

class TestDeterministicArchive:
    def test_same_tree_same_bytes(self, project):
        files = collect_files(project)
        first = build_tarball(project, files)
        second = build_tarball(project, files)
        assert first == second
        assert digest_of(first) == digest_of(second)

    def test_digest_is_stable_across_a_rewrite(self, project):
        files = collect_files(project)
        before = digest_of(build_tarball(project, files))
        # Rewriting identical content changes mtime but not the archive.
        (project / "src" / "util.ltl").write_text(
            (project / "src" / "util.ltl").read_text(encoding="utf-8"),
            encoding="utf-8")
        after = digest_of(build_tarball(project, files))
        assert before == after

    def test_file_creation_order_does_not_matter(self, tmp_path):
        def make(order):
            root = tmp_path / f"p{order[0]}"
            root.mkdir()
            (root / "lateralus.toml").write_text(MANIFEST_TOML, encoding="utf-8")
            for name in order:
                (root / name).write_text(f"// {name}\n", encoding="utf-8")
            return root

        a = make(["a.ltl", "b.ltl", "c.ltl"])
        b = make(["c.ltl", "b.ltl", "a.ltl"])
        assert digest_of(build_tarball(a, collect_files(a))) == \
               digest_of(build_tarball(b, collect_files(b)))

    def test_archive_headers_are_neutral(self, project):
        archive = build_tarball(project, collect_files(project))
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for member in tar.getmembers():
                assert member.mtime == 0
                assert member.uid == 0 and member.gid == 0
                assert member.uname == "" and member.gname == ""
                assert member.mode == 0o644

    def test_gzip_header_has_no_timestamp(self, project):
        archive = build_tarball(project, collect_files(project))
        # Gzip stores mtime as a 4-byte little-endian field at offset 4.
        assert archive[4:8] == b"\x00\x00\x00\x00"

    def test_content_change_changes_digest(self, project):
        files = collect_files(project)
        before = digest_of(build_tarball(project, files))
        (project / "src" / "util.ltl").write_text("fn add() { return 1 }\n",
                                                  encoding="utf-8")
        after = digest_of(build_tarball(project, files))
        assert before != after

    def test_archive_uses_gnu_format(self, project):
        """GNU format keeps long paths readable by every tar on earth, and the
        magic field is written at a fixed offset we can assert on."""
        import gzip
        archive = build_tarball(project, collect_files(project))
        raw = gzip.decompress(archive)
        assert raw[257:265] == b"ustar  \x00"


# ---------------------------------------------------------------------------
# Semver constraint subset
# ---------------------------------------------------------------------------

class TestSemver:
    @pytest.mark.parametrize("text,expected", [
        ("1.2.3", (1, 2, 3, "")),
        ("0.1.0", (0, 1, 0, "")),
        ("2.0.0-rc.1", (2, 0, 0, "rc.1")),
    ])
    def test_parse(self, text, expected):
        assert parse_semver(text) == expected

    @pytest.mark.parametrize("bad", ["1.2", "v1.2.3", "", "1.2.3.4", "abc"])
    def test_parse_rejects(self, bad):
        with pytest.raises(RegistryError):
            parse_semver(bad)

    @pytest.mark.parametrize("version,spec,expected", [
        ("1.2.3", "*", True),
        ("1.2.3", "1.2.3", True),
        ("1.2.4", "1.2.3", False),
        ("1.9.0", "^1.2.3", True),
        ("2.0.0", "^1.2.3", False),
        ("0.2.5", "^0.2.0", True),
        ("0.3.0", "^0.2.0", False),
        ("1.2.9", "~1.2.3", True),
        ("1.3.0", "~1.2.3", False),
        ("2.0.0", ">=1.5.0", True),
        ("1.4.0", ">=1.5.0", False),
        ("1.4.0", "<1.5.0", True),
        ("1.5.0", "<1.5.0", False),
        ("1.5.0", ">=1.0.0 <2.0.0", True),
        ("2.1.0", ">=1.0.0 <2.0.0", False),
    ])
    def test_satisfies(self, version, spec, expected):
        assert satisfies(version, spec) is expected

    def test_prerelease_sorts_below_release(self):
        index = RegistryIndex.empty()
        index.add("x", {"version": "1.0.0-rc.1"})
        index.add("x", {"version": "1.0.0"})
        assert index.packages["x"]["latest"] == "1.0.0"

    def test_resolve_picks_highest_match(self):
        index = RegistryIndex.empty()
        for version in ("1.0.0", "1.1.0", "1.2.0", "2.0.0"):
            index.add("x", {"version": version})
        assert resolve_version(index, "x", "^1.0.0") == "1.2.0"
        assert resolve_version(index, "x", "*") == "2.0.0"

    def test_resolve_reports_known_versions(self):
        index = RegistryIndex.empty()
        index.add("x", {"version": "1.0.0"})
        with pytest.raises(RegistryError) as exc:
            resolve_version(index, "x", "^9.0.0")
        assert "1.0.0" in str(exc.value)

    def test_resolve_unknown_package(self):
        with pytest.raises(RegistryError) as exc:
            resolve_version(RegistryIndex.empty(), "ghost", "*")
        assert "not in the registry" in str(exc.value)


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------

class TestPublish:
    def test_writes_archive_and_index(self, project, manifest, registry_dir):
        outcome = publish_package(project, manifest, _location(registry_dir))
        assert outcome["status"] == "published"

        archive = registry_dir / tarball_path("hello", "0.1.0")
        assert archive.exists()
        assert digest_of(archive.read_bytes()) == outcome["record"]["digest"]

        index = json.loads((registry_dir / INDEX_FILE).read_text(encoding="utf-8"))
        assert index["schema"] == 1
        entry = index["packages"]["hello"]["versions"]["0.1.0"]
        assert entry["digest"] == outcome["record"]["digest"]
        assert entry["license"] == "MIT"
        assert entry["tarball"] == "packages/hello/hello-0.1.0.tar.gz"

    def test_index_is_stable_json(self, project, manifest, registry_dir):
        publish_package(project, manifest, _location(registry_dir))
        first = (registry_dir / INDEX_FILE).read_bytes()
        # Re-publishing the same content must not churn the index.
        publish_package(project, manifest, _location(registry_dir))
        assert (registry_dir / INDEX_FILE).read_bytes() == first

    def test_republish_identical_content_is_unchanged(self, project, manifest,
                                                     registry_dir):
        publish_package(project, manifest, _location(registry_dir))
        again = publish_package(project, manifest, _location(registry_dir))
        assert again["status"] == "unchanged"

    def test_republish_changed_content_replaces(self, project, manifest,
                                                registry_dir):
        publish_package(project, manifest, _location(registry_dir))
        (project / "src" / "util.ltl").write_text("fn add() { return 0 }\n",
                                                  encoding="utf-8")
        again = publish_package(project, manifest, _location(registry_dir))
        assert again["status"] == "published"
        assert again["replaced"] is True
        assert "supersedes" in again["record"]

    def test_dry_run_writes_nothing(self, project, manifest, registry_dir):
        outcome = publish_package(project, manifest, _location(registry_dir),
                                  dry_run=True)
        assert outcome["status"] == "dry-run"
        assert list(registry_dir.iterdir()) == []

    def test_two_versions_coexist(self, project, registry_dir):
        manifest = ProjectManifest.from_file(project / "lateralus.toml")
        publish_package(project, manifest, _location(registry_dir))
        manifest.version = "0.2.0"
        publish_package(project, manifest, _location(registry_dir))

        index = RegistryIndex.load(_location(registry_dir))
        assert set(index.versions_of("hello")) == {"0.1.0", "0.2.0"}
        assert index.packages["hello"]["latest"] == "0.2.0"

    def test_empty_project_is_rejected(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        manifest = ProjectManifest(name="empty", version="0.1.0")
        with pytest.raises(RegistryError) as exc:
            publish_package(empty, manifest, _location(tmp_path / "reg"))
        assert "nothing to publish" in str(exc.value)


# ---------------------------------------------------------------------------
# fetch + integrity
# ---------------------------------------------------------------------------

class TestFetch:
    def _published(self, project, manifest, registry_dir):
        publish_package(project, manifest, _location(registry_dir))
        return RegistryIndex.load(_location(registry_dir))

    def test_roundtrip_unpacks_every_file(self, project, manifest, registry_dir,
                                          tmp_path):
        index = self._published(project, manifest, registry_dir)
        vendor = tmp_path / "consumer" / "vendor"
        result = fetch_package(index, _location(registry_dir), "hello", "*", vendor)

        assert result["version"] == "0.1.0"
        target = vendor / "hello-0.1.0"
        assert (target / "lateralus.toml").exists()
        assert (target / "main.ltl").read_text(encoding="utf-8").startswith("fn main")
        assert (target / "src" / "util.ltl").exists()
        assert not (target / "vendor").exists()

    def test_tampered_archive_is_rejected(self, project, manifest, registry_dir,
                                          tmp_path):
        index = self._published(project, manifest, registry_dir)
        archive = registry_dir / tarball_path("hello", "0.1.0")
        archive.write_bytes(archive.read_bytes() + b"tampered")

        with pytest.raises(IntegrityError) as exc:
            fetch_package(index, _location(registry_dir), "hello", "*",
                          tmp_path / "vendor")
        assert "digest mismatch" in str(exc.value)
        assert not (tmp_path / "vendor" / "hello-0.1.0").exists()

    def test_missing_archive_is_reported(self, project, manifest, registry_dir,
                                         tmp_path):
        index = self._published(project, manifest, registry_dir)
        (registry_dir / tarball_path("hello", "0.1.0")).unlink()
        with pytest.raises(RegistryError):
            fetch_package(index, _location(registry_dir), "hello", "*",
                          tmp_path / "vendor")

    def test_index_without_digest_is_rejected(self, registry_dir, tmp_path):
        index = RegistryIndex.empty()
        index.add("sketchy", {"version": "1.0.0", "tarball": "packages/sketchy/x.gz"})
        with pytest.raises(RegistryError) as exc:
            fetch_package(index, _location(registry_dir), "sketchy", "*",
                          tmp_path / "vendor")
        assert "unusable digest" in str(exc.value)

    def test_respects_version_spec(self, project, registry_dir, tmp_path):
        manifest = ProjectManifest.from_file(project / "lateralus.toml")
        for version in ("0.1.0", "0.2.0", "1.0.0"):
            manifest.version = version
            publish_package(project, manifest, _location(registry_dir))
        index = RegistryIndex.load(_location(registry_dir))

        result = fetch_package(index, _location(registry_dir), "hello", "0.1.0",
                               tmp_path / "vendor-a")
        assert result["version"] == "0.1.0"

        result = fetch_package(index, _location(registry_dir), "hello", "^1.0.0",
                               tmp_path / "vendor-b")
        assert result["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Extraction safety
# ---------------------------------------------------------------------------

def _tar_with(entries):
    """Build a gzip tarball from (name, payload) or (name, None, type) tuples."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for entry in entries:
            name, payload = entry[0], entry[1]
            kind = entry[2] if len(entry) > 2 else tarfile.REGTYPE
            info = tarfile.TarInfo(name)
            if kind == tarfile.REGTYPE:
                info.size = len(payload)
                info.type = tarfile.REGTYPE
                tar.addfile(info, io.BytesIO(payload))
            else:
                info.type = kind
                info.linkname = payload if isinstance(payload, str) else ""
                tar.addfile(info)
    import gzip
    out = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


class TestExtractionSafety:
    def test_parent_traversal_is_rejected(self, tmp_path):
        evil = _tar_with([("../../escape.txt", b"pwned")])
        with pytest.raises(RegistryError) as exc:
            unpack_tarball(evil, tmp_path / "dest")
        assert "escapes the destination" in str(exc.value)
        assert not (tmp_path / "escape.txt").exists()

    def test_absolute_path_is_rejected(self, tmp_path):
        evil = _tar_with([("/etc/passwd", b"pwned")])
        with pytest.raises(RegistryError):
            unpack_tarball(evil, tmp_path / "dest")

    def test_symlink_entry_is_rejected(self, tmp_path):
        evil = _tar_with([("link", "/etc/passwd", tarfile.SYMTYPE)])
        with pytest.raises(RegistryError) as exc:
            unpack_tarball(evil, tmp_path / "dest")
        assert "non-regular entry" in str(exc.value)

    def test_directory_entry_is_rejected(self, tmp_path):
        # We create parents ourselves; a directory record carries no data and
        # only serves as a place to hide a traversal.
        evil = _tar_with([("dir/", b"", tarfile.DIRTYPE)])
        with pytest.raises(RegistryError):
            unpack_tarball(evil, tmp_path / "dest")

    def test_unpack_budget_is_enforced(self, tmp_path):
        big = _tar_with([("big.bin", b"x" * 4096)])
        with pytest.raises(RegistryError) as exc:
            unpack_tarball(big, tmp_path / "dest", max_unpacked=1024)
        assert "budget" in str(exc.value)


# ---------------------------------------------------------------------------
# index.json handling
# ---------------------------------------------------------------------------

class TestIndexFile:
    def test_missing_index_is_empty(self, registry_dir):
        index = RegistryIndex.load(_location(registry_dir))
        assert index.packages == {}

    def test_corrupt_index_is_rejected(self, registry_dir):
        (registry_dir / INDEX_FILE).write_text("{not json", encoding="utf-8")
        with pytest.raises(RegistryError):
            RegistryIndex.load(_location(registry_dir))

    def test_future_schema_is_rejected(self, registry_dir):
        (registry_dir / INDEX_FILE).write_text(
            json.dumps({"schema": 99, "packages": {}}), encoding="utf-8")
        with pytest.raises(RegistryError) as exc:
            RegistryIndex.load(_location(registry_dir))
        assert "schema" in str(exc.value)

    def test_roundtrip(self):
        index = RegistryIndex.empty()
        index.add("a", {"version": "1.0.0", "digest": "sha256:00"})
        again = RegistryIndex.from_bytes(index.to_bytes())
        assert again.packages == index.packages

    def test_output_is_sorted_for_diffable_commits(self):
        index = RegistryIndex.empty()
        index.add("zebra", {"version": "1.0.0"})
        index.add("alpha", {"version": "1.0.0"})
        text = index.to_bytes().decode("utf-8")
        assert text.index('"alpha"') < text.index('"zebra"')


# ---------------------------------------------------------------------------
# rebuild_index
# ---------------------------------------------------------------------------

class TestRebuildIndex:
    def test_reconstructs_from_archives(self, project, manifest, registry_dir):
        publish_package(project, manifest, _location(registry_dir))
        (registry_dir / INDEX_FILE).unlink()

        index = rebuild_index(registry_dir)
        assert "hello" in index.packages
        assert index.packages["hello"]["latest"] == "0.1.0"

    def test_digest_matches_original(self, project, manifest, registry_dir):
        outcome = publish_package(project, manifest, _location(registry_dir))
        original = outcome["record"]["digest"]
        rebuilt = rebuild_index(registry_dir)
        assert rebuilt.get("hello", "0.1.0")["digest"] == original

    def test_ignores_non_semver_files(self, registry_dir):
        d = registry_dir / "packages" / "junk"
        d.mkdir(parents=True)
        (d / "junk-notaversion.tar.gz").write_bytes(b"x")
        index = rebuild_index(registry_dir)
        assert "junk" not in index.packages


# ---------------------------------------------------------------------------
# End to end over HTTP (the same code path a static host exercises)
# ---------------------------------------------------------------------------

def _load_serve_module():
    spec = importlib.util.spec_from_file_location(
        "registry_serve_under_test",
        PROJECT_ROOT / "tools" / "registry" / "serve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def http_registry(tmp_path):
    serve = _load_serve_module()
    root = tmp_path / "http-registry"
    root.mkdir()
    handler = _partial_handler(serve, root)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield root, f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _partial_handler(serve, root):
    import functools
    return functools.partial(serve.RegistryHandler, directory=str(root))


class TestHttpRoundtrip:
    def test_publish_then_fetch_over_http(self, project, manifest, http_registry,
                                          tmp_path):
        root, url = http_registry
        outcome = publish_package(project, manifest, RegistryLocation(url=url))
        assert outcome["status"] == "published"
        assert (root / INDEX_FILE).exists()

        index = RegistryIndex.load(RegistryLocation(url=url))
        result = fetch_package(index, RegistryLocation(url=url), "hello", "*",
                               tmp_path / "vendor")
        assert result["version"] == "0.1.0"
        assert (tmp_path / "vendor" / "hello-0.1.0" / "main.ltl").exists()

    def test_missing_package_over_http_is_reported(self, http_registry, tmp_path):
        _, url = http_registry
        with pytest.raises(RegistryError):
            fetch_package(RegistryIndex.empty(), RegistryLocation(url=url),
                          "ghost", "*", tmp_path / "vendor")


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------

def _run_cli(args, cwd, timeout=120):
    return subprocess.run(
        [sys.executable, "-m", "lateralus_lang", *args],
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )


@pytest.mark.e2e
class TestCli:
    def test_publish_dry_run(self, project):
        result = _run_cli(["publish", "--dry-run"], cwd=project)
        assert result.returncode == 0, result.stderr
        assert "Would publish hello@0.1.0" in result.stdout
        assert "Digest:   sha256:" in result.stdout

    def test_publish_to_path_then_add(self, project, registry_dir, tmp_path):
        published = _run_cli(
            ["publish", "--registry-path", str(registry_dir)], cwd=project)
        assert published.returncode == 0, published.stderr
        assert "Published hello@0.1.0" in published.stdout

        consumer = tmp_path / "consumer"
        consumer.mkdir()
        (consumer / "lateralus.toml").write_text(
            '[package]\nname = "consumer"\nversion = "0.1.0"\n', encoding="utf-8")

        added = _run_cli(
            ["add", "hello", "--registry-path", str(registry_dir)], cwd=consumer)
        assert added.returncode == 0, added.stderr
        assert "Added hello@0.1.0" in added.stdout
        assert (consumer / "vendor" / "hello-0.1.0" / "main.ltl").exists()

        lock = json.loads((consumer / "lateralus-lock.json").read_text(encoding="utf-8"))
        assert lock["entries"]["hello"]["version"] == "0.1.0"
        assert lock["entries"]["hello"]["integrity"].startswith("sha256:")

    def test_add_without_registry_fails_clearly(self, project, monkeypatch):
        monkeypatch.delenv("LATERALUS_REGISTRY", raising=False)
        monkeypatch.delenv("LATERALUS_REGISTRY_TOKEN", raising=False)
        consumer = project / "sub"
        consumer.mkdir()
        (consumer / "lateralus.toml").write_text(
            '[package]\nname = "sub"\nversion = "0.1.0"\n', encoding="utf-8")
        result = _run_cli(["add", "hello"], cwd=consumer)
        assert result.returncode == 1
        assert "publish failed" in result.stderr or "add failed" in result.stderr

    def test_registry_section_in_manifest_is_honoured(self, project, registry_dir,
                                                      tmp_path):
        (project / "lateralus.toml").write_text(
            MANIFEST_TOML + f'\n[registry]\npath = "{registry_dir.as_posix()}"\n',
            encoding="utf-8")
        result = _run_cli(["publish"], cwd=project)
        assert result.returncode == 0, result.stderr
        assert (registry_dir / INDEX_FILE).exists()
