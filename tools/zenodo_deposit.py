#!/usr/bin/env python3
"""
Deposit a single PDF (or any artifact) to Zenodo as a standalone record.

Why this exists
---------------
The GitHub-Zenodo integration archives every tagged *release* of the repo as a
software record. Standalone publications - the PDFs under
docs/website/papers/pdf/ - benefit from their own Zenodo records with their own
DOIs so they can be cited independently of the source-code release.

Usage
-----
    export ZENODO_TOKEN=...                          # from zenodo.org/account/settings/applications/
    # (optional) point at the sandbox first to dry-run:
    export ZENODO_BASE=https://sandbox.zenodo.org    # default: https://zenodo.org

    python3 tools/zenodo_deposit.py \\
        --pdf docs/website/papers/pdf/lateralus-extensions-distribution.pdf \\
        --title "Lateralus Extensions: Distribution & Verification" \\
        --description-file docs/website/papers/src/lateralus-extensions-distribution.py \\
        --keywords vsce open-vsx publisher-verification cloudflare-pages \\
        --publish

Without --publish the deposit is left in 'draft' state so you can review it in
the Zenodo UI before minting the DOI. The --dry-run flag prints the JSON payload
and exits without contacting Zenodo at all.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE = os.environ.get("ZENODO_BASE", "https://zenodo.org").rstrip("/")


def _http(method: str, url: str, token: str, *, data: bytes | None = None,
          ctype: str | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if ctype:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def build_metadata(args: argparse.Namespace) -> dict:
    desc = args.description or ""
    if args.description_file and Path(args.description_file).exists():
        # Pull the abstract= block out of a paper source if present.
        raw = Path(args.description_file).read_text(encoding="utf-8")
        if "abstract=(" in raw:
            chunk = raw.split("abstract=(", 1)[1].split("),", 1)[0]
            desc = " ".join(p.strip().strip('"').strip("'") for p in chunk.splitlines() if p.strip())
        else:
            desc = raw[:2000]
    if not desc:
        desc = f"Standalone publication: {args.title}."

    meta = {
        "title": args.title,
        "upload_type": args.upload_type,
        "publication_type": args.publication_type if args.upload_type == "publication" else None,
        "description": desc,
        "creators": [{"name": "bad-antics", "affiliation": "Independent (lateralus.dev)"}],
        "license": args.license,
        "access_right": "open",
        "language": "eng",
        "keywords": list(args.keywords or []) + ["lateralus", "pipeline-native"],
        "related_identifiers": [
            {"identifier": "https://lateralus.dev",
             "relation": "isDocumentedBy", "resource_type": "publication-other"},
            {"identifier": "https://github.com/bad-antics/lateralus-lang",
             "relation": "isSupplementTo", "resource_type": "software"},
        ],
        "communities": [{"identifier": "compsci"}],
    }
    return {k: v for k, v in meta.items() if v is not None}


def deposit(args: argparse.Namespace) -> int:
    pdf = Path(args.pdf).resolve()
    if not pdf.exists():
        print(f"error: {pdf} does not exist", file=sys.stderr)
        return 2

    metadata = build_metadata(args)

    if args.dry_run:
        print(json.dumps({"metadata": metadata, "file": str(pdf)}, indent=2))
        return 0

    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        print("error: ZENODO_TOKEN environment variable not set", file=sys.stderr)
        print("       create one at zenodo.org/account/settings/applications/", file=sys.stderr)
        return 3

    base = DEFAULT_BASE
    print(f"==> creating empty deposition at {base}")
    code, dep = _http("POST", f"{base}/api/deposit/depositions", token,
                      data=b"{}", ctype="application/json")
    if code >= 300:
        print(f"error: create failed ({code}): {dep}", file=sys.stderr)
        return 4
    dep_id = dep["id"]
    bucket = dep["links"]["bucket"]
    print(f"    deposition id: {dep_id}")
    print(f"    bucket:        {bucket}")

    print(f"==> uploading {pdf.name} ({pdf.stat().st_size:,} bytes)")
    with pdf.open("rb") as fh:
        body = fh.read()
    code, _ = _http("PUT", f"{bucket}/{urllib.parse.quote(pdf.name)}", token,
                    data=body, ctype="application/octet-stream")
    if code >= 300:
        print(f"error: upload failed ({code})", file=sys.stderr)
        return 5

    print(f"==> writing metadata")
    code, _ = _http("PUT", f"{base}/api/deposit/depositions/{dep_id}", token,
                    data=json.dumps({"metadata": metadata}).encode("utf-8"),
                    ctype="application/json")
    if code >= 300:
        print(f"error: metadata write failed ({code})", file=sys.stderr)
        return 6

    if args.publish:
        print(f"==> publishing (this mints the DOI and is irreversible)")
        code, pub = _http("POST", f"{base}/api/deposit/depositions/{dep_id}/actions/publish",
                          token, data=b"")
        if code >= 300:
            print(f"error: publish failed ({code}): {pub}", file=sys.stderr)
            return 7
        doi = pub.get("doi") or pub.get("metadata", {}).get("doi")
        url = pub.get("links", {}).get("record_html") or pub.get("links", {}).get("html")
        print(f"    DOI: {doi}")
        print(f"    URL: {url}")
    else:
        print(f"==> deposition left in DRAFT state")
        print(f"    review at: {base}/deposit/{dep_id}")
        print(f"    add --publish to mint the DOI")

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pdf", required=True, help="Path to the PDF (or other artifact) to deposit")
    p.add_argument("--title", required=True, help="Record title")
    p.add_argument("--description", help="Inline description text")
    p.add_argument("--description-file",
                   help="Path to a paper-source .py to extract abstract=... from")
    p.add_argument("--keywords", nargs="*", default=[],
                   help="Extra keywords (lateralus + pipeline-native are appended)")
    p.add_argument("--upload-type", default="publication",
                   choices=["publication", "software", "dataset", "presentation",
                            "poster", "report", "other"])
    p.add_argument("--publication-type", default="report",
                   choices=["article", "preprint", "report", "book",
                            "thesis", "technicalnote", "workingpaper", "other"])
    p.add_argument("--license", default="MIT")
    p.add_argument("--publish", action="store_true",
                   help="Publish (mint DOI) immediately. Without this, leaves draft.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the metadata JSON and exit without contacting Zenodo")
    args = p.parse_args()
    return deposit(args)


if __name__ == "__main__":
    sys.exit(main())
