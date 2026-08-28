EMOJI_MAX_LENGTH = 32


def validate_reaction(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"body": "Request body must be a JSON object"}
    if set(payload) != {"emoji"}:
        return {"fields": "Only emoji can be provided"}
    emoji = payload.get("emoji")
    if not isinstance(emoji, str) or not emoji.strip():
        return {"emoji": "Emoji is required"}
    if len(emoji) > EMOJI_MAX_LENGTH:
        return {"emoji": f"Emoji must be at most {EMOJI_MAX_LENGTH} characters"}
    if any(ord(character) in {0, 10, 13} for character in emoji):
        return {"emoji": "Emoji contains invalid characters"}
    return {}
