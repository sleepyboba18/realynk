from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.permissions.conversation_permissions import can_access_conversation
from app.repositories import conversation_repository
from app.services.user_service import UserNotFoundError, get_user


class ConversationError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _canonical_pair(first: UUID, second: UUID) -> tuple[UUID, UUID]:
    return tuple(sorted((first, second), key=lambda value: value.hex))


def get_for_user(conversation_id: UUID, user_id: UUID) -> tuple[Conversation, ConversationParticipant]:
    conversation = conversation_repository.get_by_id(conversation_id)
    if conversation is None:
        raise ConversationError("CONVERSATION_NOT_FOUND", "Conversation not found", 404)
    participant = conversation_repository.get_participant(conversation_id, user_id)
    if participant is None or participant.user_id != user_id or participant.left_at is not None:
        raise ConversationError("CONVERSATION_NOT_FOUND", "Conversation not found", 404)
    return conversation, participant


def create_or_reopen(requester_id: UUID, target_id: UUID) -> tuple[Conversation, bool]:
    if requester_id == target_id:
        raise ConversationError(
            "SELF_CONVERSATION_NOT_ALLOWED",
            "You cannot create a direct conversation with yourself",
            422,
        )
    try:
        target = get_user(target_id)
    except UserNotFoundError as exc:
        raise ConversationError("USER_NOT_FOUND", "User not found", 404) from exc
    if not target.is_active or target.status != "active":
        raise ConversationError("USER_INACTIVE", "User is inactive", 403)

    participant_a_id, participant_b_id = _canonical_pair(requester_id, target_id)
    existing = conversation_repository.get_direct_by_pair(participant_a_id, participant_b_id)
    if existing:
        for participant in existing.participants:
            participant.left_at = None
        db.session.commit()
        return existing, False

    conversation = Conversation(
        participant_a_id=participant_a_id,
        participant_b_id=participant_b_id,
    )
    db.session.add(conversation)
    db.session.flush()
    db.session.add_all(
        [
            ConversationParticipant(conversation_id=conversation.id, user_id=participant_a_id),
            ConversationParticipant(conversation_id=conversation.id, user_id=participant_b_id),
        ]
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = conversation_repository.get_direct_by_pair(participant_a_id, participant_b_id)
        if existing is None:
            raise ConversationError("CONVERSATION_CREATE_FAILED", "Conversation could not be created", 500)
        for participant in existing.participants:
            participant.left_at = None
        db.session.commit()
        return existing, False
    return conversation, True


def leave(conversation: Conversation, participant: ConversationParticipant) -> None:
    participant.left_at = datetime.now(timezone.utc)
    db.session.commit()
