from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.extensions.database import db
from app.permissions.reaction_permissions import can_remove_reaction, can_react_to_message, can_view_reactions
from app.repositories import reaction_repository
from app.services.message_service import MessageError, get_message_for_user, _context


class ReactionError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _access(user_id: UUID, message_id: UUID):
    try:
        message = get_message_for_user(user_id, message_id)
        context = _context(user_id, message.channel_id, message.conversation_id)
        return message, context
    except MessageError as error:
        raise ReactionError("REACTION_ACCESS_DENIED", "You cannot access this message", 403) from error


def add_reaction(user, message_id: UUID, emoji: str):
    message, access = _access(user.id, message_id)
    if message.deleted_at is not None:
        raise ReactionError("MESSAGE_DELETED", "Deleted messages cannot receive new reactions", 409)
    if not can_react_to_message(user, message, access):
        raise ReactionError("REACTION_ACCESS_DENIED", "You cannot react to this message", 403)
    if reaction_repository.get(message_id, user.id, emoji):
        raise ReactionError("REACTION_ALREADY_EXISTS", "Reaction already exists", 409)
    from app.models.message_reaction import MessageReaction
    reaction = MessageReaction(message_id=message_id, user_id=user.id, emoji=emoji)
    db.session.add(reaction)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ReactionError("REACTION_ALREADY_EXISTS", "Reaction already exists", 409) from exc
    try:
        from app.services.notification_service import notify_reaction
        notify_reaction(message, user, emoji, reaction.id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Unable to create reaction notification")
    return reaction, message


def remove_reaction(user, message_id: UUID, emoji: str):
    message, access = _access(user.id, message_id)
    if not can_view_reactions(user, message, access):
        raise ReactionError("REACTION_ACCESS_DENIED", "You cannot access this message", 403)
    reaction = reaction_repository.get(message_id, user.id, emoji)
    if reaction is None:
        raise ReactionError("REACTION_NOT_FOUND", "Reaction not found", 404)
    if not can_remove_reaction(user, reaction):
        raise ReactionError("REACTION_ACCESS_DENIED", "You can only remove your own reaction", 403)
    db.session.delete(reaction)
    db.session.commit()
    return reaction, message


def list_reactions(user, message_id: UUID):
    message, access = _access(user.id, message_id)
    if not can_view_reactions(user, message, access):
        raise ReactionError("REACTION_ACCESS_DENIED", "You cannot view reactions for this message", 403)
    return reaction_repository.aggregate(message_id, user.id), message
