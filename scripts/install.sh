#!/bin/bash

# TSM Installer Script
# Automatically downloads and installs the appropriate binary for your system
# 
# Usage as one-liner:
#   curl -fsSL https://raw.githubusercontent.com/auser/proxy-deployer/main/install.sh | bash
#
# Usage with options:
#   ./install.sh -v v1.0.0 -d ~/.local/bin

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERSION="latest"
INSTALL_DIR="/usr/local/bin"
BINARY_NAME="tsm"

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

# Function to show usage
show_usage() {
    cat << EOF
TSM Installer Script

Usage: $0 [OPTIONS]

Options:
    -v, --version VERSION    Install specific version (default: latest)
    -d, --dir DIRECTORY      Installation directory (default: /usr/local/bin)
    -h, --help              Show this help message

Examples:
    $0                        # Install latest version
    $0 -v v1.0.0            # Install specific version
    $0 -d ~/.local/bin      # Install to custom directory

One-liner installation:
    curl -fsSL https://raw.githubusercontent.com/auser/proxy-deployer/main/install.sh | bash

EOF
}

# Parse command line arguments (only if script is run directly)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
fi

# Function to detect OS and architecture
detect_system() {
    local os
    local arch
    
    # Detect OS
    case "$(uname -s)" in
        Linux*)     os="linux" ;;
        Darwin*)    os="macos" ;;
        CYGWIN*|MINGW*|MSYS*) os="windows" ;;
        *)          print_error "Unsupported operating system: $(uname -s)" && exit 1 ;;
    esac
    
    # Detect architecture
    case "$(uname -m)" in
        x86_64|amd64) arch="x86_64" ;;
        aarch64|arm64) arch="arm64" ;;
        armv7l) arch="armv7" ;;
        *) print_error "Unsupported architecture: $(uname -m)" && exit 1 ;;
    esac
    
    echo "${os}-${arch}"
}

# Function to get latest version from GitHub API
get_latest_version() {
    local version
    if [ "$VERSION" = "latest" ]; then
        version=$(curl -s https://api.github.com/repos/auser/proxy-deployer/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
        if [ -z "$version" ]; then
            print_error "Failed to get latest version from GitHub"
            exit 1
        fi
        echo "$version"
    else
        echo "$VERSION"
    fi
}

# Function to download and install binary
download_and_install() {
    local system_info
    local version
    local download_url
    local binary_name
    
    print_status "Detecting system..."
    system_info=$(detect_system)
    print_status "System detected: $system_info"
    
    print_status "Getting version..."
    version=$(get_latest_version)
    print_status "Installing version: $version"
    
    # Determine binary name based on OS
    case "$system_info" in
        linux-*) binary_name="tsm-linux" ;;
        macos-*) binary_name="tsm-macos" ;;
        windows-*) binary_name="tsm.exe" ;;
        *) print_error "Unsupported system: $system_info" && exit 1 ;;
    esac
    
    # Construct download URL
    download_url="https://github.com/auser/proxy-deployer/releases/download/${version}/${binary_name}"
    
    print_status "Downloading from: $download_url"
    
    # Create temporary directory
    local temp_dir=$(mktemp -d)
    local temp_file="$temp_dir/$binary_name"
    
    # Download binary
    if ! curl -L -o "$temp_file" "$download_url"; then
        print_error "Failed to download binary"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Make binary executable
    chmod +x "$temp_file"
    
    # Create installation directory if it doesn't exist
    if [ ! -d "$INSTALL_DIR" ]; then
        print_status "Creating installation directory: $INSTALL_DIR"
        if [ -w "$(dirname "$INSTALL_DIR")" ]; then
            mkdir -p "$INSTALL_DIR"
        else
            sudo mkdir -p "$INSTALL_DIR"
        fi
    fi
    
    # Install binary
    print_status "Installing to: $INSTALL_DIR/$BINARY_NAME"
    if [ -w "$INSTALL_DIR" ]; then
        cp "$temp_file" "$INSTALL_DIR/$BINARY_NAME"
    else
        sudo cp "$temp_file" "$INSTALL_DIR/$BINARY_NAME"
    fi
    
    # Clean up
    rm -rf "$temp_dir"
    
    print_success "TSM installed successfully!"
    print_status "You can now run: $BINARY_NAME --help"
    
    # Add to PATH if needed
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        print_status "Note: You may need to add $INSTALL_DIR to your PATH"
        print_status "Add this to your shell profile: export PATH=\"$INSTALL_DIR:\$PATH\""
    fi
}

# Main execution
main() {
    print_status "TSM Installer starting..."
    
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed. Please install curl first."
        exit 1
    fi
    
    # Check if we're running as root (optional warning)
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root. This is not recommended for security reasons."
    fi
    
    download_and_install
}

# Run main function
main "$@" 