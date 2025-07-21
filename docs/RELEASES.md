# Release Process

This document describes how to create releases for the TSM project using the provided Makefile commands.

## Prerequisites

1. **GitHub CLI**: Install the GitHub CLI (`gh`) from https://cli.github.com/
2. **Authentication**: Run `gh auth login` to authenticate with GitHub
3. **Repository Access**: Ensure you have write access to the repository

## Release Commands

### Basic Usage

```bash
# Show available release commands
make release

# Bump version by type
make release-bump TYPE=patch    # 0.1.0 -> 0.1.1
make release-bump TYPE=minor    # 0.1.0 -> 0.2.0
make release-bump TYPE=major    # 0.1.0 -> 1.0.0

# Set specific version
make release-bump VERSION=1.0.0
```

### Git Tagging

```bash
# Create git tag and push (after bumping version)
make release-tag TYPE=patch
make release-tag VERSION=1.0.0
```

### Distribution Building

```bash
# Build distribution files
make build-dist

# Clean distribution files
make clean-dist

# Build standalone binary
make build-binary

# Build binaries for all platforms
make build-all-binaries

# Clean binary artifacts
make clean-binaries
```

### Complete Release Process

```bash
# Full release with distribution build
make release-complete TYPE=patch

# Release with standalone binary
make release-with-binaries TYPE=patch

# Release with all platform binaries
make release-with-all-binaries TYPE=patch

# Create GitHub release (requires GitHub CLI)
make release-github TYPE=patch

# Automated release with GitHub release creation
make release-auto TYPE=patch
```

## Release Workflow

### 1. Manual Release Process

```bash
# 1. Bump version
make release-bump TYPE=patch

# 2. Create git tag and push
make release-tag TYPE=patch

# 3. Build distribution files
make build-dist

# 4. Create GitHub release
make release-github TYPE=patch
```

### 2. Automated Release Process

```bash
# Single command for complete release
make release-auto TYPE=patch
```

## Custom Release Notes

You can provide custom release notes by setting the `RELEASE_NOTES_FILE` variable:

```bash
make release-github TYPE=patch RELEASE_NOTES_FILE=release_notes.md
```

If no release notes file is provided, the script will automatically generate release notes from git commits.

## Version Management

The release system automatically updates version numbers in:

- `pyproject.toml` - Package version
- `src/tsm/cli.py` - CLI version display

## GitHub Release

The GitHub release will be created as a draft, allowing you to review and edit before publishing. The release includes:

- Automatic changelog from git commits
- Installation instructions
- Usage examples
- Distribution files (if built)

## Troubleshooting

### GitHub CLI Issues

```bash
# Check if gh is installed
gh --version

# Authenticate with GitHub
gh auth login

# Check authentication status
gh auth status
```

### Version Conflicts

If you encounter version conflicts, you can manually set the version:

```bash
make release-bump VERSION=1.0.0
```

### Distribution Build Issues

Ensure you have the required build dependencies:

```bash
# Install build dependencies
pip install build

# Or using uv
uv add build
```

## GitHub Actions

The project uses GitHub Actions for automated testing, building, and releasing. This ensures consistent builds across different environments and automates the entire release workflow.

### Automated Release Process

GitHub Actions automatically trigger releases when:
1. **Tag Push**: Push a tag like `v1.0.0` to trigger a release
2. **Manual Trigger**: Use the GitHub Actions UI or `make release-github-action`

### Workflows

- **`.github/workflows/release.yml`**: Handles releases with binary builds
- **`.github/workflows/test.yml`**: Runs tests and builds on pull requests

### Using GitHub Actions

```bash
# Trigger release via GitHub Actions
make release-github-action TYPE=patch

# Trigger test workflow
make test-github-action
```

## Binary Distribution

The project supports creating standalone executables that users can download and run without installing Python or dependencies.

### Building Binaries

```bash
# Build for current platform
make build-binary

# Build with debug information
make build-binary-debug

# Build for specific platforms
make build-binary-linux
make build-binary-windows
make build-binary-macos

# Build for all platforms
make build-all-binaries
```

### Binary Release Process

```bash
# Release with binary for current platform
make release-with-binaries TYPE=patch

# Release with binaries for all platforms
make release-with-all-binaries TYPE=patch
```

### Binary Usage

Users can download the binary from GitHub releases and run it directly:

```bash
# Download and run
./tsm --help

# Or on Windows
tsm.exe --help
```

## Examples

### Patch Release (Bug Fixes)

```bash
make release-auto TYPE=patch
```

### Minor Release (New Features)

```bash
make release-auto TYPE=minor
```

### Major Release (Breaking Changes)

```bash
make release-auto TYPE=major
```

### Custom Version Release

```bash
make release-auto VERSION=2.0.0-beta.1
``` 