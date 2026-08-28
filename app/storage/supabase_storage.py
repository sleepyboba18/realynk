from typing import BinaryIO

from flask import current_app


class StorageError(RuntimeError):
    """Base error for controlled storage failures."""


class StorageUploadError(StorageError):
    pass


class StorageDeleteError(StorageError):
    pass


class StorageAccessError(StorageError):
    pass


def _client():
    try:
        from supabase import create_client
        url = current_app.config["SUPABASE_URL"]
        key = current_app.config["SUPABASE_SERVICE_ROLE_KEY"]
        if not url or not key:
            raise StorageError("Supabase Storage is not configured")
        return create_client(url, key)
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError("Storage service is unavailable") from exc


def upload_file(path: str, file_obj: BinaryIO, mime_type: str) -> None:
    try:
        _client().storage.from_(current_app.config["SUPABASE_STORAGE_BUCKET"]).upload(
            path,
            file_obj,
            {"content-type": mime_type, "upsert": "false"},
        )
    except Exception as exc:
        raise StorageUploadError("Unable to upload attachment") from exc


def delete_file(path: str) -> None:
    try:
        _client().storage.from_(current_app.config["SUPABASE_STORAGE_BUCKET"]).remove([path])
    except Exception as exc:
        raise StorageDeleteError("Unable to delete attachment") from exc


def create_signed_url(path: str, expires_in: int) -> str:
    try:
        result = _client().storage.from_(current_app.config["SUPABASE_STORAGE_BUCKET"]).create_signed_url(path, expires_in)
        if isinstance(result, dict):
            return result.get("signedURL") or result.get("signedUrl") or result.get("signed_url")
        return result
    except Exception as exc:
        raise StorageAccessError("Unable to create attachment access URL") from exc
