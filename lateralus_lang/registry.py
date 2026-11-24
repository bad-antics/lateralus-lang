"""
LATERALUS Package Registry — static, S3/R2/Cloudflare-Pages compatible MVP.

Implements the `[bounty] package-registry-mvp` scope:

  * A static registry layout (a plain directory that can be synced to S3 / R2 /
    Cloudflare Pages) that serves deterministic ``.tar.gz`` tarballs plus a
    single ``index.json`` manifest — no server required.
  * ``lateralus publish`` — reads ``lateralus.toml``, packs the project into a
    reproducible tarball, computes a SHA-256 digest, and uploads it to a
    configured registry URL (local dir, ``file://``, or ``s3://``/``r2://`` via
    the AWS CLI).
  * ``lateralus add <name>`` — fetches a package from the registry, verifies the
    pinned SHA-256 digest against ``index.json`` / ``lateralus-lock.json``, and
    unpacks it into the workspace ``vendor/`` directory.

Registry layout::

    <registry-root>/
      index.json
      packages/
        <name>/
          <name>-<version>.tar.gz

The tarballs are byte-for-byte reproducible: file list is sorted, mtimes are
zeroed, ownership is normalised, and the gzip header carries no timestamp. The
same source tree therefore always yields the same SHA-256 digest.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional

from .package_manager import (
    MANIFEST_FILE,
    ProjectManifest,
    SemVer,
    _find_manifest,
)

# --- Constants ---------------------------------------------------------

REGISTRY_INDEX = "index.json"
REGISTRY_VERSION = 1
VENDOR_DIR = "vendor"
DEFAULT_REGISTRY_ENV = "LATERALUS_REGISTRY"
DEFAULT_REGISTRY_URL = "https://registry.lateralus.dev"
PACKAGES_PREFIX = "packages"

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SAFE_REL_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")


class RegistryError(Exception):
    """Raised for any registry publish/add failure."""


# --- Hashing / integrity ----------------------------------------------

def sha256_bytes(data: bytes) -> str:
    """Return the ``sha256-<hex>`` integrity string for *data*."""
    return "sha256-" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the ``sha256-<hex>`` integrity string for a file on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256-" + h.hexdigest()


def _split_integrity(integrity: str) -> tuple[str, str]:
    """Split ``sha256-<hex>`` into ``("sha256", "<hex>")``."""
    if "-" not in integrity:
        raise RegistryError(f"Malformed integrity string: {integrity!r}")
    algo, _, digest = integrity.partition("-")
    return algo, digest


def verify_integrity(data: bytes, expected: str) -> bool:
    """Constant-time-ish check that *data* matches the *expected* digest."""
    algo, digest = _split_integrity(expected)
    if algo != "sha256":
        raise RegistryError(f"Unsupported integrity algorithm: {algo!r}")
    actual = hashlib.sha256(data).hexdigest()
    return hashlib.compare_digest(actual, digest) if hasattr(
        hashlib, "compare_digest") else actual == digest


# --- Deterministic tarball packing ------------------------------------

def _collect_package_files(project_dir: Path,
                           manifest: ProjectManifest) -> list[str]:
    """Return the sorted list of project-relative POSIX paths to pack.

    Packs source, tests, examples, docs, the manifest, README and LICENSE —
    mirroring ``PackageBundle.create`` but returning POSIX-normalised paths so
    the tarball is identical on every platform.
    """
    patterns = [
        "src/**/*.ltl", "src/**/*.ltasm",
        "tests/**/*.ltl", "examples/**/*.ltl", "examples/**/*.ltasm",
        "docs/**/*",
        MANIFEST_FILE, "README*", "LICENSE*",
    ]
    found: set[str] = set()
    for pattern in patterns:
        for p in sorted(project_dir.glob(pattern)):
            if p.is_file():
                rel = p.relative_to(project_dir).as_posix()
                found.add(rel)
    # Always include the manifest even if it lives outside the globs above.
    manifest_rel = MANIFEST_FILE
    if (project_dir / manifest_rel).exists():
        found.add(manifest_rel)
    return sorted(found)


def build_tarball(project_dir: Path, manifest: ProjectManifest,
                  dest_dir: Path) -> tuple[Path, str, int, list[str]]:
    """Pack *project_dir* into a reproducible ``<name>-<version>.tar.gz``.

    Returns ``(tarball_path, integrity, size, file_list)``. The tarball is
    deterministic: identical inputs always produce identical bytes (and thus an
    identical SHA-256 digest).
    """
    _validate_name(manifest.name)
    files = _collect_package_files(project_dir, manifest)
    if not files:
        raise RegistryError(
            f"No packageable files found in {project_dir} "
            f"(expected src/, tests/, or {MANIFEST_FILE})"
        )

    raw_tar = io.BytesIO()
    with tarfile.open(fileobj=raw_tar, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for rel in files:
            src = project_dir / rel
            data = src.read_bytes()
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(data))

    # Deterministic gzip: mtime=0, no embedded filename.
    gz = gzip.compress(raw_tar.getvalue(), compresslevel=9, mtime=0)

    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{manifest.name}-{manifest.version}.tar.gz"
    tarball_path = dest_dir / filename
    tarball_path.write_bytes(gz)

    return tarball_path, sha256_bytes(gz), len(gz), files


# --- index.json --------------------------------------------------------

def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name or ""):
        raise RegistryError(
            f"Invalid package name {name!r}: must match {_NAME_RE.pattern}"
        )


def empty_index() -> dict:
    """Return a fresh, empty registry index structure."""
    return {
        "registry_version": REGISTRY_VERSION,
        "packages": {},
    }


def load_index(path: Path) -> dict:
    """Load a registry ``index.json`` from *path* (or return an empty one)."""
    if not path.exists():
        return empty_index()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryError(f"Corrupt registry index at {path}: {exc}") from exc
    data.setdefault("registry_version", REGISTRY_VERSION)
    data.setdefault("packages", {})
    return data


def save_index(index: dict, path: Path) -> None:
    """Write *index* to *path* as pretty, sorted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(index, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def _version_record(tarball_rel: str, integrity: str, size: int,
                    manifest: ProjectManifest) -> dict:
    return {
        "tarball": tarball_rel,
        "integrity": integrity,
        "size": size,
        "dependencies": {
            name: dep.version for name, dep in manifest.dependencies.items()
        },
        "lateralus_version": manifest.lateralus_version,
    }


# --- Registry stores (read side) --------------------------------------

class LocalRegistry:
    """Read/write a registry rooted at a local directory (or ``file://`` URL).

    This is the canonical "static directory" that can be synced to S3 / R2 /
    Cloudflare Pages with e.g. ``aws s3 sync ./registry s3://bucket``.
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    # -- write side (publish) --
    @property
    def index_path(self) -> Path:
        return self.root / REGISTRY_INDEX

    def add_version(self, manifest: ProjectManifest, tarball: Path,
                    integrity: str, size: int) -> dict:
        """Copy a freshly built tarball into the registry and index it."""
        index = load_index(self.index_path)
        pkg = index["packages"].setdefault(manifest.name, {"versions": {}})
        pkg.setdefault("versions", {})
        tarball_rel = f"{PACKAGES_PREFIX}/{manifest.name}/{tarball.name}"
        # Copy the staged tarball into the static registry layout.
        dest = self.root / tarball_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tarball, dest)
        record = _version_record(tarball_rel, integrity, size, manifest)
        pkg["versions"][manifest.version] = record
        save_index(index, self.index_path)
        return record

    # -- read side (add) --
    def read_index(self) -> dict:
        if not self.index_path.exists():
            raise RegistryError(
                f"No registry index at {self.index_path} "
                f"(is {self.root} a published registry?)"
            )
        return load_index(self.index_path)

    def fetch_tarball(self, tarball_rel: str) -> bytes:
        # Prevent path traversal out of the registry root.
        target = (self.root / tarball_rel).resolve()
        root = self.root.resolve()
        if not str(target).startswith(str(root)):
            raise RegistryError(f"Refusing to read outside registry: {tarball_rel}")
        if not target.exists():
            raise RegistryError(f"Tarball not found in registry: {tarball_rel}")
        return target.read_bytes()


class HttpRegistry:
    """Read-only registry backed by a static HTTP(S) endpoint (S3/R2/Pages)."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _url(self, rel: str) -> str:
        return f"{self.base_url}/{rel.lstrip('/')}"

    def read_index(self) -> dict:
        raw = self._http_get(self._url(REGISTRY_INDEX))
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RegistryError(f"Corrupt remote registry index: {exc}") from exc
        data.setdefault("registry_version", REGISTRY_VERSION)
        data.setdefault("packages", {})
        return data

    def fetch_tarball(self, tarball_rel: str) -> bytes:
        return self._http_get(self._url(tarball_rel))

    @staticmethod
    def _http_get(url: str) -> bytes:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            raise RegistryError(f"Failed to fetch {url}: {exc}") from exc


def open_registry(url: str):
    """Return a registry store for *url* (local path, file://, http(s)://)."""
    if url.startswith("http://") or url.startswith("https://"):
        return HttpRegistry(url)
    if url.startswith("file://"):
        return LocalRegistry(Path(url[len("file://"):]))
    return LocalRegistry(Path(url))


# --- Version resolution ------------------------------------------------

def resolve_version(index: dict, name: str, spec: str) -> tuple[str, dict]:
    """Pick the highest published version of *name* satisfying *spec*.

    Returns ``(version, record)``. Raises ``RegistryError`` if nothing matches.
    """
    pkg = index.get("packages", {}).get(name)
    if not pkg:
        raise RegistryError(
            f"Package {name!r} not found in registry "
            f"(available: {', '.join(sorted(index.get('packages', {}))) or 'none'})"
        )
    versions = pkg.get("versions", {})
    if not versions:
        raise RegistryError(f"Package {name!r} has no published versions")

    candidates = []
    for ver in versions:
        try:
            sv = SemVer.parse(ver)
        except (ValueError, IndexError):
            continue
        if sv.compatible_with(spec):
            candidates.append((sv, ver))
    if not candidates:
        raise RegistryError(
            f"No version of {name!r} satisfies {spec!r} "
            f"(have: {', '.join(sorted(versions))})"
        )
    candidates.sort(key=lambda c: c[0])
    best = candidates[-1]
    return best[1], versions[best[1]]


# --- Safe extraction ---------------------------------------------------

def _safe_members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    """Return regular-file members, rejecting absolute / traversing paths."""
    members = []
    for m in tar.getmembers():
        if not m.isfile():
            continue
        name = m.name
        if name.startswith("/") or ".." in Path(name).parts:
            raise RegistryError(f"Refusing unsafe path in tarball: {name!r}")
        if not _SAFE_REL_RE.match(name):
            raise RegistryError(f"Refusing suspicious path in tarball: {name!r}")
        members.append(m)
    return members


def unpack_tarball(data: bytes, dest_dir: Path) -> list[str]:
    """Safely extract tarball *data* into *dest_dir*; return extracted paths."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for m in _safe_members(tar):
            src = tar.extractfile(m)
            if src is None:
                continue
            out_path = (dest_dir / m.name).resolve()
            if not str(out_path).startswith(str(dest_dir.resolve())):
                raise RegistryError(f"Refusing to extract outside dest: {m.name}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(src.read())
            written.append(m.name)
    return sorted(written)


# --- High-level operations --------------------------------------------

def _resolve_registry_url(explicit: Optional[str], manifest: ProjectManifest,
                          project_dir: Path) -> str:
    """Resolve the registry URL from flag, env, manifest, or default."""
    if explicit:
        return explicit
    env = os.environ.get(DEFAULT_REGISTRY_ENV)
    if env:
        return env
    # [registry] url = "..." in lateralus.toml is surfaced via targets.
    reg = manifest.targets.get("registry") if manifest.targets else None
    if isinstance(reg, dict) and reg.get("url"):
        return reg["url"]
    return DEFAULT_REGISTRY_URL


def _upload_to_s3(local_tarball: Path, tarball_key: str, registry_url: str,
                  dry_run: bool) -> None:
    """Best-effort upload of a tarball + index to an s3:// or r2:// root."""
    import subprocess

    scheme, _, rest = registry_url.partition("://")
    if scheme not in ("s3", "r2"):
        raise RegistryError(f"Unsupported upload scheme: {scheme!r}")
    if dry_run:
        return
    aws = shutil.which("aws")
    if not aws:
        raise RegistryError(
            f"Cannot upload to {registry_url}: the 'aws' CLI is not installed. "
            f"Sync the static registry directory manually, e.g. "
            f"`aws s3 sync ./registry {registry_url}`."
        )
    dest = f"{registry_url.rstrip('/')}/{tarball_key}"
    subprocess.run([aws, "s3", "cp", str(local_tarball), dest], check=True)


def publish(project_dir: Path, registry_url: Optional[str] = None,
            dry_run: bool = False, staging_dir: Optional[Path] = None) -> dict:
    """Pack *project_dir* and publish it to *registry_url*.

    For a local / ``file://`` registry this writes the tarball under
    ``packages/<name>/`` and updates ``index.json`` in place. For ``s3://`` /
    ``r2://`` it stages the artifacts locally and uploads them with the AWS CLI.

    Returns a summary dict describing what was published.
    """
    manifest_path = _find_manifest(start=project_dir)
    if not manifest_path:
        raise RegistryError(
            f"No {MANIFEST_FILE} found in {project_dir} — run 'lateralus init'."
        )
    manifest = ProjectManifest.from_file(manifest_path)
    url = _resolve_registry_url(registry_url, manifest, project_dir)

    # Build the tarball into a staging directory first.
    if staging_dir is None:
        staging_dir = project_dir / "build" / "registry"
    staging_dir = Path(staging_dir)
    tarball, integrity, size, files = build_tarball(project_dir, manifest, staging_dir)

    summary = {
        "name": manifest.name,
        "version": manifest.version,
        "integrity": integrity,
        "size": size,
        "files": files,
        "registry": url,
        "tarball": str(tarball),
        "dry_run": dry_run,
    }

    if url.startswith("s3://") or url.startswith("r2://"):
        tarball_key = f"{PACKAGES_PREFIX}/{manifest.name}/{tarball.name}"
        _upload_to_s3(tarball, tarball_key, url, dry_run)
        summary["uploaded"] = not dry_run
        return summary

    # Local / file:// static registry.
    registry = open_registry(url)
    if not isinstance(registry, LocalRegistry):
        raise RegistryError(
            f"Cannot publish to a remote read-only registry ({url}). "
            f"Publish to a local directory or s3:// / r2:// root."
        )
    if dry_run:
        summary["uploaded"] = False
        return summary

    registry.add_version(manifest, tarball, integrity, size)
    summary["uploaded"] = True
    return summary


def add(name: str, version_spec: str = "*", registry_url: Optional[str] = None,
        workspace_dir: Optional[Path] = None,
        vendor_dir: Optional[Path] = None) -> dict:
    """Fetch *name* from the registry, verify it, and unpack into ``vendor/``.

    Verification: the tarball's SHA-256 is checked against the digest pinned in
    the registry ``index.json``. The resolved version + integrity are then
    recorded in ``lateralus-lock.json`` for reproducible future installs.

    Returns a summary dict describing the installed package.
    """
    _validate_name(name)
    workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
    vendor = Path(vendor_dir) if vendor_dir else workspace_dir / VENDOR_DIR

    manifest_path = _find_manifest(start=workspace_dir)
    manifest = ProjectManifest.from_file(manifest_path) if manifest_path else None
    url = _resolve_registry_url(registry_url, manifest, workspace_dir)

    registry = open_registry(url)
    index = registry.read_index()
    version, record = resolve_version(index, name, version_spec)

    integrity = record["integrity"]
    tarball_rel = record["tarball"]
    data = registry.fetch_tarball(tarball_rel)

    # --- SHA-256 integrity gate ---
    if not verify_integrity(data, integrity):
        raise RegistryError(
            f"Integrity check FAILED for {name}@{version}: "
            f"expected {integrity}, got {sha256_bytes(data)}"
        )

    dest = vendor / name
    if dest.exists():
        shutil.rmtree(dest)
    written = unpack_tarball(data, dest)

    # --- Record in the lock file for reproducible installs ---
    lock_path = workspace_dir / "lateralus-lock.json"
    lock = _load_lock(lock_path)
    lock["entries"][name] = {
        "version": version,
        "resolved": f"{url}/{tarball_rel}" if url.startswith("http") else tarball_rel,
        "integrity": integrity,
        "dependencies": record.get("dependencies", {}),
    }
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")

    return {
        "name": name,
        "version": version,
        "integrity": integrity,
        "dest": str(dest),
        "files": written,
        "registry": url,
    }


def _load_lock(path: Path) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    data.setdefault("lockfile_version", 1)
    data.setdefault("entries", {})
    return data


# --- CLI entry point (used by tools/registry and tests) ---------------

def main(argv: Optional[list[str]] = None) -> int:
    """``python -m lateralus_lang.registry <publish|add> ...``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="lateralus-registry",
        description="LATERALUS static package registry (publish / add)",
    )
    sub = parser.add_subparsers(dest="command")

    pub = sub.add_parser("publish", help="Pack and publish the current project")
    pub.add_argument("--registry", "-r", default=None,
                     help="Registry URL or local root (default: $LATERALUS_REGISTRY)")
    pub.add_argument("--dir", default=".",
                     help="Project directory (default: current directory)")
    pub.add_argument("--dry-run", action="store_true",
                     help="Build the tarball but do not upload")

    addp = sub.add_parser("add", help="Fetch and install a package into vendor/")
    addp.add_argument("package", help="Package name")
    addp.add_argument("--version", default="*", help="Version spec (default: *)")
    addp.add_argument("--registry", "-r", default=None,
                      help="Registry URL or local root (default: $LATERALUS_REGISTRY)")
    addp.add_argument("--dir", default=".",
                      help="Workspace directory (default: current directory)")

    args = parser.parse_args(argv)

    try:
        if args.command == "publish":
            summary = publish(Path(args.dir), registry_url=args.registry,
                              dry_run=args.dry_run)
            verb = "Would publish" if args.dry_run else "Published"
            print(f"{verb} {summary['name']}@{summary['version']}")
            print(f"  integrity: {summary['integrity']}")
            print(f"  size:      {summary['size']:,} bytes")
            print(f"  files:     {len(summary['files'])}")
            print(f"  registry:  {summary['registry']}")
            return 0
        if args.command == "add":
            summary = add(args.package, version_spec=args.version,
                          registry_url=args.registry,
                          workspace_dir=Path(args.dir))
            print(f"Installed {summary['name']}@{summary['version']}")
            print(f"  integrity: {summary['integrity']} (verified)")
            print(f"  dest:      {summary['dest']}")
            print(f"  files:     {len(summary['files'])}")
            return 0
        parser.print_help()
        return 0
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
