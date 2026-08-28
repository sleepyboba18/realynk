from __future__ import annotations

from typing import Any

from flask import Flask, g, request

from app.security.headers import apply_security_headers
from app.security.request_context import get_client_ip, get_request_id


def register_security_middleware(app: Flask) -> None:
    @app.before_request
    def handle_request_context() -> None:
        request_id = get_request_id()
        g.request_id = request_id
        g.client_ip = get_client_ip()

    @app.before_request
    def handle_request_limits() -> None:
        if request.method == "OPTIONS":
            return None

        data_length = 0
        if request.content_length is not None:
            data_length = request.content_length
        max_bytes = app.config.get("MAX_REQUEST_BODY_SIZE_BYTES", 5 * 1024 * 1024)
        if data_length > max_bytes:
            from app.utils.responses import error_response
            return error_response("REQUEST_TOO_LARGE", "Request body is too large", 413)

        if request.query_string and len(request.args) > app.config.get("MAX_QUERY_PARAMS", 50):
            from app.utils.responses import error_response
            return error_response("INVALID_QUERY", "Too many query parameters", 400)

        headers = request.headers
        if headers.get("Content-Type", "").startswith("application/json") and request.get_data(cache=True, as_text=False):
            if len(request.get_data(cache=True, as_text=False)) > max_bytes:
                from app.utils.responses import error_response
                return error_response("REQUEST_TOO_LARGE", "JSON payload is too large", 413)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Request-ID"] = g.get("request_id", "unknown")
        return apply_security_headers(response)

    @app.after_request
    def ensure_cors_response(response):
        origin = request.headers.get("Origin")
        if origin and request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Origin"] = origin if origin in app.config.get("CORS_ORIGINS", []) else ""
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID"
        return response
