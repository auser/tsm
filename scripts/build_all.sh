#!/bin/bash

# Build script for all platforms
set -e

echo "Building TSM for all platforms..."

# Create virtual environment using standard Python tools if uv is not available
if [ ! -f .venv ]; then
    echo "Creating .venv directory..."
    if command -v uv &> /dev/null; then
        uv venv
    else
        python -m venv .venv
    fi
fi

# Activate virtual environment
source .venv/bin/activate

# Ensure pip is available and up to date
echo "Updating pip..."
python -m ensurepip --upgrade
python -m pip install --upgrade pip

# Install required dependencies
if ! dpkg -l | grep -q libcrypt-dev; then
    echo "Installing libcrypt-dev..."
    sudo apt-get update
    sudo apt-get install -y libcrypt-dev
fi

# Install PyInstaller if not present
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    python -m pip install pyinstaller
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

# Install requirements
echo "Installing requirements..."
python -m pip install -r requirements.txt

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
    pyinstaller spec/tsm.spec --clean

# Debug: Show build output
RUN echo "=== Build Output ===" && \
    ls -la /build/dist/ && \
    echo "=== End Build Output ==="

# Clean up any generated spec files
RUN rm -f tsm.spec
EOF

        # Create a temporary container name
        local container_name="tsm_build_${platform}_${arch}"

        # Build using Docker with increased verbosity
        echo "Starting Docker build for ${platform}-${arch}..."
        if ! docker buildx build \
            --platform "$docker_platform" \
            --load \
            -t "$container_name" \
            --progress=plain \
            --no-cache \
            -f Dockerfile .; then
            echo "Docker build failed for ${platform}-${arch}"
            echo "Debug information:"
            docker buildx inspect
            exit 1
        fi

        # Create a temporary container and copy the built binary
        echo "Copying built binary from container..."
        docker create --name "${container_name}_temp" "$container_name"
        docker cp "${container_name}_temp:/build/dist/tsm" "dist/tsm"
        docker rm "${container_name}_temp"
        docker rmi "$container_name"

        # Clean up Dockerfile
        rm Dockerfile

        # Debug: Show contents of dist directory after Docker build
        echo "=== Contents of dist directory after Docker build ==="
        ls -la dist/
        echo "=== End of dist directory contents ==="
    else
        # Build using PyInstaller with the spec file
        echo "Building with PyInstaller..."
        pyinstaller spec/tsm.spec --clean
        
        # Debug: Show build output
        echo "=== Build Output ==="
        ls -la dist/
        echo "=== End Build Output ==="
        
        # Clean up any generated spec files
        rm -f tsm.spec
    fi
    
    # Move the built binary to releases directory
    if [ "$platform" = "windows" ]; then
        output_name="${output_name}.exe"
        if [ -f "dist/tsm.exe" ]; then
            mv "dist/tsm.exe" "releases/${output_name}"
        else
            echo "Error: dist/tsm.exe not found"
            echo "Contents of dist directory:"
            ls -la dist/
            exit 1
        fi
    else
        if [ -f "dist/tsm" ]; then
            mv "dist/tsm" "releases/${output_name}"
        else
            echo "Error: dist/tsm not found"
            echo "Contents of dist directory:"
            ls -la dist/
            exit 1
        fi
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
TARGETS="linux-amd64:false:linux/amd64
linux-arm64:true:linux/arm64
macos-amd64:false:linux/amd64
macos-arm64:false:linux/amd64
windows-amd64:false:linux/amd64"

# Build for all platforms
for target in $TARGETS; do
    platform_arch=$(echo "$target" | cut -d':' -f1)
    use_docker=$(echo "$target" | cut -d':' -f2)
    docker_platform=$(echo "$target" | cut -d':' -f3)
    platform=$(echo "$platform_arch" | cut -d'-' -f1)
    arch=$(echo "$platform_arch" | cut -d'-' -f2)
    build_for_platform "$platform" "$arch" "$use_docker" "$docker_platform"
done

echo "Build complete! Binaries are in the 'releases' directory."
ls -la releases/