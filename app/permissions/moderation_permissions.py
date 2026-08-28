from app.moderation.constants import ROLE_LEVELS


def is_restricted(user) -> bool:
    if not user:
        return True

    is_active = getattr(user, "is_active", True)
    status = getattr(user, "status", "active")
    if not is_active or status != "active":
        return True

    if getattr(user, "banned_at", None) is not None:
        return True

    suspended_at = getattr(user, "suspended_at", None)
    if suspended_at is not None:
        from datetime import datetime, timezone

        suspension_expires_at = getattr(user, "suspension_expires_at", None)
        if suspension_expires_at is None or suspension_expires_at > datetime.now(timezone.utc):
            return True
    return False


def has_moderation_role(user, required: str = "moderator") -> bool:
    return bool(user and not is_restricted(user) and ROLE_LEVELS.get(user.moderation_role, 0) >= ROLE_LEVELS[required])


def can_target(actor, target) -> bool:
    return bool(actor.id != target.id and ROLE_LEVELS.get(actor.moderation_role, 0) > ROLE_LEVELS.get(target.moderation_role, 0))


def can_warn_user(actor, target) -> bool:
    return has_moderation_role(actor) and can_target(actor, target)


def can_suspend_user(actor, target) -> bool:
    return can_warn_user(actor, target)


def can_ban_user(actor, target) -> bool:
    return can_warn_user(actor, target)


def can_remove_member(actor, target_membership) -> bool:
    return has_moderation_role(actor) and target_membership is not None


def can_lock_channel(actor) -> bool:
    return has_moderation_role(actor)


def can_delete_message(actor) -> bool:
    return has_moderation_role(actor)


def can_view_audit_logs(actor) -> bool:
    return has_moderation_role(actor)
