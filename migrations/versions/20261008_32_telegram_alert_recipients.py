"""Track successful Security Bot alert deliveries by recipient."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261008_32"
down_revision = "20261008_31"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("telegram_security_alert_recipients"):
        op.create_table(
            "telegram_security_alert_recipients",
            sa.Column(
                "alert_id",
                sa.Integer(),
                sa.ForeignKey("telegram_security_alerts.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("telegram_user_id", sa.BigInteger(), primary_key=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    if inspect(op.get_bind()).has_table("telegram_security_alert_recipients"):
        op.drop_table("telegram_security_alert_recipients")
