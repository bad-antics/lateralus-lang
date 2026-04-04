"""
tests/test_v17_features.py  —  LATERALUS v1.7 Package Manager & Build System
═════════════════════════════════════════════════════════════════════════════
"""
import json
import os
import shutil
import tempfile
import textwrap
from pathlib import Path

import pytest

# ─── Package manager imports ──────────────────────────────────────────
from lateralus_lang.package_manager import (
    parse_toml,
    write_toml,
    SemVer,
    Dependency,
    BuildProfile,
    Workspace,
    CfgContext,
    ProjectManifest,
    LockFile,
    LockEntry,
    DepGraph,
    DependencyCycle,
    DependencyResolver,
    PackageBundle,
    scaffold_project,
    MANIFEST_FILE,
    DEFAULT_PROFILES,
)
from lateralus_lang.ast_nodes import CfgAttr, CfgExpr
from lateralus_lang.compiler import Compiler, Target


# ═══════════════════════════════════════════════════════════════════════
# TOML Parser
# ═══════════════════════════════════════════════════════════════════════

class TestTOMLParser:
    """Test the lightweight TOML parser."""

    def test_basic_strings(self):
        data = parse_toml('name = "hello"\nversion = "1.0.0"')
        assert data["name"] == "hello"
        assert data["version"] == "1.0.0"

    def test_integers(self):
        data = parse_toml("x = 42\ny = -7")
        assert data["x"] == 42
        assert data["y"] == -7

    def test_floats(self):
        data = parse_toml("pi = 3.14\nneg = -2.5")
        assert data["pi"] == 3.14
        assert data["neg"] == -2.5

    def test_booleans(self):
        data = parse_toml("debug = true\nstrip = false")
        assert data["debug"] is True
        assert data["strip"] is False

    def test_arrays(self):
        data = parse_toml('features = ["async", "crypto", "web"]')
        assert data["features"] == ["async", "crypto", "web"]

    def test_empty_array(self):
        data = parse_toml("items = []")
        assert data["items"] == []

    def test_table_section(self):
        data = parse_toml("[package]\nname = \"test\"\nversion = \"0.1.0\"")
        assert data["package"]["name"] == "test"
        assert data["package"]["version"] == "0.1.0"

    def test_nested_tables(self):
        data = parse_toml("[profile.debug]\nopt_level = 0\ndebug = true")
        assert data["profile"]["debug"]["opt_level"] == 0
        assert data["profile"]["debug"]["debug"] is True

    def test_inline_table(self):
        data = parse_toml('math = { version = "^1.0", path = "../math" }')
        assert data["math"]["version"] == "^1.0"
        assert data["math"]["path"] == "../math"

    def test_comments(self):
        data = parse_toml("# This is a comment\nname = \"test\" # inline")
        assert data["name"] == "test"

    def test_multiline_array(self):
        toml_str = textwrap.dedent("""\
            members = [
                "packages/core",
                "packages/cli",
            ]
        """)
        data = parse_toml(toml_str)
        assert data["members"] == ["packages/core", "packages/cli"]

    def test_full_manifest(self):
        toml_str = textwrap.dedent("""\
            [package]
            name = "my-project"
            version = "1.0.0"
            description = "A test project"
            license = "MIT"
            main = "src/main.ltl"

            [dependencies]
            stdlib = "^1.0"
            math = { version = "^2.0", path = "../math" }

            [dev-dependencies]
            test_utils = "^1.0"

            [profile.debug]
            opt-level = 0
            debug = true
            strip = false

            [profile.release]
            opt-level = 3
            debug = false
            strip = true
            lto = true

            [workspace]
            members = ["packages/*"]

            [cfg]
            features = ["async", "crypto"]

            [scripts]
            start = "lateralus run src/main.ltl"
            test = "lateralus test tests/"
        """)
        data = parse_toml(toml_str)
        assert data["package"]["name"] == "my-project"
        assert data["dependencies"]["stdlib"] == "^1.0"
        assert data["dependencies"]["math"]["version"] == "^2.0"
        assert data["profile"]["release"]["lto"] is True
        assert data["workspace"]["members"] == ["packages/*"]
        assert data["cfg"]["features"] == ["async", "crypto"]

    def test_write_toml_roundtrip(self):
        data = {"name": "test", "version": "1.0.0", "debug": True}
        text = write_toml(data)
        assert 'name = "test"' in text
        assert 'version = "1.0.0"' in text
        assert "debug = true" in text


# ═══════════════════════════════════════════════════════════════════════
# SemVer
# ═══════════════════════════════════════════════════════════════════════

class TestSemVer:
    """Test semantic versioning."""

    def test_parse(self):
        v = SemVer.parse("1.2.3")
        assert (v.major, v.minor, v.patch) == (1, 2, 3)

    def test_parse_with_v_prefix(self):
        v = SemVer.parse("v2.0.1")
        assert (v.major, v.minor, v.patch) == (2, 0, 1)

    def test_parse_prerelease(self):
        v = SemVer.parse("1.0.0-beta")
        assert v.prerelease == "beta"

    def test_compare_lt(self):
        assert SemVer.parse("1.0.0") < SemVer.parse("2.0.0")
        assert SemVer.parse("1.0.0") < SemVer.parse("1.1.0")
        assert SemVer.parse("1.0.0") < SemVer.parse("1.0.1")

    def test_compare_gt(self):
        assert SemVer.parse("2.0.0") > SemVer.parse("1.0.0")
        assert SemVer.parse("1.1.0") > SemVer.parse("1.0.0")

    def test_compare_eq(self):
        assert SemVer.parse("1.2.3") == SemVer.parse("1.2.3")

    def test_compatible_caret(self):
        v = SemVer.parse("1.5.3")
        assert v.compatible_with("^1.0.0")
        assert v.compatible_with("^1.5.0")
        assert not v.compatible_with("^2.0.0")
        assert not v.compatible_with("^1.6.0")

    def test_compatible_tilde(self):
        v = SemVer.parse("1.2.5")
        assert v.compatible_with("~1.2.0")
        assert v.compatible_with("~1.2.3")
        assert not v.compatible_with("~1.3.0")

    def test_compatible_range(self):
        v = SemVer.parse("1.5.0")
        assert v.compatible_with(">=1.0.0")
        assert v.compatible_with("<=2.0.0")
        assert v.compatible_with(">1.0.0")
        assert v.compatible_with("<2.0.0")
        assert not v.compatible_with(">2.0.0")

    def test_compatible_star(self):
        assert SemVer.parse("99.0.0").compatible_with("*")

    def test_compatible_exact(self):
        assert SemVer.parse("1.2.3").compatible_with("1.2.3")
        assert not SemVer.parse("1.2.4").compatible_with("1.2.3")

    def test_compound_constraint(self):
        v = SemVer.parse("1.5.0")
        assert v.compatible_with(">=1.0.0, <2.0.0")
        assert not v.compatible_with(">=1.0.0, <1.4.0")

    def test_next_versions(self):
        v = SemVer.parse("1.2.3")
        assert str(v.next_major()) == "2.0.0"
        assert str(v.next_minor()) == "1.3.0"
        assert str(v.next_patch()) == "1.2.4"

    def test_hash(self):
        a = SemVer.parse("1.0.0")
        b = SemVer.parse("1.0.0")
        assert hash(a) == hash(b)
        assert {a, b} == {a}


# ═══════════════════════════════════════════════════════════════════════
# BuildProfile
# ═══════════════════════════════════════════════════════════════════════

class TestBuildProfile:
    """Test build profiles."""

    def test_default_profiles(self):
        assert "debug" in DEFAULT_PROFILES
        assert "release" in DEFAULT_PROFILES
        assert "bench" in DEFAULT_PROFILES

    def test_debug_profile(self):
        p = DEFAULT_PROFILES["debug"]
        assert p.opt_level == 0
        assert p.debug is True
        assert p.strip is False

    def test_release_profile(self):
        p = DEFAULT_PROFILES["release"]
        assert p.opt_level == 3
        assert p.debug is False
        assert p.strip is True
        assert p.lto is True

    def test_bench_profile(self):
        p = DEFAULT_PROFILES["bench"]
        assert "bench" in p.features

    def test_custom_profile(self):
        p = BuildProfile(
            name="custom",
            opt_level=2,
            debug=True,
            strip=False,
            features=["profiling"],
        )
        assert p.name == "custom"
        assert p.opt_level == 2
        assert p.features == ["profiling"]


# ═══════════════════════════════════════════════════════════════════════
# Workspace
# ═══════════════════════════════════════════════════════════════════════

class TestWorkspace:
    """Test workspace support."""

    def test_workspace_creation(self):
        ws = Workspace(
            members=["packages/*"],
            exclude=["packages/internal"],
        )
        assert ws.members == ["packages/*"]
        assert ws.exclude == ["packages/internal"]

    def test_resolve_members(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create package dirs with manifests
            for name in ["core", "cli", "web"]:
                pkg = root / "packages" / name
                pkg.mkdir(parents=True)
                (pkg / MANIFEST_FILE).write_text(
                    f'[package]\nname = "{name}"\nversion = "0.1.0"\n'
                )
            # Also create one without a manifest (should be excluded)
            (root / "packages" / "tmp").mkdir(parents=True)

            ws = Workspace(members=["packages/*"])
            members = ws.resolve_members(root)
            assert len(members) == 3
            names = {m.name for m in members}
            assert "core" in names
            assert "cli" in names
            assert "web" in names
            assert "tmp" not in names


# ═══════════════════════════════════════════════════════════════════════
# CfgContext
# ═══════════════════════════════════════════════════════════════════════

class TestCfgContext:
    """Test conditional compilation context."""

    def test_target_match(self):
        ctx = CfgContext(target="python")
        assert ctx.evaluate("target", "python")
        assert not ctx.evaluate("target", "c")

    def test_os_match(self):
        ctx = CfgContext(os="linux")
        assert ctx.evaluate("os", "linux")
        assert not ctx.evaluate("os", "windows")

    def test_profile_match(self):
        ctx = CfgContext(profile="release")
        assert ctx.evaluate("profile", "release")
        assert not ctx.evaluate("profile", "debug")

    def test_feature_match(self):
        ctx = CfgContext(features={"async", "crypto"})
        assert ctx.evaluate("feature", "async")
        assert ctx.evaluate("feature", "crypto")
        assert not ctx.evaluate("feature", "web")

    def test_not_target(self):
        ctx = CfgContext(target="python")
        assert ctx.evaluate("not_target", "c")
        assert not ctx.evaluate("not_target", "python")

    def test_not_feature(self):
        ctx = CfgContext(features={"async"})
        assert ctx.evaluate("not_feature", "web")
        assert not ctx.evaluate("not_feature", "async")

    def test_custom_key(self):
        ctx = CfgContext(custom={"arch": "x86_64"})
        assert ctx.evaluate("arch", "x86_64")
        assert not ctx.evaluate("arch", "arm64")


# ═══════════════════════════════════════════════════════════════════════
# DepGraph
# ═══════════════════════════════════════════════════════════════════════

class TestDepGraph:
    """Test dependency graph."""

    def test_add_nodes(self):
        g = DepGraph()
        g.add_node("a")
        g.add_node("b")
        assert "a" in g.nodes
        assert "b" in g.nodes

    def test_add_edges(self):
        g = DepGraph()
        g.add_edge("app", "core")
        g.add_edge("app", "utils")
        assert "core" in g.edges["app"]
        assert "utils" in g.edges["app"]

    def test_topological_sort_simple(self):
        g = DepGraph()
        g.add_edge("app", "core")
        g.add_edge("core", "utils")
        order = g.topological_sort()
        # utils should come before core, core before app
        assert order.index("utils") < order.index("core")
        assert order.index("core") < order.index("app")

    def test_topological_sort_diamond(self):
        g = DepGraph()
        g.add_edge("app", "left")
        g.add_edge("app", "right")
        g.add_edge("left", "base")
        g.add_edge("right", "base")
        order = g.topological_sort()
        assert order.index("base") < order.index("left")
        assert order.index("base") < order.index("right")
        assert order.index("left") < order.index("app")

    def test_cycle_detection(self):
        g = DepGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "a")
        cycles = g.detect_cycles()
        assert len(cycles) >= 1

    def test_topological_sort_cycle_raises(self):
        g = DepGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        with pytest.raises(DependencyCycle):
            g.topological_sort()

    def test_no_cycles(self):
        g = DepGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        cycles = g.detect_cycles()
        assert len(cycles) == 0


# ═══════════════════════════════════════════════════════════════════════
# ProjectManifest
# ═══════════════════════════════════════════════════════════════════════

class TestProjectManifest:
    """Test project manifest loading and saving."""

    def test_from_toml(self):
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="w",
                                         delete=False) as f:
            f.write(textwrap.dedent("""\
                [package]
                name = "test-pkg"
                version = "1.2.3"
                description = "A test"

                [dependencies]
                stdlib = "^1.0"

                [profile.release]
                opt-level = 3
                debug = false
                strip = true
            """))
            f.flush()
            manifest = ProjectManifest.from_toml(Path(f.name))
        os.unlink(f.name)

        assert manifest.name == "test-pkg"
        assert manifest.version == "1.2.3"
        assert "stdlib" in manifest.dependencies
        assert manifest.dependencies["stdlib"].version == "^1.0"
        assert "release" in manifest.profiles

    def test_from_json_legacy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                         delete=False) as f:
            json.dump({
                "name": "legacy-pkg",
                "version": "0.5.0",
                "dependencies": {"math": "^1.0"},
            }, f)
            f.flush()
            manifest = ProjectManifest.from_json(Path(f.name))
        os.unlink(f.name)

        assert manifest.name == "legacy-pkg"
        assert "math" in manifest.dependencies

    def test_to_toml(self):
        manifest = ProjectManifest(
            name="my-pkg",
            version="2.0.0",
            description="Test",
            dependencies={
                "core": Dependency(name="core", version="^1.0"),
            },
        )
        toml_str = manifest.to_toml()
        assert 'name = "my-pkg"' in toml_str
        assert 'version = "2.0.0"' in toml_str
        assert '[dependencies]' in toml_str
        assert 'core = "^1.0"' in toml_str

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / MANIFEST_FILE
            manifest = ProjectManifest(
                name="roundtrip",
                version="3.0.0",
                dependencies={
                    "stdlib": Dependency(name="stdlib", version="^1.0"),
                },
                cfg_features=["async"],
            )
            manifest.save(path)

            loaded = ProjectManifest.from_file(path)
            assert loaded.name == "roundtrip"
            assert loaded.version == "3.0.0"
            assert "stdlib" in loaded.dependencies
            assert "async" in loaded.cfg_features

    def test_workspace_in_manifest(self):
        toml_str = textwrap.dedent("""\
            [package]
            name = "mono"
            version = "1.0.0"

            [workspace]
            members = ["packages/*"]
            exclude = ["packages/internal"]
        """)
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="w",
                                         delete=False) as f:
            f.write(toml_str)
            f.flush()
            manifest = ProjectManifest.from_toml(Path(f.name))
        os.unlink(f.name)

        assert manifest.workspace is not None
        assert manifest.workspace.members == ["packages/*"]
        assert manifest.workspace.exclude == ["packages/internal"]

    def test_profiles_in_manifest(self):
        toml_str = textwrap.dedent("""\
            [package]
            name = "profiled"
            version = "1.0.0"

            [profile.release]
            opt-level = 3
            debug = false
            strip = true
            lto = true
            features = ["optimize"]
        """)
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="w",
                                         delete=False) as f:
            f.write(toml_str)
            f.flush()
            manifest = ProjectManifest.from_toml(Path(f.name))
        os.unlink(f.name)

        p = manifest.profiles["release"]
        assert p.opt_level == 3
        assert p.debug is False
        assert p.strip is True
        assert p.lto is True
        assert "optimize" in p.features


# ═══════════════════════════════════════════════════════════════════════
# Project Scaffolding
# ═══════════════════════════════════════════════════════════════════════

class TestScaffold:
    """Test project scaffolding."""

    def test_scaffold_creates_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = scaffold_project("test-project", Path(tmpdir))
            assert project.exists()
            assert (project / "src" / "main.ltl").exists()
            assert (project / "tests" / "test_main.ltl").exists()
            assert (project / MANIFEST_FILE).exists()
            assert (project / "README.md").exists()
            assert (project / ".gitignore").exists()

    def test_scaffold_manifest_is_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = scaffold_project("valid-proj", Path(tmpdir))
            manifest = ProjectManifest.from_file(project / MANIFEST_FILE)
            assert manifest.name == "valid-proj"
            assert manifest.version == "0.1.0"
            assert "start" in manifest.scripts

    def test_scaffold_main_compiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = scaffold_project("compilable", Path(tmpdir))
            src = (project / "src" / "main.ltl").read_text()
            result = Compiler().compile_source(src, target=Target.PYTHON,
                                                filename="main.ltl")
            assert result.ok, f"Scaffold main.ltl should compile: {result.errors}"


# ═══════════════════════════════════════════════════════════════════════
# DependencyResolver
# ═══════════════════════════════════════════════════════════════════════

class TestDependencyResolver:
    """Test dependency resolution."""

    def test_resolve_local_dep(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create a local dep
            dep_dir = root / "libs" / "mylib"
            dep_dir.mkdir(parents=True)
            (dep_dir / "lib.ltl").write_text("fn greet() { println(\"hi\") }")

            manifest = ProjectManifest(
                name="app",
                dependencies={
                    "mylib": Dependency(name="mylib", version="*",
                                        path="libs/mylib"),
                },
            )

            resolver = DependencyResolver(root)
            lock = resolver.resolve(manifest)
            assert "mylib" in lock.entries
            assert lock.entries["mylib"].integrity.startswith("sha256-")

    def test_resolve_git_dep(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = ProjectManifest(
                name="app",
                dependencies={
                    "remote": Dependency(
                        name="remote", version="^1.0",
                        git="https://github.com/user/repo.git",
                    ),
                },
            )
            resolver = DependencyResolver(Path(tmpdir))
            lock = resolver.resolve(manifest)
            assert "remote" in lock.entries
            assert "github.com" in lock.entries["remote"].resolved


# ═══════════════════════════════════════════════════════════════════════
# PackageBundle
# ═══════════════════════════════════════════════════════════════════════

class TestPackageBundle:
    """Test package publishing bundle."""

    def test_create_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = scaffold_project("bundle-test", Path(tmpdir))
            manifest = ProjectManifest.from_file(project / MANIFEST_FILE)
            bundle = PackageBundle.create(project, manifest)
            assert bundle.name == "bundle-test"
            assert bundle.version == "0.1.0"
            assert bundle.integrity.startswith("sha256-")
            assert bundle.size > 0
            assert len(bundle.files) > 0


# ═══════════════════════════════════════════════════════════════════════
# LockFile
# ═══════════════════════════════════════════════════════════════════════

class TestLockFile:
    """Test lock file creation and loading."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "lateralus-lock.json"
            lock = LockFile(entries={
                "core": LockEntry(
                    name="core",
                    version="1.0.0",
                    resolved="/path/to/core",
                    integrity="sha256-abc123",
                ),
            })
            lock.save(path)
            loaded = LockFile.from_file(path)
            assert "core" in loaded.entries
            assert loaded.entries["core"].version == "1.0.0"
            assert loaded.entries["core"].integrity == "sha256-abc123"


# ═══════════════════════════════════════════════════════════════════════
# Conditional Compilation — Parser
# ═══════════════════════════════════════════════════════════════════════

class TestCfgParser:
    """Test cfg!() expression parsing."""

    def test_cfg_expr_parses(self):
        src = 'let is_python = cfg!(target, "python")'
        result = Compiler().compile_source(src, target=Target.PYTHON,
                                            filename="test.ltl")
        assert result.ok, f"cfg!() should parse: {[e.message for e in result.errors]}"

    def test_cfg_expr_in_if(self):
        src = textwrap.dedent('''\
            if cfg!(target, "python") {
                println("Running on Python")
            }
        ''')
        result = Compiler().compile_source(src, target=Target.PYTHON,
                                            filename="test.ltl")
        assert result.ok, f"cfg!() in if should parse: {[e.message for e in result.errors]}"

    def test_cfg_decorator_parses(self):
        src = textwrap.dedent('''\
            @cfg(target, "python")
            fn python_only() {
                println("Python target")
            }
        ''')
        result = Compiler().compile_source(src, target=Target.PYTHON,
                                            filename="test.ltl")
        assert result.ok, f"@cfg should parse: {[e.message for e in result.errors]}"


# ═══════════════════════════════════════════════════════════════════════
# Conditional Compilation — Codegen
# ═══════════════════════════════════════════════════════════════════════

class TestCfgCodegen:
    """Test @cfg conditional compilation in code generation."""

    def test_cfg_expr_generates_true(self):
        src = 'let x = cfg!(target, "python")'
        result = Compiler().compile_source(src, target=Target.PYTHON,
                                            filename="test.ltl")
        assert result.ok
        assert "True" in result.python_src or "true" in result.python_src.lower()

    def test_cfg_decorator_included(self):
        src = textwrap.dedent('''\
            @cfg(target, "python")
            fn py_func() {
                return 42
            }
        ''')
        result = Compiler().compile_source(src, target=Target.PYTHON,
                                            filename="test.ltl")
        assert result.ok
        # Without a cfg context set, all functions should be included
        assert "py_func" in result.python_src


# ═══════════════════════════════════════════════════════════════════════
# AST Nodes
# ═══════════════════════════════════════════════════════════════════════

class TestCfgASTNodes:
    """Test v1.7 AST nodes."""

    def test_cfg_attr(self):
        attr = CfgAttr(span=None, key="target", value="python")
        assert attr.key == "target"
        assert attr.value == "python"

    def test_cfg_expr_node(self):
        expr = CfgExpr(span=None, key="feature", value="async")
        assert expr.key == "feature"
        assert expr.value == "async"


# ═══════════════════════════════════════════════════════════════════════
# Version
# ═══════════════════════════════════════════════════════════════════════

class TestVersion:
    """Verify version bump."""

    def test_version_is_1_7_0(self):
        from lateralus_lang import __version__
        assert __version__ == "2.5.1"


# ═══════════════════════════════════════════════════════════════════════
# Integration: Full v1.7 Showcase Compiles
# ═══════════════════════════════════════════════════════════════════════

class TestV17Integration:
    """Integration tests for v1.7 features."""

    def test_v17_showcase_compiles(self):
        showcase = Path(__file__).parent.parent / "examples" / "v17_showcase.ltl"
        if showcase.exists():
            src = showcase.read_text(encoding="utf-8")
            result = Compiler().compile_source(src, target=Target.PYTHON,
                                                filename="v17_showcase.ltl")
            assert result.ok, f"v17 showcase should compile: {[e.message for e in result.errors[:3]]}"

    def test_all_examples_compile(self):
        """Verify all examples still compile after v1.7 changes."""
        examples_dir = Path(__file__).parent.parent / "examples"
        compiler = Compiler()
        failed = []
        for f in sorted(examples_dir.glob("*.ltl")):
            try:
                src = f.read_text(encoding="utf-8")
                target = Target.C if "c_backend" in f.name else Target.PYTHON
                result = compiler.compile_source(src, target=target,
                                                  filename=f.name)
                if not result.ok:
                    failed.append(f"{f.name}: {result.errors[0].message if result.errors else '?'}")
            except Exception as exc:
                failed.append(f"{f.name}: EXCEPTION: {exc}")
        assert not failed, f"Examples failed:\n" + "\n".join(failed)
