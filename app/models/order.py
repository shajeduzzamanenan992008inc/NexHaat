from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ..extensions import db

DELIVERY_STATUSES = (
    "unassigned",
    "assigned",
    "picked_up",
    "out_for_delivery",
    "delivered",
    "failed",
)

# Allowed delivery (rider workflow) state transitions.
DELIVERY_TRANSITIONS = {
    "unassigned": {"assigned"},
    "assigned": {"picked_up", "out_for_delivery", "unassigned", "failed"},
    "picked_up": {"out_for_delivery", "failed"},
    "out_for_delivery": {"delivered", "failed"},
    "delivered": set(),
    "failed": {"assigned"},
}


def delivery_transition_valid(current, target):
    return target in DELIVERY_TRANSITIONS.get(current, set())


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    # Sub-orders created from one checkout share a checkout group number.
    checkout_group = db.Column(db.String(40), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    seller_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payment_id = db.Column(
        db.Integer, db.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rider_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=True)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_fee = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0"
    )
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    promotion_code = db.Column(db.String(40), nullable=True)
    payment_method = db.Column(db.String(30), nullable=False, default="cod")
    commission_rate_percent = db.Column(db.Numeric(5, 2), nullable=True)
    commission_amount = db.Column(db.Numeric(10, 2), nullable=True)
    return_window_days_snapshot = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    delivery_status = db.Column(
        db.String(20), nullable=False, default="unassigned", server_default="unassigned", index=True
    )
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    picked_up_at = db.Column(db.DateTime(timezone=True), nullable=True)
    out_for_delivery_at = db.Column(db.DateTime(timezone=True), nullable=True)
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    delivery_proof = db.Column(db.String(500), nullable=True)
    delivery_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    __table_args__ = (
        db.CheckConstraint("total >= 0", name="ck_order_total_nonnegative"),
        db.CheckConstraint("delivery_fee >= 0", name="ck_order_delivery_fee_nonnegative"),
        db.CheckConstraint("discount_amount >= 0", name="ck_order_discount_nonnegative"),
        db.CheckConstraint(
            "payment_method IN ('cod', 'sslcommerz')", name="ck_order_payment_method_valid"
        ),
        db.CheckConstraint(
            "status IN ('pending', 'confirmed', 'preparing', 'delivered', 'returned', 'cancelled', 'declined')",
            name="ck_order_status_valid",
        ),
        db.CheckConstraint(
            "delivery_status IN ('unassigned', 'assigned', 'picked_up', 'out_for_delivery', 'delivered', 'failed')",
            name="ck_order_delivery_status_valid",
        ),
        db.Index("ix_orders_user_created", "user_id", "created_at"),
        db.Index("ix_orders_status_created", "status", "created_at"),
        db.Index("ix_orders_seller_created", "seller_id", "created_at"),
        db.Index("ix_orders_rider_status", "rider_id", "delivery_status"),
    )

    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    return_request = db.relationship("OrderReturn", back_populates="order", uselist=False)
    seller = db.relationship("User", foreign_keys=[seller_id])
    rider = db.relationship("User", foreign_keys=[rider_id])
    payment = db.relationship("Payment", back_populates="orders")

    @property
    def items_subtotal(self):
        return sum((item.subtotal for item in self.items), Decimal("0.00"))

    @property
    def is_delivered(self):
        return self.delivery_status == "delivered"

    @property
    def return_deadline(self):
        if self.delivered_at is None:
            return None
        return self.delivered_at.astimezone(UTC) + timedelta(days=max(0, int(self.return_window_days_snapshot or 0)))

    @property
    def is_return_eligible(self):
        if self.status != "delivered" or self.delivered_at is None:
            return False
        deadline = self.return_deadline
        return deadline is not None and datetime.now(UTC) <= deadline


class OrderReturn(db.Model):
    __tablename__ = "order_returns"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = db.Column(db.String(255), nullable=False)
    refund_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    status = db.Column(db.String(24), nullable=False, default="requested", server_default="requested")
    review_note = db.Column(db.String(500), nullable=True)
    provider_refund_id = db.Column(db.String(80), nullable=True, index=True)
    manual_refund_reference = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint("refund_amount >= 0", name="ck_order_return_refund_amount_nonnegative"),
        db.CheckConstraint(
            "status IN ('requested', 'approved', 'rejected', 'received', 'refunded', 'failed')",
            name="ck_order_return_status_valid",
        ),
    )

    order = db.relationship("Order", back_populates="return_request")
    customer = db.relationship("User", foreign_keys=[customer_id])
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    variant_id = db.Column(
        db.Integer, db.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    product_name = db.Column(db.String(160), nullable=False)
    variant_label = db.Column(db.String(220), nullable=True)
    sku_snapshot = db.Column(db.String(80), nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    __table_args__ = (
        db.CheckConstraint("price >= 0", name="ck_order_item_price_nonnegative"),
        db.CheckConstraint("quantity BETWEEN 1 AND 20", name="ck_order_item_quantity_range"),
        db.CheckConstraint("subtotal >= 0", name="ck_order_item_subtotal_nonnegative"),
    )

    order = db.relationship("Order", back_populates="items")


ReturnRequest = OrderReturn
