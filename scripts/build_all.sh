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
    local use_docker=$3
    local docker_platform=$4
    
    echo "Building for ${platform}-${arch}..."
    
    if [ "$use_docker" = true ]; then
        # Create a temporary Dockerfile for building
        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /build
COPY . .

# Debug: List files and show directory structure
RUN echo "=== Directory Structure ===" && \
    find . -type f -o -type d | sort && \
    echo "=== Contents of spec/tsm.spec ===" && \
    cat spec/tsm.spec && \
    echo "=== End of spec/tsm.spec ==="

# Install system dependencies required for PyInstaller
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    binutils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install pyinstaller && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Build the binary using the spec file
RUN cd /build && \
    pyinstaller spec/tsm.spec

# Clean up any generated spec files
RUN rm -f tsm.spec
EOF

        # Build using Docker with increased verbosity and timeout
        echo "Starting Docker build for ${platform}-${arch}..."
        if ! docker buildx build \
            --platform "$docker_platform" \
            --output type=local,dest=./dist \
            --progress=plain \
            --no-cache \
            -f Dockerfile .; then
            echo "Docker build failed for ${platform}-${arch}"
            echo "Debug information:"
            docker buildx inspect
            exit 1
        fi

        # Clean up Dockerfile
        rm Dockerfile
    else
        # Build using PyInstaller with the spec file
        pyinstaller spec/tsm.spec
        
        # Clean up any generated spec files
        rm -f tsm.spec
    fi
    
    # Move the built binary to releases directory
    if [[ "$platform" == "windows" ]]; then
        output_name="${output_name}.exe"
        mv "dist/tsm.exe" "releases/${output_name}"
    else
        mv "dist/tsm" "releases/${output_name}"
    fi
    
    echo "✓ Built ${platform}-${arch}"
}

# Set up Docker Buildx if not already set up
if ! docker buildx inspect | grep -q "linux/arm64"; then
    echo "Setting up Docker Buildx..."
    docker buildx create --use
fi

# Verify Docker Buildx setup
echo "Verifying Docker Buildx setup..."
docker buildx inspect

# Define all target platforms
TARGETS=(
    "linux-amd64:false:linux/amd64"
    "linux-arm64:true:linux/arm64"
    "macos-amd64:false:linux/amd64"
    "macos-arm64:false:linux/amd64"
    "windows-amd64:false:linux/amd64"
)

# Build for all platforms
for target in "${TARGETS[@]}"; do
    IFS=':' read -r platform_arch use_docker docker_platform <<< "$target"
    IFS='-' read -r platform arch <<< "$platform_arch"
    build_for_platform "$platform" "$arch" "$use_docker" "$docker_platform"
done

echo "Build complete! Binaries are in the 'releases' directory."
ls -la releases/