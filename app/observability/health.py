from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions.database import db


def check_database_health() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        db.session.execute(text("SELECT 1"))
        db.session.rollback()
        latency = (time.perf_counter() - start) * 1000
        return {"status": "healthy", "latency_ms": round(latency, 3)}
    except SQLAlchemyError:
        db.session.rollback()
        return {"status": "degraded", "latency_ms": round((time.perf_counter() - start) * 1000, 3)}


def get_health_status() -> dict[str, Any]:
    database = check_database_health()
    return {
        "status": "ok" if database["status"] in {"healthy", "degraded"} else "error",
        "services": {"database": database},
    }
