"""Conservative monthly reservation for explicitly consented specialist calls."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ...extensions import db
from ...models import AIExternalSpend


def decimal_setting(value):
    try:
        result = Decimal(str(value or "0"))
        return result if result.is_finite() and result >= 0 else Decimal("0")
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def reserve_external_budget(config, provider_specs, *, input_tokens=8000, output_tokens=1024):
    """Reserve the worst configured per-token cost before external requests begin.

    Cost rates must match the configured provider/model and should be refreshed by the
    operator whenever provider pricing changes. Reservations are intentionally not
    refunded on partial failures, so concurrent requests cannot exceed the cap.
    """
    budget = decimal_setting(config.get("AI_EXTERNAL_MONTHLY_BUDGET_USD"))
    if not config.get("AI_EXTERNAL_ENABLED") or budget <= 0 or len(provider_specs) < 2:
        return False
    reserve = Decimal("0")
    for spec in provider_specs:
        input_rate = decimal_setting(spec.get("input_rate"))
        output_rate = decimal_setting(spec.get("output_rate"))
        if not spec.get("model") or not spec.get("api_key") or input_rate <= 0 or output_rate <= 0:
            return False
        reserve += (input_rate * Decimal(input_tokens) + output_rate * Decimal(output_tokens)) / Decimal(1_000_000)
    # Include one verifier call at the most expensive configured rate when a disagreement arises.
    all_specs = config.get("AI_SPECIALISTS") or {}
    rates = []
    for spec in all_specs.values():
        input_rate = decimal_setting(spec.get("input_rate"))
        output_rate = decimal_setting(spec.get("output_rate"))
        if spec.get("model") and spec.get("api_key") and input_rate > 0 and output_rate > 0:
            rates.append((input_rate, output_rate))
    if not rates:
        return False
    reserve += (max(pair[0] for pair in rates) * Decimal(input_tokens)
                + max(pair[1] for pair in rates) * Decimal(output_tokens)) / Decimal(1_000_000)
    if reserve <= 0:
        return False
    reserve = reserve.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    table = AIExternalSpend.__table__
    dialect_name = db.engine.dialect.name
    insert_factory = postgres_insert if dialect_name == "postgresql" else sqlite_insert if dialect_name == "sqlite" else None
    if insert_factory is None:
        return False
    db.session.execute(
        insert_factory(table).values(month_key=month_key, reserved_usd=Decimal("0"), updated_at=now)
        .on_conflict_do_nothing(index_elements=[table.c.month_key])
    )
    updated = db.session.execute(
        update(table).where(
            table.c.month_key == month_key,
            table.c.reserved_usd + reserve <= budget,
        ).values(reserved_usd=table.c.reserved_usd + reserve, updated_at=now)
    )
    if updated.rowcount != 1:
        db.session.rollback()
        return False
    db.session.commit()
    return True
