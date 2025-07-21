"""Tests for the utils module."""

import pytest
from pathlib import Path
from tsm.utils import ensure_directory, merge_dicts, validate_port, validate_domain, get_local_ip


def test_ensure_directory(tmp_path):
    """Test that ensure_directory creates directories."""
    test_dir = tmp_path / "test" / "nested" / "directory"
    ensure_directory(test_dir)
    assert test_dir.exists()
    assert test_dir.is_dir()


def test_ensure_directory_existing(tmp_path):
    """Test that ensure_directory works with existing directories."""
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    
    ensure_directory(existing_dir)
    assert existing_dir.exists()
    assert existing_dir.is_dir()


def test_validate_port():
    """Test validate_port function."""
    assert validate_port(8080) == True
    assert validate_port("8080") == True
    assert validate_port(0) == False
    assert validate_port(65536) == False
    assert validate_port("invalid") == False
    assert validate_port(None) == False


def test_validate_domain():
    """Test validate_domain function."""
    assert validate_domain("example.com") == True
    assert validate_domain("sub.example.com") == True
    assert validate_domain("") == False
    assert validate_domain("a" * 254) == False  # Too long


def test_merge_dicts():
    """Test merge_dicts function."""
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    
    result = merge_dicts(dict1, dict2)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_merge_dicts_empty():
    """Test merge_dicts with empty dictionaries."""
    result = merge_dicts({}, {})
    assert result == {}


def test_merge_dicts_nested():
    """Test merge_dicts with nested dictionaries."""
    dict1 = {"a": {"x": 1, "y": 2}}
    dict2 = {"a": {"y": 3, "z": 4}}
    
    result = merge_dicts(dict1, dict2)
    assert result == {"a": {"x": 1, "y": 3, "z": 4}} 