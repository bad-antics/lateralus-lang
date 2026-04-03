"""
Tests for the LATERALUS package manager.
"""
import json
import pytest
from pathlib import Path

from lateralus_lang.package_manager import (
    ProjectManifest, Dependency, LockFile, LockEntry,
    SemVer, scaffold_project, DependencyResolver,
    MANIFEST_FILE,
)


class TestSemVer:
    def test_parse_simple(self):
        v = SemVer.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_with_v(self):
        v = SemVer.parse("v2.0.0")
        assert v.major == 2

    def test_parse_prerelease(self):
        v = SemVer.parse("1.0.0-beta")
        assert v.prerelease == "beta"

    def test_parse_partial(self):
        v = SemVer.parse("1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0

    def test_comparison(self):
        assert SemVer.parse("1.0.0") < SemVer.parse("2.0.0")
        assert SemVer.parse("1.0.0") < SemVer.parse("1.1.0")
        assert SemVer.parse("1.0.0") < SemVer.parse("1.0.1")
        assert SemVer.parse("1.0.0") == SemVer.parse("1.0.0")

    def test_compatible_caret(self):
        v = SemVer.parse("1.5.3")
        assert v.compatible_with("^1.0.0")
        assert v.compatible_with("^1.5.0")
        assert not v.compatible_with("^2.0.0")

    def test_compatible_tilde(self):
        v = SemVer.parse("1.2.5")
        assert v.compatible_with("~1.2.0")
        assert v.compatible_with("~1.2.3")
        assert not v.compatible_with("~1.3.0")

    def test_compatible_star(self):
        v = SemVer.parse("99.99.99")
        assert v.compatible_with("*")

    def test_compatible_gte(self):
        v = SemVer.parse("2.0.0")
        assert v.compatible_with(">=1.0.0")
        assert not v.compatible_with(">=3.0.0")

    def test_compatible_exact(self):
        v = SemVer.parse("1.2.3")
        assert v.compatible_with("1.2.3")
        assert not v.compatible_with("1.2.4")

    def test_str(self):
        assert str(SemVer.parse("1.2.3")) == "1.2.3"
        assert str(SemVer.parse("1.0.0-alpha")) == "1.0.0-alpha"


class TestDependency:
    def test_to_dict_simple(self):
        dep = Dependency(name="math-ext", version="^1.0.0")
        d = dep.to_dict()
        assert d["version"] == "^1.0.0"
        assert "path" not in d

    def test_to_dict_with_path(self):
        dep = Dependency(name="local-lib", version="*", path="../lib")
        d = dep.to_dict()
        assert d["path"] == "../lib"

    def test_to_dict_with_git(self):
        dep = Dependency(name="remote", version="^1.0", git="https://example.com/repo")
        d = dep.to_dict()
        assert d["git"] == "https://example.com/repo"


class TestProjectManifest:
    def test_create(self):
        m = ProjectManifest(name="test-project")
        assert m.name == "test-project"
        assert m.version == "0.1.0"
        assert m.license == "MIT"

    def test_to_dict(self):
        m = ProjectManifest(
            name="test",
            version="1.0.0",
            dependencies={"math": Dependency("math", "^1.0.0")},
        )
        d = m.to_dict()
        assert d["name"] == "test"
        assert "math" in d["dependencies"]

    def test_save_and_load(self, tmp_path):
        m = ProjectManifest(
            name="roundtrip",
            version="2.0.0",
            description="Test roundtrip",
            dependencies={"dep-a": Dependency("dep-a", "^1.0.0")},
            scripts={"start": "lateralus run src/main.ltl"},
        )
        filepath = tmp_path / MANIFEST_FILE
        m.save(filepath)

        loaded = ProjectManifest.from_file(filepath)
        assert loaded.name == "roundtrip"
        assert loaded.version == "2.0.0"
        assert "dep-a" in loaded.dependencies
        assert loaded.scripts["start"] == "lateralus run src/main.ltl"


class TestLockFile:
    def test_save_and_load(self, tmp_path):
        lock = LockFile()
        lock.entries["test-dep"] = LockEntry(
            name="test-dep",
            version="1.0.0",
            resolved="/path/to/dep",
            integrity="sha256-abc123",
        )

        filepath = tmp_path / "lateralus-lock.json"
        lock.save(filepath)

        loaded = LockFile.from_file(filepath)
        assert "test-dep" in loaded.entries
        assert loaded.entries["test-dep"].version == "1.0.0"
        assert loaded.entries["test-dep"].integrity == "sha256-abc123"

    def test_empty_load(self, tmp_path):
        filepath = tmp_path / "nonexistent.json"
        lock = LockFile.from_file(filepath)
        assert len(lock.entries) == 0


class TestScaffoldProject:
    def test_scaffold_creates_structure(self, tmp_path):
        project_dir = scaffold_project("my-project", tmp_path)

        assert project_dir.exists()
        assert (project_dir / "src").exists()
        assert (project_dir / "tests").exists()
        assert (project_dir / "docs").exists()
        assert (project_dir / "examples").exists()
        assert (project_dir / MANIFEST_FILE).exists()
        assert (project_dir / "src" / "main.ltl").exists()
        assert (project_dir / "tests" / "test_main.ltl").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / ".gitignore").exists()

    def test_scaffold_manifest_content(self, tmp_path):
        project_dir = scaffold_project("test-proj", tmp_path)
        manifest = ProjectManifest.from_file(project_dir / MANIFEST_FILE)
        assert manifest.name == "test-proj"
        assert manifest.version == "0.1.0"
        assert "start" in manifest.scripts

    def test_scaffold_main_content(self, tmp_path):
        project_dir = scaffold_project("hello", tmp_path)
        main_content = (project_dir / "src" / "main.ltl").read_text()
        assert "hello" in main_content
        assert "fn main()" in main_content
        assert "|>" in main_content


class TestDependencyResolver:
    def test_resolve_local_dep(self, tmp_path):
        # Create a local dependency
        dep_dir = tmp_path / "libs" / "my-lib"
        dep_dir.mkdir(parents=True)
        (dep_dir / "lib.ltl").write_text("fn helper() { return 42 }")

        manifest = ProjectManifest(
            name="test",
            dependencies={
                "my-lib": Dependency("my-lib", "*", path="libs/my-lib"),
            },
        )

        resolver = DependencyResolver(tmp_path)
        lock = resolver.resolve(manifest)
        assert "my-lib" in lock.entries

    def test_install_creates_modules_dir(self, tmp_path):
        lock = LockFile()
        resolver = DependencyResolver(tmp_path)
        resolver.install(lock)
        assert (tmp_path / "ltl_modules").exists()
