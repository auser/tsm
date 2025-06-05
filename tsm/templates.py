from pathlib import Path

import yaml
from loguru import logger


def create_default_configs(name: str, force: bool = False) -> list[Path]:
    """Create default configuration files for TSM."""
    created_files = []
    base_dir = Path.cwd() / name
    base_dir.mkdir(parents=True, exist_ok=True)

    # Default scaling rules
    scaling_rules = {
        "services": {
            "example-service": {
                "enabled": True,
                "min_replicas": 1,
                "max_replicas": 5,
                "target_cpu": 70.0,
                "target_memory": 80.0,
                "priority": "medium",
            }
        }
    }
    scaling_file = base_dir / "scaling-rules.yml"
    if force or not scaling_file.exists():
        with open(scaling_file, "w") as f:
            yaml.dump(scaling_rules, f, default_flow_style=False)
        logger.info(f"Created {scaling_file}")
        created_files.append(scaling_file)
    else:
        logger.info(f"Skipped {scaling_file} (already exists)")

    # Default config
    config = {
        "environment": "development",
        "log_level": "INFO",
        "prometheus": {"url": "http://localhost:9090"},
        "docker": {"traefik_network": "traefik"},
    }
    config_file = base_dir / "config.yml"
    if force or not config_file.exists():
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        logger.info(f"Created {config_file}")
        created_files.append(config_file)
    else:
        logger.info(f"Skipped {config_file} (already exists)")

    return created_files
