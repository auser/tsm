#!/bin/bash

set -e

# Default values
VERSION="latest"
REPO="auser/herring"
BINARY_NAME="tsm"
INSTALL_DIR="/usr/local/bin"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Determine OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Map architecture to GitHub's format
case $ARCH in
    x86_64)
        ARCH="amd64"
        ;;
    arm64|aarch64)
        ARCH="arm64"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

# Map OS to GitHub's format
case $OS in
    linux)
        OS="linux"
        ;;
    darwin)
        OS="macos"
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

# Get the latest version if not specified
if [ "$VERSION" = "latest" ]; then
    VERSION=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
fi

# Download URL
URL="https://github.com/$REPO/releases/download/$VERSION/$BINARY_NAME-$OS-$ARCH"

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Download the binary
echo "Downloading $BINARY_NAME version $VERSION..."
curl -L "$URL" -o "$TMP_DIR/$BINARY_NAME"

# Make it executable
chmod +x "$TMP_DIR/$BINARY_NAME"

# Install the binary
echo "Installing $BINARY_NAME to $INSTALL_DIR..."
sudo mv "$TMP_DIR/$BINARY_NAME" "$INSTALL_DIR/$BINARY_NAME"

echo "Installation complete! $BINARY_NAME has been installed to $INSTALL_DIR" 