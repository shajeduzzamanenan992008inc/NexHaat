"""Role-scoped local embeddings and retrieval over explicitly curated Markdown."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from urllib.parse import urlsplit

import requests
from flask import current_app
from sqlalchemy import select

from ...extensions import db
from ...models import AIKnowledgeChunk


def _embedding_settings():
    config = current_app.config
    return (str(config.get("AI_EMBEDDING_BASE_URL") or config.get("AI_LOCAL_BASE_URL") or "").rstrip("/"),
            str(config.get("AI_EMBEDDING_MODEL") or "").strip(),
            str(config.get("AI_EMBEDDING_API_KEY") or config.get("AI_LOCAL_API_KEY") or "").strip())


def embed_text(text):
    root, model, api_key = _embedding_settings()
    parsed = urlsplit(root)
    if not root or not model or not parsed.hostname or parsed.username or parsed.password:
        return None
    if current_app.config.get("ENVIRONMENT") == "production" and parsed.scheme != "https":
        return None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = requests.post(f"{root}/embeddings", json={"model": model, "input": text[:4000]},
                                 headers=headers, timeout=min(20, int(current_app.config.get("AI_TIMEOUT", 15))))
        response.raise_for_status()
        value = response.json()["data"][0]["embedding"]
        if not isinstance(value, list) or len(value) != 1024:
            return None
        vector = [float(item) for item in value]
        return vector if all(math.isfinite(item) for item in vector) else None
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return None


def retrieve_knowledge(query, *, scope, limit=4):
    """Retrieve public plus caller-role chunks; never cross role boundaries."""
    vector = embed_text(query)
    if vector is None:
        return []
    role = {"customer_ai": "customer", "seller_ai": "seller", "admin_ai": "admin",
            "rider_ai": "rider", "security_ai": "security"}.get(scope)
    visible = ["public"] + ([role] if role else [])
    statement = select(AIKnowledgeChunk).where(AIKnowledgeChunk.scope.in_(visible))
    if db.engine.dialect.name == "postgresql":
        statement = (statement.where(AIKnowledgeChunk.embedding.is_not(None))
                     .order_by(AIKnowledgeChunk.embedding.cosine_distance(vector)).limit(limit))
        rows = db.session.scalars(statement).all()
        return [row.content[:3000] for row in rows]
    rows = db.session.scalars(statement.where(AIKnowledgeChunk.embedding.is_not(None))).all()
    ranked = []
    for row in rows:
        other = row.embedding
        if not isinstance(other, list) or len(other) != len(vector):
            continue
        numerator = sum(a * b for a, b in zip(vector, other))
        denom = math.sqrt(sum(a * a for a in vector)) * math.sqrt(sum(b * b for b in other))
        if denom:
            ranked.append((numerator / denom, row.content[:3000]))
    return [content for _, content in sorted(ranked, reverse=True)[:limit]]


def chunk_markdown(text, *, max_chars=1800, overlap=160):
    normalized = "\n".join(line.rstrip() for line in str(text).splitlines()).strip()
    chunks = []
    while normalized:
        if len(normalized) <= max_chars:
            chunks.append(normalized)
            break
        split_at = normalized.rfind("\n", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = normalized.rfind(" ", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = max_chars
        chunks.append(normalized[:split_at].strip())
        normalized = normalized[max(0, split_at - overlap):].lstrip()
    return [chunk for chunk in chunks if chunk]


def _validated_embedding(value):
    if not isinstance(value, list) or len(value) != 1024:
        return None
    try:
        vector = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in vector):
        return None
    return vector


def index_curated_knowledge(base_dir, *, scope="public"):
    """Index only operator-curated docs/ai-knowledge Markdown, never arbitrary paths."""
    if scope not in {"public", "customer", "seller", "admin", "rider", "security"}:
        raise ValueError("Unknown AI knowledge scope.")
    directory = Path(base_dir).resolve() / "docs" / "ai-knowledge"
    if not directory.is_dir():
        return 0
    indexed = 0
    try:
        for path in sorted(directory.glob("*.md")):
            resolved = path.resolve()
            if directory not in resolved.parents:
                continue
            content = path.read_text(encoding="utf-8")
            current_hashes = set()
            for chunk in chunk_markdown(content):
                digest = hashlib.sha256(
                    f"{scope}\0{path.name}\0{chunk}".encode("utf-8")
                ).hexdigest()
                current_hashes.add(digest)
                row = db.session.scalar(
                    select(AIKnowledgeChunk).where(AIKnowledgeChunk.content_hash == digest)
                )
                vector = _validated_embedding(embed_text(chunk))
                if vector is None:
                    raise RuntimeError("The local embedding endpoint returned no valid vector.")
                if row is None:
                    row = AIKnowledgeChunk(
                        source=path.name, scope=scope, content=chunk,
                        content_hash=digest, embedding=vector,
                    )
                    db.session.add(row)
                else:
                    row.content, row.embedding = chunk, vector
                indexed += 1
            old_rows = db.session.scalars(select(AIKnowledgeChunk).where(
                AIKnowledgeChunk.source == path.name, AIKnowledgeChunk.scope == scope
            )).all()
            for old in old_rows:
                if old.content_hash not in current_hashes:
                    db.session.delete(old)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return indexed
