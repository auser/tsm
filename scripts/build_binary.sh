#!/bin/bash
set -euo pipefail

# Function to build for a specific target
build_for_target() {
    local target_os=$1
    local target_arch=$2
    
    echo "Building for ${target_os}-${target_arch}..."
    TARGET_OS=$target_os TARGET_ARCH=$target_arch uv run pyinstaller --onefile --specpath spec --name tsm main.py
    mv dist/tsm "dist/tsm-${target_os}-${target_arch}"
    echo "Binary created at dist/tsm-${target_os}-${target_arch}"
}

# If specific target is provided, build only for that target
if [ -n "${TARGET_OS:-}" ] && [ -n "${TARGET_ARCH:-}" ]; then
    build_for_target "$TARGET_OS" "$TARGET_ARCH"
else
    # Build for all supported targets
    echo "Building for all supported targets..."
    
    # Linux targets
    build_for_target "linux" "x86_64"
    build_for_target "linux" "arm64"
    
    # macOS targets
    build_for_target "darwin" "x86_64"
    build_for_target "darwin" "arm64"
fi