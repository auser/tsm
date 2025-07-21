"""Tests for the discovery module."""

from tsm.discovery import Service, ServiceDiscovery


def test_service_discovery_init():
    """Test ServiceDiscovery initialization."""
    discovery = ServiceDiscovery()
    assert discovery is not None


def test_service_init():
    """Test Service initialization."""
    service = Service(
        name="test-service",
        image="nginx",
        ports=[],
        networks=[],
        labels={},
        volumes=[],
        environment={},
        depends_on=[],
    )
    assert service.name == "test-service"
    assert service.image == "nginx"


def test_discover_services_empty_file(tmp_path):
    """Test discovering services from an empty compose file."""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(
        """
version: '3.8'
services: {}
"""
    )

    discovery = ServiceDiscovery()
    services = discovery.discover_services(compose_file)
    assert services == []


def test_discover_services_basic(tmp_path):
    """Test discovering services from a basic compose file."""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(
        """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web.rule=Host(`web.example.com`)"
"""
    )

    discovery = ServiceDiscovery()
    services = discovery.discover_services(compose_file)

    assert len(services) == 1
    service = services[0]
    assert service.name == "web"
    assert service.image == "nginx"


def test_discover_services_multiple(tmp_path):
    """Test discovering multiple services."""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(
        """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web.rule=Host(`web.example.com`)"
  api:
    image: python:3.9
    ports:
      - "8081:8000"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`)"
"""
    )

    discovery = ServiceDiscovery()
    services = discovery.discover_services(compose_file)

    assert len(services) == 2
    service_names = [s.name for s in services]
    assert "web" in service_names
    assert "api" in service_names
