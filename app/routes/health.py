from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions.database import db
from app.observability.health import get_health_status
from app.observability.metrics import metrics


health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health() -> tuple[object, int]:
    try:
        db.session.execute(text("SELECT 1"))
        db.session.remove()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"status": "ok", "database": "unavailable", "mode": "degraded"}), 200

    return jsonify({"status": "ok", "database": "connected"}), 200


@health_bp.get("/health/live")
def live() -> tuple[object, int]:
    return jsonify({"status": "ok", "service": "realynk"}), 200


@health_bp.get("/health/ready")
def ready() -> tuple[object, int]:
    status = get_health_status()
    code = 200 if status["status"] in {"ok", "healthy"} else 503
    return jsonify(status), code


@health_bp.get("/metrics")
def metric_snapshot() -> tuple[object, int]:
    return jsonify(metrics.snapshot()), 200
