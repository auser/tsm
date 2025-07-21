"""Pytest configuration for TSM tests."""

import pytest
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def sample_compose_file():
    """Provide a sample docker-compose file for testing."""
    return Path(__file__).parent / "docker-compose.sample.yml" 