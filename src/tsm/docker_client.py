"""Docker client wrapper for service management."""

import subprocess
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, DockerException, NotFound
from loguru import logger
from pydantic import BaseModel


class ContainerInfo(BaseModel):
    """Container information."""

    id: str
    name: str
    service_name: str | None = None
    image: str
    status: str
    state: str
    ports: dict[str, Any]
    labels: dict[str, str]
    networks: list[str]
    created: str


class ServiceStatus(BaseModel):
    """Service status information."""

    name: str
    running_containers: int
    total_containers: int
    replicas: int
    desired_replicas: int | None = None
    ports: list[int]
    domains: list[str]
    health_status: str
    scaling_enabled: bool
    priority: str | None = None
    last_scaled: str | None = None


class ContainerMetrics(BaseModel):
    """Container metrics for auto-scaling."""

    container_id: str
    name: str
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_rx_bytes: int
    network_tx_bytes: int
    timestamp: str


class DockerManager:
    """Manage Docker containers and services."""

    def __init__(self, socket_path: str = "unix:///var/run/docker.sock") -> None:
        self.logger = logger.bind(component="docker")

        try:
            self.client = docker.from_env()
            self.client.ping()
            self.logger.info("Connected to Docker daemon")
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}") from e

        # Check if we're in swarm mode
        try:
            self.client.api.inspect_swarm()
            self.swarm_mode = True
            self.logger.info("Docker swarm mode detected")
        except Exception:
            self.swarm_mode = False
            self.logger.info("Docker swarm mode not detected")

    def is_swarm_mode(self) -> bool:
        """Check if Docker is running in swarm mode."""
        return self.swarm_mode

    def get_running_services(self) -> list[str]:
        """Get list of running services."""
        try:
            containers = self.client.containers.list()
            services = set()

            for container in containers:
                # Get service name from compose label
                service_name = container.labels.get("com.docker.compose.service")
                if service_name:
                    services.add(service_name)

            return list(services)
        except DockerException as e:
            self.logger.error(f"Failed to get running services: {e}")
            return []

    def get_service_containers(self, service_name: str) -> list[ContainerInfo]:
        """Get containers for a specific service."""
        try:
            containers = self.client.containers.list(all=True)
            service_containers = []

            for container in containers:
                if container.labels.get("com.docker.compose.service") == service_name:
                    info = self._container_to_info(container)
                    service_containers.append(info)

            return service_containers
        except DockerException as e:
            self.logger.error(f"Failed to get containers for service {service_name}: {e}")
            return []

    def get_service_status(self, service_name: str) -> ServiceStatus | None:
        """Get status information for a service."""
        containers = self.get_service_containers(service_name)

        if not containers:
            return None

        running_containers = len([c for c in containers if c.state == "running"])
        total_containers = len(containers)

        # Extract ports and domains from containers
        ports = set()
        domains = set()

        for container in containers:
            # Get ports
            for port_info in container.ports.values():
                if port_info:
                    for port in port_info:
                        if port.get("HostPort"):
                            ports.add(int(port["HostPort"]))

            # Extract domains from Traefik labels
            for key, value in container.labels.items():
                if "traefik.http.routers" in key and key.endswith(".rule"):
                    domain = self._extract_domain_from_rule(value)
                    if domain:
                        domains.add(domain)

        # Check scaling configuration
        first_container = containers[0]
        scaling_enabled = first_container.labels.get("tsm.scaling.enabled") == "true"
        priority = first_container.labels.get("tsm.scaling.priority")

        # Determine health status
        if running_containers == 0:
            health_status = "unhealthy"
        elif running_containers < total_containers:
            health_status = "degraded"
        else:
            health_status = "healthy"

        return ServiceStatus(
            name=service_name,
            running_containers=running_containers,
            total_containers=total_containers,
            replicas=running_containers,
            ports=list(ports),
            domains=list(domains),
            health_status=health_status,
            scaling_enabled=scaling_enabled,
            priority=priority,
        )

    def scale_compose_service(self, service_name: str, replicas: int, compose_file: Path) -> None:
        """Scale a service using docker-compose."""
        try:
            # Try docker-compose first
            cmd = [
                "docker-compose",
                "-f",
                str(compose_file),
                "up",
                "-d",
                "--scale",
                f"{service_name}={replicas}",
                "--no-recreate",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                # Try docker compose (newer syntax)
                cmd[0] = "docker"
                cmd.insert(1, "compose")

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            self.logger.info(f"Scaled service {service_name} to {replicas} replicas")

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to scale service {service_name}: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except FileNotFoundError:
            raise RuntimeError("docker-compose command not found") from None

    def scale_swarm_service(self, service_name: str, replicas: int) -> None:
        """Scale a service in Docker Swarm."""
        try:
            cmd = ["docker", "service", "scale", f"{service_name}={replicas}"]
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            self.logger.info(f"Scaled swarm service {service_name} to {replicas} replicas")

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to scale swarm service {service_name}: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_container_metrics(self, container_id: str) -> ContainerMetrics | None:
        """Get metrics for a container."""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)

            # Parse CPU stats
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]

            cpu_usage = cpu_stats["cpu_usage"]
            precpu_usage = precpu_stats["cpu_usage"]

            cpu_delta = cpu_usage["total_usage"] - precpu_usage["total_usage"]
            system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
                "system_cpu_usage", 0
            )

            if system_delta > 0:
                online_cpus = len(cpu_usage.get("percpu_usage", [1]))
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100
            else:
                cpu_percent = 0.0

            # Parse memory stats
            memory_stats = stats["memory_stats"]
            memory_usage = memory_stats.get("usage", 0)
            memory_limit = memory_stats.get("limit", 1)
            memory_percent = (memory_usage / memory_limit) * 100

            # Parse network stats
            networks = stats.get("networks", {})
            total_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
            total_tx = sum(net.get("tx_bytes", 0) for net in networks.values())

            return ContainerMetrics(
                container_id=container_id,
                name=container.name,
                cpu_percent=cpu_percent,
                memory_usage=memory_usage,
                memory_limit=memory_limit,
                memory_percent=memory_percent,
                network_rx_bytes=total_rx,
                network_tx_bytes=total_tx,
                timestamp=stats.get("read", ""),
            )

        except (DockerException, KeyError) as e:
            self.logger.error(f"Failed to get metrics for container {container_id}: {e}")
            return None

    def get_service_metrics(self, service_name: str) -> list[ContainerMetrics]:
        """Get aggregated metrics for all containers in a service."""
        containers = self.get_service_containers(service_name)
        metrics = []

        for container in containers:
            if container.state == "running":
                container_metrics = self.get_container_metrics(container.id)
                if container_metrics:
                    metrics.append(container_metrics)

        return metrics

    def create_networks(self, networks: list[str]) -> None:
        """Create Docker networks if they don't exist."""
        for network_name in networks:
            try:
                self.client.networks.get(network_name)
                self.logger.debug(f"Network {network_name} already exists")
            except NotFound:
                try:
                    self.client.networks.create(network_name, driver="bridge")
                    self.logger.info(f"Created network: {network_name}")
                except APIError as e:
                    self.logger.warning(f"Failed to create network {network_name}: {e}")

    def clean_system(self) -> None:
        """Clean up Docker system."""
        try:
            # Prune containers
            self.client.containers.prune()
            # Prune images
            self.client.images.prune()
            # Prune networks
            self.client.networks.prune()
            # Prune volumes
            self.client.volumes.prune()
            self.logger.info("Cleaned up Docker system")
        except DockerException as e:
            self.logger.error(f"Failed to clean Docker system: {e}")
            raise RuntimeError(f"Failed to clean Docker system: {e}") from e

    def clean_volumes(self) -> None:
        """Clean up unused Docker volumes."""
        try:
            self.client.volumes.prune()
            self.logger.info("Docker volumes cleanup completed")
        except DockerException as e:
            self.logger.error(f"Failed to clean Docker volumes: {e}")

    def clean_networks(self) -> None:
        """Clean up unused Docker networks."""
        try:
            self.client.networks.prune()
            self.logger.info("Docker networks cleanup completed")
        except DockerException as e:
            self.logger.error(f"Failed to clean Docker networks: {e}")

    def init_volumes(self) -> None:
        """Initialize required volumes for Traefik configuration."""
        required_volumes = [
            "traefik_data",
            "traefik_logs",
            "traefik_dynamic",
            "prometheus_data",
            "grafana_data",
            "alertmanager_data",
        ]

        for volume_name in required_volumes:
            try:
                self.client.volumes.get(volume_name)
                self.logger.debug(f"Volume {volume_name} already exists")
            except NotFound:
                try:
                    self.client.volumes.create(volume_name)
                    self.logger.info(f"Created volume: {volume_name}")
                except APIError as e:
                    self.logger.warning(f"Failed to create volume {volume_name}: {e}")

    def _container_to_info(self, container) -> ContainerInfo:
        """Convert Docker container to ContainerInfo."""
        # Get service name from labels
        service_name = container.labels.get("com.docker.compose.service")

        # Get networks
        networks = list(container.attrs.get("NetworkSettings", {}).get("Networks", {}).keys())

        return ContainerInfo(
            id=container.id,
            name=container.name,
            service_name=service_name,
            image=container.image.tags[0] if container.image.tags else "unknown",
            status=container.status,
            state=container.attrs.get("State", {}).get("Status", "unknown"),
            ports=container.ports,
            labels=container.labels,
            networks=networks,
            created=container.attrs.get("Created", ""),
        )

    def _extract_domain_from_rule(self, rule: str) -> str | None:
        """Extract domain from Traefik rule."""
        import re

        # Extract Host rules like Host(`example.com`)
        host_pattern = r"Host\([`'\"]([^`'\"]+)[`'\"]\)"
        match = re.search(host_pattern, rule)

        if match:
            return match.group(1)

        return None

    def get_compose_services(self, compose_file: Path) -> list[str]:
        """Get list of services defined in docker-compose file."""
        try:
            # Try docker-compose
            cmd = ["docker-compose", "-f", str(compose_file), "config", "--services"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                # Try docker compose
                cmd = ["docker", "compose", "-f", str(compose_file), "config", "--services"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            services = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return services

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get compose services: {e.stderr}")
            return []
        except FileNotFoundError:
            self.logger.error("docker-compose command not found")
            return []
