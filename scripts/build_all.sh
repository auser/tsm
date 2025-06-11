#!/bin/bash

# Build script for all platforms
set -e

echo "Building TSM for all platforms..."

# Ensure pip is available
if ! command -v pip &> /dev/null; then
    echo "pip not found. Installing pip..."
    if command -v uv &> /dev/null; then
        uv pip install pip
    else
        python -m ensurepip --upgrade
    fi
fi

# Install required dependencies
if ! dpkg -l | grep -q libcrypt-dev; then
    echo "Installing libcrypt-dev..."
    sudo apt-get update
    sudo apt-get install -y libcrypt-dev
fi

# Install PyInstaller if not present
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Generate requirements.txt from pyproject.toml
echo "Generating requirements.txt..."
if command -v uv &> /dev/null; then
    uv pip compile pyproject.toml -o requirements.txt
elif command -v pip-compile &> /dev/null; then
    pip-compile pyproject.toml
else
    echo "Warning: Neither uv nor pip-tools found. Using existing requirements.txt"
    if [ ! -f requirements.txt ]; then
        echo "Error: requirements.txt not found and no tools to generate it"
        exit 1
    fi
fi

# Create releases directory
mkdir -p releases

# Function to build for a specific platform
build_for_platform() {
    local platform=$1
    local arch=$2
    local output_name="tsm-${platform}-${arch}"
    
    echo "Building for ${platform}-${arch}..."
    
    # Set PyInstaller options based on platform
    local pyinstaller_opts="--onefile --clean"
    if [[ "$platform" == "windows" ]]; then
        pyinstaller_opts="$pyinstaller_opts --noconsole"
        output_name="${output_name}.exe"
    fi
    
    # Build using PyInstaller
    pyinstaller $pyinstaller_opts -n tsm main.py
    
    # Move the built binary to releases directory
    if [[ "$platform" == "windows" ]]; then
        mv "dist/tsm.exe" "releases/${output_name}"
    else
        mv "dist/tsm" "releases/${output_name}"
    fi
    
    echo "✓ Built ${platform}-${arch}"
}

# Build for current platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if [[ "$(uname -m)" == "x86_64" ]]; then
        build_for_platform "linux" "amd64"
    elif [[ "$(uname -m)" == "aarch64" ]]; then
        build_for_platform "linux" "arm64"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if [[ "$(uname -m)" == "x86_64" ]]; then
        build_for_platform "macos" "amd64"
    elif [[ "$(uname -m)" == "arm64" ]]; then
        build_for_platform "macos" "arm64"
    fi
elif [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    if [[ "$(uname -m)" == "x86_64" ]]; then
        build_for_platform "windows" "amd64"
    elif [[ "$(uname -m)" == "aarch64" ]]; then
        build_for_platform "windows" "arm64"
    fi
fi

echo "Build complete! Binaries are in the 'releases' directory."
ls -la releases/