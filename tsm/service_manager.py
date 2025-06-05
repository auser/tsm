from pathlib import Path
from typing import Any

from loguru import logger

from .config import Config, load_config
from .discovery import Service, ServiceDiscovery
from .docker_client import DockerManager
from .generator import ConfigGenerator
from .monitoring import PrometheusClient
from .scaling import AutoScaler


class ServiceManager:
    """
    Main service manager integrating service discovery, scaling, metrics, and config generation.
    """

    def __init__(
        self,
        config_path: str | None = None,
        compose_file: str | None = None,
        scaling_config_file: str | None = None,
        output_directory: str | None = None,
        prometheus_url: str | None = None,
        domain_suffix: str | None = None,
        swarm_mode: bool | None = None,
        external_host: str | None = None,
    ):
        self.config: Config = load_config(config_path)
        self.compose_file = Path(compose_file or self.config.compose_file)
        self.scaling_config_file = Path(scaling_config_file or self.config.scaling_config_file)
        self.output_directory = Path(output_directory or self.config.output_directory)
        self.domain_suffix = domain_suffix or getattr(
            self.config.traefik, "domain_suffix", ".localhost"
        )
        self.external_host = external_host or getattr(
            self.config.traefik, "external_host", "localhost"
        )
        self.prometheus_url = prometheus_url or getattr(
            self.config.prometheus, "url", "http://localhost:9090"
        )

        self.docker_manager = DockerManager()
        self.discovery = ServiceDiscovery()
        self.generator = ConfigGenerator(
            domain_suffix=self.domain_suffix,
            external_host=self.external_host,
            swarm_mode=(
                swarm_mode if swarm_mode is not None else self.docker_manager.is_swarm_mode()
            ),
            config=self.config,
        )
        self.prometheus = PrometheusClient(self.prometheus_url)
        self.autoscaler = AutoScaler(
            docker_manager=self.docker_manager,
            prometheus_client=self.prometheus,
            scaling_config_path=self.scaling_config_file,
            compose_file_path=self.compose_file,
        )
        logger.info(f"ServiceManager initialized with compose file: {self.compose_file}")

    def discover_services(self) -> list[Service]:
        """Discover services from the compose file."""
        return self.discovery.discover_services(self.compose_file)

    def get_running_services(self) -> list[str]:
        """Get list of running service names."""
        return self.docker_manager.get_running_services()

    def get_service_replicas(self, service_name: str) -> int:
        """Get the number of running replicas for a service."""
        status = self.docker_manager.get_service_status(service_name)
        return status.replicas if status else 0

    def scale_service(self, service_name: str, replicas: int) -> None:
        """Scale a service to the specified number of replicas."""
        if self.docker_manager.is_swarm_mode():
            self.docker_manager.scale_swarm_service(service_name, replicas)
        else:
            self.docker_manager.scale_compose_service(service_name, replicas, self.compose_file)

    def generate_config(self) -> dict[str, Any]:
        """Generate Traefik configuration for discovered services."""
        services = self.discover_services()
        config = self.generator.generate_traefik_config(services)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        config_file = self.output_directory / "services.yml"
        with open(config_file, "w") as f:
            import yaml

            yaml.dump(config, f, sort_keys=False, default_flow_style=False, indent=2)
        logger.info(f"Generated Traefik config at {config_file}")
        return config

    def monitor_and_scale(self, interval: int = 60, dry_run: bool = False) -> None:
        """Start monitoring and auto-scaling loop (blocking)."""
        self.autoscaler.check_interval = interval
        self.autoscaler.dry_run = dry_run
        self.autoscaler.start()
