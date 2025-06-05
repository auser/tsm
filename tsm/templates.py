from pathlib import Path

import yaml
from loguru import logger

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def create_default_configs(
    name: str,
    force: bool = False,
    environment: str = "development",
    output_dir: Path | None = None,
) -> list[Path]:
    """Create default configuration files for TSM."""
    created_files = []
    base_dir = Path.cwd() / name
    base_dir.mkdir(parents=True, exist_ok=True)
    proxy_config_dir = base_dir / "config"
    proxy_config_dir.mkdir(parents=True, exist_ok=True)
    proxy_config_dynamic_dir = proxy_config_dir / "dynamic"
    proxy_config_dynamic_dir.mkdir(parents=True, exist_ok=True)
    proxy_config_static_dir = proxy_config_dir / "static"
    proxy_config_static_dir.mkdir(parents=True, exist_ok=True)

    # Default docker-compose.yml
    docker_compose_file = _generate_docker_compose_file(name, base_dir, force)
    if docker_compose_file:
        created_files.append(docker_compose_file)

    # Default middleware.yml
    middleware_file = _generate_middleware_file(proxy_config_dynamic_dir, force)
    if middleware_file:
        created_files.append(middleware_file)

    # Default scaling rules
    scaling_file = _generate_scaling_rules_file(base_dir, force)
    if scaling_file:
        created_files.append(scaling_file)

    # Default traefik.yml
    traefik_file = _generate_traefik_file(proxy_config_static_dir, force)
    if traefik_file:
        created_files.append(traefik_file)

    # Default config
    config_file = _generate_config_file(base_dir, environment, force)
    if config_file:
        created_files.append(config_file)

    return created_files


def _generate_config_file(dir: Path, environment: str, force: bool = False) -> str:
    """Generate a config.yml file."""
    config = {
        "environment": environment,
        "log_level": "INFO",
        "prometheus": {"url": "http://localhost:9090"},
        "docker": {"traefik_network": "traefik"},
    }
    config_file = dir / "config.yml"
    if force or not config_file.exists():
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        logger.info(f"Created {config_file}")
        return config_file
    else:
        logger.info(f"Skipped {config_file} (already exists)")
        return None


def _generate_docker_compose_file(name: str, dir: Path, force: bool = False) -> str:
    """Generate a docker-compose.yml file."""
    docker_compose_file = dir / "docker-compose.yml"
    with open(TEMPLATE_DIR / "docker-compose.yml") as f:
        docker_compose_template = f.read()
    if force or not docker_compose_file.exists():
        with open(docker_compose_file, "w") as f:
            f.write(docker_compose_template)
        logger.info(f"Created {docker_compose_file}")
        return docker_compose_file
    else:
        logger.info(f"Skipped {docker_compose_file} (already exists)")
        return None


def _generate_middleware_file(dir: Path, force: bool = False) -> str:
    """Generate a middleware.yml file."""
    middleware_file = dir / "middleware.yml"
    with open(TEMPLATE_DIR / "middleware.yml") as f:
        middleware_template = f.read()
    if force or not middleware_file.exists():
        with open(middleware_file, "w") as f:
            f.write(middleware_template)
        logger.info(f"Created {middleware_file}")
        return middleware_file
    else:
        logger.info(f"Skipped {middleware_file} (already exists)")
        return None


def _generate_scaling_rules_file(dir: Path, force: bool = False) -> str:
    """Generate a scaling-rules.yml file."""
    scaling_rules_file = dir / "scaling-rules.yml"
    with open(TEMPLATE_DIR / "scaling-rules.yml") as f:
        scaling_rules_template = f.read()
    if force or not scaling_rules_file.exists():
        with open(scaling_rules_file, "w") as f:
            f.write(scaling_rules_template)
        logger.info(f"Created {scaling_rules_file}")
        return scaling_rules_file
    else:
        logger.info(f"Skipped {scaling_rules_file} (already exists)")
        return None


def _generate_traefik_file(dir: Path, force: bool = False) -> str:
    """Generate a traefik.yml file."""
    traefik_file = dir / "traefik.yml"
    with open(TEMPLATE_DIR / "traefik.yml") as f:
        traefik_template = f.read()
    if force or not traefik_file.exists():
        with open(traefik_file, "w") as f:
            f.write(traefik_template)
        logger.info(f"Created {traefik_file}")
        return traefik_file
    else:
        logger.info(f"Skipped {traefik_file} (already exists)")
        return None
