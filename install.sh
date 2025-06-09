#!/bin/bash
# tsm installer
# This script installs tsm using uv
set -e

# Configuration (will be replaced by CI)
PROJECT_NAME="tsm"
GITHUB_REPO="${GITHUB_REPO:-auser/tsm}"
VERSION="${VERSION:-}"
WHEEL_NAME=""
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local}"
BIN_DIR="$INSTALL_DIR/bin"

# Colors and styling
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    DIM='\033[2m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' BOLD='' DIM='' NC=''
fi

# Logging functions
log() { echo -e "${DIM}$1${NC}" >&2; }
info() { echo -e "${GREEN}✓${NC} $1" >&2; }
warn() { echo -e "${YELLOW}warning${NC}: $1" >&2; }
error() { echo -e "${RED}error${NC}: $1" >&2; exit 1; }

# Download helper
download() {
    local url="$1"
    local output="$2"
    
    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 -fsSL "$url" -o "$output"
    elif command -v wget >/dev/null 2>&1; then
        wget --https-only --secure-protocol=TLSv1_2 -q "$url" -O "$output"
    else
        error "Neither curl nor wget is available"
    fi
}

# Check system compatibility
check_system() {
    case "$(uname -s)" in
        Linux|Darwin) ;;
        CYGWIN*|MINGW*|MSYS*) 
            warn "Windows detected. This installer works best on Linux/macOS."
            warn "Consider using WSL or installing Python directly on Windows."
            ;;
        *) error "Unsupported operating system: $(uname -s)" ;;
    esac
    
    log "System check passed"
}

# Ensure uv is available
ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        local uv_version
        uv_version=$(uv --version 2>/dev/null | head -1 || echo "unknown")
        log "Found uv: $uv_version"
        return
    fi
    
    info "Installing uv..."
    
    # Download and run uv installer
    local uv_installer
    uv_installer=$(mktemp)
    download "https://astral.sh/uv/install.sh" "$uv_installer"
    
    # Install uv without modifying PATH (we'll handle that)
    INSTALLER_NO_MODIFY_PATH=1 bash "$uv_installer" >/dev/null 2>&1
    rm "$uv_installer"
    
    # Add uv to current session PATH
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command -v uv >/dev/null 2>&1; then
        error "Failed to install uv. Please install manually: https://docs.astral.sh/uv/"
    fi
    
    info "uv installed successfully"
}

# Fetch latest version from GitHub
fetch_latest_version() {
    local latest_version
    local api_url="https://api.github.com/repos/$GITHUB_REPO/releases/latest"
    
    log "Fetching latest version from GitHub: $GITHUB_REPO"
    
    if command -v curl >/dev/null 2>&1; then
        latest_version=$(curl --proto '=https' --tlsv1.2 -fsSL "$api_url" 2>/dev/null | grep -Po '"tag_name": "\K.*?(?=")' || echo "")
    elif command -v wget >/dev/null 2>&1; then
        latest_version=$(wget --https-only --secure-protocol=TLSv1_2 -qO- "$api_url" 2>/dev/null | grep -Po '"tag_name": "\K.*?(?=")' || echo "")
    else
        error "Neither curl nor wget is available"
    fi
    
    if [ -z "$latest_version" ]; then
        warn "Failed to fetch latest version from GitHub. Using default version."
        echo "v0.1.0"  # Default version if fetch fails
        return
    fi
    
    echo "$latest_version"
}

# Format version with v prefix
format_version() {
    local version=$1
    # Remove v prefix if present
    version=${version#v}
    # Add v prefix
    echo "v$version"
}

# Install the project
install_project() {
    # Set version if not provided
    if [ -z "$VERSION" ]; then
        VERSION=$(fetch_latest_version)
        info "Using latest version: $VERSION"
    else
        VERSION=$(format_version "$VERSION")
    fi
    
    # Set wheel name based on version (without v prefix)
    WHEEL_NAME="${PROJECT_NAME}-${VERSION#v}-py3-none-any.whl"
    
    info "Installing $PROJECT_NAME $VERSION..."
    
    # Method 1: Try installing from GitHub release wheel
    if [ -n "$WHEEL_NAME" ]; then
        local wheel_url="https://github.com/$GITHUB_REPO/releases/download/$VERSION/$WHEEL_NAME"
        log "Attempting install from GitHub release wheel..."
        
        if uv tool install --from "$wheel_url" "$PROJECT_NAME" >/dev/null 2>&1; then
            info "Installed from GitHub release"
            return
        fi
    fi
    
    # Method 2: Try installing from PyPI
    log "Attempting install from PyPI..."
    if uv tool install "$PROJECT_NAME==${VERSION#v}" >/dev/null 2>&1; then
        info "Installed from PyPI"
        return
    fi
    
    # Method 3: Try installing from git tag
    log "Attempting install from git..."
    if uv tool install "git+https://github.com/$GITHUB_REPO@$VERSION" >/dev/null 2>&1; then
        info "Installed from git"
        return
    fi
    
    # Method 4: Try latest from git (fallback)
    warn "Specific version not found, trying latest from git..."
    if uv tool install "git+https://github.com/$GITHUB_REPO" >/dev/null 2>&1; then
        warn "Installed latest version from git (not $VERSION)"
        return
    fi
    
    error "Failed to install $PROJECT_NAME from any source"
}

# Configure shell PATH
setup_shell() {
    # Check if already in PATH
    if echo "$PATH" | grep -q "$BIN_DIR"; then
        log "uv tools directory already in PATH"
        return
    fi
    
    local shell_config=""
    local shell_name=""
    
    # Detect shell and config file
    case "$SHELL" in
        */bash)
            shell_name="bash"
            if [ -f "$HOME/.bashrc" ]; then
                shell_config="$HOME/.bashrc"
            elif [ -f "$HOME/.bash_profile" ]; then
                shell_config="$HOME/.bash_profile"
            fi
            ;;
        */zsh)
            shell_name="zsh"
            shell_config="$HOME/.zshrc"
            ;;
        */fish)
            shell_name="fish"
            if command -v fish >/dev/null 2>&1; then
                fish -c "set -U fish_user_paths $BIN_DIR \$fish_user_paths" 2>/dev/null
                info "Updated fish PATH configuration"
                return
            fi
            ;;
    esac
    
    # Add to shell config if detected
    if [ -n "$shell_config" ] && [ -f "$shell_config" ]; then
        if ! grep -q "$BIN_DIR" "$shell_config" 2>/dev/null; then
            echo "" >> "$shell_config"
            echo "# Added by $PROJECT_NAME installer" >> "$shell_config"
            echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_config"
            info "Updated $shell_name configuration ($shell_config)"
        fi
    else
        warn "Could not detect shell configuration file"
    fi
}

# Verify installation worked
verify_installation() {
    log "Verifying installation..."
    
    # Add uv tools to PATH for verification
    export PATH="$BIN_DIR:$PATH"
    
    if command -v "$PROJECT_NAME" >/dev/null 2>&1; then
        local installed_version
        installed_version=$("$PROJECT_NAME" --version 2>/dev/null | head -1 || echo "installed")
        info "Installation verified: $installed_version"
        return 0
    fi
    
    # Check if binary exists but not in PATH
    if [ -f "$BIN_DIR/$PROJECT_NAME" ]; then
        warn "$PROJECT_NAME installed but not in current PATH"
        info "Restart your shell or run: export PATH=\"$BIN_DIR:\$PATH\""
        return 0
    fi
    
    error "Installation verification failed"
}

# Show usage instructions
show_completion_message() {
    local shell_restart_msg=""
    
    case "$SHELL" in
        */bash) shell_restart_msg="source ~/.bashrc" ;;
        */zsh) shell_restart_msg="source ~/.zshrc" ;;
        *) shell_restart_msg="restart your shell" ;;
    esac
    
    cat << EOF

${BOLD}${GREEN}🎉 $PROJECT_NAME installation complete!${NC}

${BOLD}Next steps:${NC}
  1. ${shell_restart_msg}
  2. Run: ${BOLD}$PROJECT_NAME --help${NC}

${BOLD}Useful commands:${NC}
  • Update: ${DIM}uv tool upgrade $PROJECT_NAME${NC}
  • Remove: ${DIM}uv tool uninstall $PROJECT_NAME${NC}
  • List:   ${DIM}uv tool list${NC}

EOF
}

# Main installation process
main() {
    echo "${BOLD}$PROJECT_NAME installer${NC}"
    echo "${DIM}Version: $VERSION${NC}"
    echo
    
    check_system
    ensure_uv
    install_project
    setup_shell
    verify_installation
    show_completion_message
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        cat << EOF
$PROJECT_NAME installer

USAGE:
    install.sh [OPTIONS]

OPTIONS:
    -h, --help     Show this help message
    --no-modify-path   Don't modify shell configuration files

ENVIRONMENT VARIABLES:
    INSTALL_DIR    Installation directory (default: ~/.local)
    VERSION        Specific version to install (default: latest)
                  Can be specified with or without 'v' prefix (e.g., 'v0.1.0' or '0.1.0')
    GITHUB_REPO    GitHub repository in format 'owner/repo' (default: auser/tsm)

EXAMPLES:
    # Standard installation (latest version)
    curl -LsSf https://github.com/$GITHUB_REPO/releases/latest/download/install.sh | sh
    
    # Install specific version
    VERSION=0.1.0 curl -LsSf https://github.com/$GITHUB_REPO/releases/latest/download/install.sh | sh
    
    # Install from specific repository
    GITHUB_REPO=your-org/your-repo curl -LsSf https://github.com/$GITHUB_REPO/releases/latest/download/install.sh | sh
    
    # Install without modifying shell config
    curl -LsSf https://github.com/$GITHUB_REPO/releases/latest/download/install.sh | sh -s -- --no-modify-path

More info: https://github.com/$GITHUB_REPO
EOF
        exit 0
        ;;
    --no-modify-path)
        check_system
        ensure_uv
        install_project
        verify_installation
        echo "${GREEN}$PROJECT_NAME installed successfully!${NC}"
        echo "Add $BIN_DIR to your PATH to use $PROJECT_NAME"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1. Use --help for usage information."
        ;;
esac