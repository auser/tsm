import requests
from loguru import logger


class PrometheusClient:
    def __init__(
        self, url: str = "http://localhost:9090", timeout: int = 30, verify_ssl: bool = True
    ):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.logger = logger.bind(component="prometheus")

    def query(self, query: str) -> float | None:
        try:
            resp = requests.get(
                f"{self.url}/api/v1/query",
                params={"query": query},
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            if data["status"] == "success" and data["data"]["result"]:
                return float(data["data"]["result"][0]["value"][1])
            return None
        except Exception as e:
            self.logger.error(f"Prometheus query failed: {e}")
            return None

    def get_cpu(self, service: str, query_template: str) -> float | None:
        return self.query(query_template.format(service=service))

    def get_memory(self, service: str, query_template: str) -> float | None:
        return self.query(query_template.format(service=service))

    def get_response_time(self, service: str, query_template: str) -> float | None:
        return self.query(query_template.format(service=service))

    def get_error_rate(self, service: str, query_template: str) -> float | None:
        return self.query(query_template.format(service=service))
