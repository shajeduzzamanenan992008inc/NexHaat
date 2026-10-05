import re
from difflib import SequenceMatcher
from math import ceil

from sqlalchemy import and_, case, func, or_, select

from ..extensions import db
from ..models import Category, Product, ProductTranslation, ProductVariant, SellerProfile, User
from ..models.food_reference import FdcCategory, FdcFood
from ..repositories.catalog import (
    active_categories,
    active_products,
    products_for_category,
    search_active_products,
)


def _normalize_search_tokens(value):
    return [token for token in re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).split() if token]


def _fuzzy_word_score(query, candidate):
    query_tokens = _normalize_search_tokens(query)
    candidate_tokens = _normalize_search_tokens(candidate)
    if not query_tokens or not candidate_tokens:
        return 0.0
    best = 0.0
    for query_token in query_tokens:
        for candidate_token in candidate_tokens:
            if query_token == candidate_token:
                best = max(best, 1.0)
            elif query_token.startswith(candidate_token) or candidate_token.startswith(query_token):
                best = max(best, 0.8)
            else:
                ratio = SequenceMatcher(None, query_token, candidate_token).ratio()
                if ratio >= 0.75:
                    best = max(best, ratio)
    return best


def _fallback_fuzzy_product_ids(query, limit=24):
    query = (query or "").strip()
    if len(query) < 2:
        return []
    products = db.session.scalars(
        select(Product)
        .where(Product.is_available.is_(True), Product.moderation_status == "approved")
        .order_by(Product.is_featured.desc(), Product.name.asc())
    ).all()
    if not products:
        return []
    scored = []
    for product in products:
        candidates = [product.name, product.description]
        candidates.extend(translation.name for translation in product.translations if getattr(translation, "name", None))
        candidates.extend(
            translation.description for translation in product.translations if getattr(translation, "description", None)
        )
        best_score = max((_fuzzy_word_score(query, candidate) for candidate in candidates if candidate), default=0.0)
        if best_score >= 0.55:
            scored.append((best_score, product.id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [product_id for _, product_id in scored[:limit]]


def get_active_categories():
    return db.session.scalars(active_categories()).all()


def get_active_sellers():
    return db.session.scalars(
        select(SellerProfile)
        .join(User, User.id == SellerProfile.user_id)
        .where(SellerProfile.approval_status == "approved", User.is_active.is_(True))
        .order_by(SellerProfile.store_name.asc())
    ).all()


def get_active_brands():
    return db.session.scalars(
        select(Product.brand_name).where(
            Product.is_available.is_(True),
            Product.moderation_status == "approved",
            Product.brand_name.is_not(None),
            Product.brand_name != "",
        ).distinct().order_by(Product.brand_name.asc())
    ).all()


def get_home_products():
    return db.session.scalars(active_products().limit(12)).all()


def _paginate_products(statement, page, per_page):
    total = db.session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    pages = max(1, ceil(total / per_page))
    page = max(1, min(page, pages))
    products = db.session.scalars(
        statement.limit(per_page).offset((page - 1) * per_page)
    ).all()
    return products, {
        "page": page,
        "pages": pages,
        "total": total,
        "has_prev": page > 1,
        "has_next": page < pages,
    }


def get_menu_products(page=1, per_page=48):
    return _paginate_products(active_products(), page, per_page)


def get_catalog_products(
    page=1,
    per_page=48,
    query="",
    category_id=None,
    min_price=None,
    max_price=None,
    sort="featured",
    seller_id=None,
    brand_name=None,
    in_stock=False,
    variant_value="",
    deals_only=False,
):
    """Return a shared, bounded marketplace listing query for web and API clients."""
    statement = active_products()
    if deals_only:
        statement = statement.where(Product.discount_price.is_not(None))
    query = (query or "").strip()[:100]
    if query:
        exact_statement = search_active_products(query)
        exact_count = db.session.scalar(
            select(func.count()).select_from(exact_statement.order_by(None).subquery())
        ) or 0
        if exact_count:
            statement = exact_statement
        else:
            fuzzy_ids = _fallback_fuzzy_product_ids(query)
            if fuzzy_ids:
                statement = active_products().where(Product.id.in_(fuzzy_ids))
                order_map = {product_id: index for index, product_id in enumerate(fuzzy_ids)}
                statement = statement.order_by(case(order_map, value=Product.id), Product.is_featured.desc(), Product.name.asc())
            else:
                statement = active_products().where(Product.id.in_([]))
    if category_id is not None:
        statement = statement.where(Product.category_id == category_id)

    display_price = func.coalesce(Product.discount_price, Product.price)
    if min_price is not None:
        statement = statement.where(display_price >= min_price)
    if max_price is not None:
        statement = statement.where(display_price <= max_price)
    if seller_id is not None:
        statement = statement.where(Product.seller_id == seller_id)
    brand_name = (brand_name or "").strip()[:120]
    if brand_name:
        statement = statement.where(Product.brand_name == brand_name)
    if in_stock:
        statement = statement.where(or_(
            Product.stock_quantity > 0,
            Product.variants.any(and_(ProductVariant.is_active.is_(True), ProductVariant.stock_quantity > 0)),
        ))
    variant_value = (variant_value or "").strip()[:80]
    if variant_value:
        statement = statement.where(Product.variants.any(and_(
            ProductVariant.is_active.is_(True),
            ProductVariant.option_value.ilike(f"%{variant_value}%"),
        )))

    if sort == "newest":
        statement = statement.order_by(None).order_by(Product.created_at.desc(), Product.id.desc())
    elif sort == "price_asc":
        statement = statement.order_by(None).order_by(
            display_price.asc(), Product.name.asc(), Product.id.asc()
        )
    elif sort == "price_desc":
        statement = statement.order_by(None).order_by(
            display_price.desc(), Product.name.asc(), Product.id.asc()
        )
    elif query and exact_count:
        pattern = f"%{query}%"
        statement = statement.order_by(None).order_by(
            case(
                (Product.name.ilike(query), 0),
                (Product.name.ilike(f"{query}%"), 1),
                (Product.name.ilike(pattern), 2),
                else_=3,
            ),
            Product.is_featured.desc(),
            Product.name.asc(),
        )
    return _paginate_products(statement, page, max(1, min(per_page, 100)))


def get_reference_food_categories():
    return db.session.execute(
        select(FdcCategory, func.count(FdcFood.fdc_id).label("food_count"))
        .join(FdcFood, FdcFood.category_id == FdcCategory.id)
        .group_by(FdcCategory.id)
        .order_by(FdcCategory.name)
    ).all()


def get_reference_foods(page=1, per_page=48, category_id=None, query=""):
    statement = select(FdcFood).where(FdcFood.description != "")
    if category_id is not None:
        statement = statement.where(FdcFood.category_id == category_id)
    if query:
        statement = statement.where(FdcFood.description.ilike(f"%{query}%"))

    total = db.session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    pages = max(1, ceil(total / per_page))
    page = max(1, min(page, pages))
    foods = db.session.scalars(
        statement.order_by(FdcFood.description, FdcFood.fdc_id)
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).all()
    return foods, {
        "page": page,
        "pages": pages,
        "total": total,
        "has_prev": page > 1,
        "has_next": page < pages,
    }


def get_category_by_slug(slug):
    return db.session.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )


def get_category_products(category, page=1, per_page=48):
    return _paginate_products(products_for_category(category), page, per_page)


def get_product_by_slug(slug):
    return db.session.scalar(
        active_products().where(Product.slug == slug)
    )


def search_products(query, page=1, per_page=48):
    query = (query or "").strip()
    if not query:
        return [], {"page": 1, "pages": 1, "total": 0, "has_prev": False, "has_next": False}
    exact_statement = search_active_products(query)
    exact_count = db.session.scalar(select(func.count()).select_from(exact_statement.order_by(None).subquery())) or 0
    if exact_count:
        return _paginate_products(exact_statement, page, per_page)
    fuzzy_ids = _fallback_fuzzy_product_ids(query, limit=per_page * 2)
    if not fuzzy_ids:
        return [], {"page": 1, "pages": 1, "total": 0, "has_prev": False, "has_next": False}
    statement = active_products().where(Product.id.in_(fuzzy_ids))
    order_map = {product_id: index for index, product_id in enumerate(fuzzy_ids)}
    statement = statement.order_by(case(order_map, value=Product.id), Product.name.asc())
    return _paginate_products(statement, page, per_page)


def search_suggestions(query, limit=8):
    query = (query or "").strip()[:100]
    if len(query) < 2:
        return []
    results = db.session.scalars(search_active_products(query).limit(limit)).all()
    if results:
        return results
    fuzzy_ids = _fallback_fuzzy_product_ids(query, limit=limit)
    if not fuzzy_ids:
        return []
    return db.session.scalars(
        active_products().where(Product.id.in_(fuzzy_ids)).order_by(case({pid: index for index, pid in enumerate(fuzzy_ids)}, value=Product.id))
    ).all()
