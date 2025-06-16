#!/usr/bin/env bash

set -e
set -u

# Default installation directory
INSTALL_DIR="/usr/local/bin"
BINARY_NAME="tsm"
REPO="auser/tsm" 

# Function to get the latest tag
get_latest_tag() {
    curl -s "https://api.github.com/repos/${REPO}/tags" | grep -m 1 '"name":' | sed 's/.*"name": "\(.*\)".*/\1/'
}

# Function to get the appropriate binary name for the current system
get_binary_name() {
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    
    case "$arch" in
        "x86_64")
            arch="amd64"
            ;;
        "aarch64"|"arm64")
            arch="arm64"
            ;;
    esac
    
    echo "tsm-${os}-${arch}"
}

# Parse command line arguments
VERSION=""
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

# If no version specified, use latest tag
if [ -z "$VERSION" ]; then
    VERSION=$(get_latest_tag)
fi

# Get the appropriate binary name for this system
BINARY_FILE=$(get_binary_name)

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Download the binary
echo "Downloading version ${VERSION}..."
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY_FILE}"
if ! curl -L -o "${TEMP_DIR}/${BINARY_FILE}" "$DOWNLOAD_URL"; then
    echo "Failed to download binary"
    exit 1
fi

# Make the binary executable
chmod +x "${TEMP_DIR}/${BINARY_FILE}"

# Create versioned directory if it doesn't exist
VERSION_DIR="${INSTALL_DIR}/${BINARY_NAME}-${VERSION}"
sudo mkdir -p "$VERSION_DIR"

# Move binary to versioned directory
sudo mv "${TEMP_DIR}/${BINARY_FILE}" "${VERSION_DIR}/${BINARY_NAME}"

# Create or update symlink
sudo ln -sf "${VERSION_DIR}/${BINARY_NAME}" "${INSTALL_DIR}/${BINARY_NAME}"

echo "Successfully installed ${BINARY_NAME} version ${VERSION}"
echo "Binary is available at: ${INSTALL_DIR}/${BINARY_NAME}"