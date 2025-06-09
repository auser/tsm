"""Utility functions for TSM."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""

    # Remove default handler
    logger.remove()

    # Add console handler with colors
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        colorize=True,
    )

    # Add file handler for errors
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "tsm.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="10 days",
    )

    # Add error file handler
    logger.add(
        log_dir / "errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
    )


def get_local_ip() -> str | None:
    """Get local IP address."""
    import socket

    try:
        # Connect to a remote address to get local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return None


def validate_port(port: Any) -> bool:
    """Validate if a port number is valid."""
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False


def validate_domain(domain: str) -> bool:
    """Validate if a domain name is valid."""
    import re

    # Basic domain validation regex
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
    return bool(re.match(pattern, domain)) and len(domain) <= 253


def parse_memory_string(memory_str: str) -> int:
    """Parse memory string like '1GB', '512MB' into bytes."""
    import re

    match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$", memory_str.upper())
    if not match:
        raise ValueError(f"Invalid memory format: {memory_str}")

    value, unit = match.groups()
    value = float(value)

    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
        "": 1,
    }

    return int(value * units.get(unit, 1))


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f}PB"


def parse_duration_string(duration_str: str) -> int:
    """Parse duration string like '30s', '5m', '1h' into seconds."""
    import re

    match = re.match(r"^(\d+)\s*([smhd]?)$", duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value, unit = match.groups()
    value = int(value)

    units = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "": 1,  # Default to seconds
    }

    return value * units.get(unit, 1)


def format_duration(seconds: int) -> str:
    """Format seconds into human readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def safe_get(dictionary: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from nested dictionary using dot notation."""
    keys = key.split(".")
    current = dictionary

    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default

    return current


def merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries."""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def is_valid_service_name(name: str) -> bool:
    """Validate if a service name is valid for Docker."""
    import re

    # Docker service names must be lowercase alphanumeric with hyphens/underscores
    pattern = r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$"
    return bool(re.match(pattern, name)) and len(name) <= 63


def get_service_priority_weight(priority: str | None) -> int:
    """Get numeric weight for service priority."""
    priority_weights = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        None: 1,
    }
    return priority_weights.get(priority, 1)


def calculate_cpu_threshold(target: float, direction: str = "up") -> float:
    """Calculate CPU threshold based on target and direction."""
    if direction == "up":
        return target
    else:  # down
        return target * 0.4  # Scale down at 40% of target


def validate_scaling_config(config: dict[str, Any]) -> bool:
    """Validate scaling configuration parameters."""
    required_fields = ["min_replicas", "max_replicas"]

    for field in required_fields:
        if field not in config:
            return False

    min_replicas = config.get("min_replicas", 1)
    max_replicas = config.get("max_replicas", 10)

    if min_replicas < 1 or max_replicas < min_replicas:
        return False

    target_cpu = config.get("target_cpu", 70)
    if not 0 <= target_cpu <= 100:
        return False

    return True


def generate_service_url(service_name: str, port: int, external_host: str | None = None) -> str:
    """Generate service URL for load balancer."""
    host = external_host or service_name
    return f"http://{host}:{port}"


def extract_version_from_image(image: str) -> str | None:
    """Extract version tag from Docker image name."""
    if ":" in image:
        return image.split(":", 1)[1]
    return None


def is_production_environment(env: str) -> bool:
    """Check if environment is production."""
    return env.lower() in ["production", "prod", "live"]


def create_backup_filename(prefix: str, extension: str = "tar.gz") -> str:
    """Create backup filename with timestamp."""
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def ensure_directory(path: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    path.mkdir(parents=True, exist_ok=True)


def file_age_seconds(file_path: Path) -> float:
    """Get file age in seconds."""
    import time

    if not file_path.exists():
        return float("inf")

    return time.time() - file_path.stat().st_mtime


def is_file_newer_than(file_path: Path, seconds: int) -> bool:
    """Check if file is newer than specified seconds."""
    return file_age_seconds(file_path) < seconds


def get_available_port(start_port: int = 8000, max_attempts: int = 100) -> int | None:
    """Find an available port starting from start_port."""
    import socket

    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue

    return None


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry function on exception."""
    import time
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}, retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")

            raise last_exception

        return wrapper

    return decorator
