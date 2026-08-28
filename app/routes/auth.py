from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.schemas.auth import json_object, validate_login, validate_password_change, validate_registration
from app.services import auth_service, user_service
from app.services.user_service import DuplicateUserError
from app.utils.responses import error_response, success_response


auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _request_data() -> tuple[dict[str, object] | None, tuple[object, int] | None]:
    data, errors = json_object(request.get_json(silent=True))
    if errors:
        return None, error_response("VALIDATION_ERROR", "Invalid request", 400, errors)
    return data, None


@auth_bp.post("/register")
def register():
    data, error = _request_data()
    if error:
        return error
    validation_errors = validate_registration(data)
    if validation_errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, validation_errors)
    try:
        user = user_service.create_user(
            data["username"], data["email"], data["password"], data.get("display_name")
        )
    except DuplicateUserError:
        return error_response("USER_EXISTS", "Username or email is already registered", 409)
    return success_response(
        {"user": user.to_dict(include_private=True), "access_token": auth_service.issue_access_token(user)},
        201,
    )


@auth_bp.post("/login")
def login():
    data, error = _request_data()
    if error:
        return error
    validation_errors = validate_login(data)
    if validation_errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, validation_errors)
    try:
        user = auth_service.authenticate(data["identifier"], data["password"])
    except auth_service.InvalidCredentialsError:
        return error_response("INVALID_CREDENTIALS", "Invalid credentials", 401)
    return success_response(
        {"user": user.to_dict(include_private=True), "access_token": auth_service.issue_access_token(user)}
    )


@auth_bp.post("/logout")
@auth_required
def logout():
    return success_response({"message": "Logged out"})


@auth_bp.get("/me")
@auth_required
def me():
    return success_response(g.current_user.to_dict(include_private=True))


@auth_bp.post("/change-password")
@auth_required
def change_password():
    data, error = _request_data()
    if error:
        return error
    validation_errors = validate_password_change(data)
    if validation_errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, validation_errors)
    try:
        auth_service.change_password(
            g.current_user, data["current_password"], data["new_password"]
        )
    except auth_service.InvalidCredentialsError:
        return error_response("INVALID_CREDENTIALS", "Current password is incorrect", 401)
    return success_response({"message": "Password changed successfully"})
