"""
Lateralus Package Registry MVP Tooling
Provides static registry generation, publishing (`lateralus publish`), and dependency fetching (`lateralus add`).
"""

import os
import sys
import json
import tarfile
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def parse_toml(content):
    if tomllib is not None:
        return tomllib.loads(content)
    # Basic fallback parser if tomllib/tomli is missing in minimal environments
    data = {}
    current_section = None
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            data[current_section] = {}
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if current_section:
                data[current_section][key] = val
            else:
                data[key] = val
    return data


def compute_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def pack_package(project_dir, output_tar_path):
    project_path = Path(project_dir)
    toml_path = project_path / "lateralus.toml"
    if not toml_path.exists():
        raise FileNotFoundError(f"lateralus.toml not found in {project_dir}")

    config = parse_toml(toml_path.read_text(encoding="utf-8"))
    pkg_info = config.get("package", config)
    name = pkg_info.get("name", "unknown")
    version = pkg_info.get("version", "0.1.0")

    with tarfile.open(output_tar_path, "w:gz") as tar:
        for item in project_path.iterdir():
            if item.name in [".git", "vendor", "target", "__pycache__", output_tar_path]:
                continue
            tar.add(item, arcname=item.name)

    return name, version


def publish_package(project_dir, registry_dir):
    project_path = Path(project_dir)
    registry_path = Path(registry_dir)
    registry_path.mkdir(parents=True, exist_ok=True)

    tar_path = registry_path / "temp_pkg.tar.gz"
    name, version = pack_package(project_path, tar_path)

    digest = compute_sha256(tar_path)
    final_tar_name = f"{name}-{version}.tar.gz"
    final_tar_path = registry_path / final_tar_name
    tar_path.rename(final_tar_path)

    index_path = registry_path / "index.json"
    if index_path.exists():
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index_data = {"packages": {}}

    if name not in index_data["packages"]:
        index_data["packages"][name] = {}

    index_data["packages"][name][version] = {
        "filename": final_tar_name,
        "sha256": digest,
        "size": final_tar_path.stat().st_size
    }

    index_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    print(f"Successfully published {name} v{version} (sha256: {digest})")
    return digest


def add_package(name, version, registry_url, workspace_dir):
    workspace_path = Path(workspace_dir)
    vendor_dir = workspace_path / "vendor" / name
    vendor_dir.mkdir(parents=True, exist_ok=True)

    if registry_url.startswith("http://") or registry_url.startswith("https://"):
        index_url = f"{registry_url.rstrip('/')}/index.json"
        req = urllib.request.urlopen(index_url)
        index_data = json.loads(req.read().decode("utf-8"))
    else:
        reg_path = Path(registry_url)
        index_path = reg_path / "index.json"
        index_data = json.loads(index_path.read_text(encoding="utf-8"))

    if name not in index_data.get("packages", {}):
        raise ValueError(f"Package {name} not found in registry index")

    pkg_versions = index_data["packages"][name]
    if not version:
        version = sorted(pkg_versions.keys())[-1]

    if version not in pkg_versions:
        raise ValueError(f"Version {version} of package {name} not found in registry index")

    pkg_meta = pkg_versions[version]
    filename = pkg_meta["filename"]
    expected_sha256 = pkg_meta["sha256"]

    tar_temp = workspace_path / f"{name}-{version}.tar.gz"
    if registry_url.startswith("http://") or registry_url.startswith("https://"):
        tar_url = f"{registry_url.rstrip('/')}/{filename}"
        urllib.request.urlretrieve(tar_url, tar_temp)
    else:
        src_tar = Path(registry_url) / filename
        tar_temp.write_bytes(src_tar.read_bytes())

    actual_sha256 = compute_sha256(tar_temp)
    if actual_sha256 != expected_sha256:
        tar_temp.unlink(missing_ok=True)
        raise ValueError(f"SHA-256 mismatch for {name}! Expected {expected_sha256}, got {actual_sha256}")

    with tarfile.open(tar_temp, "r:gz") as tar:
        tar.extractall(path=vendor_dir)

    tar_temp.unlink(missing_ok=True)

    # Update lock file
    lock_path = workspace_path / "lateralus-lock.json"
    if lock_path.exists():
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
    else:
        lock_data = {"dependencies": {}}

    lock_data["dependencies"][name] = {
        "version": version,
        "sha256": actual_sha256
    }
    lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
    print(f"Successfully added {name} v{version} to vendor/ and updated lateralus-lock.json")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: registry.py [publish <project_dir> <registry_dir> | add <name> [version] <registry_url> <workspace_dir>]")
        sys.exit(1)

    cmd = args[0]
    if cmd == "publish":
        proj = args[1] if len(args) > 1 else "."
        reg = args[2] if len(args) > 2 else "./registry_root"
        publish_package(proj, reg)
    elif cmd == "add":
        pkg_name = args[1]
        ver = args[2] if len(args) > 3 and not args[2].startswith("http") and not Path(args[2]).exists() else ""
        idx = 2 if not ver else 3
        reg_url = args[idx] if len(args) > idx else "./registry_root"
        ws = args[idx+1] if len(args) > idx+1 else "."
        if not ver:
            ver = ""
        add_package(pkg_name, ver, reg_url, ws)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
