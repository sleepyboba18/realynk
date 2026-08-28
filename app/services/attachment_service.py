import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.models.attachment import Attachment
from app.repositories import attachment_repository
from app.services.message_service import MessageError, get_message_for_user
from app.storage import supabase_storage
from app.validators.attachment_validator import ValidatedFile, validate_file

logger = logging.getLogger(__name__)


class AttachmentError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def upload_attachment(user, message_id: UUID, file) -> tuple[Attachment, object]:
    try:
        message = get_message_for_user(user.id, message_id)
    except MessageError as exc:
        raise AttachmentError("ATTACHMENT_ACCESS_DENIED", "You cannot attach files to this message", 403) from exc
    if message.deleted_at is not None:
        raise AttachmentError("ATTACHMENT_ACCESS_DENIED", "Deleted messages cannot receive attachments", 409)

    max_bytes = _config("MAX_ATTACHMENT_SIZE_MB") * 1024 * 1024
    try:
        validated = validate_file(file, max_bytes)
    except OverflowError as exc:
        raise AttachmentError("ATTACHMENT_TOO_LARGE", "Attachment exceeds the size limit", 413) from exc
    except ValueError as exc:
        raise AttachmentError("INVALID_ATTACHMENT", str(exc), 422) from exc
    if attachment_repository.count_for_message(message_id) >= _config("MAX_ATTACHMENTS_PER_MESSAGE"):
        raise AttachmentError("ATTACHMENT_LIMIT_EXCEEDED", "Message attachment limit exceeded", 409)
    current_total = attachment_repository.total_size_for_message(message_id)
    if current_total + validated.file_size > _config("MAX_TOTAL_ATTACHMENT_SIZE_MB") * 1024 * 1024:
        raise AttachmentError("ATTACHMENT_LIMIT_EXCEEDED", "Total attachment size limit exceeded", 413)

    attachment = Attachment(
        id=uuid.uuid4(),
        message_id=message_id,
        uploader_id=user.id,
        original_filename=validated.filename,
        storage_path=f"attachments/{message_id}/{uuid.uuid4()}{validated.extension}",
        mime_type=validated.mime_type,
        file_size=validated.file_size,
        extension=validated.extension,
        attachment_type=validated.attachment_type,
        checksum=validated.checksum,
        width=validated.width,
        height=validated.height,
    )
    try:
        supabase_storage.upload_file(attachment.storage_path, file.stream, attachment.mime_type)
    except supabase_storage.StorageError as exc:
        raise AttachmentError("ATTACHMENT_UPLOAD_FAILED", "Unable to upload attachment", 502) from exc

    db.session.add(attachment)
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        try:
            supabase_storage.delete_file(attachment.storage_path)
        except supabase_storage.StorageError:
            logger.exception("Attachment storage cleanup failed for %s", attachment.id)
        raise AttachmentError("ATTACHMENT_UPLOAD_FAILED", "Unable to save attachment", 500) from exc
    logger.info("Attachment uploaded: %s (%s bytes, %s)", attachment.id, attachment.file_size, attachment.mime_type)
    return attachment, message


def get_attachment(user, attachment_id: UUID):
    attachment = attachment_repository.get_by_id(attachment_id)
    if attachment is None or attachment.deleted_at is not None:
        raise AttachmentError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)
    try:
        message = get_message_for_user(user.id, attachment.message_id)
    except MessageError as exc:
        raise AttachmentError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404) from exc
    return attachment, message


def access_url(user, attachment_id: UUID):
    attachment, message = get_attachment(user, attachment_id)
    try:
        url = supabase_storage.create_signed_url(
            attachment.storage_path,
            _config("ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS"),
        )
    except supabase_storage.StorageError as exc:
        raise AttachmentError("ATTACHMENT_ACCESS_FAILED", "Unable to access attachment", 502) from exc
    return attachment, url


def delete_attachment(user, attachment_id: UUID):
    attachment, message = get_attachment(user, attachment_id)
    if attachment.uploader_id != user.id and message.sender_id != user.id:
        raise AttachmentError("ATTACHMENT_DELETE_FORBIDDEN", "You cannot delete this attachment", 403)
    attachment.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    try:
        supabase_storage.delete_file(attachment.storage_path)
    except supabase_storage.StorageError as exc:
        logger.exception("Attachment storage deletion failed for %s", attachment.id)
        raise AttachmentError("ATTACHMENT_DELETE_FAILED", "Attachment was hidden but storage cleanup failed", 502) from exc
    return attachment, message


def list_message_attachments(user, message_id: UUID):
    try:
        get_message_for_user(user.id, message_id)
    except MessageError as exc:
        raise AttachmentError("ATTACHMENT_ACCESS_DENIED", "You cannot access this message", 403) from exc
    return attachment_repository.get_for_message(message_id)


def cleanup_deleted_attachments(before_datetime: datetime) -> int:
    """Reserved for an explicit maintenance job; never runs during startup."""
    return 0


def _config(name: str) -> int:
    from flask import current_app
    return int(current_app.config[name])
