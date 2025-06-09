"""Service discovery from Docker Compose files."""

from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel

from .config import ScalingConfig


class ServicePort(BaseModel):
    """Container port configuration."""

    internal: int
    external: int | None = None
    protocol: str = "tcp"


class Service(BaseModel):
    """Discovered service information."""

    name: str
    image: str
    ports: list[ServicePort]
    networks: list[str]
    labels: dict[str, str]
    volumes: list[str]
    environment: dict[str, str]
    depends_on: list[str]
    restart_policy: str | None = None

    # Traefik configuration
    traefik_enabled: bool = False
    traefik_rule: str | None = None
    traefik_service_port: int | None = None
    traefik_middlewares: list[str] = []

    # Auto-scaling configuration
    scaling_config: ScalingConfig | None = None

    @property
    def main_port(self) -> int | None:
        """Get the main service port: prefer Traefik label port if present, else first port."""
        if self.traefik_service_port:
            logger.debug(
                f"Service {self.name}: Using traefik_service_port={self.traefik_service_port} from label."
            )
            return self.traefik_service_port
        if self.ports:
            logger.debug(
                f"Service {self.name}: Using first port from ports list: {self.ports[0].internal}"
            )
            return self.ports[0].internal
        logger.debug(f"Service {self.name}: No port found.")
        return None

    @property
    def domain_names(self) -> list[str]:
        """Extract domain names from Traefik rule."""
        if not self.traefik_rule:
            return []

        domains = []
        import re

        # Extract Host rules like Host(`example.com`) or Host(`app.domain.com`)
        host_pattern = r"Host\([`'\"]([^`'\"]+)[`'\"]\)"
        matches = re.findall(host_pattern, self.traefik_rule)
        domains.extend(matches)

        # Extract HostRegexp rules
        regexp_pattern = r"HostRegexp\([`'\"]([^`'\"]+)[`'\"]\)"
        matches = re.findall(regexp_pattern, self.traefik_rule)
        domains.extend(matches)

        return domains


class ServiceDiscovery:
    """Discover services from Docker Compose files."""

    def __init__(self) -> None:
        self.logger = logger.bind(component="discovery")

    def discover_services(self, compose_file: Path) -> list[Service]:
        """Discover services from a Docker Compose file."""

        self.logger.info(f"Discovering services from {compose_file}")

        try:
            with open(compose_file) as f:
                compose_data = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse compose file: {e}")

        if "services" not in compose_data:
            self.logger.warning("No services found in compose file")
            return []

        services = []
        for service_name, service_config in compose_data["services"].items():
            try:
                service = self._parse_service(service_name, service_config)
                services.append(service)
                self.logger.debug(f"Discovered service: {service_name}")
            except Exception as e:
                self.logger.error(f"Failed to parse service {service_name}: {e}")
                continue

        self.logger.info(f"Discovered {len(services)} services")
        return services

    def _parse_service(self, name: str, config: dict) -> Service:
        """Parse a single service configuration."""

        # Parse ports
        ports = self._parse_ports(config.get("ports", []))

        # Parse networks
        networks = self._parse_networks(config.get("networks", []))

        # Parse labels
        labels = config.get("deploy", {}).get("labels", [])
        if isinstance(labels, list):
            # Convert list format to dict
            label_dict = {}
            for label in labels:
                if "=" in label:
                    key, value = label.split("=", 1)
                    label_dict[key] = value
            labels = label_dict

        # Parse environment variables
        environment = self._parse_environment(config.get("environment", {}))

        # Parse volumes
        volumes = self._parse_volumes(config.get("volumes", []))

        # Parse depends_on
        depends_on = config.get("depends_on", [])
        if isinstance(depends_on, dict):
            depends_on = list(depends_on.keys())
        elif not isinstance(depends_on, list):
            depends_on = []

        # Parse Traefik configuration from labels
        traefik_config = self._parse_traefik_labels(labels)

        # Parse auto-scaling configuration from labels
        scaling_config = self._parse_scaling_labels(labels)

        return Service(
            name=name,
            image=config.get("image", ""),
            ports=ports,
            networks=networks,
            labels=labels,
            volumes=volumes,
            environment=environment,
            depends_on=depends_on,
            restart_policy=config.get("restart"),
            **traefik_config,
            scaling_config=scaling_config,
        )

    def _parse_ports(self, ports_config: list) -> list[ServicePort]:
        """Parse port configuration."""
        ports = []

        for port in ports_config:
            if isinstance(port, int):
                # Simple port mapping
                ports.append(ServicePort(internal=port))
            elif isinstance(port, str):
                # String format like "8080:80" or "8080:80/tcp"
                if ":" in port:
                    external_str, internal_str = port.split(":", 1)

                    # Handle protocol
                    protocol = "tcp"
                    if "/" in internal_str:
                        internal_str, protocol = internal_str.split("/", 1)

                    try:
                        external = int(external_str) if external_str else None
                        internal = int(internal_str)
                        ports.append(
                            ServicePort(internal=internal, external=external, protocol=protocol)
                        )
                    except ValueError:
                        continue
                else:
                    # Just internal port
                    try:
                        ports.append(ServicePort(internal=int(port)))
                    except ValueError:
                        continue
            elif isinstance(port, dict):
                # Dict format with target, published, protocol
                internal = port.get("target")
                external = port.get("published")
                protocol = port.get("protocol", "tcp")

                if internal:
                    ports.append(
                        ServicePort(internal=internal, external=external, protocol=protocol)
                    )

        return ports

    def _parse_networks(self, networks_config) -> list[str]:
        """Parse network configuration."""
        if isinstance(networks_config, list):
            return networks_config
        elif isinstance(networks_config, dict):
            return list(networks_config.keys())
        else:
            return []

    def _parse_environment(self, env_config) -> dict[str, str]:
        """Parse environment variables."""
        if isinstance(env_config, list):
            # Convert list format to dict
            env_dict = {}
            for env in env_config:
                if "=" in env:
                    key, value = env.split("=", 1)
                    env_dict[key] = value
            return env_dict
        elif isinstance(env_config, dict):
            # Convert all values to strings
            return {k: str(v) for k, v in env_config.items()}
        else:
            return {}

    def _parse_volumes(self, volumes_config: list) -> list[str]:
        """Parse volume configuration."""
        volumes = []

        for volume in volumes_config:
            if isinstance(volume, str):
                volumes.append(volume)
            elif isinstance(volume, dict):
                # Dict format with source, target, etc.
                source = volume.get("source", "")
                target = volume.get("target", "")
                if source and target:
                    volumes.append(f"{source}:{target}")
                elif target:
                    volumes.append(target)

        return volumes

    def _parse_traefik_labels(self, labels: dict[str, str]) -> dict:
        """Parse Traefik configuration from labels."""
        traefik_config = {
            "traefik_enabled": False,
            "traefik_rule": None,
            "traefik_service_port": None,
            "traefik_middlewares": [],
        }

        # Check if Traefik is enabled
        if labels.get("traefik.enable") == "true":
            traefik_config["traefik_enabled"] = True

        # Find router configuration
        router_name = None
        for key in labels:
            if key.startswith("traefik.http.routers.") and key.endswith(".rule"):
                router_name = key.split(".")[3]
                traefik_config["traefik_rule"] = labels[key]
                break

        # Find all possible service port labels
        port_labels = [
            (k, v)
            for k, v in labels.items()
            if k.startswith("traefik.http.services.") and k.endswith(".loadbalancer.server.port")
        ]

        selected_port = None
        selected_label = None
        # Prefer port label matching router name
        if router_name:
            expected_key = f"traefik.http.services.{router_name}.loadbalancer.server.port"
            for k, v in port_labels:
                if k == expected_key:
                    try:
                        selected_port = int(v)
                        selected_label = k
                        break
                    except ValueError:
                        continue
        # Otherwise, use the first available port label
        if selected_port is None and port_labels:
            for k, v in port_labels:
                try:
                    selected_port = int(v)
                    selected_label = k
                    break
                except ValueError:
                    continue
        if selected_port is not None:
            traefik_config["traefik_service_port"] = selected_port
            logger.debug(f"Service port from label: {selected_label} = {selected_port}")

        # Get middlewares
        if router_name:
            middleware_key = f"traefik.http.routers.{router_name}.middlewares"
            if middleware_key in labels:
                middlewares = labels[middleware_key].split(",")
                traefik_config["traefik_middlewares"] = [m.strip() for m in middlewares]

        return traefik_config

    def _parse_scaling_labels(self, labels: dict[str, str]) -> ScalingConfig | None:
        """Parse auto-scaling configuration from labels."""
        if labels.get("tsm.scaling.enabled") != "true":
            return None

        scaling_config = {}

        # Parse scaling parameters
        for key, value in labels.items():
            if not key.startswith("tsm.scaling."):
                continue

            param = key.replace("tsm.scaling.", "")

            try:
                if param in [
                    "min_replicas",
                    "max_replicas",
                    "scale_up_cooldown",
                    "scale_down_cooldown",
                ]:
                    scaling_config[param] = int(value)
                elif param in [
                    "target_cpu",
                    "target_memory",
                    "scale_up_threshold",
                    "scale_down_threshold",
                ]:
                    scaling_config[param] = float(value)
                elif param == "enabled":
                    scaling_config[param] = value.lower() == "true"
                elif param == "priority":
                    scaling_config[param] = value
            except ValueError:
                logger.warning(f"Invalid scaling parameter value: {key}={value}")
                continue

        try:
            return ScalingConfig(**scaling_config)
        except Exception as e:
            logger.warning(f"Invalid scaling configuration: {e}")
            return None

    def get_service_dependencies(self, services: list[Service]) -> dict[str, set[str]]:
        """Build service dependency graph."""
        dependencies = {}

        for service in services:
            dependencies[service.name] = set(service.depends_on)

        return dependencies

    def get_services_by_network(self, services: list[Service]) -> dict[str, list[str]]:
        """Group services by network."""
        networks = {}

        for service in services:
            for network in service.networks:
                if network not in networks:
                    networks[network] = []
                networks[network].append(service.name)

        return networks

    def get_traefik_enabled_services(self, services: list[Service]) -> list[Service]:
        """Get services that have Traefik enabled."""
        return [service for service in services if service.traefik_enabled]

    def get_scalable_services(self, services: list[Service]) -> list[Service]:
        """Get services that have auto-scaling enabled."""
        return [
            service
            for service in services
            if service.scaling_config and service.scaling_config.enabled
        ]
