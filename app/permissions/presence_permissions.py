from app.repositories.presence_repository import can_view_presence as _can_view_presence


def can_view_presence(viewer, target_user) -> bool:
    return bool(viewer and target_user and _can_view_presence(viewer.id, target_user.id))
