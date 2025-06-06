#!/bin/bash

# Ensure Docker socket has correct permissions and ownership
sudo chown root:docker /var/run/docker.sock
sudo chmod 660 /var/run/docker.sock

# Add vscode user to docker group
sudo usermod -aG docker vscode

# Verify Docker access
docker ps

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to path
export PATH="$HOME/.local/bin:$PATH"

# Install uv packages
uv sync

echo "Ready"