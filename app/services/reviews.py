"""Product reviews: purchase eligibility, submission, aggregation, moderation."""

from datetime import UTC, datetime

from flask_babel import gettext
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Order, OrderItem, Review, ReviewHelpfulVote, ReviewReport


class ReviewError(Exception):
    """Raised when a review cannot be created for a business reason."""


def reviews_for_product(product_id, status="approved"):
    """Return a product's reviews, newest first (approved by default)."""
    statement = select(Review).where(Review.product_id == product_id)
    if status is not None:
        statement = statement.where(Review.status == status)
    return db.session.scalars(statement.order_by(Review.created_at.desc())).all()


def rating_summary(product_id):
    count, average = db.session.execute(
        select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.product_id == product_id, Review.status == "approved"
        )
    ).one()
    count = count or 0
    return {
        "count": count,
        "average": round(float(average), 1) if count and average is not None else None,
    }


def rating_summaries(product_ids):
    """Approved-review averages and counts for several products in one query.

    Only real, approved reviews produce a summary. A product with no reviews is
    absent from the mapping so serializers never emit a fabricated rating.
    """
    ids = _review_ids(product_ids)
    if not ids:
        return {}
    rows = db.session.execute(
        select(Review.product_id, func.count(Review.id), func.avg(Review.rating))
        .where(Review.product_id.in_(ids), Review.status == "approved")
        .group_by(Review.product_id)
    ).all()
    return {
        int(product_id): {"count": int(count), "average": round(float(average), 1)}
        for product_id, count, average in rows
        if count and average is not None
    }


def rating_histogram(product_id):
    """Approved-review star distribution with ready-to-render bar widths."""
    rows = db.session.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.product_id == product_id, Review.status == "approved")
        .group_by(Review.rating)
    ).all()
    counts = dict.fromkeys(range(1, 6), 0)
    for rating, count in rows:
        star = int(rating)
        if star in counts:
            counts[star] = int(count)
    total = sum(counts.values())
    return {
        "counts": counts,
        "total": total,
        "peak": max(counts.values(), default=0),
        "rows": [
            {
                "stars": star,
                "count": counts[star],
                "percent": round(counts[star] * 100 / total) if total else 0,
            }
            for star in range(5, 0, -1)
        ],
    }

def _review_ids(review_ids, limit=200):
    return [int(review_id) for review_id in review_ids][:limit]

def helpful_counts(review_ids):
    """Helpful-vote totals for a page of reviews in one bounded query."""
    ids = _review_ids(review_ids)
    if not ids:
        return {}
    rows = db.session.execute(
        select(ReviewHelpfulVote.review_id, func.count(ReviewHelpfulVote.id))
        .where(ReviewHelpfulVote.review_id.in_(ids))
        .group_by(ReviewHelpfulVote.review_id)
    ).all()
    return {int(review_id): int(count) for review_id, count in rows}

def open_report_counts(review_ids):
    """Open abuse-report totals per review, so moderation can flag hot rows."""
    ids = _review_ids(review_ids)
    if not ids:
        return {}
    rows = db.session.execute(
        select(ReviewReport.review_id, func.count(ReviewReport.id))
        .where(ReviewReport.review_id.in_(ids), ReviewReport.status == "open")
        .group_by(ReviewReport.review_id)
    ).all()
    return {int(review_id): int(count) for review_id, count in rows}

def viewer_helpful_review_ids(user, review_ids):
    """Which of these reviews the signed-in viewer already marked helpful."""
    ids = _review_ids(review_ids)
    if user is None or getattr(user, "id", None) is None or not ids:
        return set()
    return set(
        db.session.scalars(
            select(ReviewHelpfulVote.review_id).where(
                ReviewHelpfulVote.user_id == user.id,
                ReviewHelpfulVote.review_id.in_(ids),
            )
        ).all()
    )

def toggle_helpful_vote(user, review):
    """Add or remove one helpful vote. Returns True when the review is now voted."""
    if user is None or getattr(user, "id", None) is None:
        raise ReviewError(gettext("Sign in to mark a review helpful."))
    if review is None or review.status != "approved":
        raise ReviewError(gettext("That review is not available."))
    if review.user_id == user.id:
        raise ReviewError(gettext("You cannot vote on your own review."))
    existing = db.session.scalar(
        select(ReviewHelpfulVote).where(
            ReviewHelpfulVote.review_id == review.id,
            ReviewHelpfulVote.user_id == user.id,
        )
    )
    if existing is not None:
        db.session.delete(existing)
        db.session.commit()
        return False
    db.session.add(ReviewHelpfulVote(review_id=review.id, user_id=user.id))
    db.session.commit()
    return True

def report_review(user, review, reason):
    """Record one shopper's abuse report for Admin triage."""
    if user is None or getattr(user, "id", None) is None:
        raise ReviewError(gettext("Sign in to report a review."))
    if review is None or review.status != "approved":
        raise ReviewError(gettext("That review is not available."))
    if review.user_id == user.id:
        raise ReviewError(gettext("You cannot report your own review."))
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 5:
        raise ReviewError(gettext("Describe the problem in at least 5 characters."))
    if len(clean_reason) > 500:
        raise ReviewError(gettext("Keep the report under 500 characters."))
    existing = db.session.scalar(
        select(ReviewReport).where(
            ReviewReport.review_id == review.id,
            ReviewReport.reporter_user_id == user.id,
        )
    )
    if existing is not None:
        if existing.status != "open":
            existing.status = "open"
            existing.reason = clean_reason
            existing.resolved_at = None
            existing.resolved_by_id = None
            db.session.commit()
        raise ReviewError(gettext("You already reported this review."))
    report = ReviewReport(review_id=review.id, reporter_user_id=user.id, reason=clean_reason)
    db.session.add(report)
    db.session.commit()
    return report

def open_review_reports(limit=100):
    """Open abuse reports with their review and product for the Admin queue."""
    return db.session.scalars(
        select(ReviewReport)
        .options(selectinload(ReviewReport.review).selectinload(Review.product))
        .where(ReviewReport.status == "open")
        .order_by(ReviewReport.created_at.asc())
        .limit(limit)
    ).all()

def open_review_report_count():
    return db.session.scalar(
        select(func.count(ReviewReport.id)).where(ReviewReport.status == "open")
    ) or 0

def resolve_review_report(report, decision, resolver):
    """Close one report as reviewed or dismissed. Returns None when not actionable."""
    if report is None or report.status != "open" or decision not in {"reviewed", "dismissed"}:
        return None
    report.status = decision
    report.resolved_at = datetime.now(UTC)
    report.resolved_by_id = getattr(resolver, "id", None)
    db.session.commit()
    return report

def pending_reviews(limit=100):
    return db.session.scalars(
        select(Review)
        .where(Review.status == "pending")
        .order_by(Review.created_at.asc())
        .limit(limit)
    ).all()


def eligible_order_id(user, product_id):
    """Return a delivered order the user can still review this product with, else None."""
    if user is None or getattr(user, "id", None) is None:
        return None
    reviewed_orders = select(Review.order_id).where(
        Review.product_id == product_id, Review.user_id == user.id
    )
    return db.session.scalar(
        select(OrderItem.order_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.product_id == product_id,
            Order.user_id == user.id,
            Order.status == "delivered",
            OrderItem.order_id.not_in(reviewed_orders),
        )
        .order_by(OrderItem.order_id.desc())
    )


def author_name(user):
    """Return a display name snapshot for a review author."""
    profile = getattr(user, "customer_profile", None)
    if profile and profile.full_name:
        return profile.full_name[:120]
    return (user.email or "Customer")[:120]


def create_review(user, product, rating, comment=""):
    """Create a pending review for a delivered purchase, or raise ReviewError."""
    if user is None:
        raise ReviewError(gettext("Sign in to review this product."))
    order_id = eligible_order_id(user, product.id)
    if order_id is None:
        raise ReviewError(gettext("You can review a product after your order is delivered."))
    try:
        rating_value = int(rating)
    except (TypeError, ValueError) as error:
        raise ReviewError(gettext("Choose a rating from 1 to 5 stars.")) from error
    if not 1 <= rating_value <= 5:
        raise ReviewError(gettext("Choose a rating from 1 to 5 stars."))
    clean_comment = (comment or "").strip()
    if len(clean_comment) > 2000:
        raise ReviewError(gettext("Your review must be 2000 characters or fewer."))
    review = Review(
        product_id=product.id,
        user_id=user.id,
        order_id=order_id,
        rating=rating_value,
        comment=clean_comment or None,
        author_name=author_name(user),
        status="pending",
    )
    db.session.add(review)
    db.session.commit()
    return review
