"""Create banners table for home carousel.

Revision ID: 20261031_01
Revises: 20261012_03
Create Date: 2026-10-31

This migration intentionally refuses automatic downgrade to prevent accidental
loss of pre-existing or migrated banner data. If you must revert, first back up
the banners table with a manual dump, then drop only if you have verified the
backup and confirmed no dependent data must be preserved.

Manual rollback sequence (documented, not executed by this migration):
1. Back up the table: psql -c "COPY banners TO STDOUT" > banners_backup.sql
   (or equivalent sqlite3 .dump / mysqldump / pg_dump command for your database).
2. Verify the backup contains the rows you expect.
3. Drop the indexes and table manually only if the backup is confirmed:
   - DROP INDEX IF EXISTS ix_banners_active_order;
   - DROP INDEX IF EXISTS ix_banners_is_active;
   - DROP TABLE IF EXISTS banners;
4. Re-run `alembic upgrade <base>` or the appropriate earlier revision.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
import re as _re

revision = "20261031_01"
down_revision = "20261012_03"
branch_labels = None
depends_on = None

BANNER_COLUMNS = {
    "id": (sa.Integer(), False),
    "title": (sa.String(length=120), False),
    "subtitle": (sa.String(length=255), True),
    "image_url": (sa.String(length=500), True),
    "link_url": (sa.String(length=500), True),
    "link_type": (sa.String(length=32), False),
    "is_active": (sa.Boolean(), False),
    "display_order": (sa.Integer(), False),
    "created_at": (sa.DateTime(timezone=True), False),
}

_LINK_TYPE_CHECK = (
    "link_type IN ('products', 'category', 'search', 'external')"
)


def upgrade():
    inspector = inspect(op.get_bind())
    if "banners" not in inspector.get_table_names():
        op.create_table(
            "banners",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("subtitle", sa.String(length=255), nullable=True),
            sa.Column("image_url", sa.String(length=500), nullable=True),
            sa.Column(
                "link_url", sa.String(length=500), nullable=True
            ),
            sa.Column(
                "link_type",
                sa.String(length=32),
                nullable=False,
                server_default="products",
            ),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False
            ),
            sa.Column(
                "display_order", sa.Integer(), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.CheckConstraint(
                "length(trim(title)) > 0", name="ck_banner_title_nonempty"
            ),
            sa.CheckConstraint(
                "link_type IN ('products', 'category', 'search', 'external')",
                name="ck_banner_link_type",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_banners_is_active", "banners", ["is_active"]
        )
        op.create_index(
            "ix_banners_active_order",
            "banners",
            ["is_active", "display_order"],
        )
        return

    _ensure_banner_schema_compatibility()


def _ensure_banner_schema_compatibility():
    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}

    if set(columns.keys()) != set(BANNER_COLUMNS.keys()):
        missing = set(BANNER_COLUMNS.keys()) - set(columns.keys())
        extra = set(columns.keys()) - set(BANNER_COLUMNS.keys())
        details = []
        if missing:
            details.append(f"missing columns: {','.join(sorted(missing))}")
        if extra:
            details.append(f"unexpected columns: {','.join(sorted(extra))}")
        raise RuntimeError(
            "banners table exists but its column set is incompatible with "
            f"revision 20261031_01. {'. '.join(details) if details else 'No column mismatch details available.'}"
        )

    _check_column_type("id", sa.Integer())
    _check_column_type_legacy_sqlite("is_active", sa.Boolean())
    _check_column_type("display_order", sa.Integer())
    _check_column_type_legacy_sqlite("created_at", sa.DateTime(timezone=True))

    _check_column("title", expected_type=sa.String(length=120), nullable=False)
    _check_column(
        "subtitle", expected_type=sa.String(length=255), nullable=True
    )
    _check_column(
        "image_url", expected_type=sa.String(length=500), nullable=True
    )
    _check_column(
        "link_url", expected_type=sa.String(length=500), nullable=True
    )
    _check_column(
        "link_type", expected_type=sa.String(length=32), nullable=False
    )

    _check_server_default("link_type", "products")

    _check_indexes(inspector)
    _check_constraints(inspector)


def _check_column_type_legacy_sqlite(name, expected):
    """Compatibility check for SQLite column types.

    SQLite's type system is intentionally duck-typed; the declared type name
    may not match the SQLAlchemy type class that ends up in the inspection
    result. For Boolean and DateTime columns we accept the SQLite BOOLEAN /
    DATETIME names directly in addition to the SQLAlchemy type classes.
    """
    from sqlalchemy import Boolean as _Boolean
    from sqlalchemy import DateTime as _DateTime

    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}
    col = columns[name]
    py_type = getattr(col["type"], "python_type", None)

    if isinstance(col["type"], _Boolean) or py_type is bool:
        return

    if isinstance(col["type"], _DateTime):
        return

    actual_cls = type(col["type"]).__name__
    if actual_cls in {"BOOLEAN", "DATETIME", "BOOL", "TIMESTAMP"}:
        return

    expected_cls = type(expected).__name__
    if expected_cls in {"Boolean", "DateTime"} and actual_cls in {"BOOLEAN", "DATETIME"}:
        return

    raise RuntimeError(
        f"banners.{name} type is incompatible with expected type "
        f"{expected} (got {actual_cls})."
    )


def _check_column_type(name, expected):
    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}
    dialect = inspector.bind.dialect.name
    actual = columns[name]["type"]

    if not _type_compatible(actual, expected, dialect):
        raise RuntimeError(
            f"banners.{name} type is incompatible with expected type "
            f"{expected} (got {type(actual).__name__})."
        )


def _check_column_type_legacy_sqlite(name, expected):
    """Compatibility check for SQLite column types.

    SQLite's type system is intentionally duck-typed; the declared type name
    may not match the SQLAlchemy type class that ends up in the inspection
    result. For Boolean and DateTime columns we accept the SQLite BOOLEAN /
    DATETIME names directly in addition to the SQLAlchemy type classes.
    """
    from sqlalchemy import Boolean as _Boolean
    from sqlalchemy import DateTime as _DateTime

    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}
    col = columns[name]
    py_type = getattr(col["type"], "python_type", None)

    if isinstance(col["type"], _Boolean) or py_type is bool:
        return

    if isinstance(col["type"], _DateTime):
        return

    actual_cls = type(col["type"]).__name__
    if actual_cls in {"BOOLEAN", "DATETIME"}:
        return

    raise RuntimeError(
        f"banners.{name} type is incompatible with expected type "
        f"{expected} (got {actual_cls})."
    )


def _check_column(name, expected_type, nullable):
    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}
    col = columns[name]

    if col["nullable"] is not nullable:
        raise RuntimeError(
            f"banners.{name} is not nullable={nullable} as expected."
        )

    if not _type_compatible(col["type"], expected_type, inspector.bind.dialect.name):
        raise RuntimeError(
            f"banners.{name} type is incompatible with the expected type "
            f"{expected_type}."
        )


def _check_server_default(column_name, expected):
    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}
    actual = columns[column_name].get("default")

    if actual is None:
        raise RuntimeError(
            f"banners.{column_name} has no server default but "
            f"revision 20261031_01 expects server_default={expected!r}."
        )

    if not _server_default_matches(actual, expected):
        raise RuntimeError(
            f"banners.{column_name} server default is {actual!r}, expected "
            f"{expected!r}."
        )


def _server_default_matches(actual, expected):
    """Return True if the observed server default is compatible with expected.

    SQLAlchemy inspectors may return the default as a quoted string (for
    example "'products'") even when the migration declared an unquoted
    server_default="products". We accept both representations.
    """
    if actual is None:
        return False

    actual_str = str(actual).strip()
    if actual_str == str(expected):
        return True

    if actual_str == repr(expected):
        return True

    return False


def _check_indexes(inspector):
    indexes = inspector.get_indexes("banners")
    index_names = {idx["name"] for idx in indexes}

    missing = ["ix_banners_active_order", "ix_banners_is_active"]
    missing = [i for i in missing if i not in index_names]
    if missing:
        raise RuntimeError(
            "banners table is missing required indexes: "
            f"{', '.join(sorted(missing))}."
        )

    active_order = next(
        (idx for idx in indexes if idx["name"] == "ix_banners_active_order"),
        None,
    )
    if active_order is None or active_order["column_names"] != [
        "is_active",
        "display_order",
    ]:
        raise RuntimeError(
            "banners.ix_banners_active_order must cover "
            "(is_active, display_order) exactly."
        )


def _check_constraints(inspector):
    constraints = inspector.get_check_constraints("banners")
    constraint_names = {c["name"] for c in constraints}

    required = {"ck_banner_title_nonempty", "ck_banner_link_type"}
    if not required.issubset(constraint_names):
        missing = required - constraint_names
        raise RuntimeError(
            "banners table is missing required constraints: "
            f"{', '.join(sorted(missing))}."
        )


def _type_compatible(actual, expected, dialect):
    """Compare a column type with the expected SQLAlchemy type.

    This is intentionally lenient: SQLite storage classes differ from the
    declared types, PostgreSQL-native types may render as dialect-specific
    variants, and length metadata can differ across backends. We only reject
    clearly wrong conversions such as Integer vs Boolean vs DateTime, or a
    String whose maximum length is materially smaller than expected.
    """
    actual_cls_name = type(actual).__name__
    expected_cls_name = type(expected).__name__

    if expected_cls_name == "Boolean":
        if actual_cls_name == "Boolean":
            return True
        if dialect == "sqlite" and getattr(actual, "python_type", None) is bool:
            return True
        if dialect == "sqlite" and hasattr(actual, "impl") and getattr(actual.impl, "python_type", None) is bool:
            return True
        if dialect == "postgresql" and actual_cls_name == "BOOLEAN":
            return True
        if dialect == "mysql" and actual_cls_name in {"TINYINT", "BOOLEAN"}:
            return True
        return False

    if expected_cls_name == "Integer" and actual_cls_name == "Integer":
        return True

    if expected_cls_name == "DateTime":
        if actual_cls_name != "DateTime":
            return False
        return True

    if expected_cls_name == "String":
        expected_len = getattr(expected, "length", None)
        actual_len = getattr(actual, "length", None)
        if expected_len is not None and actual_len is not None:
            if actual_len < expected_len:
                return False
        return True

    return True


def downgrade():
    raise RuntimeError(
        "Automatic downgrade of revision 20261031_01 is intentionally "
        "disabled. This prevents accidental loss of pre-existing or migrated "
        "banner data.\n\n"
        "To roll back safely, back up the banners table first (for example: "
        "psql -c 'COPY banners TO STDOUT' > banners_backup.sql, or the "
        "equivalent dump command for your database), verify the backup, and "
        "then drop the indexes and table manually if you still need to "
        "revert:\n"
        "  - DROP INDEX IF EXISTS ix_banners_active_order;\n"
        "  - DROP INDEX IF EXISTS ix_banners_is_active;\n"
        "  - DROP TABLE IF EXISTS banners;\n"
        "After completing those manual steps, re-run the earlier revision "
        "with something like `alembic upgrade <earlier-revision>`."
    )
