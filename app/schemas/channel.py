from uuid import UUID


CHANNEL_NAME_MIN = 2
CHANNEL_NAME_MAX = 80
DESCRIPTION_MAX = 2000
VALID_ROLES = {"admin", "member"}


def validate_create_channel(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    errors: dict[str, str] = {}
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        errors["name"] = "Channel name is required"
    elif len(name.strip()) < CHANNEL_NAME_MIN or len(name.strip()) > CHANNEL_NAME_MAX:
        errors["name"] = f"Channel name must be {CHANNEL_NAME_MIN}-{CHANNEL_NAME_MAX} characters"
    elif any(ord(character) < 32 or ord(character) == 127 for character in name):
        errors["name"] = "Channel name cannot contain control characters"
    if "description" in payload and payload["description"] is not None:
        if not isinstance(payload["description"], str) or len(payload["description"]) > DESCRIPTION_MAX:
            errors["description"] = f"Description must be at most {DESCRIPTION_MAX} characters"
    if "is_private" in payload and not isinstance(payload["is_private"], bool):
        errors["is_private"] = "is_private must be a boolean"
    if "channel_type" in payload and payload["channel_type"] != "text":
        errors["channel_type"] = "Only text channels are supported"
    return errors


def validate_update_channel(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    errors: dict[str, str] = {}
    allowed = {"name", "description", "is_private"}
    if set(payload) - allowed:
        errors["fields"] = "Only name, description, and is_private can be updated"
    if "name" in payload:
        name = payload["name"]
        if not isinstance(name, str) or not name.strip() or not CHANNEL_NAME_MIN <= len(name.strip()) <= CHANNEL_NAME_MAX:
            errors["name"] = f"Channel name must be {CHANNEL_NAME_MIN}-{CHANNEL_NAME_MAX} characters"
        elif any(ord(character) < 32 or ord(character) == 127 for character in name):
            errors["name"] = "Channel name cannot contain control characters"
    if "description" in payload and payload["description"] is not None:
        if not isinstance(payload["description"], str) or len(payload["description"]) > DESCRIPTION_MAX:
            errors["description"] = f"Description must be at most {DESCRIPTION_MAX} characters"
    if "is_private" in payload and not isinstance(payload["is_private"], bool):
        errors["is_private"] = "is_private must be a boolean"
    return errors


def validate_user_id(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    value = payload.get("user_id")
    try:
        UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return {"user_id": "A valid user ID is required"}
    return {}


def validate_role(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict) or payload.get("role") not in VALID_ROLES:
        return {"role": "Role must be admin or member"}
    return {}
