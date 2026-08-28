def validate_profile_update(payload: dict[str, object]) -> dict[str, str]:
    errors: dict[str, str] = {}
    allowed = {"display_name", "avatar_url"}
    unknown = set(payload) - allowed
    if unknown:
        errors["fields"] = "Only display_name and avatar_url can be updated"
    if "display_name" in payload and payload["display_name"] is not None:
        if not isinstance(payload["display_name"], str) or len(payload["display_name"]) > 100:
            errors["display_name"] = "Display name must be at most 100 characters"
    if "avatar_url" in payload and payload["avatar_url"] is not None:
        if not isinstance(payload["avatar_url"], str) or len(payload["avatar_url"]) > 2048:
            errors["avatar_url"] = "Avatar URL must be at most 2048 characters"
    return errors
