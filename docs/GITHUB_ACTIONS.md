# GitHub Actions

This project uses GitHub Actions for automated testing, building, and releasing.

## Workflows

### Release Workflow (`.github/workflows/release.yml`)

Automatically creates releases when:
- A tag is pushed (e.g., `git tag v1.0.0 && git push origin v1.0.0`)
- Manually triggered via GitHub Actions UI
- Triggered via `make release-github-action`

**Features:**
- Builds distribution files (wheel, sdist)
- Creates standalone binaries for all platforms
- Automatically creates GitHub releases
- Uploads all artifacts to the release

### Test Workflow (`.github/workflows/test.yml`)

Runs on every push and pull request:
- Tests across Python 3.10, 3.11, 3.12
- Builds and tests binaries
- Runs linting (black, ruff, mypy)
- Uploads coverage reports

## Usage

### Automatic Release (Recommended)

1. **Bump version locally:**
   ```bash
   make release-bump TYPE=patch
   ```

2. **Commit and push:**
   ```bash
   git add .
   git commit -m "Bump version to 1.0.1"
   git push origin main
   ```

3. **Create and push tag:**
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

4. **GitHub Actions automatically:**
   - Builds all binaries
   - Creates GitHub release
   - Uploads all artifacts

### Manual Release

1. **Trigger via GitHub CLI:**
   ```bash
   make release-github-action TYPE=patch
   ```

2. **Or via GitHub UI:**
   - Go to Actions → Release → Run workflow
   - Fill in version and options

### Testing

Trigger test workflow:
```bash
make test-github-action
```

## Artifacts

Each release includes:
- **Source distribution**: `tsm-1.0.0.tar.gz`
- **Wheel distribution**: `tsm-1.0.0-py3-none-any.whl`
- **Linux binary**: `tsm-linux`
- **Windows binary**: `tsm.exe`
- **macOS binary**: `tsm-macos`

## Configuration

### Required Permissions

The workflows require these repository permissions:
- `contents: write` - For creating releases
- `packages: write` - For uploading artifacts

### Environment Variables

No additional environment variables are required. The workflows use the default `GITHUB_TOKEN`.

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the repository has the required permissions
2. **Build Failures**: Check the Actions logs for dependency issues
3. **Binary Issues**: Verify PyInstaller is working correctly

### Debugging

1. **Check workflow runs**: Go to Actions tab in GitHub
2. **View logs**: Click on any workflow run to see detailed logs
3. **Re-run failed jobs**: Use the "Re-run jobs" button in GitHub UI

## Local vs GitHub Actions

| Feature        | Local                | GitHub Actions  |
| -------------- | -------------------- | --------------- |
| Speed          | Fast                 | Slower (CI/CD)  |
| Consistency    | Depends on local env | Consistent      |
| Automation     | Manual               | Fully automated |
| Cross-platform | Limited              | All platforms   |
| Dependencies   | Manual               | Automatic       |

**Recommendation**: Use GitHub Actions for releases, local builds for development. 