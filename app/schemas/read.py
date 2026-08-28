from uuid import UUID

MAX_READ_BATCH = 100


def validate_message_ids(payload: object) -> tuple[list[UUID] | None, dict[str, str]]:
    if not isinstance(payload, dict) or set(payload) != {"message_ids"}:
        return None, {"fields": "Only message_ids can be provided"}
    values = payload.get("message_ids")
    if not isinstance(values, list) or not values:
        return None, {"message_ids": "At least one message ID is required"}
    if len(values) > MAX_READ_BATCH:
        return None, {"message_ids": f"At most {MAX_READ_BATCH} message IDs are allowed"}
    parsed: list[UUID] = []
    for value in values:
        try:
            parsed.append(UUID(str(value)))
        except (ValueError, TypeError, AttributeError):
            return None, {"message_ids": "Every message ID must be a valid UUID"}
    if len(set(parsed)) != len(parsed):
        return None, {"message_ids": "Message IDs must be unique"}
    return parsed, {}
