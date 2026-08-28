from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.permissions.presence_permissions import can_view_presence
from app.repositories import presence_repository
from app.services import presence_service
from app.utils.responses import error_response, success_response


presence_bp = Blueprint("presence", __name__, url_prefix="/api/v1/presence")
MAX_BATCH_IDS = 100


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        return None


def _data(user_id: UUID) -> dict[str, object]:
    user = presence_repository.get_user(user_id)
    return presence_service.payload(user_id, user.last_seen_at if user else None)


@presence_bp.get("")
@auth_required
def batch_presence():
    raw_ids = request.args.get("user_ids", "")
    values = [value.strip() for value in raw_ids.split(",") if value.strip()]
    if not values or len(values) > MAX_BATCH_IDS:
        return error_response("INVALID_PRESENCE_TARGET", "Provide between 1 and 100 user IDs", 422)
    ids = [_parse_uuid(value) for value in values]
    if any(user_id is None for user_id in ids):
        return error_response("INVALID_PRESENCE_TARGET", "Every user ID must be a valid UUID", 422)
    users = {user.id: user for user in presence_repository.get_users(ids)}
    visible = [user_id for user_id in ids if user_id in users and can_view_presence(g.current_user, users[user_id])]
    return success_response({"items": [_data(user_id) for user_id in visible]})


@presence_bp.get("/<user_id>")
@auth_required
def get_presence(user_id: str):
    parsed = _parse_uuid(user_id)
    if parsed is None:
        return error_response("INVALID_PRESENCE_TARGET", "User ID must be a valid UUID", 422)
    target = presence_repository.get_user(parsed)
    if target is None:
        return error_response("PRESENCE_USER_NOT_FOUND", "User not found", 404)
    if not can_view_presence(g.current_user, target):
        return error_response("PRESENCE_ACCESS_DENIED", "You cannot view this user's presence", 403)
    return success_response(_data(parsed))
