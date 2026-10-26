from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import User
from utils import local_now

verification_bp = Blueprint("verification", __name__)


@verification_bp.route("/verify", methods=["GET", "POST"])
@login_required
def apply():
    """A host applies to be verified. Only verified hosts can post events."""
    if not current_user.is_host:
        flash("Only host accounts need to be verified.")
        return redirect(url_for("opportunities.index"))

    status = current_user.verification_status
    if status == "verified":
        flash("Your organization is already verified.")
        return redirect(url_for("hours.host_dashboard"))

    if request.method == "POST" and status != "pending":
        form = request.form
        org_name = form.get("org_name", "").strip()
        org_contact = form.get("org_contact", "").strip()
        org_description = form.get("org_description", "").strip()

        error = None
        if not org_name:
            error = "Enter your organization's name."
        elif not org_contact:
            error = "Enter a website, email, or phone number we can use to check."
        elif len(org_description) < 20:
            error = "Tell us a bit more about your organization (at least a sentence)."

        if error:
            flash(error)
            return render_template("verify.html", form=form)

        current_user.org_name = org_name[:150]
        current_user.org_contact = org_contact[:200]
        current_user.org_description = org_description[:2000]
        current_user.verification_status = "pending"
        db.session.commit()
        flash("Application sent. You can keep posting events while it's reviewed.")
        return redirect(url_for("hours.host_dashboard"))

    form = {
        "org_name": current_user.org_name or "",
        "org_contact": current_user.org_contact or "",
        "org_description": current_user.org_description or "",
    }
    return render_template("verify.html", form=form)


def _require_admin():
    if not current_user.is_admin:
        abort(403)


@verification_bp.route("/admin/hosts")
@login_required
def admin_hosts():
    _require_admin()
    pending = User.query.filter_by(verification_status="pending").order_by(User.id).all()
    decided = (
        User.query.filter(User.verification_status.in_(["verified", "rejected"]))
        .order_by(User.verification_reviewed_at.desc())
        .limit(20)
        .all()
    )
    return render_template("admin_hosts.html", pending=pending, decided=decided)


@verification_bp.route("/admin/hosts/<int:user_id>/approve", methods=["POST"])
@login_required
def approve_host(user_id):
    _require_admin()
    host = db.get_or_404(User, user_id)
    if host.role != "host" or host.verification_status != "pending":
        flash("That application isn't waiting for review.")
        return redirect(url_for("verification.admin_hosts"))

    host.verification_status = "verified"
    host.verification_reviewed_at = local_now()
    db.session.commit()
    flash(f"Verified {host.org_name}.")
    return redirect(url_for("verification.admin_hosts"))


@verification_bp.route("/admin/hosts/<int:user_id>/reject", methods=["POST"])
@login_required
def reject_host(user_id):
    _require_admin()
    host = db.get_or_404(User, user_id)
    if host.role != "host" or host.verification_status != "pending":
        flash("That application isn't waiting for review.")
        return redirect(url_for("verification.admin_hosts"))

    host.verification_status = "rejected"
    host.verification_reviewed_at = local_now()
    db.session.commit()
    flash(f"Rejected the application from {host.org_name}.")
    return redirect(url_for("verification.admin_hosts"))