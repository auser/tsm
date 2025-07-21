"""Tests for the config module."""

import pytest
from tsm.config import Config, load_config


def test_config_defaults():
    """Test that Config has default values."""
    config = Config()
    assert config.environment == "development"
    assert config.output_directory == "config/dynamic"


def test_config_custom_values():
    """Test that Config can be created with custom values."""
    config = Config(
        environment="production",
        output_directory="custom/output"
    )
    assert config.environment == "production"
    assert config.output_directory == "custom/output"


def test_load_config_default():
    """Test loading default config."""
    config = load_config()
    assert isinstance(config, Config)
    assert config.environment == "development"


def test_load_config_with_path(tmp_path):
    """Test loading config from a file."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
environment: production
output_directory: test/output
""")
    
    config = load_config(str(config_file))
    assert config.environment == "production"
    assert config.output_directory == "test/output" 