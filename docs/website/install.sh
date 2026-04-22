#!/usr/bin/env bash
# Lateralus Language Installer
# Usage: curl -fsSL https://lateralus.dev/install.sh | bash
set -euo pipefail

VERSION="${LATERALUS_VERSION:-latest}"
INSTALL_DIR="${LATERALUS_INSTALL_DIR:-$HOME/.lateralus}"
BIN_DIR="${LATERALUS_BIN_DIR:-$INSTALL_DIR/bin}"

REPO="bad-antics/lateralus-lang"
GITHUB_API="https://api.github.com/repos/$REPO"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}=>${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }

# Detect OS/arch
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64)  ARCH="x86_64" ;;
    aarch64|arm64) ARCH="aarch64" ;;
    *)             fail "Unsupported architecture: $ARCH" ;;
esac

case "$OS" in
    linux)  PLATFORM="linux" ;;
    darwin) PLATFORM="macos" ;;
    *)      fail "Unsupported OS: $OS" ;;
esac

echo ""
echo "  ◇◉✦⊕ Lateralus Language Installer ⊕✦◉◇"
echo ""

# Resolve version
if [ "$VERSION" = "latest" ]; then
    info "Fetching latest version..."
    VERSION=$(curl -fsSL "$GITHUB_API/releases/latest" 2>/dev/null | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"//;s/".*//')
    [ -z "$VERSION" ] && fail "Could not determine latest version"
fi
info "Installing Lateralus $VERSION for $PLATFORM-$ARCH"

# Try pip install first (most reliable for Python-based distribution)
if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
    PIP=$(command -v pip3 || command -v pip)
    info "Installing via pip..."
    if $PIP install "lateralus-lang>=${VERSION#v}" 2>/dev/null; then
        ok "Installed via pip"
        lateralus --version 2>/dev/null && ok "Lateralus is ready!" || ok "Installed. Run: lateralus --version"
        exit 0
    fi
fi

# Fallback: download release tarball
mkdir -p "$BIN_DIR"
TARBALL="lateralus-${VERSION}-${PLATFORM}-${ARCH}.tar.gz"
DOWNLOAD_URL="https://github.com/$REPO/releases/download/$VERSION/$TARBALL"

info "Downloading $TARBALL..."
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

if curl -fsSL "$DOWNLOAD_URL" -o "$TMPDIR/$TARBALL" 2>/dev/null; then
    # Verify SHA-256 checksum if available
    CHECKSUM_URL="https://github.com/$REPO/releases/download/$VERSION/SHA256SUMS"
    if curl -fsSL "$CHECKSUM_URL" -o "$TMPDIR/SHA256SUMS" 2>/dev/null; then
        info "Verifying checksum..."
        EXPECTED=$(grep "$TARBALL" "$TMPDIR/SHA256SUMS" | awk '{print $1}')
        if [ -n "$EXPECTED" ]; then
            if command -v sha256sum &>/dev/null; then
                ACTUAL=$(sha256sum "$TMPDIR/$TARBALL" | awk '{print $1}')
            elif command -v shasum &>/dev/null; then
                ACTUAL=$(shasum -a 256 "$TMPDIR/$TARBALL" | awk '{print $1}')
            else
                info "No sha256sum available — skipping verification"
                ACTUAL="$EXPECTED"
            fi
            [ "$ACTUAL" != "$EXPECTED" ] && fail "Checksum mismatch! Expected $EXPECTED, got $ACTUAL"
            ok "Checksum verified"
        else
            info "No checksum entry for $TARBALL — skipping verification"
        fi
    else
        info "No SHA256SUMS file found for $VERSION — skipping verification"
    fi
    tar xzf "$TMPDIR/$TARBALL" -C "$BIN_DIR" 2>/dev/null
    chmod +x "$BIN_DIR/lateralus" 2>/dev/null
    ok "Installed to $BIN_DIR/lateralus"
else
    info "No binary release found, falling back to source install..."
    if command -v git &>/dev/null; then
        git clone --depth 1 "https://github.com/$REPO.git" "$INSTALL_DIR/src" 2>/dev/null
        if [ -f "$INSTALL_DIR/src/setup.py" ] || [ -f "$INSTALL_DIR/src/pyproject.toml" ]; then
            cd "$INSTALL_DIR/src"
            pip3 install -e . 2>/dev/null || pip install -e . 2>/dev/null
            ok "Installed from source"
        fi
    else
        fail "Could not install. Please install manually: pip install lateralus-lang"
    fi
fi

# Add to PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    SHELL_RC=""
    case "${SHELL:-/bin/bash}" in
        */zsh)  SHELL_RC="$HOME/.zshrc" ;;
        */bash) SHELL_RC="$HOME/.bashrc" ;;
        */fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
    esac
    if [ -n "$SHELL_RC" ]; then
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
        info "Added $BIN_DIR to PATH in $SHELL_RC"
    fi
fi

echo ""
ok "Lateralus $VERSION installed!"
echo ""
echo "  Run: lateralus --version"
echo "  REPL: lateralus"
echo "  Docs: https://lateralus.dev"
echo ""
