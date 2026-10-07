"""Add local-first AI consent, budget, memory and scoped knowledge storage.

Revision ID: 20261007_27
Revises: 20261006_26
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - optional in local SQLite development
    Vector = None


revision = "20261007_27"
down_revision = "20261006_26"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    inspector = inspect(bind)
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    preference_columns = {item["name"] for item in inspector.get_columns("ai_preferences")}
    if "long_term_memory_enabled" not in preference_columns:
        op.add_column("ai_preferences", sa.Column(
            "long_term_memory_enabled", sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ))

    if not inspector.has_table("ai_external_consents"):
        op.create_table(
            "ai_external_consents",
            sa.Column("principal_hash", sa.String(length=64), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not inspector.has_table("ai_external_spend"):
        op.create_table(
            "ai_external_spend",
            sa.Column("month_key", sa.String(length=7), primary_key=True),
            sa.Column("reserved_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("reserved_usd >= 0", name="ck_ai_external_spend_nonnegative"),
        )
    if not inspector.has_table("ai_user_memories"):
        op.create_table(
            "ai_user_memories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("content", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "ix_ai_user_memories_user_id" not in {item["name"] for item in inspect(bind).get_indexes("ai_user_memories")}:
        op.create_index("ix_ai_user_memories_user_id", "ai_user_memories", ["user_id"])
    if not inspector.has_table("ai_knowledge_chunks"):
        op.create_table(
            "ai_knowledge_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source", sa.String(length=240), nullable=False),
            sa.Column("scope", sa.String(length=24), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "embedding",
                Vector(1024) if is_postgres and Vector is not None else sa.Text(),
                nullable=True,
            ),
            sa.Column("content_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "scope IN ('public', 'customer', 'seller', 'admin', 'rider', 'security')",
                name="ck_ai_knowledge_scope",
            ),
        )
    knowledge_indexes = {item["name"] for item in inspect(bind).get_indexes("ai_knowledge_chunks")}
    if "ix_ai_knowledge_chunks_source" not in knowledge_indexes:
        op.create_index("ix_ai_knowledge_chunks_source", "ai_knowledge_chunks", ["source"])
    if "ix_ai_knowledge_chunks_scope" not in knowledge_indexes:
        op.create_index("ix_ai_knowledge_chunks_scope", "ai_knowledge_chunks", ["scope"])
    if is_postgres:
        if "ix_ai_knowledge_chunks_embedding_hnsw" not in knowledge_indexes:
            op.create_index(
                "ix_ai_knowledge_chunks_embedding_hnsw", "ai_knowledge_chunks", ["embedding"],
                postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"},
            )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("ix_ai_knowledge_chunks_embedding_hnsw", table_name="ai_knowledge_chunks")
    op.drop_index("ix_ai_knowledge_chunks_scope", table_name="ai_knowledge_chunks")
    op.drop_index("ix_ai_knowledge_chunks_source", table_name="ai_knowledge_chunks")
    op.drop_table("ai_knowledge_chunks")
    op.drop_index("ix_ai_user_memories_user_id", table_name="ai_user_memories")
    op.drop_table("ai_user_memories")
    op.drop_table("ai_external_spend")
    op.drop_table("ai_external_consents")
    op.drop_column("ai_preferences", "long_term_memory_enabled")
