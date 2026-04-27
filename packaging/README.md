# Distribution Packaging

This directory holds packaging manifests so downstream maintainers can
adopt Lateralus on their platform without reverse-engineering the layout.

| File | Target | Submission status |
|------|--------|-------------------|
| [homebrew/lateralus-lang.rb](homebrew/lateralus-lang.rb) | Homebrew tap (macOS / Linuxbrew) | Ready for `homebrew/core` PR after `brew audit --strict --new --online` |
| [aur/PKGBUILD](aur/PKGBUILD) | Arch User Repository | Ready for `aurpublish lateralus-lang` |
| [snap/snapcraft.yaml](snap/snapcraft.yaml) | Canonical Snap Store | Ready for `snapcraft register lateralus && snapcraft upload` |
| [flatpak/dev.lateralus.Toolchain.yaml](flatpak/dev.lateralus.Toolchain.yaml) | Flathub | Submit to `flathub/flathub` repo as new app PR |

## Maintainer checklist before each release

1. Bump `version` / `pkgver` in all four files
2. Re-run `pip download lateralus-lang==X.Y.Z --no-binary :all: --no-deps -d /tmp/sdist` to obtain canonical SHA256
3. Replace `SKIP` / `REPLACE_WITH_*` placeholders
4. Lint: `brew audit`, `namcap PKGBUILD`, `snapcraft lint`, `flatpak-builder --dry-run`
5. Open downstream PR / push to AUR / call `snapcraft upload` / push to flathub fork

## Already-published registries (no manifest needed in this repo)

- **PyPI** — `lateralus-lang` (canonical source-of-truth)
- **npm** — 9 packages (grammars + CLI + LSP + toolkit)
- **Open VSX / VS Marketplace** — extension `lateralus.lateralus-lang`
- **GHCR** — `ghcr.io/bad-antics/lateralus-lang:latest`
- **GitHub Releases** — wheels, sdists, VSIX, bootable ISO
