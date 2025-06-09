#!/usr/bin/env bash

set -euo pipefail

# Default installation directory
INSTALL_DIR="${HOME}/.local/bin"
TSM_VERSION="0.1.0"

# Detect OS and architecture
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# Map architecture to Python wheel format
case "$ARCH" in
  "x86_64") ARCH="x86_64" ;;
  "arm64") ARCH="aarch64" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Create temporary directory
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Download and install
echo "Installing tsm v${TSM_VERSION}..."
python3 -m pip install --user "tsm==${TSM_VERSION}"

# Ensure the installation directory exists
mkdir -p "$INSTALL_DIR"

# Add to PATH if not already present
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  echo "Adding $INSTALL_DIR to your PATH..."
  echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "${HOME}/.bashrc"
  echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "${HOME}/.zshrc"
fi

echo "Installation complete! You may need to restart your shell or run:"
echo "source ~/.bashrc  # or source ~/.zshrc" 