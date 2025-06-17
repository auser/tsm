"""Configuration management for TSM."""

from typing import Any
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel, Field


class ScalingConfig(BaseModel):
    """Auto-scaling configuration for a service."""

    enabled: bool = True
    min_replicas: int = Field(ge=1, default=1)
    max_replicas: int = Field(ge=1, default=10)
    target_cpu: float = Field(ge=0, le=100, default=70.0)
    target_memory: float = Field(ge=0, le=100, default=80.0)
    scale_up_threshold: float | None = Field(ge=0, le=100, default=None)
    scale_down_threshold: float | None = Field(ge=0, le=100, default=None)
    scale_up_cooldown: int = Field(ge=0, default=300)  # seconds
    scale_down_cooldown: int = Field(ge=0, default=600)  # seconds
    priority: str | None = Field(default=None, pattern=r"^(low|medium|high|critical)$")

    def model_post_init(self, __context: Any) -> None:
        """Set default thresholds based on target values."""
        if self.scale_up_threshold is None:
            self.scale_up_threshold = self.target_cpu
        if self.scale_down_threshold is None:
            self.scale_down_threshold = self.target_cpu * 0.4  # 40% of target


class GlobalScalingConfig(BaseModel):
    """Global auto-scaling configuration."""

    check_interval: int = Field(ge=10, default=60)  # seconds
    scale_up_threshold: float = Field(ge=0, le=100, default=80.0)
    scale_down_threshold: float = Field(ge=0, le=100, default=30.0)
    scale_up_cooldown: int = Field(ge=0, default=300)  # seconds
    scale_down_cooldown: int = Field(ge=0, default=600)  # seconds
    max_scale_up_step: int = Field(ge=1, default=2)
    max_scale_down_step: int = Field(ge=1, default=1)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    burst: int = Field(ge=1, default=100)
    average: int = Field(ge=1, default=50)
    period: str = Field(default="1m", pattern=r"^\d+[smh]$")


class HealthCheckConfig(BaseModel):
    """Health check configuration."""

    interval: str = Field(default="30s", pattern=r"^\d+[smh]$")
    timeout: str = Field(default="5s", pattern=r"^\d+[smh]$")
    retries: int = Field(ge=1, default=3)
    start_period: str = Field(default="0s", pattern=r"^\d+[smh]$")


class PrometheusConfig(BaseModel):
    """Prometheus configuration."""

    url: str = Field(default="http://localhost:9090")
    timeout: int = Field(ge=1, default=30)
    verify_ssl: bool = Field(default=True)

    # Metric queries
    cpu_query: str = Field(
        default='rate(container_cpu_usage_seconds_total{{name=~".*{service}.*"}}[5m]) * 100'
    )
    memory_query: str = Field(
        default='(container_memory_usage_bytes{{name=~".*{service}.*"}} / '
        'container_spec_memory_limit_bytes{{name=~".*{service}.*"}}) * 100'
    )
    response_time_query: str = Field(
        default="histogram_quantile(0.95, sum(rate("
        'traefik_service_request_duration_seconds_bucket{{service=~".*{service}.*"}}[5m])) by (le))'
    )
    error_rate_query: str = Field(
        default='sum(rate(traefik_service_requests_total{{service=~".*{service}.*",code=~"5.."}}[5m])) / '
        'sum(rate(traefik_service_requests_total{{service=~".*{service}.*"}}[5m]))'
    )


class TraefikConfig(BaseModel):
    """Traefik configuration."""

    domain_suffix: str = Field(default=".ddev")
    external_host: str | None = Field(default=None)

    # TLS configuration
    tls_enabled: bool = Field(default=True)
    # cert_resolver: str = Field(default="letsencrypt")

    # Default middleware chains
    default_middleware: list[str] = Field(default=["secure-headers@file", "compress@file"])
    api_middleware: list[str] = Field(default=["secure-headers@file", "rate-limit-api@file"])
    admin_middleware: list[str] = Field(default=["secure-headers@file", "auth@file"])


class DockerConfig(BaseModel):
    """Docker configuration."""

    socket_path: str = Field(default="unix:///var/run/docker.sock")
    api_version: str = Field(default="auto")
    timeout: int = Field(ge=1, default=60)

    # Network configuration
    traefik_network: str = Field(default="traefik")
    monitoring_network: str = Field(default="monitoring")


class Config(BaseModel):
    """Main TSM configuration."""

    # Global settings
    environment: str = Field(default="development", pattern=r"^(development|staging|production)$")
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    base_dir: Path = Field(default_factory=Path.cwd)

    # Component configurations
    global_scaling: GlobalScalingConfig = Field(default_factory=GlobalScalingConfig)
    services: dict[str, ScalingConfig] = Field(default_factory=dict)
    rate_limits: dict[str, RateLimitConfig] = Field(default_factory=dict)
    health_checks: HealthCheckConfig = Field(default_factory=HealthCheckConfig)
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)
    traefik: TraefikConfig = Field(default_factory=TraefikConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)

    # File paths
    compose_file: str = Field(default="docker-compose.yml")
    scaling_config_file: str = Field(default="scaling-rules.yml")
    output_directory: str = Field(default="config/dynamic")

    def get_service_scaling_config(self, service_name: str) -> ScalingConfig:
        """Get scaling configuration for a service, using defaults if not specified."""
        if service_name in self.services:
            return self.services[service_name]


def load_config(path=None):
    """Load configuration from YAML file or return default Config."""
    from pathlib import Path

    if path is None:
        logger.info("No config path provided, using default Config.")
        return Config()
    try:
        path = Path(path)
        # If the path ends with docker-compose.yml, treat it as a compose file
        if path.name == "docker-compose.yml":
            config = Config()
            config.compose_file = str(path.absolute())
            config.base_dir = path.parent.absolute()
            return config
            
        with open(path) as f:
            data = yaml.safe_load(f)
        return Config(**data)
    except Exception as e:
        logger.error(f"Failed to load config from {path}: {e}")
        return Config()
