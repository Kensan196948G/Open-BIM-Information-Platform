"""Lightweight Prometheus-format metrics (no external dependencies).

Exposes request counts and latency totals for ``/metrics`` so the existing
``scripts/monitor.sh`` / SLI/SLO tooling has an internal source of truth.
The registry is process-local; multi-instance deployments should aggregate
per instance (or move to a shared metrics backend).
"""

import time

from app.core.config import settings

_requests_total: dict[tuple[str, str, str], int] = {}
_duration_sum: dict[tuple[str, str], float] = {}
_duration_count: dict[tuple[str, str], int] = {}


def _route_path(scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None) if route else None
    return path or scope.get("path", "unmatched")


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()

        async def _send_wrapper(message):
            if message["type"] == "http.response.start":
                status = str(message["status"])
                route = _route_path(scope)
                method = scope.get("method", "UNKNOWN")
                key = (method, route, status)
                _requests_total[key] = _requests_total.get(key, 0) + 1
                dur_key = (method, route)
                _duration_sum[dur_key] = _duration_sum.get(dur_key, 0.0) + (
                    time.perf_counter() - start
                )
                _duration_count[dur_key] = _duration_count.get(dur_key, 0) + 1
            await send(message)

        await self.app(scope, receive, _send_wrapper)


def render_metrics() -> str:
    lines = [
        "# HELP bim_http_requests_total Total HTTP requests.",
        "# TYPE bim_http_requests_total counter",
    ]
    for (method, route, status), count in sorted(_requests_total.items()):
        lines.append(
            f'bim_http_requests_total{{method="{method}",route="{route}",'
            f'status="{status}"}} {count}'
        )
    lines.append("# HELP bim_http_request_duration_seconds Request duration.")
    lines.append("# TYPE bim_http_request_duration_seconds summary")
    for (method, route), count in sorted(_duration_count.items()):
        lines.append(
            f'bim_http_request_duration_seconds_sum{{method="{method}",'
            f'route="{route}"}} {_duration_sum.get((method, route), 0.0):.6f}'
        )
        lines.append(
            f'bim_http_request_duration_seconds_count{{method="{method}",'
            f'route="{route}"}} {count}'
        )
    lines.append(
        f'bim_app_info{{version="{settings.APP_VERSION}",'
        f'environment="{settings.ENVIRONMENT}"}} 1'
    )
    return "\n".join(lines) + "\n"
