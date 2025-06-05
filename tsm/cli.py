#!/usr/bin/env python3
"""
Traefik Service Manager (TSM) - CLI Interface

A modern service discovery and auto-scaling tool for Traefik with Docker.
"""

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from .config import Config, load_config
from .discovery import ServiceDiscovery
from .docker_client import DockerManager
from .generator import ConfigGenerator
from .monitoring import PrometheusClient
from .scaling import AutoScaler
from .utils import setup_logging

console = Console()


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Enable quiet mode")
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool, quiet: bool) -> None:
    """Traefik Service Manager - Auto-scaling and service discovery for Docker microservices."""

    # Setup logging
    log_level = "DEBUG" if verbose else "WARNING" if quiet else "INFO"
    setup_logging(log_level)

    # Load configuration
    config_path = Path(config) if config else None
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)

    logger.info("TSM started", version="0.1.0", log_level=log_level)


@cli.command()
@click.option(
    "--compose-file", "-f", default="docker-compose.yaml", help="Docker Compose file path"
)
@click.option(
    "--output-dir",
    "-o",
    default="proxy/config/dynamic",
    help="Output directory for generated configs",
)
@click.option("--domain-suffix", "-d", default=".ddev", help="Domain suffix for services")
@click.option("--external-host", "-h", help="External host IP address")
@click.option("--swarm-mode", is_flag=True, help="Generate for Docker Swarm mode")
@click.option("--watch", "-w", is_flag=True, help="Watch for file changes and regenerate")
@click.pass_context
def generate(
    ctx: click.Context,
    compose_file: str,
    output_dir: str,
    domain_suffix: str,
    external_host: str | None,
    swarm_mode: bool,
    watch: bool,
) -> None:
    """Generate Traefik configuration from Docker Compose file."""

    config: Config = ctx.obj["config"]
    compose_path = Path(compose_file)
    output_path = Path(output_dir)

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
    "--compose-file", "-f", default="docker-compose.yaml", help="Docker Compose file path"
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
@click.argument("service_name")
@click.argument("replicas", type=int)
@click.option(
    "--compose-file", "-f", default="docker-compose.yaml", help="Docker Compose file path"
)
@click.option("--update-config", is_flag=True, help="Update Traefik config after scaling")
@click.pass_context
def scale(
    ctx: click.Context,
    service_name: str,
    replicas: int,
    compose_file: str,
    update_config: bool,
) -> None:
    """Scale a service to the specified number of replicas."""

    if replicas < 0:
        console.print("[red]Error: Replicas must be >= 0[/red]")
        sys.exit(1)

    docker_manager = DockerManager()
    compose_path = Path(compose_file)

    try:
        console.print(f"[blue]Scaling {service_name} to {replicas} replicas...[/blue]")

        if docker_manager.is_swarm_mode():
            docker_manager.scale_swarm_service(service_name, replicas)
        else:
            docker_manager.scale_compose_service(service_name, replicas, compose_path)

        console.print(f"[green]✓ Successfully scaled {service_name} to {replicas} replicas[/green]")

        if update_config:
            console.print("[blue]Updating Traefik configuration...[/blue]")
            # Trigger config regeneration
            ctx.invoke(generate, compose_file=compose_file)

    except Exception as e:
        logger.error(f"Scaling failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--compose-file", "-f", default="docker-compose.yaml", help="Docker Compose file path"
)
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
    compose_file: str,
    scaling_config: str,
    prometheus_url: str,
    interval: int,
    dry_run: bool,
) -> None:
    """Start auto-scaling monitor."""

    compose_path = Path(compose_file)
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
def status(service: str | None, detailed: bool, format: str) -> None:
    """Show service status."""

    docker_manager = DockerManager()

    try:
        if service:
            # Show specific service status
            service_info = docker_manager.get_service_status(service)
            if not service_info:
                console.print(f"[red]Service '{service}' not found[/red]")
                sys.exit(1)

            if format == "json":
                import json

                console.print(json.dumps(service_info.__dict__, indent=2, default=str))
            elif format == "yaml":
                import yaml

                console.print(yaml.dump(service_info.__dict__, default_flow_style=False))
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
            # Show all services
            services = docker_manager.get_running_services()

            table = Table(title="Service Status")
            table.add_column("Service", style="cyan")
            table.add_column("Running", style="green")
            table.add_column("Health", style="yellow")
            table.add_column("Scaling", style="blue")
            table.add_column("Priority", style="magenta")

            for service_name in services:
                service_info = docker_manager.get_service_status(service_name)
                if service_info:
                    scaling = "✓" if service_info.scaling_enabled else "✗"
                    priority = service_info.priority or "-"

                    table.add_row(
                        service_info.name,
                        f"{service_info.running_containers}/{service_info.total_containers}",
                        service_info.health_status,
                        scaling,
                        priority,
                    )

            console.print(table)

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command("init-config")
@click.option("--name", "-n", default="proxy", help="Name of the project")
@click.option("--environment", "-e", default="development", help="Environment")
@click.option("--compose-file", "-f", default="docker-compose.yml", help="Docker Compose file path")
@click.option("--default-backend-host", "-b", help="Default backend host for HTTP services")
def init_config(
    name: str, environment: str, compose_file: str, default_backend_host: str | None
) -> None:
    """Initialize default configuration files."""

    compose_path = Path(compose_file)
    if not compose_path.exists():
        console.print(f"[red]Error: Compose file not found: {compose_path}[/red]")
        sys.exit(1)

    try:
        discovery = ServiceDiscovery()
        services = discovery.discover_services(compose_path)

        generator = ConfigGenerator(
            name=name, environment=environment, default_backend_host=default_backend_host
        )
        base_dir = Path.cwd() / name
        created_files = generator.write_config_files(output_dir=base_dir, services=services)

        console.print("[green]✓ Default configuration files created:[/green]")
        for file_path in created_files:
            console.print(f"  • {file_path}")

        console.print("\n[blue]Next steps:[/blue]")
        console.print("  1. Edit scaling-rules.yml to configure auto-scaling")
        console.print("  2. Run 'tsm generate' to create Traefik config")
        console.print("  3. Run 'tsm monitor' to start auto-scaling")

    except Exception as e:
        logger.error(f"Config initialization failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


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

    table.add_row("TSM", "0.1.0")
    table.add_row("Python", platform.python_version())
    table.add_row("Platform", platform.system())

    try:
        docker_client = docker.from_env()
        docker_version = docker_client.version()["Version"]
        table.add_row("Docker", docker_version)
    except Exception:
        table.add_row("Docker", "Not available")

    console.print(table)


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
