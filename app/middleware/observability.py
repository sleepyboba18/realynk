from __future__ import annotations

import logging
import time
from typing import Any

from flask import Flask, g, request

from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.security.request_context import get_request_id

logger = get_logger(__name__)


def register_observability_middleware(app: Flask) -> None:
    @app.before_request
    def bind_request_context() -> None:
        g.request_id = get_request_id()
        g.request_started_at = time.perf_counter()
        g.request_path = request.path
        g.request_method = request.method

    @app.after_request
    def record_request_metrics(response):
        started = getattr(g, "request_started_at", None)
        duration_ms = 0.0
        if started is not None:
            duration_ms = (time.perf_counter() - started) * 1000
        metrics.increment(f"http.{request.method.lower()}.{request.path}", 1)
        metrics.observe("http.request_duration_ms", duration_ms)

        logger.info(
            "request_completed",
            extra={
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "route": request.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 3),
            },
        )
        return response

    @app.teardown_appcontext
    def teardown_request_context(_exc: Any) -> None:
        g.pop("request_started_at", None)
