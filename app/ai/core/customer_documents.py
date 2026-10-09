"""Bounded, owner-scoped text extraction and lexical retrieval for Customer AI."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
import re

from sqlalchemy import select

from ...extensions import db
from ...models import AICustomerDocument


MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_DOCUMENT_TEXT = 24_000
MAX_DOCUMENTS_PER_CUSTOMER = 10
MAX_DOCUMENT_CONTEXT_CHARS = 4_000
_ALLOWED_TYPES = {
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}
_WORD = re.compile(r"[\w-]{2,}", re.UNICODE)


class CustomerDocumentError(ValueError):
    """A Customer AI document did not meet the safe-ingestion requirements."""


def _extract_text(data: bytes, suffix: str) -> str:
    if suffix in {".txt", ".md"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise CustomerDocumentError("Text documents must use UTF-8 encoding.") from error
    else:
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data), strict=True)
            if len(reader.pages) > 40:
                raise CustomerDocumentError("PDF documents are limited to 40 pages.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except CustomerDocumentError:
            raise
        except Exception as error:
            raise CustomerDocumentError("The PDF could not be read safely.") from error
    text = "\n".join(line.strip() for line in text.splitlines()).strip()
    if not text:
        raise CustomerDocumentError("The document contains no searchable text.")
    return text[:MAX_DOCUMENT_TEXT]


def ingest_customer_document(user, filename: str, data: bytes) -> AICustomerDocument:
    """Validate and store extracted text only; source bytes remain transient."""
    clean_name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    clean_name = clean_name.replace("\x00", "").strip()[:180]
    suffix = PurePosixPath(clean_name).suffix.lower()
    content_type = _ALLOWED_TYPES.get(suffix)
    if not clean_name or not content_type:
        raise CustomerDocumentError("Upload a PDF, TXT, or Markdown document.")
    if not isinstance(data, bytes) or not data or len(data) > MAX_DOCUMENT_BYTES:
        raise CustomerDocumentError("Documents must be between 1 byte and 2 MB.")
    if suffix == ".pdf" and not data.startswith(b"%PDF-"):
        raise CustomerDocumentError("Upload a valid PDF document.")
    content = _extract_text(data, suffix)
    digest = sha256((content_type + "\0" + content).encode("utf-8")).hexdigest()
    duplicate = db.session.scalar(select(AICustomerDocument.id).where(
        AICustomerDocument.user_id == user.id,
        AICustomerDocument.content_sha256 == digest,
    ))
    if duplicate is not None:
        raise CustomerDocumentError("This document is already in your library.")
    count = db.session.scalar(select(db.func.count(AICustomerDocument.id)).where(
        AICustomerDocument.user_id == user.id,
    )) or 0
    if count >= MAX_DOCUMENTS_PER_CUSTOMER:
        raise CustomerDocumentError("Delete a document before adding another.")
    document = AICustomerDocument(
        user_id=user.id,
        filename=clean_name,
        content_type=content_type,
        content=content,
        content_sha256=digest,
    )
    db.session.add(document)
    db.session.commit()
    return document


def search_customer_documents(user, query: str, *, document_ids=None, limit=3):
    """Rank lexical matches only within the authenticated customer's documents."""
    terms = list(dict.fromkeys(
        token.casefold() for token in _WORD.findall(query) if len(token) >= 2
    ))[:12]
    if not terms:
        return []
    statement = select(AICustomerDocument).where(AICustomerDocument.user_id == user.id)
    if document_ids is not None:
        statement = statement.where(AICustomerDocument.id.in_(document_ids))
    rows = db.session.scalars(
        statement.order_by(AICustomerDocument.created_at.desc()).limit(MAX_DOCUMENTS_PER_CUSTOMER)
    ).all()
    ranked = []
    for document in rows:
        folded = document.content.casefold()
        matched = [term for term in terms if term in folded]
        if not matched:
            continue
        first_position = min(folded.find(term) for term in matched)
        start = max(0, first_position - 500)
        excerpt = document.content[start:start + 1500].strip()
        ranked.append((
            len(matched), document.created_at, {
                "document_id": document.id,
                "filename": document.filename,
                "excerpt": excerpt,
                "matched_terms": len(matched),
            },
        ))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    results = []
    remaining = MAX_DOCUMENT_CONTEXT_CHARS
    for _, _, result in ranked[:max(1, min(limit, 5))]:
        excerpt = result["excerpt"][:remaining]
        if not excerpt:
            break
        result["excerpt"] = excerpt
        remaining -= len(excerpt)
        results.append(result)
    return results
