#!/bin/bash
set -euo pipefail

# Ensure we're in a virtual environment and have Nuitka installed
setup_environment() {
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python -m venv .venv
    fi

    source .venv/bin/activate

    # Install Nuitka if not already installed
    if ! python -c "import nuitka" 2>/dev/null; then
        echo "Installing Nuitka..."
        pip install nuitka
    fi
}

# Function to build for a specific target
build_for_target() {
    local target_os=$1
    local target_arch=$2
    local libc=${3:-glibc}  # Default to glibc if not specified
    
    echo "Building for $target_os $target_arch with $libc..."
    
    # Set environment variables for Nuitka
    export TARGET_OS=$target_os
    export TARGET_ARCH=$target_arch
    export TARGET_LIBC=$libc
    
    # Set Nuitka architecture flags
    if [ "$target_arch" = "aarch64" ]; then
        export NUITKA_ARCH="aarch64"
    elif [ "$target_arch" = "arm64" ]; then
        export NUITKA_ARCH="arm64"
    else
        export NUITKA_ARCH="x86_64"
    fi
    
    # Build the binary
    python -m nuitka --standalone --onefile \
        --include-package=tsm \
        --output-dir=dist \
        --output-filename="tsm-$target_os-$target_arch${libc:+-$libc}" \
        --target-arch="$NUITKA_ARCH" \
        --target-os="$target_os" \
        tsm/__main__.py
    
    # Verify the binary architecture
    if [ "$target_os" = "linux" ]; then
        echo "Verifying binary architecture..."
        file "dist/tsm-$target_os-$target_arch${libc:+-$libc}"
    fi
}

# Main script execution
setup_environment

# Check if specific target is provided
if [ -n "${TARGET_OS:-}" ] && [ -n "${TARGET_ARCH:-}" ]; then
    # Build for specified target
    build_for_target "$TARGET_OS" "$TARGET_ARCH" "${TARGET_LIBC:-glibc}"
else
    # Build for all supported targets
    echo "Building for all supported targets..."
    
    # Linux targets
    build_for_target "linux" "x86_64" "glibc"
    build_for_target "linux" "x86_64" "musl"
    build_for_target "linux" "arm64" "glibc"
    build_for_target "linux" "arm64" "musl"
    build_for_target "linux" "aarch64" "glibc"
    build_for_target "linux" "aarch64" "musl"
    
    # macOS targets
    build_for_target "darwin" "x86_64"
    build_for_target "darwin" "arm64"
    
    # Windows targets
    build_for_target "windows" "x86_64"
    build_for_target "windows" "arm64"
fi