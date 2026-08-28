from uuid import UUID


def validate_create_conversation(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    if set(payload) != {"user_id"}:
        return {"fields": "Only user_id can be provided"}
    try:
        UUID(str(payload["user_id"]))
    except (ValueError, TypeError, AttributeError):
        return {"user_id": "A valid user ID is required"}
    return {}
