#!/usr/bin/env python3
"""Rebuild ``index.json`` from the archives already sitting in a registry.

Run this after copying a registry between hosts, after deleting a bad version
by hand, or in CI as a drift check.

    python tools/registry/build_index.py /srv/lateralus-registry
    python tools/registry/build_index.py /srv/lateralus-registry --check

``--check`` exits 1 when the index on disk disagrees with the archives, which
is what you want in a pre-deploy step: it catches a half-finished upload
before anyone tries to install from it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lateralus_lang.registry import INDEX_FILE, rebuild_index  # noqa: E402


def _summary(index) -> tuple[int, int]:
    packages = len(index.packages)
    versions = sum(len(entry.get("versions") or {})
                   for entry in index.packages.values())
    return packages, versions


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild a Lateralus registry index.json from its archives")
    parser.add_argument("root", nargs="?", default=".",
                        help="registry root directory (default: current directory)")
    parser.add_argument("--check", action="store_true",
                        help="do not write; exit 1 if index.json is out of date")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    index = rebuild_index(root)
    packages, versions = _summary(index)
    target = root / INDEX_FILE
    fresh = index.to_bytes()

    if args.check:
        current = target.read_bytes() if target.exists() else b""
        try:
            current_packages = (json.loads(current.decode("utf-8"))
                                .get("packages") or {})
        except (UnicodeDecodeError, json.JSONDecodeError):
            current_packages = None
        if current_packages is None:
            print(f"index.json is missing or unreadable: {target}", file=sys.stderr)
            return 1
        if current_packages != index.packages:
            print(f"index.json is out of date with the archives in {root}",
                  file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"index.json is current ({packages} package(s), "
                  f"{versions} version(s))")
        return 0

    target.write_bytes(fresh)
    if not args.quiet:
        print(f"rebuilt {target}")
        print(f"  packages: {packages}")
        print(f"  versions: {versions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
