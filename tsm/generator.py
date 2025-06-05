"""Traefik configuration generator."""

from pathlib import Path
from typing import Any, TextIO

import yaml
from loguru import logger

from .config import Config
from .discovery import Service

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class ConfigGenerator:
    """Generate Traefik configuration from discovered services."""

    def __init__(
        self,
        name: str = "proxy",
        environment: str = "development",
        domain_suffix: str = ".ddev",
        external_host: str | None = None,
        swarm_mode: bool = False,
        config: Config | None = None,
        default_backend_host: str | None = None,
    ) -> None:
        self.name = name
        self.environment = environment
        self.domain_suffix = domain_suffix
        self.external_host = external_host
        self.swarm_mode = swarm_mode
        self.config = config or Config()
        self.default_backend_host = default_backend_host
        self.logger = logger.bind(component="generator")

    def generate_traefik_config(self, services: list[Service]) -> dict[str, Any]:
        """Generate complete Traefik configuration, supporting both HTTP and TCP."""

        self.logger.info(f"Generating Traefik config for {len(services)} services")

        config = {
            "http": {
                "routers": {},
                "services": {},
                "middlewares": {},
            },
            "tcp": {
                "routers": {},
                "services": {},
            },
        }

        for service in services:
            # HTTP routers/services
            if service.traefik_enabled and not self._is_tcp_service(service):
                self._add_service_config(config["http"], service)
            # TCP routers/services
            if self._is_tcp_service(service):
                self._add_tcp_service_config(config["tcp"], service)

        # Add default middlewares to HTTP only
        self._add_default_middlewares(config["http"])

        self.logger.info(
            f"Generated config with {len(config['http']['routers'])} HTTP routers and {len(config['tcp']['routers'])} TCP routers"
        )
        return config

    def _add_service_config(self, config: dict[str, Any], service: Service) -> None:
        """Add configuration for a single service."""

        router_name = f"{service.name}_router"
        service_name = f"{service.name}_service"

        # Generate router configuration
        router_config = self._generate_router_config(service, service_name)
        config["routers"][router_name] = router_config

        # Generate service configuration
        service_config = {"loadBalancer": {"servers": []}}
        address_set = False
        # Find all address labels
        address_labels = [
            (k, v)
            for k, v in service.labels.items()
            if k.startswith("traefik.http.services.") and k.endswith(".loadbalancer.server.address")
        ]
        # Prefer one matching the service name (hyphen or underscore)
        preferred_keys = [
            f"traefik.http.services.{service.name}.loadbalancer.server.address",
            f"traefik.http.services.{service.name.replace('_', '-')}.loadbalancer.server.address",
            f"traefik.http.services.{service.name.replace('-', '_')}.loadbalancer.server.address",
        ]
        selected_label = None
        selected_value = None
        for key in preferred_keys:
            for k, v in address_labels:
                if k == key:
                    selected_label = k
                    selected_value = v
                    break
            if selected_label:
                break
        # If no preferred, use the first found
        if not selected_label and address_labels:
            selected_label, selected_value = address_labels[0]
        if selected_label:
            service_config["loadBalancer"]["servers"].append({"url": selected_value})
            address_set = True
            self.logger.debug(
                f"Service {service.name}: Using address from label {selected_label} = {selected_value}"
            )
        # If no address, check for port label
        if not address_set:
            for k, v in service.labels.items():
                if k.startswith(f"traefik.http.services.{service_name}.loadbalancer.server.port"):
                    port = v
                    host = self.default_backend_host or service.name
                    url = f"http://{host}:{port}"
                    service_config["loadBalancer"]["servers"].append({"url": url})
                    address_set = True
                    self.logger.debug(f"Service {service.name}: Using port from label {k} = {v}")
                    break
        # If neither, fall back to main port
        if not address_set:
            service_config = self._generate_service_config(service)
            self.logger.debug(f"Service {service.name}: Falling back to main port logic.")
        health_check = self._generate_health_check(service)
        if health_check:
            service_config["loadBalancer"]["healthCheck"] = health_check
        if self._is_web_service(service):
            service_config["loadBalancer"]["sticky"] = {
                "cookie": {
                    "name": f"{service.name}_session",
                    "secure": True,
                    "httpOnly": True,
                }
            }
        config["services"][service_name] = service_config
        self.logger.debug(f"Added config for service: {service.name}")

    def _generate_router_config(self, service: Service, service_name: str) -> dict[str, Any]:
        """Generate router configuration for a service."""

        # Generate rule from service name if not provided
        rule = service.traefik_rule
        if not rule:
            domain = f"{service.name}{self.domain_suffix}"
            rule = f"Host(`{domain}`)"

        router_config = {
            "rule": rule,
            "service": service_name,
            "entryPoints": ["websecure"],  # Always use websecure
        }

        # Add TLS configuration
        # if self.config.traefik.tls_enabled:
        #     router_config["tls"] = {"certResolver": self.config.traefik.cert_resolver}

        # Add middlewares
        middlewares = service.traefik_middlewares.copy()
        if not middlewares:
            # Use default middlewares based on service characteristics
            middlewares = self._get_default_middlewares(service)

        if middlewares:
            router_config["middlewares"] = middlewares

        return router_config

    def _generate_service_config(self, service: Service) -> dict[str, Any]:
        """Generate service configuration."""

        service_config = {"loadBalancer": {"servers": self._generate_servers(service)}}

        # Add health check if available
        health_check = self._generate_health_check(service)
        if health_check:
            service_config["loadBalancer"]["healthCheck"] = health_check

        # Add sticky sessions for web services
        if self._is_web_service(service):
            service_config["loadBalancer"]["sticky"] = {
                "cookie": {
                    "name": f"{service.name}_session",
                    "secure": True,
                    "httpOnly": True,
                }
            }

        return service_config

    def _generate_servers(self, service: Service) -> list[dict[str, str]]:
        """Generate server list for load balancer."""

        port = service.main_port
        if not port:
            self.logger.warning(f"No port found for service {service.name}")
            return []

        if self.swarm_mode:
            # In swarm mode, use service name as hostname
            url = f"http://{service.name}:{port}"
        else:
            # Use default_backend_host if set, else external_host, else service.name
            host = self.default_backend_host or self.external_host or service.name
            url = f"http://{host}:{port}"

        return [{"url": url}]

    def _generate_health_check(self, service: Service) -> dict[str, Any] | None:
        """Generate health check configuration."""

        # Look for health check in labels
        health_path = service.labels.get("traefik.http.services.*.loadbalancer.healthcheck.path")
        if not health_path:
            # Try common health check paths
            if "spring" in service.image.lower() or "java" in service.image.lower():
                health_path = "/actuator/health"
            elif "rails" in service.image.lower() or "ruby" in service.image.lower():
                health_path = "/health"
            elif "django" in service.image.lower() or "python" in service.image.lower():
                health_path = "/health/"
            elif "express" in service.image.lower() or "node" in service.image.lower():
                health_path = "/health"
            else:
                return None

        health_config = {
            "path": health_path,
            "interval": self.config.health_checks.interval,
            "timeout": self.config.health_checks.timeout,
        }

        # Add authentication if needed
        if service.labels.get("traefik.http.services.*.loadbalancer.healthcheck.headers"):
            headers = service.labels["traefik.http.services.*.loadbalancer.healthcheck.headers"]
            health_config["headers"] = self._parse_headers(headers)

        return health_config

    def _get_default_middlewares(self, service: Service) -> list[str]:
        """Get default middlewares for a service based on its characteristics."""

        middlewares = []

        # Always add security headers
        middlewares.append("secure-headers@file")

        # Add compression for web services
        if self._is_web_service(service):
            middlewares.append("compress@file")

        # Add rate limiting based on service priority
        if service.scaling_config and service.scaling_config.priority:
            priority = service.scaling_config.priority
            if priority == "critical":
                middlewares.append("rate-limit-critical@file")
            elif priority in ["high", "medium"]:
                middlewares.append("rate-limit-api@file")
            else:
                middlewares.append("rate-limit@file")
        else:
            middlewares.append("rate-limit@file")

        # Add auth for admin services
        if "admin" in service.name.lower() or "dashboard" in service.name.lower():
            middlewares.append("auth@file")

        return middlewares

    def _is_web_service(self, service: Service) -> bool:
        """Check if service is a web application."""
        web_indicators = [
            "rails",
            "django",
            "express",
            "nginx",
            "apache",
            "php",
            "laravel",
            "symfony",
            "vue",
            "react",
        ]

        image_lower = service.image.lower()
        name_lower = service.name.lower()

        return any(
            indicator in image_lower or indicator in name_lower for indicator in web_indicators
        )

    def _is_api_service(self, service: Service) -> bool:
        """Check if service is an API."""
        api_indicators = ["api", "service", "microservice", "rest", "graphql"]

        name_lower = service.name.lower()
        return any(indicator in name_lower for indicator in api_indicators)

    def _parse_headers(self, headers_str: str) -> dict[str, str]:
        """Parse header string into dictionary."""
        headers = {}

        for header in headers_str.split(","):
            if ":" in header:
                key, value = header.split(":", 1)
                headers[key.strip()] = value.strip()

        return headers

    def _add_default_middlewares(self, config: dict[str, Any]) -> None:
        """Add default middleware configurations."""

        # These are basic middlewares - the full middleware config should be
        # loaded from the middleware.yml file
        default_middlewares = {
            "default-headers": {
                "headers": {
                    "X-Forwarded-Proto": "https",
                    "X-Real-IP": "{http_x_forwarded_for}",
                }
            }
        }

        config["middlewares"].update(default_middlewares)

    def generate_middleware_config(self) -> dict[str, Any]:
        """Generate middleware configuration."""

        with open(TEMPLATE_DIR / "middleware.yml") as f:
            middleware_template = yaml.safe_load(f)

        return middleware_template

    def generate_static_config(self) -> dict[str, Any]:
        """Generate Traefik static configuration."""

        return {
            "global": {"checkNewVersion": False, "sendAnonymousUsage": False},
            "api": {"dashboard": True, "insecure": True},  # Set to False in production
            "entryPoints": {"web": {"address": ":80"}, "websecure": {"address": ":443"}},
            "providers": {
                "docker": {
                    "exposedByDefault": False,
                    "network": self.config.docker.traefik_network,
                },
                "file": {"directory": "/etc/traefik/dynamic", "watch": True},
            },
            "metrics": {"prometheus": {"addEntryPointsLabels": True, "addServicesLabels": True}},
            "log": {"level": "INFO"},
            "accessLog": {},
        }

    def generate_docker_compose_file(self) -> str:
        """Generate docker-compose.yml file."""
        with open(TEMPLATE_DIR / "docker-compose.yml") as f:
            docker_compose_template = f.read()
        return docker_compose_template

    def generate_scaling_rules_file(self) -> str:
        """Generate scaling-rules.yml file."""
        with open(TEMPLATE_DIR / "scaling-rules.yml") as f:
            scaling_rules_template = f.read()
        return scaling_rules_template

    @staticmethod
    def write_yaml(data: dict[str, Any], file: TextIO) -> None:
        """Write data as YAML to file."""
        yaml.dump(
            data,
            file,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2,
        )

    def write_config_files(self, output_dir: Path, services: list[Service]) -> list[Path]:
        """Write all configuration files to output directory."""

        output_dir.mkdir(parents=True, exist_ok=True)
        config_dir = output_dir / "config"
        config_dir.mkdir(exist_ok=True)
        static_config_dir = config_dir / "static"
        static_config_dir.mkdir(exist_ok=True)
        dynamic_config_dir = config_dir / "dynamic"
        dynamic_config_dir.mkdir(exist_ok=True)
        created_files = []

        # Generate and write service configuration
        traefik_config = self.generate_traefik_config(services)
        services_file = dynamic_config_dir / "services.yml"
        with open(services_file, "w") as f:
            self.write_yaml({"http": traefik_config["http"]}, f)
        created_files.append(services_file)

        # Generate and write TCP service configuration
        tcp_services_file = dynamic_config_dir / "tcp-services.yml"
        with open(tcp_services_file, "w") as f:
            self.write_yaml({"tcp": traefik_config["tcp"]}, f)
        created_files.append(tcp_services_file)

        # Generate and write middleware configuration
        middleware_config = self.generate_middleware_config()
        middleware_file = dynamic_config_dir / "middleware.yml"
        with open(middleware_file, "w") as f:
            self.write_yaml(middleware_config, f)
        created_files.append(middleware_file)

        # Generate and write static configuration
        static_config = self.generate_static_config()
        static_file = static_config_dir / "traefik.yml"
        with open(static_file, "w") as f:
            self.write_yaml(static_config, f)
        created_files.append(static_file)

        # Generate and write docker-compose.yml file
        docker_compose_contents = self.generate_docker_compose_file()
        docker_compose_path = output_dir / "docker-compose.yml"
        with open(docker_compose_path, "w") as f:
            f.write(docker_compose_contents)
        created_files.append(docker_compose_path)

        # Generate and write scaling-rules.yml file
        scaling_rules_contents = self.generate_scaling_rules_file()
        scaling_rules_path = output_dir / "scaling-rules.yml"
        with open(scaling_rules_path, "w") as f:
            f.write(scaling_rules_contents)
        created_files.append(scaling_rules_path)

        return created_files

    def _is_tcp_service(self, service: Service) -> bool:
        """Detect if a service should be routed as TCP based on labels."""
        # Check for traefik.tcp.* labels or scheme=tcp
        for k, v in service.labels.items():
            if k.startswith("traefik.tcp."):
                return True
            if (
                k.startswith("traefik.http.services.")
                and ".loadbalancer.server.scheme" in k
                and v.strip().lower() == "tcp"
            ):
                return True
        return False

    def _add_tcp_service_config(self, tcp_config: dict[str, Any], service: Service) -> None:
        """Add TCP router and service config from labels."""
        routers = {}
        services = {}
        for k, v in service.labels.items():
            if k.startswith("traefik.tcp.routers."):
                parts = k.split(".")
                if len(parts) >= 4:
                    router_name = parts[3]
                    subkey = ".".join(parts[4:]) if len(parts) > 4 else None
                    if router_name not in routers:
                        routers[router_name] = {}
                    if subkey:
                        if subkey == "entrypoints":
                            routers[router_name]["entryPoints"] = [
                                ep.strip() for ep in v.split(",")
                            ]
                        else:
                            routers[router_name][subkey] = v
            elif k.startswith("traefik.tcp.services."):
                parts = k.split(".")
                if len(parts) >= 4:
                    service_name = parts[3]
                    subkey = ".".join(parts[4:]) if len(parts) > 4 else None
                    if service_name not in services:
                        services[service_name] = {"loadBalancer": {"servers": []}}
                    if subkey == "loadbalancer.server.address":
                        services[service_name]["loadBalancer"]["servers"].append({"address": v})
                    elif subkey == "loadbalancer.server.port":
                        # Only add if address not already set
                        if not any(
                            "address" in s
                            for s in services[service_name]["loadBalancer"]["servers"]
                        ):
                            port = v
                            host = self.default_backend_host or service.name
                            address = f"{host}:{port}"
                            services[service_name]["loadBalancer"]["servers"].append(
                                {"address": address}
                            )
        for router_name, router in routers.items():
            tcp_config["routers"][router_name] = router
        for service_name, svc in services.items():
            tcp_config["services"][service_name] = svc
