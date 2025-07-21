#!/usr/bin/env python3
"""
Traefik Service Manager (TSM) - CLI Interface

A modern service discovery and auto-scaling tool for Traefik with Docker.
"""

import os
import shutil
import subprocess
import sys
import logging
from pathlib import Path
from typing import Optional, Literal

import click
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.table import Table

from .certs import copy_certs as copy_certs_func
from .config import Config, load_config
from .discovery import ServiceDiscovery
from .docker_client import DockerManager
from .generator import ConfigGenerator
from .monitoring import PrometheusClient
from .scaling import AutoScaler
from .utils import setup_logging

console = Console()

load_dotenv(Path.cwd() / ".env")

TemplateType = Literal["all", "scaling", "certs", "monitoring", "dockerfiles"]


def resolve_path(ctx: click.Context, path: str | None) -> Path:
    """Resolve a path relative to the base directory."""
    if not path:
        return Path.cwd()
    path = Path(path)
    if path.is_absolute():
        return path
    return (ctx.obj.base_dir / path).resolve()


@click.group()
@click.option("--config", "-c", help="Path to config file or docker-compose.yml")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output")
@click.option("--base-dir", "-d", help="Base directory for configs")
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool, quiet: bool, base_dir: str | None) -> None:
    """Traefik Service Manager (TSM) - Manage Traefik and service configurations."""
    # Configure logging
    log_level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("TSM started")

    # Load configuration
    config_path = Path(config) if config else None
    logger.debug(f"Config path: {config_path}")
    if config_path and config_path.suffix in {'.yml', '.yaml'} and 'compose' in config_path.name:
        logger.debug(f"Creating config with compose file: {config_path}")
        ctx.obj = Config(compose_file=str(config_path.absolute()), base_dir=config_path.parent.absolute())
        logger.debug(f"Base dir set to: {ctx.obj.base_dir}")
    else:
        ctx.obj = load_config(config_path)

    # Set base directory if provided
    if base_dir:
        ctx.obj.base_dir = Path(base_dir)
        logger.debug(f"Base dir overridden to: {ctx.obj.base_dir}")

@cli.command()
def steps():
    """List all available commands."""
    console.print("[green]Path to deploy a project:[/green]")
    console.print("1. tsm init-config -n <project-name> -e <environment> -b <default-backend-host>")
    console.print("2. tsm generate -f <compose-file> -o <output-dir> -d <domain-suffix> -h <external-host>")
    console.print("3. tsm generate-certs -c <cert-config-file> -t <type> -n <name> -h <hosts> -o <output-dir> -p <profile> -b <bundle>")
    console.print("4. tsm generate-usersfile -u <username> -p <password> -o <output-dir>")
    console.print("5. docker-compose up -d")

@cli.command()
@click.option(
    "--compose-file",
    "-f",
    default=os.environ.get("SERVICES_COMPOSE_FILE", "docker-compose.yml"),
    help="Docker Compose file path (env: SERVICES_COMPOSE_FILE)",
)
@click.option(
    "--output-dir",
    "-o",
    default=os.environ.get("OUTPUT_DIR", "config/traefik/dynamic"),
    help="Output directory for generated configs (env: OUTPUT_DIR)",
)
@click.option(
    "--domain-suffix",
    "-d",
    default=os.environ.get("DOMAIN_SUFFIX", ".ddev"),
    help="Domain suffix for services (env: DOMAIN_SUFFIX)",
)
@click.option(
    "--external-host",
    "-h",
    default=os.environ.get("EXTERNAL_HOST"),
    help="External host IP address (env: EXTERNAL_HOST)",
)
@click.option(
    "--swarm-mode",
    is_flag=True,
    default=os.environ.get("SWARM_MODE", "false").lower() == "true",
    help="Generate for Docker Swarm mode (env: SWARM_MODE)",
)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    default=os.environ.get("WATCH", "false").lower() == "true",
    help="Watch for file changes and regenerate (env: WATCH)",
)
@click.option(
    "--default-backend-host",
    "-b",
    default=os.environ.get("DEFAULT_BACKEND_HOST"),
    help="Default backend host for HTTP services (env: DEFAULT_BACKEND_HOST)",
)
@click.pass_context
def generate(
    ctx: click.Context,
    compose_file: str,
    output_dir: str,
    domain_suffix: str,
    external_host: str | None,
    swarm_mode: bool,
    watch: bool,
    default_backend_host: str | None,
) -> None:
    """Generate Traefik configuration from Docker Compose file."""

    config: Config = ctx.obj
    compose_path = resolve_path(ctx, compose_file)
    output_path = resolve_path(ctx, output_dir)

    if not compose_path.exists():
        console.print(f"[red]Error: Compose file not found: {compose_path}[/red]")
        sys.exit(1)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize components
    discovery = ServiceDiscovery()
    generator = ConfigGenerator(
        domain_suffix=domain_suffix,
        external_host=external_host,
        swarm_mode=swarm_mode,
        default_backend_host=default_backend_host,
    )

    def generate_configs() -> None:
        """Generate configuration files."""
        try:
            console.print(f"[blue]Discovering services from {compose_path}...[/blue]")
            services = discovery.discover_services(compose_path)

            console.print(f"[green]Found {len(services)} services[/green]")
            for service in services:
                console.print(f"  • {service.name} ({service.image})")

            console.print("[blue]Generating Traefik configuration...[/blue]")
            traefik_config = generator.generate_traefik_config(services)

            # Write configuration files
            config_file = output_path / "services.yml"
            with open(config_file, "w") as f:
                generator.write_yaml(traefik_config, f)

            console.print(f"[green]✓ Configuration written to {config_file}[/green]")

        except Exception as e:
            logger.error(f"Configuration generation failed: {e}")
            console.print(f"[red]Error: {e}[/red]")
            if not watch:
                sys.exit(1)

    # Generate once
    generate_configs()

    if watch:
        console.print(f"[yellow]Watching {compose_path} for changes...[/yellow]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")

        from .watcher import FileWatcher

        watcher = FileWatcher(compose_path, generate_configs)

        try:
            watcher.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping file watcher...[/yellow]")
            watcher.stop()


@cli.command()
@click.option(
    "--compose-file", "-f", default="docker-compose.yml", help="Docer Compose file path"
)
@click.pass_context
def discover(ctx: click.Context, compose_file: str) -> None:
    """Discover services from Docker Compose file."""

    compose_path = Path(compose_file)
    if not compose_path.exists():
        console.print(f"[red]Error: Compose file not found: {compose_path}[/red]")
        sys.exit(1)

    discovery = ServiceDiscovery()
    services = discovery.discover_services(compose_path)

    # Create a nice table
    table = Table(title="Discovered Services")
    table.add_column("Service", style="cyan")
    table.add_column("Image", style="green")
    table.add_column("Ports", style="yellow")
    table.add_column("Networks", style="blue")
    table.add_column("Scaling", style="magenta")

    for service in services:
        ports = ", ".join(str(p) for p in service.ports)
        networks = ", ".join(service.networks)
        scaling = "✓" if service.scaling_config and service.scaling_config.enabled else "✗"

        table.add_row(
            service.name,
            service.image,
            ports or "-",
            networks or "-",
            scaling,
        )

    console.print(table)


@cli.command()
@click.option(
    "--scaling-config", "-r", default="scaling-rules.yml", help="Auto-scaling configuration file"
)
@click.option(
    "--prometheus-url", "-p", default="http://localhost:9090", help="Prometheus server URL"
)
@click.option("--interval", "-i", default=60, help="Check interval in seconds")
@click.option("--dry-run", is_flag=True, help="Show what would be scaled without actually scaling")
@click.pass_context
def monitor(
    ctx: click.Context,
    scaling_config: str,
    prometheus_url: str,
    interval: int,
    dry_run: bool,
) -> None:
    """Start auto-scaling monitor."""

    config: Config = ctx.obj
    compose_path = resolve_path(ctx, config.compose_file)
    scaling_config_path = Path(scaling_config)

    if not compose_path.exists():
        console.print(f"[red]Error: Compose file not found: {compose_path}[/red]")
        sys.exit(1)

    if not scaling_config_path.exists():
        console.print(f"[red]Error: Scaling config not found: {scaling_config_path}[/red]")
        console.print("[yellow]Run 'tsm init-config' to create a default configuration[/yellow]")
        sys.exit(1)

    # Initialize components
    docker_manager = DockerManager()
    prometheus = PrometheusClient(prometheus_url)
    autoscaler = AutoScaler(
        docker_manager=docker_manager,
        prometheus_client=prometheus,
        scaling_config_path=scaling_config_path,
        compose_file_path=compose_path,
        check_interval=interval,
        dry_run=dry_run,
    )

    console.print("[green]Starting auto-scaling monitor...[/green]")
    console.print(f"  Compose file: {compose_path}")
    console.print(f"  Scaling config: {scaling_config_path}")
    console.print(f"  Prometheus: {prometheus_url}")
    console.print(f"  Check interval: {interval}s")
    console.print(f"  Dry run: {'Yes' if dry_run else 'No'}")
    console.print("\n[dim]Press Ctrl+C to stop[/dim]")

    try:
        autoscaler.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping auto-scaling monitor...[/yellow]")
        autoscaler.stop()


@cli.command()
@click.option("--service", "-s", help="Show status for specific service")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option(
    "--format",
    "-F",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def status(ctx: click.Context, service: str | None, detailed: bool, format: str) -> None:
    """Show service status."""

    docker_manager = DockerManager()
    config: Config = ctx.obj
    compose_path = resolve_path(ctx, config.compose_file)

    if not compose_path.exists():
        console.print(f"[red]Error: Compose file not found: {compose_path}[/red]")
        sys.exit(1)

    # Get services from compose file
    discovery = ServiceDiscovery()
    compose_services = {s.name for s in discovery.discover_services(compose_path)}

    try:
        if service:
            # Show specific service status
            if service not in compose_services:
                console.print(f"[red]Service '{service}' not found in compose file[/red]")
                sys.exit(1)

            service_info = docker_manager.get_service_status(service)
            if not service_info:
                console.print(f"[red]Service '{service}' is not running[/red]")
                sys.exit(1)

            if format == "json":
                import json
                print(json.dumps(service_info.__dict__, indent=2, default=str))
            elif format == "yaml":
                import yaml
                print(yaml.dump(service_info.__dict__, default_flow_style=False))
            else:
                # Table format
                table = Table(title=f"Service Status: {service}")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Name", service_info.name)
                table.add_row("Running Containers", str(service_info.running_containers))
                table.add_row("Total Containers", str(service_info.total_containers))
                table.add_row("Health", service_info.health_status)
                table.add_row("Scaling Enabled", "✓" if service_info.scaling_enabled else "✗")

                if service_info.priority:
                    table.add_row("Priority", service_info.priority)

                console.print(table)
        else:
            # Show all services from compose file
            services_info = {}
            for service_name in compose_services:
                service_info = docker_manager.get_service_status(service_name)
                if service_info:
                    services_info[service_name] = service_info.__dict__
                else:
                    services_info[service_name] = {
                        "name": service_name,
                        "running_containers": 0,
                        "total_containers": 0,
                        "health_status": "not running",
                        "scaling_enabled": False,
                        "priority": None
                    }

            if format == "json":
                import json
                print(json.dumps(services_info, indent=2, default=str))
            elif format == "yaml":
                import yaml
                print(yaml.dump(services_info, default_flow_style=False))
            else:
                # Table format
                table = Table(title="Service Status")
                table.add_column("Service", style="cyan")
                table.add_column("Running", style="green")
                table.add_column("Health", style="yellow")
                table.add_column("Scaling", style="blue")
                table.add_column("Priority", style="magenta")

                for service_name, info in services_info.items():
                    scaling = "✓" if info.get("scaling_enabled") else "✗"
                    priority = info.get("priority") or "-"

                    table.add_row(
                        info["name"],
                        f"{info['running_containers']}/{info['total_containers']}",
                        info["health_status"],
                        scaling,
                        priority,
                    )

                console.print(table)

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command("init-config")
@click.option("--name", "-n", default=os.environ.get("NAME", "proxy"), help="Name of the project")
@click.option("--environment", "-e", default=os.environ.get("ENVIRONMENT", "development"), help="Environment")
@click.option("--default-backend-host", "-b", default=os.environ.get("DEFAULT_BACKEND_HOST"), help="Default backend host for HTTP services")
@click.option("--template", "-t", type=click.Choice(["all", "scaling", "certs", "monitoring", "dockerfiles"]), default="all", help="Which template to generate")
@click.option("--overwrite", "-o", is_flag=True, help="Overwrite existing files")
@click.pass_context
def init_config(
    ctx: click.Context,
    name: str, 
    environment: str, 
    default_backend_host: str | None,
    template: TemplateType,
    overwrite: bool
) -> None:
    """Initialize default configuration files."""
    config = ctx.obj
    logger.debug(f"Config compose file: {config.compose_file}")
    logger.debug(f"Config base dir: {config.base_dir}")
    compose_path = Path(config.compose_file)
    logger.debug(f"Compose path: {compose_path}")
    if not compose_path.exists():
        console.print(f"[red]Error: Compose file not found: {compose_path}[/red]")
        sys.exit(1)

    try:
        discovery = ServiceDiscovery()
        services = discovery.discover_services(compose_path)

        generator = ConfigGenerator(
            name=name, environment=environment, default_backend_host=default_backend_host
        )
        base_dir = Path(name)
        created_files = generator.generate_templates(base_dir, template, overwrite, compose_file=compose_path)

        if created_files:
            console.print("[green]✓ Default configuration files created:[/green]")
            for file_path in created_files:
                console.print(f"  • {file_path}")

            console.print("\n[blue]Next steps:[/blue]")
            if template in ["all", "certs"]:
                console.print("  1. Edit cert-config.yml to configure certificates")
                console.print("  2. Run 'tsm generate-certs -c cert-config.yml' to generate certificates")
            if template in ["all", "scaling"]:
                console.print("  3. Edit scaling-rules.yml to configure auto-scaling")
            console.print("  4. Run 'tsm generate' to create Traefik config")
            console.print("  5. Run 'tsm monitor' to start auto-scaling")
        else:
            console.print("[yellow]No new files were created. Use --overwrite to force regeneration.[/yellow]")

    except Exception as e:
        logger.error(f"Config initialization failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
def sync_config() -> None:
    """Initialize named volumes for Traefik config."""

    docker_manager = DockerManager()
    docker_manager.init_volumes()


@cli.command()
@click.option("--all", "-a", is_flag=True, help="Clean all Docker resources")
@click.option("--volumes", is_flag=True, help="Remove volumes")
@click.option("--networks", is_flag=True, help="Remove networks")
def clean(all: bool, volumes: bool, networks: bool) -> None:
    """Clean up Docker resources."""

    docker_manager = DockerManager()

    try:
        if all:
            volumes = networks = True

        console.print("[blue]Cleaning up Docker resources...[/blue]")

        # Clean system
        docker_manager.clean_system()
        console.print("  ✓ System cleanup completed")

        if volumes:
            docker_manager.clean_volumes()
            console.print("  ✓ Volumes cleaned")

        if networks:
            docker_manager.clean_networks()
            console.print("  ✓ Networks cleaned")

        console.print("[green]✓ Cleanup completed[/green]")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show TSM version information."""

    import platform

    import docker

    table = Table(title="TSM Version Information")
    table.add_column("Component", style="cyan")
    table.add_column("Version", style="green")

    table.add_row("TSM", "1.0.1")
    table.add_row("Python", platform.python_version())
    table.add_row("Platform", platform.system())

    try:
        docker_client = docker.from_env()
        docker_version = docker_client.version()["Version"]
        table.add_row("Docker", docker_version)
    except Exception:
        table.add_row("Docker", "Not available")

    console.print(table)


@cli.command("generate-hosts")
@click.option(
    "--compose-file",
    "-f",
    default=os.environ.get("SERVICES_COMPOSE_FILE", "docker-compose.yml"),
    help="Docker Compose file path (env: SERVICES_COMPOSE_FILE)",
)
@click.option(
    "--ip",
    default=None,
    help="IP address to use for hosts entries (env: HOSTS_IP). If not provided, will auto-detect local IP.",
)
@click.option(
    "--output", "-o", default=None, help="Output file for hosts block (default: print to stdout)"
)
@click.pass_context
def generate_hosts(
    ctx: click.Context, compose_file: str, ip: str | None, output: str | None
) -> None:
    """Generate a /etc/hosts line for all service domains."""
    import socket

    from .discovery import ServiceDiscovery

    compose_path = Path(compose_file)
    if not compose_path.exists():
        console.print(f"[red]Error: Compose file not found: {compose_path}[/red]")
        sys.exit(1)
    # Auto-detect IP if not provided
    if not ip:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = "127.0.0.1"
    discovery = ServiceDiscovery()
    services = discovery.discover_services(compose_path)
    all_domains = set()
    for service in services:
        all_domains.update(service.domain_names)
    if not all_domains:
        console.print("[yellow]No domains found in services.[/yellow]")
        sys.exit(0)
    hosts_line = f"{ip} " + " ".join(sorted(all_domains))
    if output:
        with open(output, "w") as f:
            f.write(hosts_line + "\n")
        console.print(f"[green]✓ Hosts line written to {output}[/green]")
    else:
        console.print("[blue]Add the following line to your /etc/hosts:[/blue]")
        console.print(hosts_line)


@cli.command("build-dockerfiles")
@click.option(
    "--dockerfiles-dir",
    "-d",
    default=os.environ.get("DOCKERFILES_DIR", "dockerfiles"),
    help="Directory containing dockerfile subdirectories (default: ./dockerfiles)",
)
@click.option(
    "--tag-prefix",
    default=os.environ.get("TAG_PREFIX", "fp/"),
    help="Prefix for built image tags (default: fp/)",
)
@click.option(
    "--context-dir",
    default=os.environ.get("CONTEXT_DIR"),
    help="Docker build context directory (default: .)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Do not use cache when building the image",
)
@click.pass_context
def build_dockerfiles(ctx: click.Context, dockerfiles_dir: str, tag_prefix: str, context_dir: Optional[str], no_cache: bool) -> None:
    """Build all Dockerfiles in the dockerfiles directory with the specified build context."""
    from .certs import copy_prod_certs_if_present

    # Copy production certs if present before building
    if context_dir is None:
        context_dir = ctx.obj["base_dir"]

    copy_prod_certs_if_present()
    dockerfiles_path = Path(dockerfiles_dir)
    context_path = Path(context_dir)
    if not dockerfiles_path.exists() or not dockerfiles_path.is_dir():
        console.print(f"[red]Dockerfiles directory not found: {dockerfiles_path}[/red]")
        sys.exit(1)
    if not context_path.exists() or not context_path.is_dir():
        console.print(f"[red]Context directory not found: {context_path}[/red]")
        sys.exit(1)

    built_any = False
    for subdir in dockerfiles_path.iterdir():
        if subdir.is_dir():
            dockerfile = subdir / "Dockerfile"
            if dockerfile.exists():
                image_tag = f"{tag_prefix}{subdir.name}"
                console.print(
                    f"[blue]Building {dockerfile} as {image_tag} with context {context_path}...[/blue]"
                )
                import subprocess

                command = ["docker", "buildx", "build", "-f", str(dockerfile)]
                if no_cache:
                    command.append("--no-cache")
                command.extend(["-t", image_tag, str(context_path)])

                logger.debug(f"[blue]Running command: {command}[/blue]")
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    console.print(f"[green]✓ Built {image_tag}[/green]")
                    built_any = True
                else:
                    console.print(f"[red]Failed to build {image_tag}[/red]")
                    console.print(result.stderr)
    if not built_any:
        console.print("[yellow]No Dockerfiles found to build.[/yellow]")


@cli.command("generate-certs")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=os.environ.get("CERT_CONFIG_FILE", "cert-config.yml"),
    help="Path to certificate configuration YAML file",
)
@click.option(
    "--type",
    type=click.Choice(["all", "ca", "server", "client", "peer"]),
    default="all",
    show_default=True,
    help="Certificate type: ca, server, client, peer, or all (default: all)",
)
@click.option("--name", default=None, help="Name for the certificate files (default: type name)")
@click.option(
    "--common-name",
    default=os.environ.get("COMMON_NAME", "traefik"),
    help="Common Name (CN) for the certificate (default: traefik)",
)
@click.option(
    "--hosts",
    default=os.environ.get("HOSTS", "localhost,127.0.0.1,traefik"),
    help="Comma-separated list of hosts for the cert",
)
@click.option(
    "--output-dir",
    default=os.environ.get("OUTPUT_DIR", "./certs"),
    help="Base directory to write certs to (default: ./certs)",
)
@click.option(
    "--cert-config-dir",
    default=os.environ.get("CERT_CONFIG_DIR", "cert-config"),
    help="Directory containing ca-csr.json, ca-config.json, csr-template.json",
)
@click.option("--profile", default="server", help="cfssl profile to use (default: server)")
@click.option(
    "--domain",
    default=os.environ.get("DOMAIN", "example.com"),
    help="Domain for wildcard certs (default: example.com)",
)
@click.option(
    "--bundle",
    type=click.Choice(["traefik"]),
    default=None,
    help="Generate a bundle of certs for a specific use case (e.g., traefik)",
)
@click.pass_context
def generate_certs(
    ctx: click.Context,
    config: str | None,
    type: str,
    name: str | None,
    common_name: str,
    hosts: str,
    output_dir: str,
    cert_config_dir: str,
    profile: str,
    domain: str,
    bundle: str | None,
) -> None:
    """Generate CA or service certificates using cfssl/cfssljson (replaces gen-certs.sh)."""
    from .certs import generate_certs_cli, generate_certs_from_config

    console.print(f"[blue]Generating certs with config: {config}[/blue]")
    console.print(f"[blue]Generating certs with output_dir: {output_dir}[/blue]")
    console.print(f"[blue]Generating certs with cert_config_dir: {cert_config_dir}[/blue]")

    if config:
        # Use YAML configuration file
        config_path = resolve_path(ctx, config)
        output_path = resolve_path(ctx, output_dir)
        cert_config_path = resolve_path(ctx, cert_config_dir)
        
        cli_args = {
            'type': type,
            'name': name,
            'common_name': common_name,
            'hosts': hosts,
            'profile': profile,
            'domain': domain,
            'bundle': bundle,
        }
        generate_certs_from_config(config_path, output_path, cert_config_path, console, cli_args)
    else:
        console.print(f"[red]No config file provided[/red]")
        console.print(f"[red]Run 'tsm init-config' to create a default configuration[/red]")
        sys.exit(1)


@cli.command("copy-certs")
@click.option("--from-dir", required=True, help="Source directory for certs")
@click.option("--to-dir", required=True, help="Destination directory for certs")
@click.pass_context
def copy_certs(ctx: click.Context, from_dir: str, to_dir: str) -> None:
    """Copy certificates from one directory to another if they exist."""
    from_path = resolve_path(ctx, from_dir)
    to_path = resolve_path(ctx, to_dir)
    copy_certs_func(from_path, to_path, console)


@cli.command("generate-usersfile")
@click.option("--username", '-u', required=True, help="Username for basic auth")
@click.option("--password", '-p', required=True, help="Password for basic auth")
@click.option(
    "--output", '-o', default=os.environ.get("OUTPUT_DIR", "./config/usersfile"), help="Output path for usersfile (e.g., ./config/usersfile)"
)
@click.pass_context
def generate_usersfile_cmd(ctx: click.Context, username: str, password: str, output: str) -> None:
    """Generate an htpasswd usersfile using Docker (httpd:alpine)."""
    from .usersfile import generate_usersfile

    try:
        output_path = resolve_path(ctx, output)
        generate_usersfile(username, password, output_path)
        console.print(f"[green]✓ Usersfile written to {output_path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to generate usersfile: {e}[/red]")


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
