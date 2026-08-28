MAX_REASON_LENGTH = 1000
MAX_DURATION_SECONDS = 365 * 24 * 60 * 60


def validate_reason(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    reason = payload.get("reason")
    if reason is not None and (not isinstance(reason, str) or len(reason.strip()) > MAX_REASON_LENGTH):
        return {"reason": f"Reason must be at most {MAX_REASON_LENGTH} characters"}
    return {}


def validate_duration(payload: object, required: bool = False) -> dict[str, str]:
    errors = validate_reason(payload)
    if not isinstance(payload, dict):
        return errors
    value = payload.get("duration_seconds")
    if required and value is None:
        errors["duration_seconds"] = "Duration is required"
    elif value is not None and (not isinstance(value, int) or value <= 0 or value > MAX_DURATION_SECONDS):
        errors["duration_seconds"] = "Duration must be between 1 and 31536000 seconds"
    return errors
