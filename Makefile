# Default target
.DEFAULT_GOAL := help

# Show help
.PHONY: help
help:
	@echo "TSM (Traefik Service Manager) - Available Commands"
	@echo "=================================================="
	@echo ""
	@echo "Development Commands:"
	@echo "  compile-requirements  Compile requirements.txt from pyproject.toml"
	@echo ""
	@echo "Release Management:"
	@echo "  release              Show release usage information"
	@echo "  release-bump         Bump version in pyproject.toml and cli.py"
	@echo "  release-tag          Create git tag and push to GitHub"
	@echo "  release-full         Bump version and create git tag"
	@echo "  build-dist           Build distribution files (wheel, sdist)"
	@echo "  clean-dist           Clean distribution files"
	@echo "  release-complete     Full release with distribution build"
	@echo "  release-github       Create GitHub release (requires GitHub CLI)"
	@echo "  release-auto         Complete automated release process"
	@echo ""
	@echo "Binary Distribution:"
	@echo "  build-binary         Build standalone binary for current platform"
	@echo "  build-binary-debug   Build binary with debug information"
	@echo "  build-binary-linux   Build Linux binary"
	@echo "  build-binary-windows Build Windows binary"
	@echo "  build-binary-macos   Build macOS binary"
	@echo "  build-all-binaries   Build binaries for all platforms"
	@echo "  clean-binaries       Clean binary build artifacts"
	@echo "  release-with-binaries Release with standalone binary"
	@echo "  release-with-all-binaries Release with all platform binaries"
	@echo ""
	@echo "Usage Examples:"
	@echo "  make help                    # Show this help"
	@echo "  make compile-requirements    # Update requirements.txt"
	@echo "  make build-binary            # Build standalone binary"
	@echo "  make release-bump TYPE=patch # Bump patch version"
	@echo "  make release-auto TYPE=minor # Complete minor release"
	@echo "  make release-auto VERSION=1.0.0 # Release specific version"
	@echo "  make release-with-binaries TYPE=patch # Release with binary"
	@echo ""
	@echo "For detailed release documentation, see: docs/RELEASES.md"
	@echo ""
	@echo "GitHub Actions:"
	@echo "  make release-github-action    # Trigger GitHub Action release"
	@echo "  make test-github-action       # Run tests via GitHub Actions"

compile-requirements:
	uv pip compile pyproject.toml -o requirements.txt

# Release management
.PHONY: release
release:
	@echo "Usage: make release VERSION=x.y.z [TYPE=major|minor|patch]"
	@echo "Examples:"
	@echo "  make release VERSION=1.0.0"
	@echo "  make release TYPE=patch"
	@echo "  make release TYPE=minor"

# Bump version and create release
.PHONY: release-bump
release-bump:
	@if [ -z "$(VERSION)" ] && [ -z "$(TYPE)" ]; then \
		echo "Error: Must specify either VERSION or TYPE"; \
		exit 1; \
	fi
	@if [ -n "$(TYPE)" ]; then \
		CURRENT_VERSION=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
		MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
		MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
		PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
		case "$(TYPE)" in \
			major) NEW_VERSION=$$((MAJOR + 1)).0.0 ;; \
			minor) NEW_VERSION=$$MAJOR.$$((MINOR + 1)).0 ;; \
			patch) NEW_VERSION=$$MAJOR.$$MINOR.$$((PATCH + 1)) ;; \
		esac; \
	else \
		NEW_VERSION=$(VERSION); \
	fi; \
	echo "Bumping version to $$NEW_VERSION..."; \
	sed -i.bak "s/^version = \".*\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	sed -i.bak "s/\"TSM\", \".*\"/\"TSM\", \"$$NEW_VERSION\"/" src/tsm/cli.py; \
	rm -f pyproject.toml.bak src/tsm/cli.py.bak; \
	echo "Version bumped to $$NEW_VERSION"

# Create git tag and push
.PHONY: release-tag
release-tag:
	@if [ -z "$(VERSION)" ] && [ -z "$(TYPE)" ]; then \
		echo "Error: Must specify either VERSION or TYPE"; \
		exit 1; \
	fi
	@if [ -n "$(TYPE)" ]; then \
		CURRENT_VERSION=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
		MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
		MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
		PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
		case "$(TYPE)" in \
			major) NEW_VERSION=$$((MAJOR + 1)).0.0 ;; \
			minor) NEW_VERSION=$$MAJOR.$$((MINOR + 1)).0 ;; \
			patch) NEW_VERSION=$$MAJOR.$$MINOR.$$((PATCH + 1)) ;; \
		esac; \
	else \
		NEW_VERSION=$(VERSION); \
	fi; \
	echo "Creating git tag v$$NEW_VERSION..."; \
	git add pyproject.toml src/tsm/cli.py; \
	git commit -m "Bump version to $$NEW_VERSION"; \
	git tag -a v$$NEW_VERSION -m "Release v$$NEW_VERSION"; \
	git push origin main; \
	git push origin v$$NEW_VERSION; \
	echo "Tag v$$NEW_VERSION created and pushed"

# Full release process
.PHONY: release-full
release-full: release-bump release-tag
	@echo "Release v$(NEW_VERSION) completed!"
	@echo "Next steps:"
	@echo "1. Create a GitHub release at: https://github.com/yourusername/tsm/releases/new"
	@echo "2. Upload the built distribution files"
	@echo "3. Update the changelog"

# Build distribution files
.PHONY: build-dist
build-dist:
	@echo "Building distribution files..."
	@python -m build
	@echo "Distribution files built in dist/"

# Clean distribution files
.PHONY: clean-dist
clean-dist:
	@echo "Cleaning distribution files..."
	@rm -rf dist/ build/ *.egg-info/
	@echo "Distribution files cleaned"

# Complete release with distribution build
.PHONY: release-complete
release-complete: clean-dist release-full build-dist
	@echo "Complete release v$(NEW_VERSION) ready!"
	@echo "Distribution files are in dist/"
	@echo "Don't forget to create the GitHub release!"

# Create GitHub release (requires GitHub CLI)
.PHONY: release-github
release-github:
	@if [ -z "$(VERSION)" ] && [ -z "$(TYPE)" ]; then \
		echo "Error: Must specify either VERSION or TYPE"; \
		exit 1; \
	fi
	@if [ -n "$(TYPE)" ]; then \
		CURRENT_VERSION=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
		MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
		MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
		PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
		case "$(TYPE)" in \
			major) NEW_VERSION=$$((MAJOR + 1)).0.0 ;; \
			minor) NEW_VERSION=$$MAJOR.$$((MINOR + 1)).0 ;; \
			patch) NEW_VERSION=$$MAJOR.$$MINOR.$$((PATCH + 1)) ;; \
		esac; \
	else \
		NEW_VERSION=$(VERSION); \
	fi; \
	echo "Creating GitHub release for v$$NEW_VERSION..."; \
	./scripts/create_release.sh $$NEW_VERSION $(RELEASE_NOTES_FILE); \
	echo "GitHub release created for v$$NEW_VERSION"

# Full automated release process
.PHONY: release-auto
release-auto: release-complete release-github
	@echo "Automated release v$(NEW_VERSION) completed!"
	@echo "Check the GitHub release and publish when ready."

# Binary distribution commands
.PHONY: build-binary
build-binary:
	@echo "Building standalone binary..."
	@echo "Installing PyInstaller if not available..."
	@uv add pyinstaller --dev
	@source .venv/bin/activate && pyinstaller --onefile --name tsm main.py
	@echo "Binary created: dist/tsm"

.PHONY: build-binary-debug
build-binary-debug:
	@echo "Building standalone binary with debug info..."
	@echo "Installing PyInstaller if not available..."
	@uv add pyinstaller --dev
	@source .venv/bin/activate && pyinstaller --onefile --name tsm --debug all main.py
	@echo "Debug binary created: dist/tsm"

.PHONY: build-binary-cross
build-binary-cross:
	@echo "Building cross-platform binaries..."
	@echo "Note: Cross-platform builds require Docker or specific toolchains"
	@echo "For Linux: make build-binary-linux"
	@echo "For Windows: make build-binary-windows"
	@echo "For macOS: make build-binary-macos"

.PHONY: build-binary-linux
build-binary-linux:
	@echo "Building Linux binary..."
	@echo "Installing PyInstaller if not available..."
	@uv add pyinstaller --dev
	@source .venv/bin/activate && pyinstaller --onefile --name tsm-linux main.py
	@echo "Linux binary created: dist/tsm-linux"

.PHONY: build-binary-windows
build-binary-windows:
	@echo "Building Windows binary..."
	@echo "Installing PyInstaller if not available..."
	@uv add pyinstaller --dev
	@source .venv/bin/activate && pyinstaller --onefile --name tsm.exe main.py
	@echo "Windows binary created: dist/tsm.exe"

.PHONY: build-binary-macos
build-binary-macos:
	@echo "Building macOS binary..."
	@echo "Installing PyInstaller if not available..."
	@uv add pyinstaller --dev
	@source .venv/bin/activate && pyinstaller --onefile --name tsm-macos main.py
	@echo "macOS binary created: dist/tsm-macos"

.PHONY: build-all-binaries
build-all-binaries: build-binary-linux build-binary-windows build-binary-macos
	@echo "All platform binaries built in dist/"

.PHONY: clean-binaries
clean-binaries:
	@echo "Cleaning binary build artifacts..."
	@rm -rf build/ dist/ *.spec
	@echo "Binary artifacts cleaned"

# Complete release with binaries
.PHONY: release-with-binaries
release-with-binaries: release-complete build-binary
	@echo "Release v$(NEW_VERSION) with binary completed!"
	@echo "Binary available: dist/tsm"
	@echo "Don't forget to upload the binary to GitHub release!"

# Complete release with all platform binaries
.PHONY: release-with-all-binaries
release-with-all-binaries: release-complete build-all-binaries
	@echo "Release v$(NEW_VERSION) with all platform binaries completed!"
	@echo "Binaries available in dist/:"
	@ls -la dist/
	@echo "Don't forget to upload the binaries to GitHub release!"

# GitHub Actions commands
.PHONY: release-github-action
release-github-action:
	@if [ -z "$(VERSION)" ] && [ -z "$(TYPE)" ]; then \
		echo "Error: Must specify either VERSION or TYPE"; \
		exit 1; \
	fi
	@if [ -n "$(TYPE)" ]; then \
		CURRENT_VERSION=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
		MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
		MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
		PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
		case "$(TYPE)" in \
			major) NEW_VERSION=$$((MAJOR + 1)).0.0 ;; \
			minor) NEW_VERSION=$$MAJOR.$$((MINOR + 1)).0 ;; \
			patch) NEW_VERSION=$$MAJOR.$$MINOR.$$((PATCH + 1)) ;; \
		esac; \
	else \
		NEW_VERSION=$(VERSION); \
	fi; \
	echo "Triggering GitHub Action release for v$$NEW_VERSION..."; \
	gh workflow run release.yml --field version=$$NEW_VERSION --field release_type=$(TYPE) --field build_binaries=true; \
	echo "GitHub Action release triggered for v$$NEW_VERSION"

.PHONY: test-github-action
test-github-action:
	@echo "Triggering GitHub Action test workflow..."
	@gh workflow run test.yml
	@echo "GitHub Action test workflow triggered"
