# Verify installation
verify_installation() {
    local method="$1"
    
    print_status "Verifying installation..."
    
    # Determine TSM executable location
    local tsm_cmd
    if [[ "$method" == "source" ]]; then
        tsm_cmd="$(pwd)/.venv/bin/tsm"
    else
        tsm_cmd="$HOME/.local/share/tsm/.venv/bin/tsm"
    fi
    
    # Check if TSM is installed and working
    if "$tsm_cmd" --help >/dev/null 2>&1; then
        print_success "TSM CLI is working"
        local version
        version=$("$tsm_cmd" --version 2>/dev/null || echo "unknown")
        print_status "TSM version: $version"
    else
        print_error "TSM CLI is not working properly"
        return 1
    fi
    
    # Check if symlink exists and works
    if command -v tsm >/dev/null 2>&1; then
        print_success "TSM is available in PATH"
    else
        print_warning "TSM is not in PATH"
        print_status "Make sure $HOME/.local/bin is in your PATH"
        print_status "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo '  export PATH="$HOME/.local/bin:$PATH"'
    fi#!/bin/bash

# TSM (Traefik Service Manager) Production Install Script
# This script installs TSM for production use

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory or installing from source
check_installation_method() {
    local install_method=""
    
    # Check if we're in a git repository with pyproject.toml
    if [[ -f "pyproject.toml" ]] && grep -q "name = \"tsm\"" pyproject.toml 2>/dev/null; then
        install_method="source"
        print_success "Found TSM source code - installing from source"
    # Check if TSM is available on PyPI or we should install from git
    elif [[ "$1" == "--from-git" ]] || [[ "$1" == "--dev" ]]; then
        install_method="git"
        print_status "Installing TSM from Git repository"
    else
        install_method="pypi"
        print_status "Installing TSM from PyPI"
    fi
    
    echo "$install_method"
}

# Install Python if needed (UV will handle this)
check_python_version() {
    # UV can install Python for us, so we don't require it to be pre-installed
    if command -v python3 >/dev/null 2>&1; then
        local python_version
        python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
        
        if [[ "$python_version" != "unknown" ]] && [[ $(echo "$python_version 3.10" | awk '{print ($1 >= $2)}') -eq 1 ]]; then
            print_success "Python $python_version found (compatible)"
            return 0
        fi
    fi
    
    print_status "Python 3.10+ not found. UV will install Python automatically."
}

# Install uv if not present
install_uv() {
    if command -v uv >/dev/null 2>&1; then
        local uv_version
        uv_version=$(uv --version 2>/dev/null | cut -d' ' -f2 || echo "unknown")
        print_success "uv is already installed (version: $uv_version)"
        return 0
    fi
    
    print_status "Installing uv package manager..."
    print_status "Note: uv will automatically download and manage Python versions as needed"
    
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        print_error "Neither curl nor wget is available."
        print_status "Please install curl or wget, or install uv manually:"
        print_status "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        print_status "  OR download from: https://github.com/astral-sh/uv/releases"
        exit 1
    fi
    
    # Source the shell configuration to make uv available
    if [[ -f "$HOME/.cargo/env" ]]; then
        source "$HOME/.cargo/env"
    fi
    
    # Add to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if command -v uv >/dev/null 2>&1; then
        print_success "uv installed successfully"
        print_status "uv can now automatically install Python 3.10+ if needed"
    else
        print_error "uv installation failed or not in PATH"
        print_status "Try opening a new terminal or running: source ~/.bashrc"
        print_status "Or manually add ~/.cargo/bin to your PATH"
        exit 1
    fi
}

# Install TSM for user operation
install_tsm() {
    local method="$1"
    local install_location="${INSTALL_LOCATION:-$HOME/.local/share/tsm}"
    
    print_status "Installing TSM for user operation..."
    
    case "$method" in
        "source")
            print_status "Installing from source code..."
            # Create virtual environment in project directory
            uv venv --python 3.10
            
            # Install only production dependencies
            uv sync --no-dev
            ;;
            
        "git")
            print_status "Installing from Git repository..."
            mkdir -p "$install_location"
            
            # Clone repository
            if command -v git >/dev/null 2>&1; then
                git clone https://github.com/yourusername/tsm.git "$install_location" || {
                    print_error "Failed to clone TSM repository"
                    exit 1
                }
                cd "$install_location"
                uv venv --python 3.10
                uv sync --no-dev
            else
                print_error "Git is required for --from-git installation"
                exit 1
            fi
            ;;
            
        "pypi")
            print_status "Installing from PyPI..."
            mkdir -p "$install_location"
            cd "$install_location"
            uv venv --python 3.10
            uv pip install tsm
            ;;
    esac
    
    print_success "TSM installed to $install_location"
    
    # Create user-local bin directory and symlink
    local user_bin="$HOME/.local/bin"
    mkdir -p "$user_bin"
    
    if [[ "$method" == "source" ]]; then
        ln -sf "$(pwd)/.venv/bin/tsm" "$user_bin/tsm" 2>/dev/null && {
            print_success "TSM symlink created in $user_bin"
        } || {
            print_warning "Could not create symlink in $user_bin"
        }
    else
        ln -sf "$install_location/.venv/bin/tsm" "$user_bin/tsm" 2>/dev/null && {
            print_success "TSM symlink created in $user_bin"
        } || {
            print_warning "Could not create symlink in $user_bin"
        }
    fi
}

# Create user configuration directory and sample config
setup_configuration() {
    local config_dir="$HOME/.config/tsm"
    
    print_status "Setting up user configuration..."
    
    # Create config directory
    mkdir -p "$config_dir" "$HOME/.local/share/tsm/logs"
    
    # Create sample configuration if it doesn't exist
    if [[ ! -f "$config_dir/config.yaml" ]]; then
        cat > "$config_dir/config.yaml" << 'EOF'
# TSM Configuration
tsm:
  # Docker settings
  docker:
    socket: "/var/run/docker.sock"
    network: "traefik"
  
  # Traefik settings
  traefik:
    config_dir: "./traefik/dynamic"
    reload_endpoint: "http://localhost:8080/api/providers/file/reload"
  
  # Scaling settings
  scaling:
    check_interval: 30
    cpu_threshold: 80
    memory_threshold: 80
    min_replicas: 1
    max_replicas: 10
  
  # Logging
  logging:
    level: "INFO"
    file: "$HOME/.local/share/tsm/logs/tsm.log"
    max_size: "10MB"
    backup_count: 5

# Service definitions will be auto-discovered from Docker labels
EOF
        print_success "Sample configuration created at $config_dir/config.yaml"
    else
        print_status "Configuration file already exists at $config_dir/config.yaml"
    fi
}

# Create configuration directory and sample config
setup_configuration() {
    local install_location="${INSTALL_LOCATION:-/opt/tsm}"
    local config_dir="$install_location"
    
    print_status "Setting up configuration..."
    
    # Create config directory
    mkdir -p "$config_dir" "/var/log/tsm"
    
    # Create sample configuration if it doesn't exist
    if [[ ! -f "$config_dir/config.yaml" ]]; then
        cat > "$config_dir/config.yaml" << 'EOF'
# TSM Configuration
tsm:
  # Docker settings
  docker:
    socket: "/var/run/docker.sock"
    network: "traefik"
  
  # Traefik settings
  traefik:
    config_dir: "/etc/traefik/dynamic"
    reload_endpoint: "http://localhost:8080/api/providers/file/reload"
  
  # Scaling settings
  scaling:
    check_interval: 30
    cpu_threshold: 80
    memory_threshold: 80
    min_replicas: 1
    max_replicas: 10
  
  # Logging
  logging:
    level: "INFO"
    file: "/var/log/tsm/tsm.log"
    max_size: "10MB"
    backup_count: 5

# Service definitions will be auto-discovered from Docker labels
EOF
        print_success "Sample configuration created at $config_dir/config.yaml"
    else
        print_status "Configuration file already exists at $config_dir/config.yaml"
    fi
}

# Show usage instructions
show_usage() {
    local method="$1"
    
    print_success "TSM installation complete!"
    print_status "Usage instructions:"
    echo ""
    
    if command -v tsm >/dev/null 2>&1; then
        echo "  Run TSM commands:"
        echo "    tsm --help                    # Show help"
        echo "    tsm init                      # Initialize TSM in current directory"
        echo "    tsm start                     # Start monitoring services"
        echo "    tsm status                    # Show service status"
        echo "    tsm scale <service> <count>   # Scale a service"
    else
        echo "  Add TSM to your PATH first:"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        echo ""
        echo "  Then run TSM commands:"
        echo "    tsm --help                    # Show help"
        echo "    tsm init                      # Initialize TSM in current directory"
        echo "    tsm start                     # Start monitoring services"
    fi
    
    echo ""
    echo "  Configuration:"
    echo "    Config file: ~/.config/tsm/config.yaml"
    echo "    Log files:   ~/.local/share/tsm/logs/"
    echo ""
    echo "  Getting started:"
    echo "    1. Make sure Docker and Traefik are running"
    echo "    2. Run 'tsm init' in your project directory"
    echo "    3. Configure your services with Docker labels"
    echo "    4. Run 'tsm start' to begin monitoring"
    echo ""
    
    if [[ "$method" == "source" ]]; then
        echo "  Development (source install):"
        echo "    Edit code and run: $(pwd)/.venv/bin/tsm"
        echo ""
    fi
}

# Main installation flow
main() {
    print_status "TSM (Traefik Service Manager) Installer"
    print_status "======================================="
    
    local install_method
    install_method=$(check_installation_method "$@")
    
    check_python_version
    install_uv
    install_tsm "$install_method"
    setup_configuration
    verify_installation "$install_method"
    show_usage "$install_method"
    
    print_success "Installation complete! 🚀"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "This script installs TSM (Traefik Service Manager) for user operation."
            echo ""
            echo "Installation methods:"
            echo "  (default)          Install from PyPI (when available)"
            echo "  --from-git         Install from Git repository"
            echo "  --dev              Install from Git repository (development)"
            echo ""
            echo "Options:"
            echo "  --help, -h         Show this help message"
            echo "  --force            Force reinstallation"
            echo ""
            echo "Environment variables:"
            echo "  INSTALL_LOCATION   Installation directory (default: ~/.local/share/tsm)"
            echo ""
            exit 0
            ;;
        --force)
            FORCE_INSTALL=true
            shift
            ;;
        --from-git|--dev)
            INSTALL_FROM_GIT=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            print_status "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Handle force installation
if [[ "$FORCE_INSTALL" == "true" ]]; then
    if [[ -d ".venv" ]]; then
        print_warning "Removing existing virtual environment..."
        rm -rf .venv
    fi
    if [[ -d "$HOME/.local/share/tsm" ]]; then
        print_warning "Removing existing TSM installation..."
        rm -rf "$HOME/.local/share/tsm"
    fi
fi

# Run the installer
main "$@"