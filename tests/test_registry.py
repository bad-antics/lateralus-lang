"""
Tests for the LATERALUS static package registry (package-registry-mvp bounty).

Covers the full publish → add → integrity-verify round-trip plus determinism,
tamper detection, version resolution, and safe extraction.
"""

import hashlib
import io
import json
import tarfile

import pytest

from lateralus_lang.package_manager import MANIFEST_FILE, ProjectManifest
from lateralus_lang.registry import (
    REGISTRY_INDEX,
    RegistryError,
    add,
    build_tarball,
    empty_index,
    load_index,
    publish,
    resolve_version,
    sha256_bytes,
    unpack_tarball,
    verify_integrity,
)

# ── Helpers ──────────────────────────────────────────────────────────────

def _make_project(root, name="demo-pkg", version="1.2.0"):
    """Scaffold a minimal but realistic LATERALUS project on disk."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "src" / "main.ltl").write_text(
        f'// {name}\nfn greet() {{ return "hi from {name}" }}\n'
    )
    (root / "src" / "util.ltl").write_text("fn helper() { return 42 }\n")
    (root / "tests" / "test_main.ltl").write_text(
        "@test\nfn t() { assert_eq(1 + 1, 2) }\n"
    )
    (root / "README.md").write_text(f"# {name}\n\nA demo package.\n")
    manifest = ProjectManifest(
        name=name,
        version=version,
        description="demo",
        dependencies={},
    )
    manifest.save(root / MANIFEST_FILE)
    return manifest


# ── Integrity primitives ─────────────────────────────────────────────────

class TestIntegrity:
    def test_sha256_bytes(self):
        assert sha256_bytes(b"") == (
            "sha256-" + hashlib.sha256(b"").hexdigest()
        )

    def test_verify_integrity_ok(self):
        data = b"hello world"
        digest = sha256_bytes(data)
        assert verify_integrity(data, digest) is True

    def test_verify_integrity_mismatch(self):
        data = b"hello world"
        digest = sha256_bytes(b"different")
        assert verify_integrity(data, digest) is False

    def test_verify_integrity_bad_algo(self):
        with pytest.raises(RegistryError):
            verify_integrity(b"x", "md5-deadbeef")


# ── Deterministic tarball packing ────────────────────────────────────────

class TestBuildTarball:
    def test_build_produces_tarball(self, tmp_path):
        _make_project(tmp_path)
        manifest = ProjectManifest.from_file(tmp_path / MANIFEST_FILE)
        tarball, integrity, size, files = build_tarball(
            tmp_path, manifest, tmp_path / "out"
        )
        assert tarball.exists()
        assert tarball.name == "demo-pkg-1.2.0.tar.gz"
        assert integrity.startswith("sha256-")
        assert size > 0
        assert "src/main.ltl" in files
        assert MANIFEST_FILE in files

    def test_build_is_deterministic(self, tmp_path):
        _make_project(tmp_path)
        manifest = ProjectManifest.from_file(tmp_path / MANIFEST_FILE)
        t1, i1, _, _ = build_tarball(tmp_path, manifest, tmp_path / "o1")
        t2, i2, _, _ = build_tarball(tmp_path, manifest, tmp_path / "o2")
        # Same inputs → byte-identical tarball → identical digest.
        assert t1.read_bytes() == t2.read_bytes()
        assert i1 == i2

    def test_tarball_contains_expected_members(self, tmp_path):
        _make_project(tmp_path)
        manifest = ProjectManifest.from_file(tmp_path / MANIFEST_FILE)
        tarball, _, _, _ = build_tarball(tmp_path, manifest, tmp_path / "out")
        with tarfile.open(tarball, "r:gz") as tar:
            names = tar.getnames()
        assert "src/main.ltl" in names
        assert "src/util.ltl" in names
        assert "tests/test_main.ltl" in names
        assert MANIFEST_FILE in names

    def test_empty_project_rejected(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        manifest = ProjectManifest(name="empty", version="0.1.0")
        with pytest.raises(RegistryError):
            build_tarball(empty, manifest, tmp_path / "out")

    def test_invalid_name_rejected(self, tmp_path):
        _make_project(tmp_path)
        manifest = ProjectManifest(name="Bad Name!", version="1.0.0")
        with pytest.raises(RegistryError):
            build_tarball(tmp_path, manifest, tmp_path / "out")


# ── index.json ───────────────────────────────────────────────────────────

class TestIndex:
    def test_empty_index(self):
        idx = empty_index()
        assert idx["registry_version"] == 1
        assert idx["packages"] == {}

    def test_save_and_load(self, tmp_path):
        idx = empty_index()
        idx["packages"]["foo"] = {"versions": {"1.0.0": {"integrity": "sha256-x"}}}
        path = tmp_path / REGISTRY_INDEX
        from lateralus_lang.registry import save_index
        save_index(idx, path)
        loaded = load_index(path)
        assert "foo" in loaded["packages"]
        assert loaded["packages"]["foo"]["versions"]["1.0.0"]["integrity"] == "sha256-x"

    def test_load_missing_returns_empty(self, tmp_path):
        idx = load_index(tmp_path / "nope.json")
        assert idx["packages"] == {}


# ── Version resolution ───────────────────────────────────────────────────

class TestResolveVersion:
    def _index(self):
        return {
            "registry_version": 1,
            "packages": {
                "pkg": {
                    "versions": {
                        "1.0.0": {"integrity": "sha256-a"},
                        "1.2.0": {"integrity": "sha256-b"},
                        "1.5.0": {"integrity": "sha256-c"},
                        "2.0.0": {"integrity": "sha256-d"},
                    }
                }
            },
        }

    def test_star_picks_highest(self):
        ver, rec = resolve_version(self._index(), "pkg", "*")
        assert ver == "2.0.0"

    def test_caret_stays_in_major(self):
        ver, _ = resolve_version(self._index(), "pkg", "^1.0.0")
        assert ver == "1.5.0"

    def test_tilde_stays_in_minor(self):
        ver, _ = resolve_version(self._index(), "pkg", "~1.2.0")
        assert ver == "1.2.0"

    def test_exact(self):
        ver, _ = resolve_version(self._index(), "pkg", "1.0.0")
        assert ver == "1.0.0"

    def test_missing_package(self):
        with pytest.raises(RegistryError):
            resolve_version(self._index(), "absent", "*")

    def test_no_matching_version(self):
        with pytest.raises(RegistryError):
            resolve_version(self._index(), "pkg", "^3.0.0")


# ── Safe extraction ──────────────────────────────────────────────────────

class TestUnpack:
    def test_unpack_roundtrip(self, tmp_path):
        _make_project(tmp_path)
        manifest = ProjectManifest.from_file(tmp_path / MANIFEST_FILE)
        tarball, _, _, _ = build_tarball(tmp_path, manifest, tmp_path / "out")
        dest = tmp_path / "vendor" / "demo-pkg"
        written = unpack_tarball(tarball.read_bytes(), dest)
        assert (dest / "src" / "main.ltl").exists()
        assert "src/main.ltl" in written

    def test_rejects_path_traversal(self, tmp_path):
        # Craft a malicious tarball with a ../ entry.
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="../evil.ltl")
            payload = b"pwned"
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        dest = tmp_path / "vendor" / "evil"
        with pytest.raises(RegistryError):
            unpack_tarball(buf.getvalue(), dest)


# ── End-to-end: publish → add → integrity-verify ─────────────────────────

class TestPublishAddRoundTrip:
    def test_full_roundtrip(self, tmp_path):
        # 1. Create a project and publish it to a local static registry.
        project = tmp_path / "proj"
        project.mkdir()
        _make_project(project, name="math-ext", version="1.2.0")
        registry_root = tmp_path / "registry"

        summary = publish(project, registry_url=str(registry_root))
        assert summary["uploaded"] is True
        assert summary["name"] == "math-ext"
        assert summary["version"] == "1.2.0"

        # Registry layout: index.json + packages/<name>/<name>-<ver>.tar.gz
        assert (registry_root / REGISTRY_INDEX).exists()
        tarball = registry_root / "packages" / "math-ext" / "math-ext-1.2.0.tar.gz"
        assert tarball.exists()

        # index.json records the correct integrity.
        idx = load_index(registry_root / REGISTRY_INDEX)
        record = idx["packages"]["math-ext"]["versions"]["1.2.0"]
        assert record["integrity"] == summary["integrity"]
        assert record["integrity"] == sha256_bytes(tarball.read_bytes())

        # 2. Consume it into a separate workspace's vendor/ directory.
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / MANIFEST_FILE).write_text(
            '[package]\nname = "app"\nversion = "0.1.0"\n'
        )
        result = add("math-ext", registry_url=str(registry_root),
                     workspace_dir=workspace)
        assert result["name"] == "math-ext"
        assert result["version"] == "1.2.0"
        assert result["integrity"] == summary["integrity"]

        # Files landed in vendor/math-ext/.
        vendored = workspace / "vendor" / "math-ext" / "src" / "main.ltl"
        assert vendored.exists()
        assert "math-ext" in vendored.read_text()

        # Lock file pins the version + integrity for reproducibility.
        lock = json.loads((workspace / "lateralus-lock.json").read_text())
        assert lock["entries"]["math-ext"]["version"] == "1.2.0"
        assert lock["entries"]["math-ext"]["integrity"] == summary["integrity"]

    def test_add_detects_tampering(self, tmp_path):
        # Publish, then corrupt the tarball on disk; add must reject it.
        project = tmp_path / "proj"
        project.mkdir()
        _make_project(project, name="tamper-pkg", version="1.0.0")
        registry_root = tmp_path / "registry"
        publish(project, registry_url=str(registry_root))

        tarball = registry_root / "packages" / "tamper-pkg" / "tamper-pkg-1.0.0.tar.gz"
        # Flip some bytes while keeping it a readable-ish file.
        data = bytearray(tarball.read_bytes())
        data[-5] ^= 0xFF
        tarball.write_bytes(bytes(data))

        workspace = tmp_path / "ws"
        workspace.mkdir()
        with pytest.raises(RegistryError):
            add("tamper-pkg", registry_url=str(registry_root),
                workspace_dir=workspace)

    def test_add_missing_package(self, tmp_path):
        registry_root = tmp_path / "registry"
        registry_root.mkdir()
        from lateralus_lang.registry import save_index
        save_index(empty_index(), registry_root / REGISTRY_INDEX)
        workspace = tmp_path / "ws"
        workspace.mkdir()
        with pytest.raises(RegistryError):
            add("ghost", registry_url=str(registry_root), workspace_dir=workspace)

    def test_publish_dry_run_writes_nothing(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        _make_project(project, name="dry-pkg", version="0.1.0")
        registry_root = tmp_path / "registry"
        summary = publish(project, registry_url=str(registry_root), dry_run=True)
        assert summary["uploaded"] is False
        assert not (registry_root / REGISTRY_INDEX).exists()

    def test_multiple_versions(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        registry_root = tmp_path / "registry"

        _make_project(project, name="multi", version="1.0.0")
        publish(project, registry_url=str(registry_root))
        _make_project(project, name="multi", version="1.1.0")
        publish(project, registry_url=str(registry_root))

        idx = load_index(registry_root / REGISTRY_INDEX)
        versions = idx["packages"]["multi"]["versions"]
        assert set(versions) == {"1.0.0", "1.1.0"}

        # Resolving "*" picks the newest.
        ver, _ = resolve_version(idx, "multi", "*")
        assert ver == "1.1.0"


# ── CLI smoke test ───────────────────────────────────────────────────────

class TestRegistryCLI:
    def test_cli_publish_and_add(self, tmp_path):
        from lateralus_lang.registry import main

        project = tmp_path / "proj"
        project.mkdir()
        _make_project(project, name="cli-pkg", version="2.0.0")
        registry_root = tmp_path / "registry"

        rc = main(["publish", "--dir", str(project),
                   "--registry", str(registry_root)])
        assert rc == 0
        assert (registry_root / REGISTRY_INDEX).exists()

        workspace = tmp_path / "ws"
        workspace.mkdir()
        rc = main(["add", "cli-pkg", "--dir", str(workspace),
                   "--registry", str(registry_root)])
        assert rc == 0
        assert (workspace / "vendor" / "cli-pkg" / "src" / "main.ltl").exists()

    def test_cli_add_missing_returns_error(self, tmp_path):
        from lateralus_lang.registry import main
        registry_root = tmp_path / "registry"
        registry_root.mkdir()
        from lateralus_lang.registry import save_index
        save_index(empty_index(), registry_root / REGISTRY_INDEX)
        workspace = tmp_path / "ws"
        workspace.mkdir()
        rc = main(["add", "ghost", "--dir", str(workspace),
                   "--registry", str(registry_root)])
        assert rc == 1
