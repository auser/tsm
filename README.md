# Traefik Service Manager (TSM)

A modern service discovery and auto-scaling tool for Traefik with Docker.

## Summary

TSM is a comprehensive tool for managing Traefik proxy configurations in Docker environments. It provides:

- **Service Discovery**: Automatically discovers services from Docker Compose files
- **Certificate Management**: Flexible certificate generation and management with YAML configuration
- **Auto-scaling**: Prometheus-based monitoring and automatic service scaling
- **Configuration Generation**: Dynamic Traefik configuration based on service definitions
- **User Management**: Basic auth user file generation
- **Docker Integration**: Seamless integration with Docker and Docker Compose

## Installation

### Using Homebrew (macOS/Linux)

```bash
brew install auser/tap/tsm
```

### Using the Install Script

```bash
curl -LsSf https://raw.githubusercontent.com/auser/tsm/main/install.sh | sh
```

### Using pip

```bash
pip install tsm
```

## Quickstart

1. **Install Dependencies**
   ```bash
   tsm install-deps
   ```

2. **Initialize Configuration**
   ```bash
   # Initialize with your Docker Compose file
   tsm init-config -f docker-compose.yml
   ```

3. **Configure Certificates**
   ```bash
   # Edit the generated cert-config.yml
   vim proxy/cert-config.yml
   
   # Generate certificates
   tsm generate-certs -c proxy/cert-config.yml
   ```

4. **Generate Traefik Configuration**
   ```bash
   # Generate initial configuration
   tsm generate
   
   # Or watch for changes
   tsm generate --watch
   ```

5. **Launch Services**
   ```bash
   # Start all services
   tsm up
   ```

6. **Monitor Services**
   ```bash
   # Check service status
   tsm status
   
   # Start auto-scaling monitor
   tsm monitor
   ```

### Common Tasks

- **Scale a Service**
  ```bash
  tsm scale my-service 3
  ```

- **Generate Hosts File**
  ```bash
  tsm generate-hosts
  ```

- **Create Basic Auth**
  ```bash
  tsm generate-usersfile -u admin -p secret
  ```

- **Clean Up**
  ```bash
  tsm clean --all
  ```

## CLI Commands

### Generate Configuration

```bash
tsm generate [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path (env: COMPOSE_FILE)
  --output-dir, -o PATH      Output directory for generated configs (env: OUTPUT_DIR)
  --domain-suffix, -d TEXT   Domain suffix for services (env: DOMAIN_SUFFIX)
  --external-host TEXT       External host IP address (env: EXTERNAL_HOST)
  --swarm-mode              Generate for Docker Swarm mode (env: SWARM_MODE)
  --watch, -w               Watch for file changes and regenerate (env: WATCH)
  --default-backend-host TEXT Default backend host for HTTP services (env: DEFAULT_BACKEND_HOST)
```

Generates Traefik configuration from Docker Compose file. The command:
- Discovers services from the compose file
- Generates Traefik configuration
- Creates output directory if it doesn't exist
- Optionally watches for changes and regenerates

### Discover Services

```bash
tsm discover [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path
```

Lists all services discovered from the Docker Compose file, showing:
- Service name
- Image
- Ports
- Networks
- Scaling configuration

### Scale Service

```bash
tsm scale SERVICE_NAME REPLICAS [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path
  --update-config           Update Traefik config after scaling
```

Scales a service to the specified number of replicas. The command:
- Validates replica count (must be >= 0)
- Scales service in Swarm or Compose mode
- Optionally updates Traefik configuration

### Monitor Services

```bash
tsm monitor [OPTIONS]

Options:
  --compose-file, -f PATH    Docker Compose file path
  --scaling-config, -r PATH  Auto-scaling configuration file
  --prometheus-url, -p URL   Prometheus server URL
  --interval, -i SECONDS    Check interval in seconds
  --dry-run                Show what would be scaled without actually scaling
```

Starts the auto-scaling monitor. The command:
- Loads scaling configuration
- Connects to Prometheus
- Monitors service metrics
- Scales services based on rules
- Supports dry-run mode

### Show Service Status

```bash
tsm status [OPTIONS]

Options:
  --service, -s TEXT        Show status for specific service
  --detailed, -d           Show detailed information
  --format TEXT            Output format (table, json, yaml)
```

Shows service status information. The command:
- Lists all services or specific service
- Shows running containers, health, scaling status
- Supports multiple output formats

### Initialize Configuration

```bash
tsm init-config [OPTIONS]

Options:
  --name, -n TEXT          Name of the project (env: NAME)
  --environment, -e TEXT   Environment (env: ENVIRONMENT)
  --compose-file, -f PATH  Docker Compose file path (env: COMPOSE_FILE)
  --default-backend-host TEXT Default backend host for HTTP services (env: DEFAULT_BACKEND_HOST)
```

Initializes default configuration files. The command:
- Creates project directory structure
- Generates certificate templates
- Creates default configuration files
- Sets up monitoring configuration

### Generate Certificates

```bash
tsm generate-certs [OPTIONS]

Options:
  --config, -c PATH        Path to certificate configuration YAML file
  --type TEXT             Certificate type: ca, server, client, peer, or all
  --name TEXT             Name for the certificate files
  --common-name TEXT      Common Name (CN) for the certificate
  --hosts TEXT            Comma-separated list of hosts for the cert
  --output-dir PATH       Base directory to write certs to
  --cert-config-dir PATH  Directory containing ca-csr.json, ca-config.json, csr-template.json
  --profile TEXT          cfssl profile to use
  --domain TEXT           Domain for wildcard certs
  --bundle TEXT           Generate a bundle of certs for a specific use case
```

Generates certificates using cfssl/cfssljson. The command:
- Supports YAML configuration or command-line arguments
- Generates CA and service certificates
- Creates certificate bundles
- Manages file permissions

### Copy Certificates

```bash
tsm copy-certs [OPTIONS]

Options:
  --from-dir PATH         Source directory for certs
  --to-dir PATH          Destination directory for certs
```

Copies certificates from one directory to another. The command:
- Copies only existing certificates
- Preserves file permissions
- Creates destination directory if needed

### Install Dependencies

```bash
tsm install-deps
```

Installs required dependencies. The command:
- Checks for required tools (docker, python3, uv)
- Installs cfssl and cfssljson if missing
- Sets up Python virtual environment
- Installs Python dependencies

### Generate Hosts File

```bash
tsm generate-hosts [OPTIONS]

Options:
  --compose-file, -f PATH  Docker Compose file path
  --ip TEXT               IP address to use for hosts entries
  --output, -o PATH      Output file for hosts block
```

Generates /etc/hosts entries for all service domains. The command:
- Discovers service domains from compose file
- Auto-detects local IP if not provided
- Outputs to file or stdout

### Build Dockerfiles

```bash
tsm build-dockerfiles [OPTIONS]

Options:
  --dockerfiles-dir, -d PATH  Directory containing dockerfile subdirectories
  --tag-prefix TEXT          Prefix for built image tags
  --context-dir PATH         Docker build context directory
```

Builds all Dockerfiles in the specified directory. The command:
- Copies production certs if present
- Builds each Dockerfile with specified context
- Tags images with prefix
- Shows build output

### Generate Users File

```bash
tsm generate-usersfile [OPTIONS]

Options:
  --username, -u TEXT     Username for basic auth
  --password, -p TEXT     Password for basic auth
  --output, -o PATH      Output path for usersfile
```

Generates an htpasswd usersfile using Docker. The command:
- Creates usersfile with specified credentials
- Uses httpd:alpine for generation
- Outputs to specified path

### Launch Services

```bash
tsm up [OPTIONS]

Options:
  --compose-file, -f PATH  Docker Compose file path
```

Launches all services defined in the Docker Compose file. The command:
- Uses docker compose or docker-compose
- Launches services in detached mode
- Shows launch status

### Clean Resources

```bash
tsm clean [OPTIONS]

Options:
  --all, -a              Clean all Docker resources
  --volumes              Remove volumes
  --networks             Remove networks
```

Cleans up Docker resources. The command:
- Removes containers, images, and networks
- Optionally removes volumes
- Shows cleanup status

### Show Version

```bash
tsm version
```

Shows TSM version information. The command displays:
- TSM version
- Python version
- Platform information
- Docker version

## Certificate Management

TSM provides a flexible certificate management system that supports both command-line and YAML-based configuration.

### Command Line Options

```bash
tsm generate-certs [OPTIONS]

Options:
  --config, -c PATH     Path to certificate configuration YAML file
  --type TEXT           Certificate type: ca, server, client, peer, or all (default: all)
  --name TEXT           Name for the certificate files (default: type name)
  --common-name TEXT    Common Name (CN) for the certificate (default: traefik)
  --hosts TEXT          Comma-separated list of hosts for the cert
  --output-dir PATH     Base directory to write certs to (default: ./proxy/certs)
  --cert-config-dir PATH Directory containing ca-csr.json, ca-config.json, csr-template.json
  --profile TEXT        cfssl profile to use (default: server)
  --domain TEXT         Domain for wildcard certs (default: example.com)
  --bundle TEXT         Generate a bundle of certs for a specific use case
```

### YAML Configuration

The certificate configuration file (`cert-config.yml`) supports the following structure:

```yaml
# Global defaults
defaults:
  common_name: "traefik"  # Can be overridden by CLI --common-name or env COMMON_NAME
  hosts: "localhost,127.0.0.1,traefik"  # Can be overridden by CLI --hosts or env HOSTS
  domain: "example.com"  # Can be overridden by CLI --domain or env DOMAIN
  profile: "server"
  permissions:
    mode: 0o644  # File permissions (octal)
    owner: "traefik"  # File owner
    group: "traefik"  # File group

# CA Configuration
ca:
  generate: true  # Set to false to use existing CA
  name: "ca"
  common_name: "CA Name"
  hosts: "localhost,127.0.0.1"
  domain: "example.com"

# Individual Certificates
certificates:
  - name: "cert1"
    type: "server"
    common_name: "cert1"
    hosts: "localhost,127.0.0.1,cert1"
    permissions:
      mode: 0o600
      owner: "traefik"
      group: "traefik"

# Certificate Bundles
bundles:
  example:
    - name: "bundle-cert1"
      source: "cert1"
      copy: true
      permissions:
        mode: 0o644
        owner: "traefik"
        group: "traefik"
```

### File Permissions

The certificate system supports flexible file permission management:

1. **No permissions specified**: No changes are made to file permissions
2. **Only mode specified**: Uses current user:group for ownership
3. **Only owner specified**: Uses current group
4. **Full permissions**: Sets mode, owner, and group

Example permission configurations:
```yaml
# No permissions - no changes made
certificates:
  - name: "cert1"
    type: "server"
    common_name: "cert1"

# Only mode - uses current user:group
certificates:
  - name: "cert2"
    type: "server"
    permissions:
      mode: 0o600

# Only owner - uses current group
certificates:
  - name: "cert3"
    type: "server"
    permissions:
      owner: "traefik"

# Full permissions
certificates:
  - name: "cert4"
    type: "server"
    permissions:
      mode: 0o600
      owner: "traefik"
      group: "traefik"
```

### Value Inheritance

Values are inherited in the following order (highest to lowest priority):
1. Certificate-specific configuration
2. CLI arguments
3. Environment variables
4. Global defaults

### Certificate Bundles

Bundles allow you to group related certificates together. Each bundle can:
- Copy certificates from individual certificate definitions
- Apply its own permissions
- Override certificate names in the bundle

Example bundle:
```yaml
bundles:
  example:
    - name: "bundle-cert1"  # New name in bundle
      source: "cert1"       # Source certificate
      copy: true           # Copy the certificate
      permissions:         # Bundle-specific permissions
        mode: 0o644
        owner: "traefik"
        group: "traefik"
```

## Configuration


