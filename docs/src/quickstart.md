# Quickstart Guide

This guide will help you get started with TSM quickly. Follow these steps to set up and run your first service.

## 1. Install Dependencies

First, install the required dependencies:

```bash
tsm install-deps
```

## 2. Initialize Configuration

Initialize your configuration with your Docker Compose file:

```bash
tsm init-config -f docker-compose.yml
```

This will create the necessary configuration files in the `proxy` directory.

## 3. Configure Certificates

Edit the generated certificate configuration:

```bash
vim proxy/cert-config.yml
```

Then generate your certificates:

```bash
tsm generate-certs -c proxy/cert-config.yml
```

## 4. Generate Traefik Configuration

Generate the initial Traefik configuration:

```bash
tsm generate
```

For development, you can watch for changes:

```bash
tsm generate --watch
```

## 5. Launch Services

Start all your services:

```bash
tsm up
```

## 6. Monitor Services

Check the status of your services:

```bash
tsm status
```

To start auto-scaling monitoring:

```bash
tsm monitor
```

## Example Docker Compose File

Here's a basic example of a Docker Compose file that works with TSM:

```yaml
version: '3'

services:
  traefik:
    image: traefik:v2.10
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./proxy:/etc/traefik
    networks:
      - traefik

  whoami:
    image: traefik/whoami
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.rule=Host(`whoami.localhost`)"
    networks:
      - traefik

networks:
  traefik:
    external: true
```

## Next Steps

- Learn more about [CLI Commands](./cli-commands.md)
- Understand [Certificate Management](./certificate-management.md)
- Explore advanced configuration options
