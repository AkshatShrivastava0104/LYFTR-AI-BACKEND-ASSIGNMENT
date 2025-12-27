from collections import defaultdict
from typing import Dict, List
import threading

class MetricsCollector:
    def __init__(self):
        self.http_requests = defaultdict(int)
        self.webhook_requests = defaultdict(int)
        self.latency_buckets = defaultdict(int)
        self.latency_count = 0
        self.lock = threading.Lock()

    def inc_http_request(self, path: str, status: int):
        with self.lock:
            key = f'path="{path}",status="{status}"'
            self.http_requests[key] += 1

    def inc_webhook_request(self, result: str):
        with self.lock:
            key = f'result="{result}"'
            self.webhook_requests[key] += 1

    def observe_latency(self, latency_ms: float):
        with self.lock:
            self.latency_count += 1
            if latency_ms <= 100:
                self.latency_buckets['100'] += 1
            if latency_ms <= 500:
                self.latency_buckets['500'] += 1
            self.latency_buckets['+Inf'] += 1

    def generate_metrics(self) -> str:
        with self.lock:
            lines = []

            lines.append('# HELP http_requests_total Total HTTP requests')
            lines.append('# TYPE http_requests_total counter')
            for labels, count in self.http_requests.items():
                lines.append(f'http_requests_total{{{labels}}} {count}')

            lines.append('# HELP webhook_requests_total Total webhook requests')
            lines.append('# TYPE webhook_requests_total counter')
            for labels, count in self.webhook_requests.items():
                lines.append(f'webhook_requests_total{{{labels}}} {count}')

            lines.append('# HELP request_latency_ms_bucket Request latency in milliseconds')
            lines.append('# TYPE request_latency_ms_bucket histogram')
            for bucket, count in sorted(self.latency_buckets.items(),
                                       key=lambda x: float(x[0]) if x[0] != '+Inf' else float('inf')):
                lines.append(f'request_latency_ms_bucket{{le="{bucket}"}} {count}')
            lines.append(f'request_latency_ms_count {self.latency_count}')

            return '\n'.join(lines) + '\n'

metrics = MetricsCollector()
