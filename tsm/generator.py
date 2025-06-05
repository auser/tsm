"""Traefik configuration generator."""

from pathlib import Path
from typing import Any, TextIO

import yaml
from loguru import logger

from .config import Config
from .discovery import Service


class ConfigGenerator:
    """Generate Traefik configuration from discovered services."""

    def __init__(
        self,
        domain_suffix: str = ".ddev",
        external_host: str | None = None,
        swarm_mode: bool = False,
        config: Config | None = None,
    ) -> None:
        self.domain_suffix = domain_suffix
        self.external_host = external_host
        self.swarm_mode = swarm_mode
        self.config = config or Config()
        self.logger = logger.bind(component="generator")

    def generate_traefik_config(self, services: list[Service]) -> dict[str, Any]:
        """Generate complete Traefik configuration."""

        self.logger.info(f"Generating Traefik config for {len(services)} services")

        config = {
            "http": {
                "routers": {},
                "services": {},
                "middlewares": {},
            }
        }

        # Generate configuration for each service
        for service in services:
            if service.traefik_enabled:
                self._add_service_config(config, service)

        # Add default middlewares
        self._add_default_middlewares(config)

        self.logger.info(f"Generated config with {len(config['http']['routers'])} routers")
        return config

    def _add_service_config(self, config: dict[str, Any], service: Service) -> None:
        """Add configuration for a single service."""

        router_name = f"{service.name}_router"
        service_name = f"{service.name}_service"

        # Generate router configuration
        router_config = self._generate_router_config(service, service_name)
        config["http"]["routers"][router_name] = router_config

        # Generate service configuration
        service_config = self._generate_service_config(service)
        config["http"]["services"][service_name] = service_config

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
        }

        # Add TLS configuration
        if self.config.traefik.tls_enabled:
            router_config["tls"] = {"certResolver": self.config.traefik.cert_resolver}

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
            # In compose mode, use external host or service name
            host = self.external_host or service.name
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

        config["http"]["middlewares"].update(default_middlewares)

    def generate_middleware_config(self) -> dict[str, Any]:
        """Generate middleware configuration."""

        return {
            "http": {
                "middlewares": {
                    "secure-headers": {
                        "headers": {
                            "accessControlAllowMethods": [
                                "GET",
                                "OPTIONS",
                                "PUT",
                                "POST",
                                "DELETE",
                            ],
                            "accessControlAllowOriginList": [
                                "https://localhost",
                                f"https://*{self.domain_suffix}",
                            ],
                            "accessControlMaxAge": 100,
                            "addVaryHeader": True,
                            "browserXssFilter": True,
                            "contentTypeNosniff": True,
                            "forceSTSHeader": True,
                            "frameDeny": True,
                            "referrerPolicy": "same-origin",
                            "sslRedirect": True,
                            "stsIncludeSubdomains": True,
                            "stsPreload": True,
                            "stsSeconds": 31536000,
                            "customRequestHeaders": {"X-Forwarded-Proto": "https"},
                        }
                    },
                    "compress": {"compress": {}},
                    "rate-limit": {"rateLimit": {"burst": 100, "average": 50, "period": "1m"}},
                    "rate-limit-api": {"rateLimit": {"burst": 50, "average": 25, "period": "1m"}},
                    "rate-limit-critical": {
                        "rateLimit": {"burst": 25, "average": 10, "period": "1m"}
                    },
                    "auth": {
                        "basicAuth": {
                            "users": [
                                "admin:$2y$10$2b2cu0pXZ8mUTtFBUhsKSeRWPYvN.7BjJePEKFz0N1AkD2EY.r9UG"
                            ],
                            "realm": "Traefik Protected Area",
                        }
                    },
                }
            }
        }

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
            "certificatesResolvers": {
                "letsencrypt": {
                    "acme": {
                        "email": "admin@localhost",
                        "storage": "/letsencrypt/acme.json",
                        "httpChallenge": {"entryPoint": "web"},
                    }
                }
            },
            "metrics": {"prometheus": {"addEntryPointsLabels": True, "addServicesLabels": True}},
            "log": {"level": "INFO"},
            "accessLog": {},
        }

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
        created_files = []

        # Generate and write service configuration
        traefik_config = self.generate_traefik_config(services)
        services_file = output_dir / "services.yml"
        with open(services_file, "w") as f:
            self.write_yaml(traefik_config, f)
        created_files.append(services_file)

        # Generate and write middleware configuration
        middleware_config = self.generate_middleware_config()
        middleware_file = output_dir / "middleware.yml"
        with open(middleware_file, "w") as f:
            self.write_yaml(middleware_config, f)
        created_files.append(middleware_file)

        # Generate and write static configuration
        static_config = self.generate_static_config()
        static_dir = output_dir.parent / "static"
        static_dir.mkdir(exist_ok=True)
        static_file = static_dir / "static.yml"
        with open(static_file, "w") as f:
            self.write_yaml(static_config, f)
        created_files.append(static_file)

        return created_files
