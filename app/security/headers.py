from __future__ import annotations

from flask import Response


def get_security_headers() -> dict[str, str]:
    headers: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
    }
    return headers


def apply_security_headers(response: Response) -> Response:
    headers = get_security_headers()
    for key, value in headers.items():
        response.headers[key] = value
    return response
