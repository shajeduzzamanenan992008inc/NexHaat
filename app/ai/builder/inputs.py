"""Bounded, transient text extraction for multimodal Admin Builder inputs."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
import zipfile
from xml.etree import ElementTree

from .project_files import ProjectFilesError, inspect_uploaded_project
from ...services.product_images import MAX_PRODUCT_IMAGE_BYTES, ProductImageError, normalize_product_image


MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_TEXT = 24_000
_IMAGE_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
}
_AUDIO_TYPES = {
    ".ogg": "audio/ogg", ".wav": "audio/wav", ".webm": "audio/webm",
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
}
_TEXT_EXTENSIONS = {
    ".cjs", ".cfg", ".css", ".html", ".ini", ".js", ".jsx", ".json", ".md",
    ".mjs", ".py", ".pyi", ".sql", ".toml", ".ts", ".tsx", ".txt", ".xml",
    ".yaml", ".yml",
}


class BuilderInputError(ValueError):
    """A Builder attachment could not be accepted safely."""


def _audio_signature_matches(content_type: str, data: bytes) -> bool:
    if content_type == "audio/wav":
        return data.startswith(b"RIFF") and data[8:12] == b"WAVE"
    if content_type == "audio/webm":
        return data.startswith(bytes.fromhex("1A45DFA3"))
    if content_type == "audio/ogg":
        return data.startswith(b"OggS")
    if content_type == "audio/mpeg":
        return data.startswith(b"ID3") or (
            len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
        )
    if content_type == "audio/mp4":
        return len(data) > 8 and data[4:8] == b"ftyp"
    return False


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise BuilderInputError("PDF text extraction is not installed on this host.") from error
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) > 40:
            raise BuilderInputError("PDFs are limited to 40 pages.")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except BuilderInputError:
        raise
    except Exception as error:
        raise BuilderInputError("The PDF could not be read safely.") from error
    if not text.strip():
        raise BuilderInputError("The PDF has no text-extractable content.")
    return text[:MAX_DOCUMENT_TEXT]


def _extract_docx(data: bytes) -> str:
    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except (OSError, zipfile.BadZipFile, ValueError) as error:
        raise BuilderInputError("Upload a valid DOCX document.") from error
    try:
        entries = archive.infolist()
        if len(entries) > 200 or sum(item.file_size for item in entries) > 16 * 1024 * 1024:
            raise BuilderInputError("The DOCX document exceeds the inspection limit.")
        document = next((item for item in entries if item.filename == "word/document.xml"), None)
        if document is None or document.file_size > 4 * 1024 * 1024:
            raise BuilderInputError("The DOCX document has no readable text body.")
        raw = archive.read(document)
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise BuilderInputError("The DOCX document could not be read safely.") from error
    finally:
        archive.close()
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as error:
        raise BuilderInputError("The DOCX document contains invalid XML.") from error
    text = " ".join(
        node.text or "" for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "t"
    )
    if not text.strip():
        raise BuilderInputError("The DOCX document has no readable text.")
    return text[:MAX_DOCUMENT_TEXT]


def inspect_builder_attachment(data: bytes, filename: str, service):
    """Return source text, source category and optional files; media bytes stay transient."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    suffix = PurePosixPath(name).suffix.lower()
    if suffix == ".zip":
        files = inspect_uploaded_project(data, name)
        text = "\n".join(f"FILE: {item['path']}\n{item['content']}" for item in files)
        return text[:MAX_DOCUMENT_TEXT], "code", files
    if suffix in _IMAGE_TYPES:
        if len(data) > MAX_PRODUCT_IMAGE_BYTES:
            raise BuilderInputError("Images are limited to 5 MB.")
        try:
            normalized = normalize_product_image(data)
        except ProductImageError as error:
            raise BuilderInputError(str(error)) from error
        try:
            description = service.describe_image(normalized, content_type="image/jpeg")
        except Exception as error:
            raise BuilderInputError("Private image analysis is not available.") from error
        if not isinstance(description, str) or not description.strip():
            raise BuilderInputError("The private vision service returned no description.")
        return f"Untrusted image description:\n{description[:5000]}", "media", None
    if suffix in _AUDIO_TYPES:
        if len(data) > MAX_AUDIO_BYTES:
            raise BuilderInputError("Audio files are limited to 8 MB.")
        content_type = _AUDIO_TYPES[suffix]
        if not data or not _audio_signature_matches(content_type, data):
            raise BuilderInputError("The audio bytes do not match the selected file type.")
        try:
            transcript = service.transcribe(
                data, filename="admin-audio", content_type=content_type
            )
        except Exception as error:
            raise BuilderInputError("Private voice transcription is not available.") from error
        if not isinstance(transcript, str) or not transcript.strip():
            raise BuilderInputError("The private transcription service returned no text.")
        return f"Untrusted voice transcript:\n{transcript[:5000]}", "media", None
    if suffix == ".pdf":
        if len(data) > MAX_DOCUMENT_BYTES:
            raise BuilderInputError("PDF files are limited to 8 MB.")
        return _extract_pdf(data), "document", None
    if suffix == ".docx":
        if len(data) > MAX_DOCUMENT_BYTES:
            raise BuilderInputError("DOCX files are limited to 8 MB.")
        return _extract_docx(data), "document", None
    if suffix in _TEXT_EXTENSIONS or name.lower() in {"dockerfile", "makefile", "procfile"}:
        try:
            files = inspect_uploaded_project(data, name)
        except ProjectFilesError as error:
            raise BuilderInputError(str(error)) from error
        text = "\n".join(f"FILE: {item['path']}\n{item['content']}" for item in files)
        return text[:MAX_DOCUMENT_TEXT], "code", files
    raise BuilderInputError("Upload a ZIP, source text, PDF, DOCX, image, or audio file.")
