"""Catalog services: listings, facets, weighted search, and discovery fallbacks.

Search scoring is deterministic and server-side. Candidate pools are bounded, so
a broad query can never scan the whole catalog, and relevance comes from weighted
field matches (name, brand, category, description, translations) plus a capped
popularity signal taken from real order quantities. Bangla product text is also
matched through a small Latin transliteration so Banglish queries keep working.
"""

import re
from difflib import SequenceMatcher
from math import ceil

from sqlalchemy import and_, case, func, or_, select

from ..extensions import db
from ..models import Category, Product, ProductVariant, SellerProfile, User
from ..models.food_reference import FdcCategory, FdcFood
from ..repositories.catalog import (
    active_brand_counts,
    active_categories,
    active_category_counts,
    active_products,
    approval_rating_product_ids,
    bounded_active_products,
    product_sales_totals,
    products_for_category,
    search_candidate_products,
)

# --- search tuning ---------------------------------------------------------
# Every bound below is deliberate: candidate pools and scans are capped so a
# single request can never load an unbounded number of rows.

SEARCH_TOKEN_LIMIT = 8
SEARCH_CANDIDATE_DEPTH = 300
SEARCH_RESULT_DEPTH = 200
SEARCH_FUZZY_SCAN_DEPTH = 200
FALLBACK_PRODUCT_DEPTH = 200
SEARCH_MIN_RELEVANCE = 0.45
SEARCH_TOKEN_MATCH_FLOOR = 0.30
FUZZY_TOKEN_RATIO = 0.75
FUZZY_TOKEN_MIN_LENGTH = 4
PREFIX_TOKEN_MIN_LENGTH = 3
NAME_PREFIX_SIMILARITY = 0.85
POPULARITY_BOOST_STEP = 0.01
POPULARITY_BOOST_CAP = 0.5
FALLBACK_TERM_MIN_SCORE = 0.5

FIELD_WEIGHTS = {
    "name": 1.0,
    "brand": 0.7,
    "category": 0.6,
    "description": 0.4,
}
TRANSLATION_NAME_WEIGHT = 0.9
TRANSLATION_DESCRIPTION_WEIGHT = 0.35

# A small, dependency-free Bangla-to-Latin map. It is intentionally approximate:
# it exists so a Banglish query ("chal") still matches Bangla product text
# ("চাল") when no translation row exists yet.
BANGLA_TRANSLITERATION = {
    "অ": "a", "আ": "a", "ই": "i", "ঈ": "i", "উ": "u", "ঊ": "u", "ঋ": "ri",
    "এ": "e", "ঐ": "oi", "ও": "o", "ঔ": "ou",
    "ক": "k", "খ": "kh", "গ": "g", "ঘ": "gh", "ঙ": "ng",
    "চ": "ch", "ছ": "chh", "জ": "j", "ঝ": "jh", "ঞ": "n",
    "ট": "t", "ঠ": "th", "ড": "d", "ঢ": "dh", "ণ": "n",
    "ত": "t", "থ": "th", "দ": "d", "ধ": "dh", "ন": "n",
    "প": "p", "ফ": "ph", "ব": "b", "ভ": "bh", "ম": "m",
    "য": "j", "র": "r", "ল": "l", "শ": "sh", "ষ": "sh", "স": "s", "হ": "h",
    "ড়": "r", "ঢ়": "rh", "য়": "y", "ৎ": "t", "ং": "ng", "ঃ": "h", "ঁ": "n",
    "া": "a", "ি": "i", "ী": "i", "ু": "u", "ূ": "u", "ৃ": "ri",
    "ে": "e", "ৈ": "oi", "ো": "o", "ৌ": "ou", "্": "",
    "০": "0", "১": "1", "২": "2", "৩": "3", "৪": "4",
    "৫": "5", "৬": "6", "৭": "7", "৮": "8", "৯": "9",
}
TRANSLITERATION_MULTI = {
    key: value for key, value in BANGLA_TRANSLITERATION.items() if len(key) > 1
}
TRANSLITERATION_TABLE = str.maketrans(
    {key: value for key, value in BANGLA_TRANSLITERATION.items() if len(key) == 1}
)

def transliterate_bangla(value):
    """Return a rough Latin form of Bangla text, or an empty string."""
    if not value:
        return ""
    if not any("\u0980" <= char <= "\u09ff" for char in value):
        return ""
    for source, target in TRANSLITERATION_MULTI.items():
        value = value.replace(source, target)
    return value.translate(TRANSLITERATION_TABLE)

def _normalize_search_tokens(value):
    """Unicode-safe tokens: English, Banglish, and Bangla script all survive.

    The Bangla block is matched explicitly because combining vowel signs are
    word characters, which would otherwise split each Bangla word into separate
    letters instead of one searchable token.
    """
    tokens = []
    for raw in re.findall(r"[\w\u0980-\u09ff]+", (value or "").lower()):
        token = raw.replace("_", "").strip()
        if token:
            tokens.append(token)
        if len(tokens) >= SEARCH_TOKEN_LIMIT:
            break
    return tokens

def _token_similarity(query_token, candidate_token):
    """Similarity in 0..1, allowing exact, prefix, and small typo matches."""
    if not query_token or not candidate_token:
        return 0.0
    if query_token == candidate_token:
        return 1.0
    shortest = min(len(query_token), len(candidate_token))
    if shortest >= PREFIX_TOKEN_MIN_LENGTH and (
        candidate_token.startswith(query_token) or query_token.startswith(candidate_token)
    ):
        return NAME_PREFIX_SIMILARITY
    if shortest >= FUZZY_TOKEN_MIN_LENGTH:
        ratio = SequenceMatcher(None, query_token, candidate_token).ratio()
        if ratio >= FUZZY_TOKEN_RATIO:
            return ratio
    return 0.0

def _text_scores(query_tokens, text):
    """Best similarity per query token against one text field."""
    candidate_tokens = _normalize_search_tokens(text)
    if not candidate_tokens or not query_tokens:
        return [0.0] * len(query_tokens)
    return [
        max((_token_similarity(token, candidate) for candidate in candidate_tokens), default=0.0)
        for token in query_tokens
    ]

def _search_fields(product):
    """Weighted searchable text for one product, including transliterations."""
    category_name = product.category.name if getattr(product, "category", None) else ""
    fields = [
        (product.name, FIELD_WEIGHTS["name"]),
        (transliterate_bangla(product.name), FIELD_WEIGHTS["name"] * 0.95),
        (product.brand_name, FIELD_WEIGHTS["brand"]),
        (transliterate_bangla(product.brand_name), FIELD_WEIGHTS["brand"] * 0.95),
        (category_name, FIELD_WEIGHTS["category"]),
        (product.description, FIELD_WEIGHTS["description"]),
    ]
    for translation in getattr(product, "translations", None) or []:
        name = getattr(translation, "name", "") or ""
        description = getattr(translation, "description", "") or ""
        fields.append((name, TRANSLATION_NAME_WEIGHT))
        fields.append((transliterate_bangla(name), TRANSLATION_NAME_WEIGHT * 0.95))
        fields.append((description, TRANSLATION_DESCRIPTION_WEIGHT))
    return fields

def relevance_score(query_tokens, product):
    """Weighted relevance in 0..1 for one product, before any popularity boost."""
    if not query_tokens:
        return 0.0
    best = [0.0] * len(query_tokens)
    for text, weight in _search_fields(product):
        if not text:
            continue
        for index, similarity in enumerate(_text_scores(query_tokens, text)):
            best[index] = max(best[index], weight * similarity)
    matched = sum(1 for score in best if score >= SEARCH_TOKEN_MATCH_FLOOR)
    coverage = matched / len(best)
    strength = sum(best) / len(best)
    return 0.65 * coverage + 0.35 * strength

def popularity_boost(units):
    """Capped boost so a best seller never outranks a clearly better match."""
    return min(POPULARITY_BOOST_CAP, max(0, int(units or 0)) * POPULARITY_BOOST_STEP)

def _rank_scored(query_tokens, products, popularity):
    scored = []
    for product in products:
        base = relevance_score(query_tokens, product)
        if base < SEARCH_MIN_RELEVANCE:
            continue
        units = int(popularity.get(product.id, 0) or 0)
        scored.append((base * (1 + popularity_boost(units)), units, product))
    scored.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            not item[2].is_featured,
            item[2].name.casefold(),
            item[2].id,
        )
    )
    return [product for _, _, product in scored]

def _search_pool(query_tokens):
    """Bounded candidate pool: token matches first, then a fuzzy scan."""
    pool = db.session.scalars(
        search_candidate_products(query_tokens, SEARCH_CANDIDATE_DEPTH)
    ).unique().all()
    if pool:
        return pool
    return db.session.scalars(
        bounded_active_products(SEARCH_FUZZY_SCAN_DEPTH)
    ).unique().all()

def ranked_search_products(query, limit=SEARCH_RESULT_DEPTH):
    """Relevance-ranked products for a query using bounded candidate pools."""
    query_tokens = _normalize_search_tokens(query)
    if not query_tokens:
        return []
    pool = _search_pool(query_tokens)
    if not pool:
        return []
    return _rank_scored(query_tokens, pool, product_sales_totals())[:limit]

def _pagination(page, pages, total):
    """Shared pagination payload, including concrete prev/next page numbers."""
    return {
        "page": page,
        "pages": pages,
        "total": total,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if page < pages else None,
    }

def get_active_categories():
    return db.session.scalars(active_categories()).all()

def get_active_sellers():
    return db.session.scalars(
        select(SellerProfile)
        .join(User, User.id == SellerProfile.user_id)
        .where(SellerProfile.approval_status == "approved", User.is_active.is_(True))
        .order_by(SellerProfile.store_name.asc())
    ).all()

def store_name_for_product(product):
    """Return the public store name for a listing, or None for a direct sale."""
    seller = getattr(product, "seller", None)
    profile = getattr(seller, "seller_profile", None) if seller is not None else None
    return profile.store_name if profile is not None else None

def get_active_brands():
    return db.session.scalars(
        select(Product.brand_name)
        .where(
            Product.is_available.is_(True),
            Product.moderation_status == "approved",
            Product.brand_name.is_not(None),
            Product.brand_name != "",
        )
        .distinct()
        .order_by(Product.brand_name.asc())
    ).all()

def get_home_products():
    return db.session.scalars(active_products().limit(12)).all()

def get_new_arrivals(limit=12):
    """Return the newest publicly listed products with a bounded query."""
    limit = max(1, min(int(limit), 24))
    statement = active_products().order_by(None).order_by(
        Product.created_at.desc(), Product.id.desc()
    )
    return db.session.scalars(statement.limit(limit)).all()

def _paginate_products(statement, page, per_page):
    total = db.session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    pages = max(1, ceil(total / per_page))
    page = max(1, min(page, pages))
    products = db.session.scalars(statement.limit(per_page).offset((page - 1) * per_page)).all()
    return products, _pagination(page, pages, total)

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
    min_rating=None,
    discount_only=False,
):
    """Return a shared, bounded marketplace listing query for web and API clients."""
    statement = active_products()
    query = (query or "").strip()[:100]
    ranked_ids = []
    rank_map = {}
    if query:
        ranked_ids = [product.id for product in ranked_search_products(query, limit=SEARCH_RESULT_DEPTH)]
        if ranked_ids:
            rank_map = {product_id: index for index, product_id in enumerate(ranked_ids)}
            statement = statement.where(Product.id.in_(ranked_ids))
        else:
            statement = statement.where(Product.id.in_([]))
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
    if deals_only or discount_only:
        statement = statement.where(Product.discount_price.is_not(None))
    if min_rating is not None:
        statement = statement.where(Product.id.in_(approval_rating_product_ids(min_rating)))
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
    elif ranked_ids:
        statement = statement.order_by(None).order_by(
            case(rank_map, value=Product.id),
            Product.is_featured.desc(),
            Product.name.asc(),
            Product.id.asc(),
        )
    return _paginate_products(statement, page, max(1, min(per_page, 100)))

def popular_products(limit=4):
    """Best-selling public products, falling back to featured listings."""
    popularity = product_sales_totals()
    pool = db.session.scalars(bounded_active_products(FALLBACK_PRODUCT_DEPTH)).unique().all()
    if not pool:
        return []
    if popularity:
        pool = sorted(
            pool,
            key=lambda product: (
                -int(popularity.get(product.id, 0) or 0),
                not product.is_featured,
                product.name.casefold(),
                product.id,
            ),
        )
    else:
        pool = sorted(pool, key=lambda product: (not product.is_featured, -product.id))
    return pool[:limit]

def related_search_terms(query, limit=6):
    """Related category and brand links for a query that returned no products."""
    query_tokens = _normalize_search_tokens(query)
    sources = []
    for name, slug, count in active_category_counts(limit=60):
        sources.append({"label": name, "kind": "category", "slug": slug, "_count": int(count or 0)})
    for brand, count in active_brand_counts(limit=60):
        sources.append({"label": brand, "kind": "brand", "value": brand, "_count": int(count or 0)})
    scored = []
    for term in sources:
        similarities = _text_scores(query_tokens, term["label"]) if query_tokens else []
        score = max(similarities, default=0.0)
        if query_tokens and score >= FALLBACK_TERM_MIN_SCORE:
            scored.append((score, term["_count"], term))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]["label"].casefold()))
    terms = [term for _, _, term in scored]
    if len(terms) < 3:
        seen = {(term["kind"], term["label"]) for term in terms}
        for term in sources:
            key = (term["kind"], term["label"])
            if key in seen:
                continue
            terms.append(term)
            seen.add(key)
            if len(terms) >= 3:
                break
    for term in terms:
        term.pop("_count", None)
    return terms[:limit]

def discovery_fallback(query, *, term_limit=6, product_limit=4):
    """Related search terms plus popular products for a zero-result query."""
    return {
        "terms": related_search_terms(query, limit=term_limit),
        "products": popular_products(limit=product_limit),
    }

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
    return foods, _pagination(page, pages, total)

def get_category_by_slug(slug):
    return db.session.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )

def get_category_products(category, page=1, per_page=48):
    return _paginate_products(products_for_category(category), page, per_page)

def get_product_by_slug(slug):
    return db.session.scalar(active_products().where(Product.slug == slug))

def search_products(query, page=1, per_page=48):
    """Paginated relevance search over the bounded ranking pipeline."""
    query = (query or "").strip()
    ranked_ids = [product.id for product in ranked_search_products(query, limit=per_page * 4)] if query else []
    if not ranked_ids:
        return [], _pagination(1, 1, 0)
    rank_map = {product_id: index for index, product_id in enumerate(ranked_ids)}
    statement = active_products().where(Product.id.in_(ranked_ids)).order_by(
        case(rank_map, value=Product.id), Product.name.asc()
    )
    return _paginate_products(statement, page, per_page)

def search_suggestions(query, limit=8):
    """Ranked autocomplete suggestions for the marketplace search box."""
    if not isinstance(query, str):
        return []
    query = query.strip()[:100]
    if len(query) < 2:
        return []
    try:
        limit = max(1, min(int(limit), 8))
    except (TypeError, ValueError):
        return []
    return ranked_search_products(query, limit=limit)
