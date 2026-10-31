"""Probe migration for banners schema compatibility checks.

Revision ID: 20261031_01_probe
Revises: 20261012_03
Create Date: 2026-10-31

This probe is temporary. It exercises the same compatibility checks we want in
the real migration so we can confirm the helper logic loads cleanly.

It is intentionally not wired into the real revision graph; discard when done.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261031_01_probe"
down_revision = "20261012_03"
branch_labels = None
depends_on = None


def _type_compatible(actual, expected, dialect):
    actual_cls = type(actual).__name__
    expected_cls = type(expected).__name__

    if expected_cls == "Boolean":
        return actual_cls == "Boolean"

    if expected_cls == "Integer" and actual_cls == "Integer":
        return True

    if expected_cls == "DateTime":
        if actual_cls != "DateTime":
            return False
        if dialect == "sqlite":
            return True
        return getattr(actual, "timezone", None) is not None

    if expected_cls == "String":
        expected_len = getattr(expected, "length", None)
        actual_len = getattr(actual, "length", None)
        if expected_len is not None and actual_len is not None:
            if actual_len < expected_len:
                return False
        return True

    return True


def _check_column_type(name, expected):
    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}
    dialect = inspector.bind.dialect.name
    actual = columns[name]["type"]

    if not _type_compatible(actual, expected, dialect):
        raise RuntimeError(
            "banners.%s type is incompatible" % name
        )


def _check_column(name, expected_type, nullable):
    inspector = inspect(op.get_bind())
    columns = {col["name"]: col for col in inspector.get_columns("banners")}
    col = columns[name]

    if col["nullable"] is not nullable:
        raise RuntimeError(
            "banners.%s is not nullable=%s as expected." % (name, nullable)
        )

    if not _type_compatible(
        col["type"], expected_type, inspector.bind.dialect.name
    ):
        raise RuntimeError(
            "banners.%s type is incompatible" % name
        )


def upgrade():
    pass


def downgrade():
    pass
