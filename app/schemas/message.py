from uuid import UUID

MAX_MESSAGE_LENGTH = 4000


def validate_create_message(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    errors: dict[str, str] = {}
    contexts = [key for key in ("channel_id", "conversation_id") if payload.get(key) is not None]
    if len(contexts) == 0:
        errors["context"] = "Exactly one channel_id or conversation_id is required"
    elif len(contexts) > 1:
        errors["context"] = "Only one message context may be provided"
    for key in contexts:
        try:
            UUID(str(payload[key]))
        except (ValueError, TypeError, AttributeError):
            errors[key] = f"{key} must be a valid UUID"
    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        errors["content"] = "Message content is required"
    elif len(content) > MAX_MESSAGE_LENGTH:
        errors["content"] = f"Message content must be at most {MAX_MESSAGE_LENGTH} characters"
    unknown = set(payload) - {"channel_id", "conversation_id", "content"}
    if unknown:
        errors["fields"] = "Only channel_id, conversation_id, and content are accepted"
    return errors


def validate_update_message(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    errors: dict[str, str] = {}
    if set(payload) != {"content"}:
        errors["fields"] = "Only content can be updated"
    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        errors["content"] = "Message content is required"
    elif len(content) > MAX_MESSAGE_LENGTH:
        errors["content"] = f"Message content must be at most {MAX_MESSAGE_LENGTH} characters"
    return errors
