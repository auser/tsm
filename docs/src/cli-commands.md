# CLI Commands

TSM provides a comprehensive set of CLI commands for managing your Traefik services. Here are the most commonly used commands:

## Generate Configuration

```bash
tsm generate [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path
  --output-dir, -o PATH      Output directory for generated configs
  --domain-suffix, -d TEXT   Domain suffix for services
  --external-host TEXT       External host IP address
  --swarm-mode              Generate for Docker Swarm mode
  --watch, -w               Watch for file changes and regenerate
```

## Discover Services

```bash
tsm discover [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path
```

## Scale Service

```bash
tsm scale SERVICE_NAME REPLICAS [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path
  --update-config           Update Traefik config after scaling
```

## Monitor Services

```bash
tsm monitor [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path
  --scaling-config, -r PATH  Auto-scaling configuration file
  --prometheus-url, -p URL   Prometheus server URL
  --interval, -i SECONDS    Check interval in seconds
  --dry-run                Show what would be scaled without actually scaling
```

## Show Service Status

```bash
tsm status [OPTIONS]

Options:
  --service, -s TEXT        Show status for specific service
  --detailed, -d           Show detailed information
  --format TEXT            Output format (table, json, yaml)
```

## Initialize Configuration

```bash
tsm init-config [OPTIONS]

Options:
  --name, -n TEXT          Name of the project
  --environment, -e TEXT   Environment
  --compose-file, -f PATH  Docker Compose file path
```

## Generate Certificates

```bash
tsm generate-certs [OPTIONS]

Options:
  --config, -c PATH        Path to certificate configuration YAML file
  --type TEXT             Certificate type: ca, server, client, peer, or all
  --name TEXT             Name for the certificate files
  --common-name TEXT      Common Name (CN) for the certificate
  --hosts TEXT            Comma-separated list of hosts for the cert
  --output-dir PATH       Base directory to write certs to
```

## Install Dependencies

```bash
tsm install-deps
```

## Generate Hosts File

```bash
tsm generate-hosts [OPTIONS]

Options:
  --compose-file, -f PATH  Docker Compose file path
  --ip TEXT               IP address to use for hosts entries
  --output, -o PATH      Output file for hosts block
```

## Launch Services

```bash
tsm up [OPTIONS]

Options:
  --compose-file, -f PATH  Docker Compose file path
```

## Clean Resources

```bash
tsm clean [OPTIONS]

Options:
  --all, -a              Clean all Docker resources
  --volumes              Remove volumes
  --networks             Remove networks
```

## Show Version

```bash
tsm version
```
