#!/bin/bash

# Build script for all platforms
set -e

echo "Building TSM for all platforms..."

# Ensure pip is available for PyOxidizer
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

# Define targets
TARGETS=(
    "linux-amd64"
    "linux-arm64"
    "macos-amd64"
    "macos-arm64"
    "windows-amd64"
    "windows-arm64"
)

# Create releases directory
mkdir -p releases

# Build each target
for target in "${TARGETS[@]}"; do
    echo "Building for $target..."
    
    # Build the target
    case "$target" in
        "linux-amd64")
            pyoxidizer build --target-triple x86_64-unknown-linux-gnu
            ;;
        "linux-arm64")
            pyoxidizer build --target-triple aarch64-unknown-linux-gnu
            ;;
        "macos-amd64")
            pyoxidizer build --target-triple x86_64-apple-darwin
            ;;
        "macos-arm64")
            pyoxidizer build --target-triple aarch64-apple-darwin
            ;;
        "windows-amd64")
            pyoxidizer build --target-triple x86_64-pc-windows-msvc
            ;;
        "windows-arm64")
            pyoxidizer build --target-triple aarch64-pc-windows-msvc
            ;;
        *)
            echo "Unknown target: $target"
            exit 1
            ;;
    esac
    
    # Find and copy the built binary
    if [[ "$target" == *"windows"* ]]; then
        # Windows executable
        find build -name "tsm.exe" -type f -exec cp {} "releases/tsm-$target.exe" \;
    else
        # Unix executable
        find build -name "tsm" -type f -executable -exec cp {} "releases/tsm-$target" \;
    fi
    
    echo "✓ Built $target"
done

echo "All builds complete! Binaries are in the 'releases' directory."
ls -la releases/