ROLE_LEVELS = {"member": 1, "admin": 2, "owner": 3}


def has_channel_role(membership, required_role: str) -> bool:
    return bool(
        membership
        and membership.role in ROLE_LEVELS
        and required_role in ROLE_LEVELS
        and ROLE_LEVELS[membership.role] >= ROLE_LEVELS[required_role]
    )


def can_view_channel(channel, membership) -> bool:
    return not channel.is_private or membership is not None


def can_manage_channel(membership) -> bool:
    return has_channel_role(membership, "admin")


def can_delete_channel(membership) -> bool:
    return has_channel_role(membership, "owner")


def can_manage_member(actor_membership, target_membership=None) -> bool:
    if not has_channel_role(actor_membership, "admin"):
        return False
    return not target_membership or target_membership.role != "owner"
