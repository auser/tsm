# Certificate Management

TSM provides a flexible certificate management system that supports both command-line and YAML-based configuration.

## Command Line Options

```bash
tsm generate-certs [OPTIONS]

Options:
  --config, -c PATH     Path to certificate configuration YAML file
  --type TEXT           Certificate type: ca, server, client, peer, or all
  --name TEXT           Name for the certificate files
  --common-name TEXT    Common Name (CN) for the certificate
  --hosts TEXT          Comma-separated list of hosts for the cert
  --output-dir PATH     Base directory to write certs to
```

## YAML Configuration

The certificate configuration file (`cert-config.yml`) supports the following structure:

```yaml
# Global defaults
defaults:
  common_name: "traefik"
  hosts: "localhost,127.0.0.1,traefik"
  domain: "example.com"
  profile: "server"
  permissions:
    mode: 0o644
    owner: "traefik"
    group: "traefik"

# CA Configuration
ca:
  generate: true
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
```

## File Permissions

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

## Value Inheritance

Values are inherited in the following order (highest to lowest priority):
1. Certificate-specific configuration
2. CLI arguments
3. Environment variables
4. Global defaults

## Certificate Bundles

Bundles allow you to group related certificates together. Each bundle can:
- Copy certificates from individual certificate definitions
- Apply its own permissions
- Override certificate names in the bundle

Example bundle:
```yaml
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
