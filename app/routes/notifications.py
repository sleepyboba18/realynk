from math import ceil
from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.schemas.notification import validate_bulk_preferences, validate_preference
from app.services import notification_preference_service, notification_service
from app.utils.responses import error_response, success_response


notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


def _uuid(value: str):
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        return None


def _error(error):
    return error_response(error.code, error.message, error.status)


def _pagination():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return None, error_response("VALIDATION_ERROR", "Invalid pagination", 422)
    if page < 1 or limit < 1 or limit > 100:
        return None, error_response("VALIDATION_ERROR", "Invalid pagination", 422)
    return (page, limit), None


def _notification_id(value: str):
    parsed = _uuid(value)
    if parsed is None:
        return error_response("NOTIFICATION_NOT_FOUND", "Notification not found", 404)
    return parsed


@notifications_bp.get("")
@auth_required
def list_notifications():
    pagination, error = _pagination()
    if error:
        return error
    page, limit = pagination
    unread_only = request.args.get("unread", "false").lower() in {"1", "true", "yes"}
    items, total = notification_service.list_notifications(g.current_user, page, limit, unread_only)
    return success_response({
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": ceil(total / limit), "has_more": page * limit < total},
    })


@notifications_bp.get("/<notification_id>")
@auth_required
def get_notification(notification_id: str):
    parsed = _notification_id(notification_id)
    if not isinstance(parsed, UUID):
        return parsed
    try:
        notification = notification_service.get_notification(g.current_user, parsed)
    except notification_service.NotificationError as error:
        return _error(error)
    return success_response(notification.to_dict())


@notifications_bp.post("/<notification_id>/read")
@auth_required
def mark_read(notification_id: str):
    parsed = _notification_id(notification_id)
    if not isinstance(parsed, UUID):
        return parsed
    try:
        notification, _ = notification_service.mark_as_read(g.current_user, parsed)
    except notification_service.NotificationError as error:
        return _error(error)
    return success_response({"notification_id": str(notification.id), "read_at": notification.read_at.isoformat() if notification.read_at else None})


@notifications_bp.post("/read-all")
@auth_required
def mark_all_read():
    changed, read_at = notification_service.mark_all_as_read(g.current_user)
    return success_response({"read_at": read_at.isoformat(), "changed": changed})


@notifications_bp.delete("/<notification_id>")
@auth_required
def delete_notification(notification_id: str):
    parsed = _notification_id(notification_id)
    if not isinstance(parsed, UUID):
        return parsed
    try:
        notification = notification_service.delete_notification(g.current_user, parsed)
    except notification_service.NotificationError as error:
        return _error(error)
    return success_response({"notification_id": str(notification.id)})


@notifications_bp.get("/unread-count")
@auth_required
def unread_count():
    return success_response({"count": notification_service.get_unread_count(g.current_user.id)})


@notifications_bp.get("/preferences")
@auth_required
def get_preferences():
    return success_response(notification_preference_service.get_preferences(g.current_user))


@notifications_bp.patch("/preferences")
@auth_required
def update_preference():
    data = request.get_json(silent=True)
    errors = validate_preference(data)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid preference", 422, errors)
    try:
        preference = notification_preference_service.set_preference(
            g.current_user, data["notification_type"], data["enabled"]
        )
    except notification_preference_service.NotificationPreferenceError:
        return error_response("VALIDATION_ERROR", "Invalid preference", 422)
    return success_response({preference.notification_type: preference.enabled})


@notifications_bp.put("/preferences")
@auth_required
def update_preferences():
    data = request.get_json(silent=True)
    errors = validate_bulk_preferences(data)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid preferences", 422, errors)
    try:
        notification_preference_service.set_preferences(g.current_user, data)
    except notification_preference_service.NotificationPreferenceError:
        return error_response("VALIDATION_ERROR", "Invalid preferences", 422)
    return success_response(notification_preference_service.get_preferences(g.current_user))
