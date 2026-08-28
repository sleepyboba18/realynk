from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.schemas.user import validate_profile_update
from app.services import user_service
from app.utils.responses import error_response, success_response


users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@users_bp.get("/<user_id>")
def get_public_user(user_id: str):
    try:
        user = user_service.get_user(UUID(user_id))
    except (ValueError, user_service.UserNotFoundError):
        return error_response("NOT_FOUND", "User not found", 404)
    return success_response(user.to_dict())


@users_bp.patch("/me")
@auth_required
def update_me():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response(
            "VALIDATION_ERROR", "Invalid request", 400, {"body": "Request body must be a JSON object"}
        )
    validation_errors = validate_profile_update(data)
    if validation_errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, validation_errors)
    if not data:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, {"body": "At least one field is required"})
    user = user_service.update_profile(g.current_user, data)
    return success_response(user.to_dict(include_private=True))
