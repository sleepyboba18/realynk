import hashlib
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import PurePath

from werkzeug.datastructures import FileStorage


ALLOWED_MIME_TYPES = {
    "image/jpeg": "image", "image/png": "image", "image/gif": "image", "image/webp": "image",
    "application/pdf": "document", "text/plain": "document", "application/json": "document", "application/zip": "document",
    "audio/mpeg": "audio", "audio/wav": "audio", "audio/ogg": "audio", "audio/webm": "audio",
    "video/mp4": "video", "video/webm": "video", "video/quicktime": "video",
}
ALLOWED_EXTENSIONS = {
    "image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/gif": {".gif"}, "image/webp": {".webp"},
    "application/pdf": {".pdf"}, "text/plain": {".txt", ".text"}, "application/json": {".json"}, "application/zip": {".zip"},
    "audio/mpeg": {".mp3"}, "audio/wav": {".wav"}, "audio/ogg": {".ogg"}, "audio/webm": {".webm"},
    "video/mp4": {".mp4"}, "video/webm": {".webm"}, "video/quicktime": {".mov"},
}
DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".scr", ".ps1", ".sh", ".php", ".py", ".js", ".vbs", ".jar", ".msi", ".svg"}
MAGIC = {
    b"\xFF\xD8\xFF": "image/jpeg", b"\x89PNG\r\n\x1a\n": "image/png", b"GIF87a": "image/gif", b"GIF89a": "image/gif",
    b"%PDF-": "application/pdf", b"PK\x03\x04": "application/zip",
}


@dataclass
class ValidatedFile:
    filename: str
    extension: str
    mime_type: str
    attachment_type: str
    file_size: int
    checksum: str
    width: int | None = None
    height: int | None = None


def sanitize_filename(filename: str) -> str:
    filename = filename.replace("\\", "/").split("/")[-1].replace("\x00", "")
    filename = re.sub(r"[^\w.()\- ]", "_", filename, flags=re.UNICODE).strip(" .")
    if not filename:
        raise ValueError("Filename is required")
    return filename[:255]


def validate_file(file: FileStorage, max_bytes: int) -> ValidatedFile:
    if not file or not file.filename:
        raise ValueError("File is required")
    filename = sanitize_filename(file.filename)
    extension = os.path.splitext(filename)[1].lower()
    if extension in DANGEROUS_EXTENSIONS:
        raise ValueError("File extension is not allowed")
    stream = file.stream
    start = stream.tell()
    stream.seek(0, 2)
    file_size = stream.tell()
    stream.seek(0)
    if file_size <= 0:
        raise ValueError("File cannot be empty")
    if file_size > max_bytes:
        raise OverflowError("File is too large")
    sample = stream.read(16)
    stream.seek(0)
    detected = next((mime for signature, mime in MAGIC.items() if sample.startswith(signature)), None)
    declared = file.mimetype or mimetypes.guess_type(filename)[0]
    mime_type = detected or declared
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError("File type is not allowed")
    if detected and declared and declared != detected and not (detected == "application/zip" and declared == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        raise ValueError("File type does not match its content")
    if extension not in ALLOWED_EXTENSIONS.get(mime_type, set()):
        raise ValueError("File extension does not match its type")
    digest = hashlib.sha256()
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    stream.seek(0)
    return ValidatedFile(filename, extension, mime_type, ALLOWED_MIME_TYPES[mime_type], file_size, digest.hexdigest())
