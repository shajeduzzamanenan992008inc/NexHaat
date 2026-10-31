"""Home banner carousel API.

Public, read-only endpoint returning active banners for the Android home
carousel. Banners are filtered to active records and ordered by display
order so the carousel presents a predictable rotation.
"""

from flask import Blueprint, request

from ...extensions import db
from ...models import Banner
from ..responses import success_response
from ..serializers import banner_to_dict

banners_api = Blueprint("api_banners", __name__)


@banners_api.get("/banners")
def list_banners():
    """Return the active home banners for the carousel."""
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=10, type=int)
    if page is None or limit is None or page < 1 or limit < 1 or limit > 50:
        return success_response([], message="Invalid pagination.", status=422)
    offset = (page - 1) * limit
    banners = db.session.scalars(
        db.select(Banner)
        .where(Banner.is_active.is_(True))
        .order_by(Banner.display_order.asc(), Banner.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return success_response(
        [banner_to_dict(b) for b in banners],
        message="Banners retrieved.",
    )
