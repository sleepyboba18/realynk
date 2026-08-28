from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.services import attachment_service
from app.utils.responses import error_response, success_response


attachments_bp = Blueprint("attachments", __name__, url_prefix="/api/v1")


def _error(error):
    return error_response(error.code, error.message, error.status)


def _id(value: str):
    try:
        return UUID(value)
    except ValueError:
        return None


def _room(message):
    prefix = "channel" if message.channel_id else "conversation"
    value = message.channel_id or message.conversation_id
    return f"{prefix}:{value}"


@attachments_bp.post("/messages/<message_id>/attachments")
@auth_required
def upload(message_id: str):
    parsed = _id(message_id)
    if parsed is None:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    file = request.files.get("file")
    try:
        attachment, message = attachment_service.upload_attachment(g.current_user, parsed, file)
    except attachment_service.AttachmentError as error:
        return _error(error)
    from app.extensions.socketio import socketio
    socketio.emit("attachment_added", {"message_id": str(message.id), "attachment": attachment.to_dict()}, to=_room(message))
    return success_response(attachment.to_dict(), 201)


@attachments_bp.get("/attachments/<attachment_id>")
@auth_required
def access(attachment_id: str):
    parsed = _id(attachment_id)
    if parsed is None:
        return error_response("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)
    try:
        attachment, url = attachment_service.access_url(g.current_user, parsed)
    except attachment_service.AttachmentError as error:
        return _error(error)
    from flask import current_app
    return success_response({"attachment": attachment.to_dict(), "url": url, "expires_in": current_app.config["ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS"]})


@attachments_bp.delete("/attachments/<attachment_id>")
@auth_required
def delete(attachment_id: str):
    parsed = _id(attachment_id)
    if parsed is None:
        return error_response("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)
    try:
        attachment, message = attachment_service.delete_attachment(g.current_user, parsed)
    except attachment_service.AttachmentError as error:
        return _error(error)
    from app.extensions.socketio import socketio
    socketio.emit("attachment_deleted", {"message_id": str(message.id), "attachment_id": str(attachment.id)}, to=_room(message))
    return success_response({"message": "Attachment deleted"})


@attachments_bp.get("/messages/<message_id>/attachments")
@auth_required
def list_attachments(message_id: str):
    parsed = _id(message_id)
    if parsed is None:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    try:
        attachments = attachment_service.list_message_attachments(g.current_user, parsed)
    except attachment_service.AttachmentError as error:
        return _error(error)
    return success_response({"items": [attachment.to_dict() for attachment in attachments]})
