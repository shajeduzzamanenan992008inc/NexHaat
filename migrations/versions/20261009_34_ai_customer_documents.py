"""Add owner-scoped text documents for Customer AI retrieval."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261009_34"
down_revision = "20261009_33"
branch_labels = None
depends_on = None


def upgrade():
    if inspect(op.get_bind()).has_table("ai_customer_documents"):
        return
    op.create_table(
        "ai_customer_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("filename", sa.String(length=180), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "content_sha256", name="uq_ai_customer_document_digest"
        ),
        sa.CheckConstraint(
            "content_type IN ('text/plain', 'text/markdown', 'application/pdf')",
            name="ck_ai_customer_document_content_type",
        ),
    )
    op.create_index(
        "ix_ai_customer_documents_user_id", "ai_customer_documents", ["user_id"]
    )
    op.create_index(
        "ix_ai_customer_documents_user_created",
        "ai_customer_documents",
        ["user_id", "created_at"],
    )


def downgrade():
    if not inspect(op.get_bind()).has_table("ai_customer_documents"):
        return
    indexes = {item["name"] for item in inspect(op.get_bind()).get_indexes("ai_customer_documents")}
    for name in ("ix_ai_customer_documents_user_created", "ix_ai_customer_documents_user_id"):
        if name in indexes:
            op.drop_index(name, table_name="ai_customer_documents")
    op.drop_table("ai_customer_documents")
