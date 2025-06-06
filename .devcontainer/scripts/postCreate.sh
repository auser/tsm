#!/bin/bash

# Ensure Docker socket has correct permissions and ownership
sudo chown root:docker /var/run/docker.sock
sudo chmod 660 /var/run/docker.sock

# Add vscode user to docker group
sudo usermod -aG docker vscode

# Install Docker CLI if not present
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com/builds/Linux/x86_64/docker-latest.tgz | tar -xzC /usr/local/bin --strip=1 docker/docker
fi

# Verify Docker access
docker ps

echo "Ready"