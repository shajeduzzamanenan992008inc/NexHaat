import pytest

from app.ai.core.knowledge import (
    chunk_markdown,
    index_curated_knowledge,
)
from app.extensions import db
from app.models import AIKnowledgeChunk


def _embedding():
    return [1.0] + [0.0] * 1023


def _knowledge_dir(tmp_path):
    directory = tmp_path / "docs" / "ai-knowledge"
    directory.mkdir(parents=True)
    return directory


def test_chunk_markdown_is_bounded_and_preserves_content():
    source = ("NexHaat verified guidance. " * 100).strip()

    chunks = chunk_markdown(source, max_chars=400, overlap=40)

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 400 for chunk in chunks)
    assert "NexHaat verified guidance." in chunks[0]
    assert all(chunk.strip() for chunk in chunks)


def test_curated_index_is_idempotent_and_replaces_removed_chunks(
    app, tmp_path, monkeypatch,
):
    directory = _knowledge_dir(tmp_path)
    source_file = directory / "public.md"
    source_file.write_text("Verified first guidance.", encoding="utf-8")
    (directory / "ignore.txt").write_text("This is not Markdown.", encoding="utf-8")
    monkeypatch.setattr("app.ai.core.knowledge.embed_text", lambda _text: _embedding())

    with app.app_context():
        first_count = index_curated_knowledge(tmp_path, scope="public")
        first_rows = AIKnowledgeChunk.query.all()
        first_hashes = {row.content_hash for row in first_rows}

        second_count = index_curated_knowledge(tmp_path, scope="public")
        second_rows = AIKnowledgeChunk.query.all()

        assert first_count == second_count == 1
        assert len(first_rows) == len(second_rows) == 1
        assert {row.content_hash for row in second_rows} == first_hashes
        assert AIKnowledgeChunk.query.filter_by(source="ignore.txt").count() == 0

        source_file.write_text("Verified replacement guidance.", encoding="utf-8")
        replacement_count = index_curated_knowledge(tmp_path, scope="public")
        rows = AIKnowledgeChunk.query.all()

    assert replacement_count == 1
    assert len(rows) == 1
    assert rows[0].content == "Verified replacement guidance."
    assert rows[0].content_hash not in first_hashes


@pytest.mark.parametrize(
    "invalid_embedding",
    [None, [], [float("nan")] + [0.0] * 1023, ["not-a-number"] * 1024],
    ids=["missing", "wrong-dimension", "non-finite", "non-numeric"],
)
def test_invalid_embedding_fails_closed_and_rolls_back_previous_index(
    app, tmp_path, monkeypatch, invalid_embedding,
):
    directory = _knowledge_dir(tmp_path)
    source_file = directory / "public.md"
    source_file.write_text("Previously verified content.", encoding="utf-8")

    with app.app_context():
        monkeypatch.setattr("app.ai.core.knowledge.embed_text", lambda _text: _embedding())
        assert index_curated_knowledge(tmp_path, scope="public") == 1
        original = AIKnowledgeChunk.query.one()
        original_hash = original.content_hash

        source_file.write_text("Replacement awaiting valid embedding.", encoding="utf-8")
        monkeypatch.setattr(
            "app.ai.core.knowledge.embed_text",
            lambda _text: invalid_embedding,
        )
        with pytest.raises(RuntimeError, match="no valid vector"):
            index_curated_knowledge(tmp_path, scope="public")

        preserved = AIKnowledgeChunk.query.all()
        assert len(preserved) == 1
        assert preserved[0].content_hash == original_hash
        assert preserved[0].content == "Previously verified content."


def test_indexing_keeps_scope_specific_chunks_separate(app, tmp_path, monkeypatch):
    directory = _knowledge_dir(tmp_path)
    (directory / "public.md").write_text("Reviewed NexHaat guidance.", encoding="utf-8")
    monkeypatch.setattr("app.ai.core.knowledge.embed_text", lambda _text: _embedding())

    with app.app_context():
        assert index_curated_knowledge(tmp_path, scope="public") == 1
        assert index_curated_knowledge(tmp_path, scope="seller") == 1
        rows = AIKnowledgeChunk.query.order_by(AIKnowledgeChunk.scope).all()

    assert [(row.source, row.scope) for row in rows] == [
        ("public.md", "public"),
        ("public.md", "seller"),
    ]
