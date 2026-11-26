#!/usr/bin/env python3
"""
tools/registry — static LATERALUS package registry (MVP).

A *registry* is just a directory laid out like this::

    registry/
      index.json                       # the catalog (see below)
      packages/
        <name>/
          <name>-<version>.tar.gz      # deterministic package tarballs

Because it is entirely static, you can host it anywhere that serves files:

  * **Cloudflare Pages / any static host** — commit the directory, point a
    domain at it. ``lateralus add`` reads ``index.json`` + tarballs over HTTP.
  * **Amazon S3** — ``aws s3 sync registry/ s3://my-bucket/registry/`` and set
    ``LATERALUS_REGISTRY=https://my-bucket.s3.amazonaws.com/registry``.
  * **Cloudflare R2** — same as S3, ``r2://`` / R2 public bucket URL.
  * **Local directory** — great for CI and tests; ``--registry ./registry``.

index.json shape::

    {
      "registry_version": 1,
      "packages": {
        "<name>": {
          "versions": {
            "<version>": {
              "tarball": "packages/<name>/<name>-<version>.tar.gz",
              "integrity": "sha256-<hex>",
              "size": 12345,
              "dependencies": {"other-pkg": "^1.0.0"},
              "lateralus_version": ">=1.7.0"
            }
          }
        }
      }
    }

Usage::

    # Publish the project in the current directory to a local registry dir:
    lateralus publish --registry ./registry

    # ...or via this helper:
    python3 tools/registry/publish.py --registry ./registry

    # Consume a package into ./vendor with SHA-256 verification:
    lateralus add mypkg --registry ./registry

The heavy lifting lives in ``lateralus_lang/registry.py``; this script is a thin
wrapper so the registry can be driven without installing the package.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make ``lateralus_lang`` importable when run straight from a checkout.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lateralus_lang.registry import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
