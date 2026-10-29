"""Human customer support cases; AI chat transcripts are never stored here."""

from datetime import UTC, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import SupportConversation, SupportMessage
from ..security import admin_required, current_session_user, customer_required
from ..services.notifications import notify

support_bp = Blueprint("support", __name__)
_CATEGORIES = {"order", "delivery", "returns", "account", "product", "other"}
_STAFF_ROLES = {"admin", "super_admin", "support"}


def _case_or_404(case_id, *, owner_id=None):
    statement = select(SupportConversation).options(
        selectinload(SupportConversation.messages)
    ).where(SupportConversation.id == case_id)
    if owner_id is not None:
        statement = statement.where(SupportConversation.user_id == owner_id)
    case = db.session.scalar(statement)
    if case is None:
        abort(404)
    return case


@support_bp.route("/support", methods=["GET", "POST"])
@customer_required
def customer_cases():
    user = current_session_user("customer")
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        body = request.form.get("message", "").strip()
        category = request.form.get("category", "other")
        if not 3 <= len(subject) <= 160 or not 1 <= len(body) <= 5000 or category not in _CATEGORIES:
            flash(gettext("Add a short subject, a message under 5,000 characters, and a valid topic."), "error")
        else:
            now = datetime.now(UTC)
            case = SupportConversation(user_id=user.id, subject=subject,
                                      category=category, status="open",
                                      created_at=now, updated_at=now)
            case.messages.append(SupportMessage(sender_user_id=user.id,
                                                sender_role="customer", body=body,
                                                created_at=now))
            db.session.add(case)
            db.session.commit()
            flash(gettext("Your support request was sent to the NexHaat team."), "success")
            return redirect(url_for("support.customer_case", case_id=case.id))
    cases = db.session.scalars(
        select(SupportConversation).where(SupportConversation.user_id == user.id)
        .order_by(SupportConversation.updated_at.desc()).limit(100)
    ).all()
    return render_template("support/customer.html", cases=cases,
                           categories=sorted(_CATEGORIES))


@support_bp.get("/support/<int:case_id>")
@customer_required
def customer_case(case_id):
    user = current_session_user("customer")
    case = _case_or_404(case_id, owner_id=user.id)
    return render_template("support/case.html", case=case, staff_view=False)


@support_bp.post("/support/<int:case_id>/reply")
def reply(case_id):
    user = current_session_user()
    if user is None:
        abort(403)
    is_staff = user.role in _STAFF_ROLES
    if not is_staff and user.role != "customer":
        abort(403)
    case = _case_or_404(case_id, owner_id=None if is_staff else user.id)
    body = request.form.get("message", "").strip()
    if not 1 <= len(body) <= 5000:
        flash(gettext("Write a reply under 5,000 characters."), "error")
    elif case.status == "closed" and not is_staff:
        flash(gettext("This case is closed. Start a new support request if you still need help."), "error")
    else:
        now = datetime.now(UTC)
        case.messages.append(SupportMessage(sender_user_id=user.id,
                                            sender_role="staff" if is_staff else "customer",
                                            body=body, created_at=now))
        case.status = request.form.get("status", "pending") if is_staff else "open"
        if case.status not in {"open", "pending", "closed"}:
            abort(400)
        case.updated_at = now
        if is_staff and case.user_id:
            notify(case.user_id, gettext("The NexHaat team replied to support request %(subject)s.", subject=case.subject[:80]),
                   type="system", link=url_for("support.customer_case", case_id=case.id))
        db.session.commit()
        flash(gettext("Your reply was sent."), "success")
    if is_staff:
        return redirect(url_for("support.staff_case", case_id=case.id))
    return redirect(url_for("support.customer_case", case_id=case.id))


@support_bp.get("/admin/support")
@admin_required
def staff_queue():
    cases = db.session.scalars(
        select(SupportConversation).options(selectinload(SupportConversation.messages))
        .where(SupportConversation.status.in_(("open", "pending")))
        .order_by(SupportConversation.updated_at.asc()).limit(100)
    ).all()
    return render_template("support/staff_queue.html", cases=cases)


@support_bp.get("/admin/support/<int:case_id>")
@admin_required
def staff_case(case_id):
    case = _case_or_404(case_id)
    return render_template("support/case.html", case=case, staff_view=True)
