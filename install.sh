#!/bin/sh
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Version
VERSION="0.1.0"

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print error and exit
error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
    exit 1
}

# Print warning
warn() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

# Print success
success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

# Install Python and pip if not present
install_python() {
    if command_exists apt-get; then
        echo "Installing Python and pip..."
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    elif command_exists yum; then
        echo "Installing Python and pip..."
        sudo yum install -y python3 python3-pip
    elif command_exists brew; then
        echo "Installing Python and pip..."
        brew install python
    else
        error "Could not install Python. Please install Python 3 and pip manually."
    fi
}

# Create and activate virtual environment
setup_venv() {
    echo "Setting up Python virtual environment..."
    python3 -m venv .venv
    . .venv/bin/activate
}

# Install uv if not present
install_uv() {
    if ! command_exists uv; then
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
}

# Main installation process
main() {
    echo "Installing tsm v${VERSION}..."

    # Check for Python
    if ! command_exists python3; then
        warn "Python 3 not found. Installing..."
        install_python
    fi

    # Check for pip
    if ! command_exists pip3; then
        warn "pip not found. Installing..."
        install_python
    fi

    # Install uv
    install_uv

    # Setup virtual environment
    setup_venv

    # Install tsm
    echo "Installing tsm..."
    pip install tsm

    success "tsm v${VERSION} has been installed successfully!"
    echo "To start using tsm, run: source .venv/bin/activate"
}

# Run main installation
main 