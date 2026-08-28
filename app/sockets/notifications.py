from uuid import UUID

from flask import request

from app.extensions.socketio import socketio
from app.services import notification_service


def _failure(code: str, message: str):
    return {"success": False, "error": {"code": code, "message": message}}


def _user():
    return getattr(request, "current_user", None)


def _id(data):
    try:
        return UUID(str(data.get("notification_id"))) if isinstance(data, dict) else None
    except (ValueError, TypeError, AttributeError):
        return None


@socketio.on("mark_notification_read")
def mark_notification_read(data):
    user = _user()
    notification_id = _id(data)
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    if notification_id is None:
        return _failure("NOTIFICATION_NOT_FOUND", "Notification not found")
    try:
        notification, _ = notification_service.mark_as_read(user, notification_id)
    except notification_service.NotificationError as error:
        return _failure(error.code, error.message)
    return {"success": True, "data": {"notification_id": str(notification.id), "read_at": notification.read_at.isoformat()}}


@socketio.on("mark_notifications_read")
def mark_notifications_read():
    user = _user()
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    changed, read_at = notification_service.mark_all_as_read(user)
    return {"success": True, "data": {"read_at": read_at.isoformat(), "changed": changed}}


@socketio.on("delete_notification")
def delete_notification(data):
    user = _user()
    notification_id = _id(data)
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    if notification_id is None:
        return _failure("NOTIFICATION_NOT_FOUND", "Notification not found")
    try:
        notification_service.delete_notification(user, notification_id)
    except notification_service.NotificationError as error:
        return _failure(error.code, error.message)
    return {"success": True, "data": {"notification_id": str(notification_id)}}
