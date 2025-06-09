#!/bin/bash

set -euo pipefail

# Initialize variables
FORCE_INSTALL=false
INSTALL_FROM_GIT=false
VERSION="latest"
TEMP_DIR=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Detect OS and architecture
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        MINGW*)     echo "windows";;
        *)          echo "unknown";;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64)     echo "amd64";;
        arm64)      echo "arm64";;
        *)          echo "unknown";;
    esac
}

# Download the binary
download_binary() {
    local os=$(detect_os)
    local arch=$(detect_arch)
    local repo="auser/tsm"
    local binary_name="tsm"
    if [[ "$os" == "windows" ]]; then
        binary_name="tsm.exe"
    fi

    print_status "Downloading TSM binary for $os/$arch..."

    # Create a temporary directory
    TEMP_DIR=$(mktemp -d)

    # Download the binary
    if [[ "$VERSION" == "latest" ]]; then
        # Fetch the latest tag in format v<version>
        local latest_tag=$(curl -s "https://api.github.com/repos/$repo/tags" | grep -o '"name": "v[0-9]*\.[0-9]*\.[0-9]*"' | head -1 | cut -d'"' -f4)
        if [[ -z "$latest_tag" ]]; then
            print_error "Failed to fetch latest tag"
            exit 1
        fi
        VERSION="$latest_tag"
        print_status "Found latest version: $VERSION"
    fi

    # Verify the release exists and get its assets
    print_status "Verifying release $VERSION..."
    local release_info=$(curl -s "https://api.github.com/repos/$repo/releases/tags/$VERSION")
    if [[ -z "$release_info" ]]; then
        print_error "Release $VERSION not found"
        print_status "Available releases:"
        curl -s "https://api.github.com/repos/$repo/releases" | grep -o '"tag_name": "v[^"]*"' | cut -d'"' -f4
        exit 1
    fi

    # Check if release has any assets
    local assets_count=$(echo "$release_info" | grep -o '"assets":' | wc -l)
    if [[ $assets_count -eq 0 ]]; then
        print_error "Release $VERSION exists but has no assets"
        print_status "Please ensure the release has the following assets:"
        echo "  - tsm (for Linux/macOS)"
        echo "  - tsm.exe (for Windows)"
        print_status "You can create a release with assets using:"
        echo "  1. Go to https://github.com/$repo/releases"
        echo "  2. Click 'Draft a new release'"
        echo "  3. Select tag $VERSION"
        echo "  4. Upload the binary files"
        exit 1
    fi

    # List available assets
    print_status "Available assets in release $VERSION:"
    local assets=$(echo "$release_info" | grep -o '"name": "[^"]*"' | cut -d'"' -f4)
    if [[ -z "$assets" ]]; then
        print_error "No assets found in release $VERSION"
        exit 1
    fi
    echo "$assets"

    # Try to find the correct asset name
    local asset_name=$(echo "$assets" | grep -i "tsm.*$os.*$arch" || echo "$binary_name")
    print_status "Using asset: $asset_name"

    local download_url="https://github.com/$repo/releases/download/$VERSION/$asset_name"
    print_status "Downloading from: $download_url"
    
    # Download with verbose output and check for errors
    if ! curl -L -v -o "$TEMP_DIR/$binary_name" "$download_url" 2>&1 | tee /dev/stderr | grep -q "HTTP/.* 200"; then
        print_error "Failed to download binary (HTTP error)"
        exit 1
    fi

    # Verify the downloaded file
    if [[ ! -s "$TEMP_DIR/$binary_name" ]]; then
        print_error "Downloaded file is empty"
        exit 1
    fi

    local file_size=$(stat -c%s "$TEMP_DIR/$binary_name")
    if [[ $file_size -lt 1000 ]]; then  # Less than 1KB is suspicious
        print_error "Downloaded file is too small ($file_size bytes). Expected a binary executable."
        exit 1
    fi

    print_status "Downloaded binary size: $file_size bytes"

    # Make the binary executable
    chmod +x "$TEMP_DIR/$binary_name"

    # Move the binary to a user-accessible location
    local install_dir="$HOME/.local/bin"
    mkdir -p "$install_dir"
    
    if [[ "$FORCE_INSTALL" == "true" ]]; then
        rm -f "$install_dir/$binary_name"
    fi
    
    mv "$TEMP_DIR/$binary_name" "$install_dir/$binary_name"

    print_success "TSM binary installed to $install_dir/$binary_name"
}

# Show usage instructions
show_usage() {
    print_success "TSM installation complete!"
    print_status "Usage instructions:"
    echo ""
    echo "  Run TSM commands:"
    echo "    tsm --help                    # Show help"
    echo "    tsm init                      # Initialize TSM in current directory"
    echo "    tsm start                     # Start monitoring services"
    echo "    tsm status                    # Show service status"
    echo "    tsm scale <service> <count>   # Scale a service"
    echo ""
    echo "  Configuration:"
    echo "    Config file: ~/.config/tsm/config.yaml"
    echo "    Log files:   ~/.local/share/tsm/logs/"
    echo ""
    echo "  Getting started:"
    echo "    1. Make sure Docker and Traefik are running"
    echo "    2. Run 'tsm init' in your project directory"
    echo "    3. Configure your services with Docker labels"
    echo "    4. Run 'tsm start' to begin monitoring"
}

# Main installation flow
main() {
    print_status "TSM (Traefik Service Manager) Installer"
    print_status "======================================="

    download_binary
    show_usage

    print_success "Installation complete! 🚀"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "This script installs TSM (Traefik Service Manager)."
            echo ""
            echo "Options:"
            echo "  --help, -h         Show this help message"
            echo "  --force            Force reinstallation"
            echo "  --version VERSION  Install specific version (default: latest)"
            echo ""
            exit 0
            ;;
        --force)
            FORCE_INSTALL=true
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            print_status "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run the installer
main "$@"