#!/bin/bash

# Test script for running GitHub Actions locally with act

# Function to print usage
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -p, --platform    Platform to test (linux-amd64, linux-arm64, macos-amd64, macos-arm64, windows-amd64)"
    echo "  -t, --tag         Version tag to simulate (default: v0.1.0)"
    echo "  -h, --help        Show this help message"
    exit 1
}

# Default values
PLATFORM="linux-amd64"
TAG="v0.1.0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate platform
case $PLATFORM in
    linux-amd64|linux-arm64|macos-amd64|macos-arm64|windows-amd64)
        ;;
    *)
        echo "Invalid platform: $PLATFORM"
        usage
        ;;
esac

# Get the absolute path of the workspace
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Set up environment variables for act
export ACT_PLATFORM=$PLATFORM
export GITHUB_REF="refs/tags/$TAG"
export GITHUB_REPOSITORY="auser/tsm"

# Run act with the specified platform
echo "Testing workflow for platform: $PLATFORM with tag: $TAG"
echo "Using workspace directory: $WORKSPACE_DIR"

cd "$WORKSPACE_DIR" && act -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    --container-architecture linux/amd64 \
    --bind \
    --env-file .env \
    --secret-file .env \
    --secret-file .secrets \
    --directory "$WORKSPACE_DIR" \
    -W .github/workflows/release.yml 