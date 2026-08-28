from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from app.validators.attachment_validator import sanitize_filename, validate_file


def upload(filename, content, mimetype):
    return FileStorage(stream=BytesIO(content), filename=filename, content_type=mimetype)


def test_filename_sanitization_removes_path_traversal_and_control_characters():
    assert sanitize_filename("../../report.pdf") == "report.pdf"
    assert "/" not in sanitize_filename("folder\\report.pdf")
    assert "_" in sanitize_filename("<script>.pdf")


def test_pdf_validation_calculates_size_and_checksum():
    item = validate_file(upload("report.pdf", b"%PDF-1.7 test", "application/pdf"), 1024)
    assert item.mime_type == "application/pdf"
    assert item.attachment_type == "document"
    assert item.file_size == len(b"%PDF-1.7 test")
    assert len(item.checksum) == 64


def test_dangerous_extension_and_empty_file_are_rejected():
    with pytest.raises(ValueError):
        validate_file(upload("run.exe", b"MZ", "application/x-msdownload"), 1024)
    with pytest.raises(ValueError):
        validate_file(upload("empty.txt", b"", "text/plain"), 1024)


def test_oversized_file_is_rejected():
    with pytest.raises(OverflowError):
        validate_file(upload("large.txt", b"x" * 11, "text/plain"), 10)


def test_mismatched_known_signature_is_rejected():
    with pytest.raises(ValueError):
        validate_file(upload("image.jpg", b"%PDF-1.7 test", "image/jpeg"), 1024)
