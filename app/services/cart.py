from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import CustomerCartItem, Product, ProductVariant


class CartError(ValueError):
    """A cart operation cannot be completed with current catalog state."""


def cart_item_key(product_id, variant_id=None):
    return f"{product_id}:{variant_id}" if variant_id else str(product_id)


def _resolve_item(product_id, variant_id=None):
    product = db.session.scalar(
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    if not product or not product.is_available or not product.category.is_active:
        raise CartError("Product is unavailable.")

    active_variants = [item for item in product.variants if item.is_active]
    variant = next((item for item in active_variants if item.id == variant_id), None) if variant_id else None
    if variant_id and variant is None:
        raise CartError("Product option is unavailable.")
    if not variant and len(active_variants) == 1:
        variant = active_variants[0]
    elif not variant and len(active_variants) > 1:
        raise CartError("Choose a product option first.")
    stock = variant.stock_quantity if variant else product.stock_quantity
    if stock <= 0:
        raise CartError("Product is out of stock.")
    return product, variant, stock


def _upsert_item(user_id, product_id, variant_id, quantity, *, clamp=False):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise CartError("Quantity must be positive.")
    product, variant, stock = _resolve_item(product_id, variant_id)
    variant_id = variant.id if variant else None
    key = cart_item_key(product.id, variant_id)
    item = db.session.scalar(
        select(CustomerCartItem).where(
            CustomerCartItem.user_id == user_id,
            CustomerCartItem.item_key == key,
        )
    )
    requested = (item.quantity if item else 0) + quantity
    if requested > min(stock, 20):
        if not clamp:
            raise CartError("Requested quantity exceeds available stock.")
        requested = min(stock, 20)
    if item is None:
        item = CustomerCartItem(
            user_id=user_id,
            product_id=product.id,
            variant_id=variant_id,
            item_key=key,
            quantity=requested,
        )
        db.session.add(item)
    else:
        item.quantity = requested
    return item


def add_customer_cart_item(user_id, product_id, variant_id=None, quantity=1, *, clamp=False):
    item = _upsert_item(user_id, product_id, variant_id, quantity, clamp=clamp)
    db.session.commit()
    return item


def update_customer_cart_item(user_id, key, quantity):
    item = db.session.scalar(
        select(CustomerCartItem).where(
            CustomerCartItem.user_id == user_id,
            CustomerCartItem.item_key == key,
        )
    )
    if item is None:
        raise CartError("Cart item not found.")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 0 <= quantity <= 20:
        raise CartError("Quantity must be between 0 and 20.")
    if quantity == 0:
        db.session.delete(item)
        db.session.commit()
        return
    _product, _variant, stock = _resolve_item(item.product_id, item.variant_id)
    if quantity > stock:
        raise CartError("Requested quantity exceeds available stock.")
    item.quantity = quantity
    db.session.commit()


def remove_customer_cart_item(user_id, key):
    item = db.session.scalar(
        select(CustomerCartItem).where(
            CustomerCartItem.user_id == user_id,
            CustomerCartItem.item_key == key,
        )
    )
    if item is None:
        return False
    db.session.delete(item)
    db.session.commit()
    return True


def clear_customer_cart(user_id, *, commit=True):
    db.session.execute(delete(CustomerCartItem).where(CustomerCartItem.user_id == user_id))
    if commit:
        db.session.commit()


def customer_cart_items(user_id):
    return db.session.scalars(
        select(CustomerCartItem)
        .options(
            selectinload(CustomerCartItem.product).selectinload(Product.category),
            selectinload(CustomerCartItem.product).selectinload(Product.variants),
        )
        .where(CustomerCartItem.user_id == user_id)
        .order_by(CustomerCartItem.created_at, CustomerCartItem.id)
    ).all()


def customer_cart_rows(user_id):
    rows = []
    changed = False
    for item in customer_cart_items(user_id):
        try:
            product, variant, stock = _resolve_item(item.product_id, item.variant_id)
        except CartError:
            db.session.delete(item)
            changed = True
            continue
        variant_id = variant.id if variant else None
        key = cart_item_key(product.id, variant_id)
        quantity = min(item.quantity, stock, 20)
        if item.variant_id != variant_id or item.item_key != key or item.quantity != quantity:
            item.variant_id = variant_id
            item.item_key = key
            item.quantity = quantity
            changed = True
        price = variant.price if variant and variant.price is not None else product.display_price
        rows.append({
            "item": item,
            "product": product,
            "variant": variant,
            "price": price,
            "quantity": quantity,
            "subtotal": price * quantity,
            "stock": stock,
        })
    if changed:
        db.session.commit()
    return rows


def merge_guest_cart(user_id, guest_cart):
    if not isinstance(guest_cart, dict):
        return
    changed = False
    for key, raw_quantity in list(guest_cart.items())[:100]:
        parts = str(key).split(":", 1)
        try:
            product_id = int(parts[0])
            variant_id = int(parts[1]) if len(parts) == 2 else None
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            continue
        try:
            _upsert_item(user_id, product_id, variant_id, quantity, clamp=True)
            changed = True
        except CartError:
            continue
    if changed:
        db.session.commit()
    else:
        db.session.rollback()
