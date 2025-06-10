#!/bin/bash
set -euo pipefail

# Function to build for a specific target
build_for_target() {
    local target_os=$1
    local target_arch=$2
    local libc=${3:-glibc}  # Default to glibc if not specified
    
    echo "Building for ${target_os}-${target_arch} (${libc})..."
    
    # Set environment variables for the build
    export TARGET_OS=$target_os
    export TARGET_ARCH=$target_arch
    export TARGET_LIBC=$libc
    
    # Build the binary
    uv run pyinstaller --onefile --specpath spec --name tsm main.py
    
    # Rename with libc info for musl builds
    if [ "$libc" = "musl" ]; then
        mv dist/tsm "dist/tsm-${target_os}-${target_arch}-musl"
        echo "Binary created at dist/tsm-${target_os}-${target_arch}-musl"
    else
        mv dist/tsm "dist/tsm-${target_os}-${target_arch}"
        echo "Binary created at dist/tsm-${target_os}-${target_arch}"
    fi
}

# If specific target is provided, build only for that target
if [ -n "${TARGET_OS:-}" ] && [ -n "${TARGET_ARCH:-}" ]; then
    build_for_target "$TARGET_OS" "$TARGET_ARCH" "${TARGET_LIBC:-glibc}"
else
    # Build for all supported targets
    echo "Building for all supported targets..."
    
    # Linux targets (both glibc and musl)
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