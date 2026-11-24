"""Static package registry for Lateralus.

The registry is a plain directory tree that any static host can serve — S3,
Cloudflare R2, Cloudflare Pages, an nginx root, a USB stick::

    <registry-root>/
        index.json                              # every package, every version
        packages/<name>/<name>-<version>.tar.gz # deterministic archives

There is no server component. ``publish`` writes the archive and updates
``index.json`` in place (local path) or PUTs both to a URL. ``fetch`` reads
``index.json``, resolves a semver constraint, downloads the archive, verifies
its SHA-256 digest before touching the filesystem, and unpacks it into
``vendor/``.

Determinism
-----------
Two runs over the same source tree must produce byte-identical archives, so
that the digest in ``index.json`` means something. That requires pinning every
field a tar or gzip header would otherwise fill in from the environment:

* entries sorted by path (filesystem order is not stable across platforms)
* ``mtime = 0``, ``uid = gid = 0``, ``uname = gname = ""``
* mode normalised to ``0o644``
* gzip header ``mtime = 0`` and no embedded filename

Without those five, the same project published from two machines has two
different digests and integrity checking is decorative.

Security
--------
Archives come from the network. Extraction rejects anything that is not a
regular file (symlinks, hardlinks, devices, directories) and anything whose
resolved path escapes the destination, so a malicious package cannot write
outside ``vendor/``. A byte budget caps decompression bombs.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

INDEX_FILE = "index.json"
PACKAGE_DIR = "packages"
DIGEST_ALGORITHM = "sha256"
SCHEMA_VERSION = 1

#: Directories that never belong in a published package, even if a glob matches.
EXCLUDED_DIRS = {".git", ".hg", ".svn", "__pycache__", "vendor", "node_modules",
                 ".venv", "venv", "dist", "build", ".mypy_cache", ".pytest_cache"}

#: What goes into an archive. Kept explicit rather than "everything minus
#: exclusions" so that a stray 400 MB fixture cannot be published by accident.
INCLUDE_GLOBS: tuple[str, ...] = (
    "lateralus.toml",
    "lateralus.json",
    "README.md",
    "README.*.md",
    "LICENSE",
    "LICENSE.*",
    "*.ltl",
    "src/**/*.ltl",
    "lib/**/*.ltl",
    "tests/**/*.ltl",
    "examples/**/*.ltl",
    "docs/**/*.md",
    "docs/**/*.ltl",
    "docs/**/*.ltlm",
)

#: Nothing bigger than this gets unpacked. A compiler package is source code.
DEFAULT_MAX_UNPACKED = 64 * 1024 * 1024


class RegistryError(Exception):
    """Any failure that should abort a publish or fetch with a readable message."""


class IntegrityError(RegistryError):
    """The downloaded archive does not match the digest recorded in the index."""


# ---------------------------------------------------------------------------
# Deterministic archives
# ---------------------------------------------------------------------------

def _normalise_mode(path: Path) -> int:
    """Executable bits are dropped on purpose.

    A package is source code; whether the author's laptop had bit 0x40 set is
    noise that would make the archive non-reproducible across checkouts.
    """
    return 0o644


def collect_files(project_dir: Path) -> list[str]:
    """Return the sorted, de-duplicated, POSIX-style paths to publish."""
    project_dir = Path(project_dir)
    seen: set[str] = set()
    for pattern in INCLUDE_GLOBS:
        for path in project_dir.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(project_dir)
            if any(part in EXCLUDED_DIRS for part in rel.parts[:-1]):
                continue
            seen.add(rel.as_posix())
    return sorted(seen)


def build_tarball(project_dir: Path, files: Sequence[str]) -> bytes:
    """Build a gzip-compressed tar of ``files`` with every timestamp pinned.

    Returns the raw archive bytes; callers hash these and hand them to a
    registry.
    """
    project_dir = Path(project_dir)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for rel in sorted(files):
            source = project_dir / rel
            payload = source.read_bytes()
            info = tarfile.TarInfo(rel)
            info.size = len(payload)
            info.mtime = 0
            info.mode = _normalise_mode(source)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(payload))

    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=compressed, mode="wb",
                       compresslevel=9, mtime=0) as gz:
        gz.write(raw.getvalue())
    return compressed.getvalue()


def digest_of(data: bytes) -> str:
    """``sha256:<hex>`` — the form recorded in ``index.json``."""
    return f"{DIGEST_ALGORITHM}:{hashlib.sha256(data).hexdigest()}"


def unpack_tarball(data: bytes, dest: Path,
                   max_unpacked: int = DEFAULT_MAX_UNPACKED) -> int:
    """Extract ``data`` into ``dest``, refusing anything that escapes it.

    Returns the number of files written.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    prefix = str(root) + os.sep
    written = 0
    total = 0

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                raise RegistryError(
                    f"archive contains a non-regular entry: {member.name!r} "
                    f"(type {member.type!r}); only regular files are allowed")
            target = (dest / member.name).resolve()
            if not str(target).startswith(prefix):
                raise RegistryError(
                    f"archive entry escapes the destination: {member.name!r}")
            total += member.size
            if total > max_unpacked:
                raise RegistryError(
                    f"archive exceeds the {max_unpacked} byte unpack budget")
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            target.write_bytes(extracted.read())
            written += 1
    return written


# ---------------------------------------------------------------------------
# Where a registry lives
# ---------------------------------------------------------------------------

@dataclass
class RegistryLocation:
    """A registry addressable either as a local directory or as a base URL."""

    path: Optional[Path] = None
    url: Optional[str] = None
    token: Optional[str] = None
    timeout: int = 30
    #: ``publish --dry-run`` needs to build and hash an archive without having
    #: been told where it would go. Reads then behave as "empty registry" and
    #: writes refuse, so a dry run can never touch a real host.
    allow_unconfigured: bool = False

    def __post_init__(self) -> None:
        if self.path is not None:
            self.path = Path(self.path)
            return
        if self.url:
            return
        if not self.allow_unconfigured:
            raise RegistryError(
                "no registry configured: set [registry] path or url in "
                "lateralus.toml, pass --registry-path/--registry-url, or set "
                "LATERALUS_REGISTRY")

    @property
    def configured(self) -> bool:
        return self.path is not None or bool(self.url)

    @classmethod
    def from_manifest(cls, manifest, override_path=None,
                      override_url=None,
                      allow_unconfigured=False) -> "RegistryLocation":
        """Build a location from ``[registry]`` in the manifest, overrides win."""
        token = None
        path = override_path
        url = override_url
        registry = getattr(manifest, "registry", None) or {}
        if isinstance(registry, dict):
            path = path or registry.get("path")
            url = url or registry.get("url")
            token = registry.get("token")
        token = token or os.environ.get("LATERALUS_REGISTRY_TOKEN")
        return cls(path=path, url=url, token=token,
                   allow_unconfigured=allow_unconfigured)

    # -- reads ---------------------------------------------------------
    def read(self, rel: str) -> bytes:
        if self.path is None and not self.url:
            raise RegistryError("no registry configured")
        if self.path is not None:
            target = self.path / rel
            if not target.exists():
                raise RegistryError(f"not found in registry: {rel}")
            return target.read_bytes()
        return self._http("GET", rel)

    def exists(self, rel: str) -> bool:
        try:
            self.read(rel)
            return True
        except (RegistryError, urllib.error.HTTPError):
            return False

    # -- writes --------------------------------------------------------
    def write(self, rel: str, data: bytes) -> None:
        if self.path is None and not self.url:
            raise RegistryError(
                "no registry configured; refusing to write (this is expected "
                "during --dry-run)")
        if self.path is not None:
            target = self.path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(target)
            return
        self._http("PUT", rel, data)

    def _http(self, method: str, rel: str, data: Optional[bytes] = None) -> bytes:
        url = self.url.rstrip("/") + "/" + rel.lstrip("/")
        headers = {"User-Agent": "lateralus-pkg/1.0"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if data is not None:
            headers["Content-Type"] = "application/octet-stream"
        request = urllib.request.Request(url, data=data, headers=headers,
                                         method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise RegistryError(
                f"{method} {url} failed: HTTP {exc.code} {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RegistryError(f"{method} {url} failed: {exc.reason}") from exc

    def describe(self) -> str:
        if self.path is not None:
            return str(self.path)
        return self.url or "<unconfigured>"


# ---------------------------------------------------------------------------
# index.json
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RegistryIndex:
    """The ``index.json`` document."""

    packages: dict = field(default_factory=dict)
    updated_at: str = field(default_factory=_now)

    @classmethod
    def empty(cls) -> "RegistryIndex":
        return cls(packages={}, updated_at=_now())

    @classmethod
    def from_bytes(cls, raw: bytes) -> "RegistryIndex":
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RegistryError(f"index.json is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise RegistryError("index.json must be a JSON object")
        schema = payload.get("schema")
        if schema is not None and schema != SCHEMA_VERSION:
            raise RegistryError(
                f"index.json schema {schema!r} is not supported "
                f"(this build understands {SCHEMA_VERSION})")
        packages = payload.get("packages") or {}
        if not isinstance(packages, dict):
            raise RegistryError("index.json 'packages' must be an object")
        return cls(packages=packages,
                   updated_at=payload.get("updated_at") or _now())

    @classmethod
    def load(cls, location: RegistryLocation) -> "RegistryIndex":
        if not location.exists(INDEX_FILE):
            return cls.empty()
        return cls.from_bytes(location.read(INDEX_FILE))

    def to_bytes(self) -> bytes:
        payload = {
            "schema": SCHEMA_VERSION,
            "registry": "lateralus-static-registry",
            "updated_at": self.updated_at,
            "packages": dict(sorted(self.packages.items())),
        }
        return (json.dumps(payload, indent=2, sort_keys=True,
                           ensure_ascii=False) + "\n").encode("utf-8")

    # -- lookups -------------------------------------------------------
    def versions_of(self, name: str) -> dict:
        entry = self.packages.get(name) or {}
        return entry.get("versions") or {}

    def get(self, name: str, version: str) -> Optional[dict]:
        return self.versions_of(name).get(version)

    def add(self, name: str, record: dict) -> None:
        entry = self.packages.setdefault(name, {"name": name, "versions": {}})
        entry.setdefault("versions", {})[record["version"]] = record
        entry["latest"] = pick_latest(entry["versions"])
        self.updated_at = _now()


def tarball_path(name: str, version: str) -> str:
    return f"{PACKAGE_DIR}/{name}/{name}-{version}.tar.gz"


# ---------------------------------------------------------------------------
# Semver
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.\-]+))?$")


def parse_semver(text: str) -> tuple[int, int, int, str]:
    match = _SEMVER_RE.match(text.strip())
    if not match:
        raise RegistryError(f"not a semantic version: {text!r}")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)),
            match.group(4) or "")


def _sort_key(version: str):
    major, minor, patch, pre = parse_semver(version)
    # A release sorts above its own prereleases.
    return (major, minor, patch, 0 if pre else 1, pre)


def pick_latest(versions: dict) -> Optional[str]:
    candidates = [v for v in versions if _SEMVER_RE.match(v or "")]
    if not candidates:
        return None
    return max(candidates, key=_sort_key)


def satisfies(version: str, spec: str) -> bool:
    """A deliberately small subset of semver ranges.

    Supports ``*``/``latest``, exact pins, ``^1.2.3``, ``~1.2.3``, ``>=1.2.3``,
    ``>``, ``<=``, ``<``, and comma or space separated conjunctions. That
    covers what a registry MVP needs; anything richer belongs in a resolver,
    not in a fetch path.
    """
    spec = (spec or "*").strip()
    if spec in ("", "*", "latest", "x"):
        return True
    for clause in re.split(r"[,\s]+", spec):
        if not clause:
            continue
        if not _satisfies_one(version, clause):
            return False
    return True


def _satisfies_one(version: str, clause: str) -> bool:
    try:
        have = parse_semver(version)
    except RegistryError:
        return False
    operator = "^~<>=!"
    match = re.match(r"^(\^|~|>=|<=|>|<|=)?\s*(.+)$", clause)
    if not match:
        return False
    op, wanted_text = match.group(1) or "=", match.group(2)
    try:
        want = parse_semver(wanted_text)
    except RegistryError:
        return False
    if op == "=":
        return have == want
    if op == "^":
        if want[0] > 0:
            return have >= want and have[0] == want[0]
        if want[1] > 0:
            return have >= want and have[:2] == want[:2]
        return have >= want and have[:3] == want[:3]
    if op == "~":
        return have >= want and have[:2] == want[:2]
    if op == ">=":
        return have >= want
    if op == ">":
        return have > want
    if op == "<=":
        return have <= want
    if op == "<":
        return have < want
    return False


def resolve_version(index: RegistryIndex, name: str, spec: str = "*") -> str:
    versions = index.versions_of(name)
    if not versions:
        raise RegistryError(
            f"package {name!r} is not in the registry "
            f"({len(index.packages)} package(s) available)")
    matching = [v for v in versions if satisfies(v, spec)]
    if not matching:
        known = ", ".join(sorted(versions, key=_sort_key))
        raise RegistryError(
            f"no version of {name!r} satisfies {spec!r}; available: {known}")
    return max(matching, key=_sort_key)


# ---------------------------------------------------------------------------
# publish / fetch
# ---------------------------------------------------------------------------

def build_record(project_dir: Path, manifest, files: Sequence[str],
                 archive: bytes) -> dict:
    """The per-version record stored in ``index.json``."""
    return {
        "name": manifest.name,
        "version": manifest.version,
        "digest": digest_of(archive),
        "size": len(archive),
        "files": len(files),
        "tarball": tarball_path(manifest.name, manifest.version),
        "published_at": _now(),
        "description": getattr(manifest, "description", "") or "",
        "license": getattr(manifest, "license", "") or "",
        "dependencies": {
            name: (dep.version if hasattr(dep, "version") else str(dep))
            for name, dep in (getattr(manifest, "dependencies", {}) or {}).items()
        },
    }


def publish_package(project_dir: Path, manifest,
                    location: RegistryLocation, dry_run: bool = False) -> dict:
    """Build the archive, upload it, and update ``index.json``."""
    project_dir = Path(project_dir)
    files = collect_files(project_dir)
    if not files:
        raise RegistryError(
            "nothing to publish: no files matched the package include rules "
            "(expected lateralus.toml plus .ltl sources)")
    archive = build_tarball(project_dir, files)
    record = build_record(project_dir, manifest, files, archive)

    existing = RegistryIndex.load(location)
    previous = existing.get(manifest.name, manifest.version)
    if previous and previous.get("digest") == record["digest"]:
        result = {"status": "unchanged", "record": record, "files": files}
        if not dry_run:
            # Still rewrite so a half-written registry self-heals.
            location.write(record["tarball"], archive)
        return result
    if previous:
        record["supersedes"] = previous.get("digest")

    result = {
        "status": "dry-run" if dry_run else "published",
        "record": record,
        "files": files,
        "replaced": bool(previous),
    }
    if dry_run:
        return result

    location.write(record["tarball"], archive)
    existing.add(manifest.name, record)
    location.write(INDEX_FILE, existing.to_bytes())
    return result


def fetch_package(index: RegistryIndex, location: RegistryLocation,
                  name: str, version_spec: str, vendor_dir: Path) -> dict:
    """Download, verify, and unpack one package into ``vendor_dir``."""
    version = resolve_version(index, name, version_spec)
    record = index.get(name, version)
    if not record:
        raise RegistryError(
            f"index.json lists {name}@{version} but has no record for it")
    expected = record.get("digest") or ""
    if not expected.startswith(f"{DIGEST_ALGORITHM}:"):
        raise RegistryError(
            f"{name}@{version} has an unusable digest {expected!r}; "
            f"refusing to install")

    archive = location.read(record["tarball"])
    actual = digest_of(archive)
    if actual != expected:
        raise IntegrityError(
            f"digest mismatch for {name}@{version}: index says {expected}, "
            f"archive hashes to {actual}")

    target = Path(vendor_dir) / f"{name}-{version}"
    written = unpack_tarball(archive, target)
    return {
        "name": name,
        "version": version,
        "digest": actual,
        "path": target,
        "files": written,
    }


# ---------------------------------------------------------------------------
# Registry maintenance helpers (tools/registry/build_index.py uses these)
# ---------------------------------------------------------------------------

def rebuild_index(root: Path) -> RegistryIndex:
    """Reconstruct ``index.json`` from the archives already on disk.

    Useful after copying a registry between hosts, or after a hand-edit that
    left the index out of sync. Digests are recomputed from the files, so a
    corrupt archive shows up here rather than at install time.
    """
    root = Path(root)
    index = RegistryIndex.empty()
    packages_dir = root / PACKAGE_DIR
    if not packages_dir.is_dir():
        return index

    for package_dir in sorted(p for p in packages_dir.iterdir() if p.is_dir()):
        name = package_dir.name
        for archive_path in sorted(package_dir.glob(f"{name}-*.tar.gz")):
            version = archive_path.name[len(name) + 1:-len(".tar.gz")]
            try:
                parse_semver(version)
            except RegistryError:
                continue
            data = archive_path.read_bytes()
            record = {
                "version": version,
                "digest": digest_of(data),
                "size": len(data),
                "tarball": f"{PACKAGE_DIR}/{name}/{archive_path.name}",
                "published_at": datetime.fromtimestamp(
                    archive_path.stat().st_mtime, timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "rebuilt": True,
            }
            index.add(name, record)
    return index
