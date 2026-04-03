"""
LATERALUS Package Manager — ltlpkg  (v1.7)
Manages dependencies, builds, project scaffolding, workspaces, and build profiles.

Commands:
    ltlpkg init [name]          — Create a new LATERALUS project
    ltlpkg add <package>        — Add a dependency
    ltlpkg remove <package>     — Remove a dependency
    ltlpkg install              — Install all dependencies
    ltlpkg build [--profile X]  — Build the project
    ltlpkg test                 — Run project tests
    ltlpkg publish              — Publish to LATERALUS registry
    ltlpkg run [script]         — Run a project script
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ─── Project Manifest ──────────────────────────────────────────────────

MANIFEST_FILE = "lateralus.toml"
MANIFEST_FILE_JSON = "lateralus.json"       # legacy compat
LOCK_FILE = "lateralus-lock.json"
LTL_MODULES_DIR = "ltl_modules"

DEFAULT_MAIN = "src/main.ltl"
DEFAULT_TEST = "tests/"


# ─── Lightweight TOML Parser ──────────────────────────────────────────

class TOMLError(Exception):
    """TOML parse error."""


def parse_toml(text: str) -> dict:
    """Parse a subset of TOML into a nested dict.

    Supports: strings, integers, floats, booleans, arrays, tables, inline
    tables, multi-line strings.  Enough for lateralus.toml manifests.
    """
    result: dict = {}
    current: dict = result
    current_path: list[str] = []

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        # Skip blank and comment lines
        if not line or line.startswith("#"):
            continue

        # Table header: [section] or [section.sub]
        if line.startswith("["):
            if line.startswith("[["):
                # Array of tables: [[array]]
                key = line.strip("[] \t")
                parts = key.split(".")
                target = result
                for p in parts[:-1]:
                    target = target.setdefault(p, {})
                arr = target.setdefault(parts[-1], [])
                new_table: dict = {}
                arr.append(new_table)
                current = new_table
                current_path = parts
            else:
                key = line.strip("[] \t")
                parts = key.split(".")
                target = result
                for p in parts:
                    target = target.setdefault(p, {})
                current = target
                current_path = parts
            continue

        # Key = value
        eq_idx = line.find("=")
        if eq_idx == -1:
            continue

        key = line[:eq_idx].strip().strip('"\'')
        raw_value = line[eq_idx + 1:].strip()

        # Strip inline comments (not inside strings)
        value = _parse_toml_value(raw_value, lines, i - 1)
        if isinstance(value, tuple):
            # Multi-line consumed extra lines
            value, extra = value
            i += extra
        current[key] = value

    return result


def _parse_toml_value(raw: str, lines: list[str] = None,
                      line_idx: int = 0) -> Any:
    """Parse a single TOML value."""
    raw = raw.strip()

    # Strip trailing comments (not inside strings)
    if raw and raw[0] not in ('"', "'", "[", "{"):
        comment_idx = raw.find("#")
        if comment_idx > 0:
            raw = raw[:comment_idx].strip()
    elif raw and raw[0] in ('"', "'"):
        # String with possible inline comment: "value" # comment
        quote = raw[0]
        # Find the closing quote (skip escaped quotes)
        end_q = 1
        while end_q < len(raw):
            if raw[end_q] == '\\':
                end_q += 2
                continue
            if raw[end_q] == quote:
                # Check for triple-quote (handled below)
                if raw[1:3] == quote * 2:
                    break
                raw = raw[:end_q + 1]
                break
            end_q += 1

    # Multi-line basic string
    if raw.startswith('"""'):
        content = raw[3:]
        extra = 0
        while '"""' not in content and lines and line_idx + extra + 1 < len(lines):
            extra += 1
            content += "\n" + lines[line_idx + extra]
        end = content.find('"""')
        if end >= 0:
            content = content[:end]
        return (content, extra)

    # Basic string
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')

    # Literal string
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]

    # Boolean
    if raw == "true":
        return True
    if raw == "false":
        return False

    # Integer
    if re.match(r'^-?\d+$', raw):
        return int(raw)

    # Float
    if re.match(r'^-?\d+\.\d+$', raw):
        return float(raw)

    # Array
    if raw.startswith("["):
        return _parse_toml_array(raw, lines, line_idx)

    # Inline table
    if raw.startswith("{") and raw.endswith("}"):
        return _parse_toml_inline_table(raw)

    # Bare string (identifier-like)
    return raw


def _parse_toml_array(raw: str, lines: list[str] = None,
                      line_idx: int = 0) -> Any:
    """Parse a TOML array, possibly multi-line."""
    # Accumulate until matching ]
    content = raw
    extra = 0
    bracket_depth = content.count("[") - content.count("]")
    while bracket_depth > 0 and lines and line_idx + extra + 1 < len(lines):
        extra += 1
        next_line = lines[line_idx + extra].strip()
        if next_line.startswith("#"):
            continue
        content += " " + next_line
        bracket_depth = content.count("[") - content.count("]")

    # Strip outer brackets
    inner = content.strip()[1:-1].strip()
    if not inner:
        return ([], extra) if extra else []

    items = []
    for item in _split_toml_items(inner):
        item = item.strip()
        if item:
            v = _parse_toml_value(item)
            if isinstance(v, tuple):
                v = v[0]
            items.append(v)
    return (items, extra) if extra else items


def _parse_toml_inline_table(raw: str) -> dict:
    """Parse { key = val, key2 = val2 }."""
    inner = raw[1:-1].strip()
    if not inner:
        return {}
    result = {}
    for pair in _split_toml_items(inner):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            k = k.strip().strip('"\'')
            v = _parse_toml_value(v.strip())
            if isinstance(v, tuple):
                v = v[0]
            result[k] = v
    return result


def _split_toml_items(s: str) -> list[str]:
    """Split comma-separated items respecting quotes and brackets."""
    items: list[str] = []
    current = ""
    depth = 0
    in_str = False
    quote_char = ""
    for ch in s:
        if in_str:
            current += ch
            if ch == quote_char:
                in_str = False
        elif ch in ('"', "'"):
            in_str = True
            quote_char = ch
            current += ch
        elif ch in ("[", "{"):
            depth += 1
            current += ch
        elif ch in ("]", "}"):
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            items.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        items.append(current)
    return items


def write_toml(data: dict, indent: int = 0) -> str:
    """Serialize a dict to TOML format."""
    lines: list[str] = []
    prefix = "    " * indent

    # Simple key-value pairs first
    for key, value in data.items():
        if isinstance(value, dict):
            continue  # tables handled after
        if isinstance(value, list) and value and isinstance(value[0], dict):
            continue  # array of tables handled after
        lines.append(f"{prefix}{key} = {_toml_value(value)}")

    # Tables
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append("")
            lines.append(f"[{key}]")
            lines.append(write_toml(value))

    # Array of tables
    for key, value in data.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                lines.append("")
                lines.append(f"[[{key}]]")
                lines.append(write_toml(item))

    return "\n".join(lines)


def _toml_value(v: Any) -> str:
    """Serialize a Python value to TOML."""
    if isinstance(v, str):
        return f'"{v}"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    if isinstance(v, list):
        items = ", ".join(_toml_value(i) for i in v)
        return f"[{items}]"
    if isinstance(v, dict):
        items = ", ".join(f'{k} = {_toml_value(val)}' for k, val in v.items())
        return f"{{ {items} }}"
    return str(v)


# ─── Dependency ────────────────────────────────────────────────────────

@dataclass
class Dependency:
    """A package dependency."""
    name: str
    version: str  # semver: "^1.0.0", "~1.2", ">=1.0,<2.0", "*"
    registry: str = "local"  # "local", "git", "registry"
    path: Optional[str] = None  # for local deps
    git: Optional[str] = None  # for git deps

    def to_dict(self) -> dict:
        d = {"version": self.version}
        if self.path:
            d["path"] = self.path
        if self.git:
            d["git"] = self.git
        return d


# ─── Build Profiles ───────────────────────────────────────────────────

@dataclass
class BuildProfile:
    """A build profile (debug/release/bench/custom)."""
    name: str
    opt_level: int = 0          # 0 = none, 1 = basic, 2 = standard, 3 = aggressive
    debug: bool = True          # include debug info
    strip: bool = False         # strip symbols
    lto: bool = False           # link-time optimization
    features: list[str] = field(default_factory=list)
    target: str = "python"      # default compilation target
    extra_flags: dict[str, Any] = field(default_factory=dict)


# Default profiles
DEFAULT_PROFILES = {
    "debug": BuildProfile(
        name="debug", opt_level=0, debug=True, strip=False,
    ),
    "release": BuildProfile(
        name="release", opt_level=3, debug=False, strip=True, lto=True,
    ),
    "bench": BuildProfile(
        name="bench", opt_level=3, debug=False, strip=True,
        features=["bench"],
    ),
}


# ─── Workspace ─────────────────────────────────────────────────────────

@dataclass
class Workspace:
    """A multi-package workspace."""
    members: list[str] = field(default_factory=list)       # glob patterns
    exclude: list[str] = field(default_factory=list)
    shared_dependencies: dict[str, str] = field(default_factory=dict)

    def resolve_members(self, root: Path) -> list[Path]:
        """Expand member globs into actual directories containing manifests."""
        result = []
        for pattern in self.members:
            for p in sorted(root.glob(pattern)):
                if p.is_dir() and (p / MANIFEST_FILE).exists():
                    result.append(p)
                elif p.is_dir() and (p / MANIFEST_FILE_JSON).exists():
                    result.append(p)
        # Filter excludes
        for ex in self.exclude:
            for p in root.glob(ex):
                if p in result:
                    result.remove(p)
        return result


# ─── Cfg (Conditional Compilation) ────────────────────────────────────

@dataclass
class CfgContext:
    """Compile-time configuration context for conditional compilation.

    Evaluates @cfg(key, "value") decorators and cfg!(key, "value") expressions.
    """
    target: str = "python"       # "python", "c", "wasm", "js"
    os: str = ""                 # "linux", "windows", "macos", ""
    profile: str = "debug"       # "debug", "release", "bench"
    features: set[str] = field(default_factory=set)
    custom: dict[str, str] = field(default_factory=dict)

    def evaluate(self, key: str, value: str) -> bool:
        """Check if a @cfg condition is satisfied."""
        if key == "target":
            return self.target == value
        if key == "os":
            return self.os == value
        if key == "profile":
            return self.profile == value
        if key == "feature":
            return value in self.features
        if key == "not_target":
            return self.target != value
        if key == "not_feature":
            return value not in self.features
        return self.custom.get(key, "") == value

    @classmethod
    def from_manifest(cls, manifest: "ProjectManifest",
                      profile: str = "debug",
                      target: str = "python") -> "CfgContext":
        """Create a CfgContext from a project manifest."""
        features = set(manifest.cfg_features)
        # Add profile-specific features
        if profile in manifest.profiles:
            features.update(manifest.profiles[profile].features)
        return cls(
            target=target,
            os=_detect_os(),
            profile=profile,
            features=features,
        )


def _detect_os() -> str:
    """Detect the current operating system."""
    import platform
    name = platform.system().lower()
    if name == "linux":
        return "linux"
    if name == "darwin":
        return "macos"
    if name == "windows":
        return "windows"
    return name


# ─── Project Manifest ─────────────────────────────────────────────────

@dataclass
class ProjectManifest:
    """The lateralus.toml project manifest."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    main: str = DEFAULT_MAIN
    lateralus_version: str = ">=1.7.0"

    dependencies: dict[str, Dependency] = field(default_factory=dict)
    dev_dependencies: dict[str, Dependency] = field(default_factory=dict)

    scripts: dict[str, str] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)

    # v1.7 additions
    profiles: dict[str, BuildProfile] = field(default_factory=dict)
    workspace: Optional[Workspace] = None
    cfg_features: list[str] = field(default_factory=list)
    targets: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def from_toml(cls, path: Path) -> "ProjectManifest":
        """Load manifest from lateralus.toml."""
        data = parse_toml(path.read_text(encoding="utf-8"))
        return cls._from_data(data)

    @classmethod
    def from_json(cls, path: Path) -> "ProjectManifest":
        """Load manifest from lateralus.json (legacy)."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls._from_data(data)

    @classmethod
    def from_file(cls, path: Path) -> "ProjectManifest":
        """Load manifest from either .toml or .json."""
        if path.suffix == ".toml" or path.name == MANIFEST_FILE:
            if path.exists():
                return cls.from_toml(path)
        if path.suffix == ".json" or path.name == MANIFEST_FILE_JSON:
            if path.exists():
                return cls.from_json(path)
        raise FileNotFoundError(f"Manifest not found: {path}")

    @classmethod
    def _from_data(cls, data: dict) -> "ProjectManifest":
        """Build manifest from parsed dict (TOML or JSON)."""
        # Package section (TOML) or flat (JSON)
        pkg = data.get("package", data)

        # Parse dependencies
        deps = cls._parse_deps(data.get("dependencies", {}))
        dev_deps = cls._parse_deps(data.get("dev-dependencies",
                                             data.get("dev_dependencies", {})))

        # Parse profiles
        profiles = dict(DEFAULT_PROFILES)
        for name, prof_data in data.get("profile", {}).items():
            profiles[name] = BuildProfile(
                name=name,
                opt_level=prof_data.get("opt_level", prof_data.get("opt-level", 0)),
                debug=prof_data.get("debug", True),
                strip=prof_data.get("strip", False),
                lto=prof_data.get("lto", False),
                features=prof_data.get("features", []),
                target=prof_data.get("target", "python"),
                extra_flags=prof_data.get("extra_flags",
                                          prof_data.get("extra-flags", {})),
            )

        # Parse workspace
        ws = None
        if "workspace" in data:
            ws_data = data["workspace"]
            ws = Workspace(
                members=ws_data.get("members", []),
                exclude=ws_data.get("exclude", []),
                shared_dependencies=ws_data.get("shared-dependencies",
                                                ws_data.get("shared_dependencies", {})),
            )

        # Parse cfg
        cfg_features = []
        if "cfg" in data:
            cfg_features = data["cfg"].get("features", [])

        # Parse targets
        targets = data.get("targets", {})

        return cls(
            name=pkg.get("name", "unnamed"),
            version=pkg.get("version", "0.1.0"),
            description=pkg.get("description", ""),
            author=pkg.get("author", pkg.get("authors", "")),
            license=pkg.get("license", "MIT"),
            main=pkg.get("main", DEFAULT_MAIN),
            lateralus_version=pkg.get("lateralus_version",
                                      pkg.get("lateralus-version", ">=1.7.0")),
            dependencies=deps,
            dev_dependencies=dev_deps,
            scripts=data.get("scripts", {}),
            keywords=pkg.get("keywords", []),
            profiles=profiles,
            workspace=ws,
            cfg_features=cfg_features,
            targets=targets,
        )

    @staticmethod
    def _parse_deps(raw: dict) -> dict[str, Dependency]:
        deps = {}
        for name, spec in raw.items():
            if isinstance(spec, str):
                deps[name] = Dependency(name=name, version=spec)
            elif isinstance(spec, dict):
                deps[name] = Dependency(
                    name=name,
                    version=spec.get("version", "*"),
                    path=spec.get("path"),
                    git=spec.get("git"),
                    registry=("git" if spec.get("git") else
                              "local" if spec.get("path") else "registry"),
                )
            else:
                deps[name] = Dependency(name=name, version="*")
        return deps

    def to_toml(self) -> str:
        """Serialize manifest to TOML string."""
        lines = [
            "[package]",
            f'name = "{self.name}"',
            f'version = "{self.version}"',
        ]
        if self.description:
            lines.append(f'description = "{self.description}"')
        if self.author:
            if isinstance(self.author, list):
                lines.append(f'authors = [{", ".join(f"{a!r}" for a in self.author)}]')
            else:
                lines.append(f'author = "{self.author}"')
        lines.append(f'license = "{self.license}"')
        lines.append(f'main = "{self.main}"')
        lines.append(f'lateralus-version = "{self.lateralus_version}"')
        if self.keywords:
            kws = ", ".join(f'"{k}"' for k in self.keywords)
            lines.append(f'keywords = [{kws}]')

        # Dependencies
        if self.dependencies:
            lines.append("\n[dependencies]")
            for name, dep in self.dependencies.items():
                if dep.path:
                    lines.append(f'{name} = {{ version = "{dep.version}",'
                                 f' path = "{dep.path}" }}')
                elif dep.git:
                    lines.append(f'{name} = {{ version = "{dep.version}",'
                                 f' git = "{dep.git}" }}')
                else:
                    lines.append(f'{name} = "{dep.version}"')

        if self.dev_dependencies:
            lines.append("\n[dev-dependencies]")
            for name, dep in self.dev_dependencies.items():
                lines.append(f'{name} = "{dep.version}"')

        # Profiles (only non-default)
        for name, prof in self.profiles.items():
            if name in DEFAULT_PROFILES:
                default = DEFAULT_PROFILES[name]
                if (prof.opt_level == default.opt_level and
                    prof.debug == default.debug and
                    prof.strip == default.strip):
                    continue
            lines.append(f"\n[profile.{name}]")
            lines.append(f"opt-level = {prof.opt_level}")
            lines.append(f"debug = {'true' if prof.debug else 'false'}")
            lines.append(f"strip = {'true' if prof.strip else 'false'}")
            if prof.lto:
                lines.append("lto = true")
            if prof.features:
                feats = ", ".join(f'"{f}"' for f in prof.features)
                lines.append(f"features = [{feats}]")

        # Workspace
        if self.workspace:
            lines.append("\n[workspace]")
            members = ", ".join(f'"{m}"' for m in self.workspace.members)
            lines.append(f"members = [{members}]")
            if self.workspace.exclude:
                excl = ", ".join(f'"{e}"' for e in self.workspace.exclude)
                lines.append(f"exclude = [{excl}]")

        # Cfg
        if self.cfg_features:
            lines.append("\n[cfg]")
            feats = ", ".join(f'"{f}"' for f in self.cfg_features)
            lines.append(f"features = [{feats}]")

        # Scripts
        if self.scripts:
            lines.append("\n[scripts]")
            for name, cmd in self.scripts.items():
                lines.append(f'{name} = "{cmd}"')

        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "main": self.main,
            "lateralus_version": self.lateralus_version,
        }
        if self.dependencies:
            d["dependencies"] = {
                name: dep.to_dict() for name, dep in self.dependencies.items()
            }
        if self.dev_dependencies:
            d["dev_dependencies"] = {
                name: dep.to_dict() for name, dep in self.dev_dependencies.items()
            }
        if self.scripts:
            d["scripts"] = self.scripts
        if self.keywords:
            d["keywords"] = self.keywords
        return d

    def save(self, path: Path):
        """Save manifest to file (TOML or JSON based on extension)."""
        if path.suffix == ".toml" or path.name == MANIFEST_FILE:
            path.write_text(self.to_toml(), encoding="utf-8")
        else:
            path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")


# ─── Lock File ─────────────────────────────────────────────────────────

@dataclass
class LockEntry:
    """A resolved and locked dependency."""
    name: str
    version: str
    resolved: str  # path or URL
    integrity: str  # SHA-256 hash
    dependencies: dict[str, str] = field(default_factory=dict)


@dataclass
class LockFile:
    """The lateralus-lock.json lock file."""
    lockfile_version: int = 1
    entries: dict[str, LockEntry] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "LockFile":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        entries = {}
        for name, entry_data in data.get("entries", {}).items():
            entries[name] = LockEntry(
                name=name,
                version=entry_data["version"],
                resolved=entry_data["resolved"],
                integrity=entry_data["integrity"],
                dependencies=entry_data.get("dependencies", {}),
            )
        return cls(lockfile_version=data.get("lockfile_version", 1), entries=entries)

    def save(self, path: Path):
        data = {
            "lockfile_version": self.lockfile_version,
            "entries": {
                name: {
                    "version": e.version,
                    "resolved": e.resolved,
                    "integrity": e.integrity,
                    "dependencies": e.dependencies,
                }
                for name, e in self.entries.items()
            },
        }
        path.write_text(json.dumps(data, indent=2) + "\n")


# ─── Semver ────────────────────────────────────────────────────────────

@dataclass
class SemVer:
    """Semantic versioning."""
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    @classmethod
    def parse(cls, s: str) -> "SemVer":
        s = s.strip().lstrip("v")
        pre = ""
        if "-" in s:
            s, pre = s.split("-", 1)
        parts = s.split(".")
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 0,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
            prerelease=pre,
        )

    def __str__(self):
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            v += f"-{self.prerelease}"
        return v

    def tuple(self) -> tuple:
        return (self.major, self.minor, self.patch)

    def __hash__(self):
        return hash(self.tuple())

    def __lt__(self, other):
        return self.tuple() < other.tuple()

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return self == other or self > other

    def __eq__(self, other):
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.tuple() == other.tuple()

    def compatible_with(self, spec: str) -> bool:
        """Check if this version satisfies a version spec.

        Supports compound specs: ">=1.0.0, <2.0.0"
        """
        spec = spec.strip()
        if spec == "*":
            return True

        # Compound constraint: ">=1.0, <2.0"
        if "," in spec:
            return all(self.compatible_with(s.strip())
                       for s in spec.split(","))

        if spec.startswith("^"):
            # Compatible: same major, >= minor.patch
            target = SemVer.parse(spec[1:])
            if self.major != target.major:
                return False
            return self >= target
        if spec.startswith("~"):
            # Approximately: same major.minor, >= patch
            target = SemVer.parse(spec[1:])
            if self.major != target.major or self.minor != target.minor:
                return False
            return self.patch >= target.patch
        if spec.startswith(">="):
            return self >= SemVer.parse(spec[2:])
        if spec.startswith("<="):
            return self <= SemVer.parse(spec[2:])
        if spec.startswith(">"):
            return self > SemVer.parse(spec[1:])
        if spec.startswith("<"):
            return self < SemVer.parse(spec[1:])
        if spec.startswith("="):
            return self == SemVer.parse(spec.lstrip("="))
        # Exact match
        return self == SemVer.parse(spec)

    def next_major(self) -> "SemVer":
        return SemVer(self.major + 1, 0, 0)

    def next_minor(self) -> "SemVer":
        return SemVer(self.major, self.minor + 1, 0)

    def next_patch(self) -> "SemVer":
        return SemVer(self.major, self.minor, self.patch + 1)


# ─── Dependency Graph & Resolution ────────────────────────────────────

class DependencyCycle(Exception):
    """Raised when a circular dependency is detected."""


class DepGraph:
    """Directed acyclic graph for dependency resolution."""

    def __init__(self):
        self.nodes: set[str] = set()
        self.edges: dict[str, set[str]] = {}  # pkg -> {deps}

    def add_node(self, name: str):
        self.nodes.add(name)
        self.edges.setdefault(name, set())

    def add_edge(self, from_pkg: str, to_pkg: str):
        """from_pkg depends on to_pkg."""
        self.add_node(from_pkg)
        self.add_node(to_pkg)
        self.edges[from_pkg].add(to_pkg)

    def topological_sort(self) -> list[str]:
        """Return packages in dependency order (leaves first).

        Raises DependencyCycle if a cycle is detected.
        """
        visited: set[str] = set()
        temp: set[str] = set()
        result: list[str] = []

        def visit(node: str):
            if node in temp:
                raise DependencyCycle(f"Circular dependency detected: {node}")
            if node in visited:
                return
            temp.add(node)
            for dep in self.edges.get(node, set()):
                visit(dep)
            temp.remove(node)
            visited.add(node)
            result.append(node)

        for node in sorted(self.nodes):
            visit(node)
        return result

    def detect_cycles(self) -> list[list[str]]:
        """Return all cycles in the graph."""
        cycles: list[list[str]] = []
        visited: set[str] = set()

        def dfs(node: str, path: list[str]):
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            if node in visited:
                return
            path.append(node)
            for dep in self.edges.get(node, set()):
                dfs(dep, path[:])
            visited.add(node)

        for node in sorted(self.nodes):
            dfs(node, [])
        return cycles


class DependencyResolver:
    """Resolves and installs project dependencies with graph-based resolution."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.modules_dir = project_dir / LTL_MODULES_DIR
        self.graph = DepGraph()

    def resolve(self, manifest: ProjectManifest) -> LockFile:
        """Resolve all dependencies, build graph, and create a lock file."""
        lock = LockFile()

        # Build dependency graph
        self.graph.add_node(manifest.name)
        for name, dep in manifest.dependencies.items():
            self.graph.add_edge(manifest.name, name)
            entry = self._resolve_one(name, dep)
            if entry:
                lock.entries[name] = entry
                # Resolve transitive dependencies
                self._resolve_transitive(name, entry, lock)

        for name, dep in manifest.dev_dependencies.items():
            self.graph.add_edge(manifest.name, name)
            entry = self._resolve_one(name, dep)
            if entry:
                lock.entries[name] = entry

        # Validate no cycles
        cycles = self.graph.detect_cycles()
        if cycles:
            raise DependencyCycle(
                f"Circular dependency detected: {' → '.join(cycles[0])}"
            )

        # Sort topologically
        order = self.graph.topological_sort()
        lock.build_order = order

        return lock

    def _resolve_one(self, name: str, dep: Dependency) -> Optional[LockEntry]:
        """Resolve a single dependency."""
        if dep.path:
            # Local dependency
            local_path = self.project_dir / dep.path
            if local_path.exists():
                integrity = self._hash_directory(local_path)
                return LockEntry(
                    name=name,
                    version=dep.version,
                    resolved=str(local_path),
                    integrity=integrity,
                )
        elif dep.git:
            # Git dependency — resolve URL
            return LockEntry(
                name=name,
                version=dep.version,
                resolved=dep.git,
                integrity="git-pending",
            )
        else:
            # Registry dependency
            return LockEntry(
                name=name,
                version=dep.version,
                resolved=f"https://registry.lateralus.dev/packages/{name}",
                integrity="registry-pending",
            )
        return None

    def _resolve_transitive(self, name: str, entry: LockEntry,
                            lock: LockFile):
        """Resolve transitive dependencies from a resolved package."""
        resolved_path = Path(entry.resolved)
        for manifest_name in (MANIFEST_FILE, MANIFEST_FILE_JSON):
            manifest_path = resolved_path / manifest_name
            if manifest_path.exists():
                sub_manifest = ProjectManifest.from_file(manifest_path)
                for dep_name, dep in sub_manifest.dependencies.items():
                    self.graph.add_edge(name, dep_name)
                    if dep_name not in lock.entries:
                        sub_entry = self._resolve_one(dep_name, dep)
                        if sub_entry:
                            lock.entries[dep_name] = sub_entry
                            entry.dependencies[dep_name] = dep.version
                break

    def install(self, lock: LockFile):
        """Install resolved dependencies."""
        self.modules_dir.mkdir(exist_ok=True)

        for name, entry in lock.entries.items():
            dest = self.modules_dir / name
            source = Path(entry.resolved)

            if source.exists() and source.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(source, dest)

    @staticmethod
    def _hash_directory(path: Path) -> str:
        """Hash all .ltl files in a directory for integrity checking."""
        h = hashlib.sha256()
        for f in sorted(path.rglob("*.ltl")):
            h.update(f.read_bytes())
        return f"sha256-{h.hexdigest()}"


# ─── Project Scaffolding ──────────────────────────────────────────────

def scaffold_project(name: str, path: Path, template: str = "default") -> Path:
    """Create a new LATERALUS project structure with lateralus.toml."""
    project_dir = path / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    (project_dir / "src").mkdir(exist_ok=True)
    (project_dir / "tests").mkdir(exist_ok=True)
    (project_dir / "docs").mkdir(exist_ok=True)
    (project_dir / "examples").mkdir(exist_ok=True)

    # Create manifest (TOML)
    manifest = ProjectManifest(
        name=name,
        version="0.1.0",
        description=f"A LATERALUS project: {name}",
        lateralus_version=">=1.7.0",
        scripts={
            "start": f"lateralus run src/main.ltl",
            "test": f"lateralus test tests/",
            "build": f"lateralus build src/main.ltl -o build/{name}.ltlc",
        },
    )
    manifest.save(project_dir / MANIFEST_FILE)

    # Create main source file
    main_file = project_dir / "src" / "main.ltl"
    main_file.write_text(f'''// {name} — A LATERALUS Project
// Generated by lateralus init

fn main() {{
    println("Hello from {name}!")
    println("LATERALUS v1.7 — Package Manager Edition")

    let numbers = [1, 2, 3, 4, 5]
    let result = numbers
        |> filter(fn(x) {{ x % 2 == 0 }})
        |> map(fn(x) {{ x * x }})

    println("Even squares: " + str(result))
}}

main()
''')

    # Create test file
    test_file = project_dir / "tests" / "test_main.ltl"
    test_file.write_text(f'''// Tests for {name}

@test
fn test_basic() {{
    assert_eq(1 + 1, 2)
    println("Basic test passed!")
}}

@test
fn test_pipeline() {{
    let data = [1, 2, 3, 4, 5]
    let result = data |> map(fn(x) {{ x * 2 }}) |> filter(fn(x) {{ x > 4 }})
    assert_eq(len(result), 3)
    println("Pipeline test passed!")
}}
''')

    # Create README
    readme = project_dir / "README.md"
    readme.write_text(f'''# {name}

A project built with LATERALUS.

## Getting Started

```bash
# Run the project
lateralus run src/main.ltl

# Run tests
lateralus test tests/

# Build
lateralus build src/main.ltl -o build/{name}.ltlc --profile release
```

## Project Structure

```
{name}/
  src/              — Source code
    main.ltl        — Entry point
  tests/            — Test files
  docs/             — Documentation
  examples/         — Example programs
  lateralus.toml    — Project manifest
```
''')

    # Create .gitignore
    gitignore = project_dir / ".gitignore"
    gitignore.write_text('''# LATERALUS
build/
ltl_modules/
*.ltlc
lateralus-lock.json

# Python
__pycache__/
*.pyc
.venv/

# IDE
.vscode/
.idea/
''')

    return project_dir


# ─── Package Publishing ──────────────────────────────────────────────

@dataclass
class PackageBundle:
    """A publishable package archive."""
    name: str
    version: str
    manifest: ProjectManifest
    files: list[str]
    integrity: str
    size: int

    @classmethod
    def create(cls, project_dir: Path,
               manifest: ProjectManifest) -> "PackageBundle":
        """Create a package bundle for publishing."""
        files = []
        h = hashlib.sha256()

        for pattern in ["src/**/*.ltl", "tests/**/*.ltl", "docs/**/*",
                        "examples/**/*.ltl", MANIFEST_FILE, "README.md",
                        "LICENSE*"]:
            for p in sorted(project_dir.glob(pattern)):
                if p.is_file():
                    rel = str(p.relative_to(project_dir))
                    files.append(rel)
                    h.update(p.read_bytes())

        total_size = sum(
            (project_dir / f).stat().st_size for f in files
            if (project_dir / f).exists()
        )

        return cls(
            name=manifest.name,
            version=manifest.version,
            manifest=manifest,
            files=files,
            integrity=f"sha256-{h.hexdigest()}",
            size=total_size,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "files": self.files,
            "integrity": self.integrity,
            "size": self.size,
        }


# ─── CLI Entry Point ──────────────────────────────────────────────────

def main():
    """ltlpkg CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="ltlpkg",
        description="LATERALUS Package Manager v1.7",
    )

    sub = parser.add_subparsers(dest="command")

    # init
    init_p = sub.add_parser("init", help="Create a new project")
    init_p.add_argument("name", nargs="?", default="my-lateralus-project")
    init_p.add_argument("--template", default="default",
                        choices=["default", "lib", "app"])

    # add
    add_p = sub.add_parser("add", help="Add a dependency")
    add_p.add_argument("package")
    add_p.add_argument("--version", default="*")
    add_p.add_argument("--path", default=None)
    add_p.add_argument("--git", default=None)
    add_p.add_argument("--dev", action="store_true")

    # remove
    rm_p = sub.add_parser("remove", help="Remove a dependency")
    rm_p.add_argument("package")

    # install
    sub.add_parser("install", help="Install dependencies")

    # build
    build_p = sub.add_parser("build", help="Build the project")
    build_p.add_argument("--profile", default="debug",
                         help="Build profile: debug, release, bench")
    build_p.add_argument("--target", default="python",
                         help="Compilation target: python, c, bytecode")

    # test
    sub.add_parser("test", help="Run tests")

    # run
    run_p = sub.add_parser("run", help="Run a script")
    run_p.add_argument("script", nargs="?", default="start")

    # publish
    pub_p = sub.add_parser("publish", help="Publish package")
    pub_p.add_argument("--dry-run", action="store_true",
                       help="Show what would be published without uploading")

    # info
    sub.add_parser("info", help="Show project info")

    args = parser.parse_args()

    if args.command == "init":
        project = scaffold_project(args.name, Path.cwd(),
                                   template=getattr(args, "template", "default"))
        print(f"Created LATERALUS project: {project}")
        print(f"  cd {args.name}")
        print(f"  lateralus run src/main.ltl")

    elif args.command == "info":
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found. Run 'lateralus init' first.")
            sys.exit(1)
        manifest = ProjectManifest.from_file(manifest_path)
        print(f"  Name:       {manifest.name}")
        print(f"  Version:    {manifest.version}")
        print(f"  Main:       {manifest.main}")
        print(f"  Deps:       {len(manifest.dependencies)}")
        print(f"  Dev-deps:   {len(manifest.dev_dependencies)}")
        print(f"  Profiles:   {', '.join(manifest.profiles.keys())}")
        print(f"  Features:   {', '.join(manifest.cfg_features) or 'none'}")
        print(f"  Scripts:    {', '.join(manifest.scripts.keys()) or 'none'}")
        if manifest.workspace:
            print(f"  Workspace:  {', '.join(manifest.workspace.members)}")

    elif args.command == "install":
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found.")
            sys.exit(1)
        manifest = ProjectManifest.from_file(manifest_path)
        resolver = DependencyResolver(manifest_path.parent)
        lock = resolver.resolve(manifest)
        resolver.install(lock)
        lock.save(manifest_path.parent / LOCK_FILE)
        print(f"Installed {len(lock.entries)} dependencies.")

    elif args.command == "add":
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found.")
            sys.exit(1)
        manifest = ProjectManifest.from_file(manifest_path)
        dep = Dependency(
            name=args.package,
            version=args.version,
            path=args.path,
            git=getattr(args, "git", None),
        )
        if args.dev:
            manifest.dev_dependencies[args.package] = dep
        else:
            manifest.dependencies[args.package] = dep
        manifest.save(manifest_path)
        print(f"Added {args.package}@{args.version}")

    elif args.command == "remove":
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found.")
            sys.exit(1)
        manifest = ProjectManifest.from_file(manifest_path)
        manifest.dependencies.pop(args.package, None)
        manifest.dev_dependencies.pop(args.package, None)
        manifest.save(manifest_path)
        print(f"Removed {args.package}")

    elif args.command == "build":
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found.")
            sys.exit(1)
        manifest = ProjectManifest.from_file(manifest_path)
        profile_name = getattr(args, "profile", "debug")
        profile = manifest.profiles.get(profile_name, DEFAULT_PROFILES["debug"])
        print(f"Building {manifest.name} v{manifest.version}"
              f" [profile: {profile_name}]")
        print(f"  opt_level={profile.opt_level}  debug={profile.debug}"
              f"  strip={profile.strip}  lto={profile.lto}")

        # Compile via the compiler
        from .compiler import Compiler, Target
        target_map = {"python": Target.PYTHON, "c": Target.C,
                      "bytecode": Target.BYTECODE}
        target = target_map.get(getattr(args, "target", profile.target),
                                Target.PYTHON)
        main_file = manifest_path.parent / manifest.main
        if not main_file.exists():
            print(f"  Main file not found: {manifest.main}")
            sys.exit(1)
        compiler = Compiler()
        result = compiler.compile_file(str(main_file), target=target)
        if result.ok:
            print(f"  ✓ Build succeeded")
        else:
            print(f"  ✗ Build failed")
            for e in result.errors[:5]:
                print(f"    {e.message}")
            sys.exit(1)

    elif args.command == "publish":
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found.")
            sys.exit(1)
        manifest = ProjectManifest.from_file(manifest_path)
        bundle = PackageBundle.create(manifest_path.parent, manifest)
        if getattr(args, "dry_run", False):
            print(f"Would publish {bundle.name}@{bundle.version}")
            print(f"  Files: {len(bundle.files)}")
            print(f"  Size:  {bundle.size:,} bytes")
            print(f"  Integrity: {bundle.integrity}")
            for f in bundle.files[:10]:
                print(f"    {f}")
            if len(bundle.files) > 10:
                print(f"    ... and {len(bundle.files) - 10} more")
        else:
            print(f"Publishing {bundle.name}@{bundle.version}"
                  f" to registry.lateralus.dev ...")
            print(f"  (Registry not yet available — use --dry-run to preview)")

    else:
        parser.print_help()


def _find_manifest() -> Optional[Path]:
    """Find the project manifest (lateralus.toml or lateralus.json)."""
    cwd = Path.cwd()
    for name in (MANIFEST_FILE, MANIFEST_FILE_JSON):
        path = cwd / name
        if path.exists():
            return path
    return None


if __name__ == "__main__":
    main()
