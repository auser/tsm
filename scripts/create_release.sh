#!/bin/bash

# GitHub Release Creation Script
# Usage: ./scripts/create_release.sh VERSION [RELEASE_NOTES_FILE]

set -e

VERSION=$1
RELEASE_NOTES_FILE=$2

if [ -z "$VERSION" ]; then
    echo "Usage: $0 VERSION [RELEASE_NOTES_FILE]"
    echo "Example: $0 1.0.0"
    echo "Example: $0 1.0.0 release_notes.md"
    exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI."
    echo "Please run: gh auth login"
    exit 1
fi

# Get the repository name
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

echo "Creating GitHub release for $REPO v$VERSION..."

# Prepare release notes
if [ -n "$RELEASE_NOTES_FILE" ] && [ -f "$RELEASE_NOTES_FILE" ]; then
    RELEASE_NOTES=$(cat "$RELEASE_NOTES_FILE")
else
    # Generate basic release notes from git log
    RELEASE_NOTES=$(cat <<EOF
## What's Changed

$(git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || echo "")..HEAD | grep -v "Bump version" | head -20)

## Installation

\`\`\`bash
# Using pip
pip install tsm

# Using uv
uv add tsm

# Using Homebrew (if available)
brew install yourusername/tsm/tsm
\`\`\`

## Usage

\`\`\`bash
# Basic usage
tsm generate

# With custom config
tsm generate -c docker-compose.yml -o ./config
\`\`\`

## Full Changelog

$(git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || echo "")..HEAD)
EOF
)
fi

# Create the release
gh release create "v$VERSION" \
    --title "Release v$VERSION" \
    --notes "$RELEASE_NOTES" \
    --draft

echo "Draft release created for v$VERSION"
echo "Review and publish at: https://github.com/$REPO/releases/tag/v$VERSION"

# Optionally upload distribution files if they exist
if [ -d "dist" ]; then
    echo "Uploading distribution files..."
    for file in dist/*; do
        if [ -f "$file" ]; then
            echo "Uploading $file..."
            gh release upload "v$VERSION" "$file"
        fi
    done
    echo "Distribution files uploaded"
fi

# Upload binaries if they exist
if [ -f "dist/tsm" ] || [ -f "dist/tsm.exe" ] || [ -f "dist/tsm-linux" ] || [ -f "dist/tsm-macos" ]; then
    echo "Uploading binary files..."
    for binary in dist/tsm dist/tsm.exe dist/tsm-linux dist/tsm-macos; do
        if [ -f "$binary" ]; then
            echo "Uploading $binary..."
            gh release upload "v$VERSION" "$binary"
        fi
    done
    echo "Binary files uploaded"
fi

echo "Release creation completed!"
echo "Don't forget to publish the draft release when ready." 