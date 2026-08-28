from app.notifications.types import NotificationType


def validate_preference(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    if set(payload) != {"notification_type", "enabled"}:
        return {"fields": "notification_type and enabled are required"}
    try:
        NotificationType(payload["notification_type"])
    except (ValueError, TypeError):
        return {"notification_type": "Unknown notification type"}
    if not isinstance(payload["enabled"], bool):
        return {"enabled": "enabled must be a boolean"}
    return {}


def validate_bulk_preferences(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    valid = {item.value for item in NotificationType}
    unknown = set(payload) - valid
    if unknown or any(not isinstance(value, bool) for value in payload.values()):
        return {"preferences": "Use known notification types with boolean values"}
    return {}
