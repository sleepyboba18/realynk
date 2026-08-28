from __future__ import annotations

import ipaddress
from typing import Any
from uuid import uuid4

from flask import g, request


def normalize_ip(value: str | None) -> str:
    if not value:
        return "unknown"
    candidate = value.strip()
    if not candidate:
        return "unknown"
    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1 : candidate.index("]")]
    if candidate.count(":") == 1 and candidate.rsplit(":", 1)[1].isdigit() and "." in candidate:
        candidate = candidate.rsplit(":", 1)[0]
    try:
        ip_obj = ipaddress.ip_address(candidate)
    except ValueError:
        return "unknown"
    if ip_obj.version == 6 and ip_obj.ipv4_mapped is not None:
        return str(ip_obj.ipv4_mapped)
    return str(ip_obj)


def get_client_ip() -> str:
    if not request:
        return "unknown"
    if getattr(request, "access_route", None):
        for candidate in reversed(request.access_route):
            ip_value = normalize_ip(candidate)
            if ip_value != "unknown":
                return ip_value

    value = request.remote_addr or "unknown"
    return normalize_ip(value)


def get_request_id() -> str:
    request_id: str | None = getattr(g, "request_id", None)
    if not request_id:
        request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid4())
    cleaned = "".join(ch for ch in str(request_id) if ch.isalnum() or ch in "-_.")[:64]
    if not cleaned:
        cleaned = str(uuid4())
    g.request_id = cleaned
    return cleaned


def request_metadata() -> dict[str, Any]:
    return {
        "request_id": get_request_id(),
        "client_ip": get_client_ip(),
        "method": request.method,
        "path": request.path,
    }
