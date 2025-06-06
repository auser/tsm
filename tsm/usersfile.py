import shutil
import subprocess
from pathlib import Path

from loguru import logger


def generate_usersfile(username: str, password: str, output_path: str) -> None:
    """
    Generate an htpasswd usersfile using docker (httpd:alpine) and write to output_path.
    """
    output_path = Path(output_path)
    if not shutil.which("docker"):
        logger.error("Docker is not installed or not in PATH.")
        raise RuntimeError("Docker is required to generate the usersfile.")
    cmd = ["docker", "run", "--rm", "httpd:alpine", "htpasswd", "-nbB", username, password]
    logger.debug(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result.stdout)
        logger.info(f"Usersfile written to {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate usersfile: {e.stderr}")
        raise RuntimeError(f"Failed to generate usersfile: {e.stderr}")
