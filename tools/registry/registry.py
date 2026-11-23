"""
tools/registry/registry.py — Static S3 / R2 / Cloudflare Pages package registry for Lateralus.

Layout of a static registry directory / bucket:
    registry_root/
        index.json
        packages/
            <pkg_name>/
                <pkg_name>-<version>.tar.gz

No server required: `index.json` and `packages/**/*.tar.gz` can be served
directly from an S3 bucket, Cloudflare R2 bucket, Cloudflare Pages, or a
local filesystem directory.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

DEFAULT_REGISTRY_URL = "https://registry.lateralus.dev"
DEFAULT_STATIC_REGISTRY_DIR = Path(__file__).resolve().parent


class IntegrityError(Exception):
    """Raised when a package tarball's SHA-256 digest does not match the pinned hash."""


@dataclass
class RegistryEntry:
    """Metadata for a single published version of a package in index.json."""
    name: str
    version: str
    tarball: str          # relative path (e.g. "packages/foo/foo-0.1.0.tar.gz") or full URL
    sha256: str           # "sha256-<64 hex chars>"
    size: int = 0
    description: str = ""
    license: str = "MIT"
    dependencies: Dict[str, str] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)

    @property
    def hex_digest(self) -> str:
        if self.sha256.startswith("sha256-"):
            return self.sha256[len("sha256-"):]
        return self.sha256

    @property
    def normalized_integrity(self) -> str:
        return f"sha256-{self.hex_digest}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "tarball": self.tarball,
            "sha256": self.normalized_integrity,
            "size": self.size,
            "description": self.description,
            "license": self.license,
            "dependencies": self.dependencies,
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegistryEntry":
        raw_sha = data.get("sha256") or data.get("integrity") or ""
        if raw_sha and not raw_sha.startswith("sha256-"):
            raw_sha = f"sha256-{raw_sha}"
        return cls(
            name=data["name"],
            version=str(data["version"]),
            tarball=data["tarball"],
            sha256=raw_sha,
            size=int(data.get("size", 0)),
            description=data.get("description", ""),
            license=data.get("license", "MIT"),
            dependencies=dict(data.get("dependencies", {})),
            files=list(data.get("files", [])),
        )


@dataclass
class RegistryIndex:
    """Represents the static `index.json` manifest of a Lateralus registry."""
    schema_version: int = 1
    packages: Dict[str, Dict[str, RegistryEntry]] = field(default_factory=dict)

    def add_entry(self, entry: RegistryEntry) -> None:
        pkg_versions = self.packages.setdefault(entry.name, {})
        pkg_versions[entry.version] = entry

    def get_versions(self, name: str) -> Dict[str, RegistryEntry]:
        return self.packages.get(name, {})

    def resolve_version(self, name: str, version_spec: str = "*") -> Optional[RegistryEntry]:
        """Resolve the highest version of `name` compatible with `version_spec`."""
        from lateralus_lang.package_manager import SemVer

        versions = self.get_versions(name)
        if not versions:
            return None

        candidates: List[Tuple[SemVer, RegistryEntry]] = []
        for ver_str, entry in versions.items():
            try:
                sv = SemVer.parse(ver_str)
            except Exception:
                continue
            if sv.compatible_with(version_spec):
                candidates.append((sv, entry))

        if not candidates:
            return None

        candidates.sort(key=lambda pair: pair[0])
        return candidates[-1][1]

    def to_dict(self) -> dict:
        out_pkgs: Dict[str, dict] = {}
        for pkg_name in sorted(self.packages.keys()):
            ver_map = self.packages[pkg_name]
            latest_ver = ""
            if ver_map:
                from lateralus_lang.package_manager import SemVer
                try:
                    latest_ver = max(ver_map.keys(), key=lambda v: SemVer.parse(v))
                except Exception:
                    latest_ver = sorted(ver_map.keys())[-1]
            out_pkgs[pkg_name] = {
                "name": pkg_name,
                "latest": latest_ver,
                "versions": {
                    v: ver_map[v].to_dict()
                    for v in sorted(ver_map.keys())
                },
            }
        return {
            "schema_version": self.schema_version,
            "packages": out_pkgs,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict) -> "RegistryIndex":
        idx = cls(schema_version=int(data.get("schema_version", 1)))
        raw_pkgs = data.get("packages", {})
        for pkg_name, pkg_info in raw_pkgs.items():
            versions_dict = pkg_info.get("versions", pkg_info) if isinstance(pkg_info, dict) else {}
            for ver_str, entry_data in versions_dict.items():
                if not isinstance(entry_data, dict):
                    continue
                entry_copy = dict(entry_data)
                entry_copy.setdefault("name", pkg_name)
                entry_copy.setdefault("version", ver_str)
                idx.add_entry(RegistryEntry.from_dict(entry_copy))
        return idx

    @classmethod
    def from_json(cls, text: str) -> "RegistryIndex":
        if not text.strip():
            return cls()
        return cls.from_dict(json.loads(text))

    @classmethod
    def from_file(cls, path: Path) -> "RegistryIndex":
        if not path.exists():
            return cls()
        return cls.from_json(path.read_text(encoding="utf-8"))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")


def compute_sha256(data_or_path: Union[bytes, Path]) -> str:
    """Compute a normalized `sha256-<hex>` digest for bytes or a file."""
    h = hashlib.sha256()
    if isinstance(data_or_path, (bytes, bytearray)):
        h.update(data_or_path)
    else:
        with open(data_or_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    return f"sha256-{h.hexdigest()}"


def build_deterministic_tarball(
    project_dir: Path,
    files: List[str],
    output_path: Optional[Path] = None,
) -> Tuple[bytes, str]:
    """Create a byte-for-byte reproducible `.tar.gz` archive from `files` in `project_dir`.

    All tar headers have `mtime=0`, `uid=0`, `gid=0`, `uname=""`, `gname=""`,
    and normalized permissions (`0o644`), and the outer gzip stream has `mtime=0`.

    Returns `(tarball_bytes, "sha256-<hex>")`.
    """
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as gz:
        with tarfile.open(mode="w", fileobj=gz, format=tarfile.PAX_FORMAT) as tf:
            for rel_path in sorted(set(files)):
                full_path = project_dir / rel_path
                if not full_path.is_file():
                    continue
                raw = full_path.read_bytes()
                ti = tarfile.TarInfo(name=rel_path.replace("\\", "/"))
                ti.size = len(raw)
                ti.mtime = 0
                ti.uid = 0
                ti.gid = 0
                ti.uname = ""
                ti.gname = ""
                ti.mode = 0o644
                ti.type = tarfile.REGTYPE
                tf.addfile(ti, io.BytesIO(raw))

    tarball_bytes = buf.getvalue()
    digest = compute_sha256(tarball_bytes)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(tarball_bytes)

    return tarball_bytes, digest


def unpack_tarball_safely(
    tarball_bytes: bytes,
    dest_dir: Path,
    expected_sha256: Optional[str] = None,
) -> str:
    """Verify `expected_sha256` (if provided) and unpack `tarball_bytes` into `dest_dir`.

    Guards against path traversal (`..` or absolute paths).
    Returns the verified `sha256-<hex>` digest.
    """
    actual_sha256 = compute_sha256(tarball_bytes)
    if expected_sha256:
        norm_expected = (
            expected_sha256
            if expected_sha256.startswith("sha256-")
            else f"sha256-{expected_sha256}"
        )
        if actual_sha256 != norm_expected:
            raise IntegrityError(
                f"SHA-256 integrity mismatch: expected {norm_expected}, got {actual_sha256}"
            )

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_root = dest_dir.resolve()

    with gzip.GzipFile(fileobj=io.BytesIO(tarball_bytes), mode="rb") as gz:
        with tarfile.open(fileobj=gz, mode="r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                rel = Path(member.name)
                if rel.is_absolute() or ".." in rel.parts:
                    raise IntegrityError(f"Unsafe path in package archive: {member.name}")
                target_path = (dest_root / rel).resolve()
                if not str(target_path).startswith(str(dest_root)):
                    raise IntegrityError(f"Archive member escapes destination: {member.name}")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                extracted = tf.extractfile(member)
                if extracted is not None:
                    target_path.write_bytes(extracted.read())

    return actual_sha256


class RegistryClient:
    """Client for interacting with a static Lateralus package registry.

    Supports:
    - Local filesystem directories (`/path/to/registry` or `file:///path/to/registry`)
    - HTTP / HTTPS static endpoints (`https://registry.lateralus.dev` or Cloudflare R2 / S3 URLs)
    - S3 URIs (`s3://bucket/prefix`)
    """

    def __init__(self, registry_url: Optional[Union[str, Path]] = None):
        env_url = os.environ.get("LATERALUS_REGISTRY_URL")
        raw = str(registry_url or env_url or DEFAULT_STATIC_REGISTRY_DIR)
        self.registry_url = raw.rstrip("/")

    @property
    def is_local(self) -> bool:
        if self.registry_url.startswith(("http://", "https://", "s3://")):
            return False
        return True

    @property
    def local_root(self) -> Path:
        if self.registry_url.startswith("file://"):
            parsed = urllib.parse.urlparse(self.registry_url)
            return Path(urllib.parse.unquote(parsed.path)).resolve()
        return Path(self.registry_url).resolve()

    def fetch_index(self) -> RegistryIndex:
        """Load `index.json` from the configured registry."""
        if self.is_local:
            return RegistryIndex.from_file(self.local_root / "index.json")

        if self.registry_url.startswith("s3://"):
            index_uri = f"{self.registry_url}/index.json"
            proc = subprocess.run(
                ["aws", "s3", "cp", index_uri, "-"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return RegistryIndex()
            return RegistryIndex.from_json(proc.stdout)

        index_url = f"{self.registry_url}/index.json"
        req = urllib.request.Request(index_url, headers={"User-Agent": "lateralus-pkg/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return RegistryIndex.from_json(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return RegistryIndex()
            raise

    def fetch_tarball(self, entry: RegistryEntry) -> bytes:
        """Download or read the package tarball for `entry`."""
        tarball_ref = entry.tarball
        if tarball_ref.startswith(("http://", "https://")):
            req = urllib.request.Request(tarball_ref, headers={"User-Agent": "lateralus-pkg/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()

        if self.is_local:
            tarball_path = self.local_root / tarball_ref
            if not tarball_path.exists():
                raise FileNotFoundError(f"Package tarball not found: {tarball_path}")
            return tarball_path.read_bytes()

        if self.registry_url.startswith("s3://"):
            s3_uri = f"{self.registry_url}/{tarball_ref.lstrip('/')}"
            proc = subprocess.run(
                ["aws", "s3", "cp", s3_uri, "-"],
                capture_output=True,
                check=True,
            )
            return proc.stdout

        full_url = f"{self.registry_url}/{tarball_ref.lstrip('/')}"
        req = urllib.request.Request(full_url, headers={"User-Agent": "lateralus-pkg/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()

    def publish_project(self, project_dir: Path) -> RegistryEntry:
        """Pack `project_dir` deterministically and publish it to the registry."""
        from lateralus_lang.package_manager import MANIFEST_FILE, PackageBundle, ProjectManifest

        manifest_path = project_dir / MANIFEST_FILE
        if not manifest_path.exists():
            raise FileNotFoundError(f"No {MANIFEST_FILE} found in {project_dir}")

        manifest = ProjectManifest.from_file(manifest_path)
        bundle = PackageBundle.create(project_dir, manifest)
        tarball_bytes, sha256_digest = build_deterministic_tarball(project_dir, bundle.files)

        rel_tarball = f"packages/{manifest.name}/{manifest.name}-{manifest.version}.tar.gz"
        deps_map = {k: v.version for k, v in manifest.dependencies.items()}

        entry = RegistryEntry(
            name=manifest.name,
            version=manifest.version,
            tarball=rel_tarball,
            sha256=sha256_digest,
            size=len(tarball_bytes),
            description=manifest.description,
            license=manifest.license,
            dependencies=deps_map,
            files=bundle.files,
        )

        index = self.fetch_index()
        index.add_entry(entry)
        index_bytes = index.to_json().encode("utf-8")

        if self.is_local:
            root = self.local_root
            tarball_dest = root / rel_tarball
            tarball_dest.parent.mkdir(parents=True, exist_ok=True)
            tarball_dest.write_bytes(tarball_bytes)
            (root / "index.json").write_bytes(index_bytes)
            return entry

        if self.registry_url.startswith("s3://"):
            self._upload_s3(f"{self.registry_url}/{rel_tarball}", tarball_bytes, "application/gzip")
            self._upload_s3(f"{self.registry_url}/index.json", index_bytes, "application/json")
            return entry

        # HTTP / HTTPS PUT (S3 / R2 / Cloudflare Pages / WebDAV compatible)
        self._upload_http(f"{self.registry_url}/{rel_tarball}", tarball_bytes, "application/gzip")
        self._upload_http(f"{self.registry_url}/index.json", index_bytes, "application/json")
        return entry

    def install_package(
        self,
        name: str,
        version_spec: str = "*",
        vendor_dir: Optional[Path] = None,
        pinned_sha256: Optional[str] = None,
    ) -> Tuple[RegistryEntry, Path]:
        """Fetch `name` matching `version_spec`, verify SHA-256, and unpack into `vendor/<name>`."""
        index = self.fetch_index()
        entry = index.resolve_version(name, version_spec)
        if entry is None:
            raise ValueError(
                f"Package '{name}' matching version '{version_spec}' not found in registry ({self.registry_url})"
            )

        expected_hash = pinned_sha256 or entry.sha256
        if pinned_sha256:
            norm_pin = pinned_sha256 if pinned_sha256.startswith("sha256-") else f"sha256-{pinned_sha256}"
            if entry.normalized_integrity != norm_pin:
                raise IntegrityError(
                    f"Pinned hash mismatch for {name}@{entry.version}: "
                    f"lockfile expects {norm_pin}, registry index has {entry.normalized_integrity}"
                )

        tarball_bytes = self.fetch_tarball(entry)
        target_vendor_root = vendor_dir if vendor_dir is not None else (Path.cwd() / "vendor")
        pkg_dest = target_vendor_root / entry.name

        unpack_tarball_safely(tarball_bytes, pkg_dest, expected_sha256=expected_hash)
        return entry, pkg_dest

    @staticmethod
    def _upload_http(url: str, payload: bytes, content_type: str) -> None:
        headers = {
            "Content-Type": content_type,
            "User-Agent": "lateralus-pkg/1.0",
        }
        token = os.environ.get("LATERALUS_REGISTRY_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=payload, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201, 204):
                raise RuntimeError(f"Registry upload failed with HTTP {resp.status} for {url}")

    @staticmethod
    def _upload_s3(s3_uri: str, payload: bytes, content_type: str) -> None:
        proc = subprocess.run(
            ["aws", "s3", "cp", "-", s3_uri, "--content-type", content_type],
            input=payload,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"S3 upload failed for {s3_uri}: {proc.stderr.decode('utf-8', errors='replace')}"
            )


def rebuild_index(registry_dir: Path) -> RegistryIndex:
    """Scan `registry_dir/packages/**/*.tar.gz` and rebuild `registry_dir/index.json`."""
    from lateralus_lang.package_manager import MANIFEST_FILE, ProjectManifest

    index = RegistryIndex.from_file(registry_dir / "index.json")
    packages_dir = registry_dir / "packages"
    if not packages_dir.exists():
        index.save(registry_dir / "index.json")
        return index

    for tarball_path in sorted(packages_dir.rglob("*.tar.gz")):
        raw_bytes = tarball_path.read_bytes()
        sha256_digest = compute_sha256(raw_bytes)
        rel_path = str(tarball_path.relative_to(registry_dir)).replace("\\", "/")

        pkg_name = tarball_path.parent.name
        stem = tarball_path.name[:-len(".tar.gz")]
        version = stem[len(pkg_name) + 1:] if stem.startswith(f"{pkg_name}-") else "0.1.0"
        description = ""
        license_name = "MIT"
        deps: Dict[str, str] = {}
        files: List[str] = []

        with gzip.GzipFile(fileobj=io.BytesIO(raw_bytes), mode="rb") as gz:
            with tarfile.open(fileobj=gz, mode="r:*") as tf:
                for member in tf.getmembers():
                    if member.isfile():
                        files.append(member.name)
                        if Path(member.name).name == MANIFEST_FILE:
                            fobj = tf.extractfile(member)
                            if fobj is not None:
                                manifest_text = fobj.read().decode("utf-8", errors="replace")
                                from lateralus_lang.package_manager import parse_toml
                                m = ProjectManifest._from_data(parse_toml(manifest_text))
                                pkg_name = m.name
                                version = m.version
                                description = m.description
                                license_name = m.license
                                deps = {k: v.version for k, v in m.dependencies.items()}

        entry = RegistryEntry(
            name=pkg_name,
            version=version,
            tarball=rel_path,
            sha256=sha256_digest,
            size=len(raw_bytes),
            description=description,
            license=license_name,
            dependencies=deps,
            files=sorted(files),
        )
        index.add_entry(entry)

    index.save(registry_dir / "index.json")
    return index


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m tools.registry.registry",
        description="Lateralus Static Package Registry CLI (S3 / R2 / Cloudflare Pages)",
    )
    sub = parser.add_subparsers(dest="cmd")

    init_p = sub.add_parser("init", help="Initialize a static registry directory")
    init_p.add_argument("dir", nargs="?", default=str(DEFAULT_STATIC_REGISTRY_DIR))

    reb_p = sub.add_parser("rebuild", help="Rebuild index.json by scanning packages/**/*.tar.gz")
    reb_p.add_argument("dir", nargs="?", default=str(DEFAULT_STATIC_REGISTRY_DIR))

    ns = parser.parse_args(argv)
    if ns.cmd == "init":
        reg_dir = Path(ns.dir).resolve()
        (reg_dir / "packages").mkdir(parents=True, exist_ok=True)
        idx_path = reg_dir / "index.json"
        if not idx_path.exists():
            RegistryIndex().save(idx_path)
        print(f"Initialized static registry at {reg_dir}")
        return 0
    elif ns.cmd == "rebuild":
        reg_dir = Path(ns.dir).resolve()
        idx = rebuild_index(reg_dir)
        total = sum(len(v) for v in idx.packages.values())
        print(f"Rebuilt {reg_dir / 'index.json'} ({len(idx.packages)} packages, {total} versions)")
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
