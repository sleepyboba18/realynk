import re


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def json_object(payload: object) -> tuple[dict[str, object] | None, dict[str, str]]:
    if not isinstance(payload, dict):
        return None, {"body": "Request body must be a JSON object"}
    return payload, {}


def validate_registration(payload: dict[str, object]) -> dict[str, str]:
    errors: dict[str, str] = {}
    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    display_name = payload.get("display_name")

    if not isinstance(username, str) or not username:
        errors["username"] = "Username is required"
    elif not USERNAME_PATTERN.fullmatch(username):
        errors["username"] = "Username must be 3-30 characters using letters, numbers, or _"
    if not isinstance(email, str) or not email:
        errors["email"] = "Email is required"
    elif not EMAIL_PATTERN.fullmatch(email):
        errors["email"] = "Invalid email format"
    if not isinstance(password, str) or not password:
        errors["password"] = "Password is required"
    elif len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"
    if display_name is not None and (
        not isinstance(display_name, str) or len(display_name) > 100
    ):
        errors["display_name"] = "Display name must be at most 100 characters"
    return errors


def validate_login(payload: dict[str, object]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not isinstance(payload.get("identifier"), str) or not payload["identifier"]:
        errors["identifier"] = "Identifier is required"
    if not isinstance(payload.get("password"), str) or not payload["password"]:
        errors["password"] = "Password is required"
    return errors


def validate_password_change(payload: dict[str, object]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not isinstance(payload.get("current_password"), str) or not payload["current_password"]:
        errors["current_password"] = "Current password is required"
    new_password = payload.get("new_password")
    if not isinstance(new_password, str) or not new_password:
        errors["new_password"] = "New password is required"
    elif len(new_password) < 8:
        errors["new_password"] = "New password must be at least 8 characters"
    return errors
