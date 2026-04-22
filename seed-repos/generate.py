#!/usr/bin/env python3
"""
generate.py — materialise seed-repos/staged/{name}/ for every manifest entry.

Each output directory is a self-contained, git-ready repo with:
    .gitattributes    (forces GitHub language bar -> Lateralus)
    LICENSE           (MIT)
    README.md         (rendered from template)
    main.ltl          (per-project source; template-driven)

Usage:
    python3 generate.py
    python3 generate.py --only ltl-json-cli,ltl-snake
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: pyyaml is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
PROJECTS = ROOT / "projects"
STAGED = ROOT / "staged"


def load_manifest() -> dict:
    return yaml.safe_load((ROOT / "manifest.yml").read_text())


def render_readme(name: str, tagline: str, tree: str) -> str:
    tmpl = (TEMPLATES / "README.md.tmpl").read_text()
    return (tmpl
            .replace("{{NAME}}", name)
            .replace("{{TAGLINE}}", tagline)
            .replace("{{TREE}}", tree))


def project_source_files(repo: dict) -> dict[str, str]:
    """Return {relative_path: content} for this repo's source.

    Pulls from seed-repos/projects/{source_template}/ if that directory
    exists; otherwise emits a minimal placeholder main.ltl with the
    right shape so that the repo contains a detectable `.ltl` file.
    """
    tmpl_dir = PROJECTS / repo["source_template"]
    if tmpl_dir.is_dir():
        out: dict[str, str] = {}
        for src in tmpl_dir.rglob("*"):
            if src.is_file():
                rel = src.relative_to(tmpl_dir).as_posix()
                out[rel] = src.read_text()
        return out
    # Minimal placeholder
    return {
        "main.ltl": _placeholder(repo),
    }


def _placeholder(repo: dict) -> str:
    return f"""// {repo['name']}/main.ltl
//
// {repo['tagline']}
//
// This is an early skeleton — contribution is welcome! See the
// README for build instructions.

import std::io
import std::fmt

pub fn main(args: [str]) -> Int {{
    io::println("{repo['name']} v{repo.get('version', '0.1.0')}")
    io::println("{repo['tagline']}")
    0
}}
"""


def render_tree(files: dict[str, str]) -> str:
    lines = []
    for path in sorted(files.keys()):
        lines.append(".\n├── .gitattributes\n├── LICENSE\n├── README.md\n")
        break
    for path in sorted(files.keys()):
        lines.append(f"└── {path}")
    return "".join(lines)


def materialise(repo: dict, force: bool) -> Path:
    out = STAGED / repo["name"]
    if out.exists():
        if not force:
            return out
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    # Shared templates
    shutil.copy(TEMPLATES / ".gitattributes", out / ".gitattributes")
    shutil.copy(TEMPLATES / "LICENSE", out / "LICENSE")

    # Per-project source
    files = project_source_files(repo)
    for rel, content in files.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

    # Rendered README
    tree = render_tree(files)
    (out / "README.md").write_text(
        render_readme(repo["name"], repo["tagline"], tree)
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="Comma-separated list of repo names")
    ap.add_argument("--force", action="store_true", help="Overwrite existing staged dirs")
    args = ap.parse_args()

    manifest = load_manifest()
    selected = set(args.only.split(",")) if args.only else None

    STAGED.mkdir(exist_ok=True)
    count = 0
    for repo in manifest["repos"]:
        if selected and repo["name"] not in selected:
            continue
        path = materialise(repo, force=args.force)
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        n_files = sum(1 for _ in path.rglob("*") if _.is_file())
        print(f"  staged  {repo['name']:<28} {n_files:>2} files, {size:>6} bytes")
        count += 1

    print(f"\n{count} repo(s) staged in {STAGED.relative_to(ROOT.parent)}/")
    print("\nNext:  GITHUB_TOKEN=... ./publish.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
