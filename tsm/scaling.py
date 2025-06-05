import threading
from pathlib import Path

from loguru import logger

from .config import load_config
from .discovery import ServiceDiscovery


class AutoScaler:
    def __init__(
        self,
        docker_manager,
        prometheus_client,
        scaling_config_path: Path,
        compose_file_path: Path,
        check_interval: int = 60,
        dry_run: bool = False,
    ):
        self.docker_manager = docker_manager
        self.prometheus = prometheus_client
        self.scaling_config_path = scaling_config_path
        self.compose_file_path = compose_file_path
        self.check_interval = check_interval
        self.dry_run = dry_run
        self._stop_event = threading.Event()
        self.logger = logger.bind(component="autoscaler")

    def start(self):
        self.logger.info("AutoScaler started")
        self._stop_event.clear()
        while not self._stop_event.is_set():
            self._check_and_scale()
            self._stop_event.wait(self.check_interval)

    def stop(self):
        self.logger.info("AutoScaler stopped")
        self._stop_event.set()

    def _check_and_scale(self):
        config = load_config(self.scaling_config_path)
        discovery = ServiceDiscovery()
        services = discovery.discover_services(self.compose_file_path)
        scalable_services = discovery.get_scalable_services(services)
        for service in scalable_services:
            name = service.name
            scaling = service.scaling_config
            cpu = self.prometheus.get_cpu(name, config.prometheus.cpu_query)
            mem = self.prometheus.get_memory(name, config.prometheus.memory_query)
            if cpu is None and mem is None:
                continue
            metric = cpu if cpu is not None else mem
            desired = None
            if metric > scaling.scale_up_threshold and service.scaling_config.max_replicas > 0:
                desired = min(
                    self.docker_manager.get_service_status(name).replicas + 1, scaling.max_replicas
                )
            elif metric < scaling.scale_down_threshold and service.scaling_config.min_replicas > 0:
                desired = max(
                    self.docker_manager.get_service_status(name).replicas - 1, scaling.min_replicas
                )
            if (
                desired is not None
                and desired != self.docker_manager.get_service_status(name).replicas
            ):
                if self.dry_run:
                    self.logger.info(f"[Dry Run] Would scale {name} to {desired} replicas")
                else:
                    self.logger.info(f"Scaling {name} to {desired} replicas")
                    if self.docker_manager.is_swarm_mode():
                        self.docker_manager.scale_swarm_service(name, desired)
                    else:
                        self.docker_manager.scale_compose_service(
                            name, desired, self.compose_file_path
                        )
