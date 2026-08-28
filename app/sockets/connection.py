import logging

from flask import request
from flask_socketio import emit
from flask_socketio import join_room

from app.auth.jwt import TokenError, decode_access_token
from app.extensions.socketio import socketio
from app.repositories.user_repository import get_by_id
from app.sockets.presence import broadcast_presence, cleanup_typing_socket
from app.services import presence_service
from app.permissions.moderation_permissions import is_restricted
from app.notifications.manager import room as notification_room


logger = logging.getLogger(__name__)


@socketio.on("connect")
def handle_connect() -> None:
    auth = request.args.get("auth")
    socket_auth = getattr(request, "auth", None)
    if isinstance(socket_auth, dict):
        auth = socket_auth.get("token")
    if isinstance(auth, str) and auth.strip():
        try:
            user = get_by_id(decode_access_token(auth.removeprefix("Bearer ").strip()))
        except TokenError:
            return False
        if user is None or not user.is_active or user.status != "active" or is_restricted(user):
            return False
        request.current_user = user
        join_room(notification_room(user.id))
        if presence_service.register_connection(user.id, request.sid):
            broadcast_presence(user.id)
        logger.info("Authenticated Socket.IO client connected: %s", request.sid)
    else:
        logger.info("Public Socket.IO client connected: %s", request.sid)
    emit("connected", {"status": "ok"})


def get_socket_current_user():
    return getattr(request, "current_user", None)


@socketio.on("disconnect")
def handle_disconnect() -> None:
    cleanup_typing_socket(request.sid)
    user_id, became_offline = presence_service.unregister_connection(request.sid)
    if user_id and became_offline:
        last_seen_at = presence_service.persist_last_seen(user_id)
        broadcast_presence(user_id, last_seen_at)
    logger.info("Socket.IO client disconnected: %s", request.sid)
