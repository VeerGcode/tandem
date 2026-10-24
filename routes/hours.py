from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import HourRequest, Opportunity

hours_bp = Blueprint("hours", __name__)


@hours_bp.route("/scan")
@login_required
def scan_page():
    """The Scan tab: opens the camera and reads the event QR code."""
    if current_user.is_host:
        flash("Host accounts don't scan. Show your event's QR code instead.")
        return redirect(url_for("hours.host_dashboard"))
    return render_template("scan.html")


@hours_bp.route("/scan/<token>")
@login_required
def scan(token):
    """One scan when leaving the event creates a pending hours request."""
    opp = Opportunity.query.filter_by(qr_token=token).first_or_404()

    if current_user.is_host:
        flash("Host accounts can't scan for hours.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    if not any(s.user_id == current_user.id for s in opp.signups):
        flash("Sign up for this event before submitting hours.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    # Scans work from the event start until 2 hours after it ends
    now = datetime.now()
    if now < opp.start_time or now > opp.end_time + timedelta(hours=2):
        flash("Hours can only be submitted during the event or shortly after it ends.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    existing = HourRequest.query.filter_by(
        user_id=current_user.id, opportunity_id=opp.id
    ).first()
    if existing:
        flash("You've already submitted hours for this event.")
        return redirect(url_for("hours.my_hours"))

    # checked_in_at now simply records when the scan happened
    db.session.add(HourRequest(user_id=current_user.id, opportunity_id=opp.id, checked_in_at=now))
    db.session.commit()
    flash("Hours submitted! Your host will review them.")
    return redirect(url_for("hours.my_hours"))


@hours_bp.route("/my-hours")
@login_required
def my_hours():
    requests = (
        HourRequest.query.filter_by(user_id=current_user.id)
        .order_by(HourRequest.checked_in_at.desc())
        .all()
    )
    return render_template("my_hours.html", requests=requests)


@hours_bp.route("/host/dashboard")
@login_required
def host_dashboard():
    if not current_user.is_host:
        abort(403)

    # Pending requests for events that belong to this host
    pending = (
        HourRequest.query.join(Opportunity)
        .filter(Opportunity.host_id == current_user.id, HourRequest.status == "pending")
        .order_by(HourRequest.checked_in_at)
        .all()
    )
    my_opps = (
        Opportunity.query.filter_by(host_id=current_user.id)
        .order_by(Opportunity.start_time.desc())
        .all()
    )
    return render_template("host_dashboard.html", pending=pending, my_opps=my_opps)


@hours_bp.route("/host/requests/<int:req_id>/approve", methods=["POST"])
@login_required
def approve(req_id):
    hour_request = db.get_or_404(HourRequest, req_id)
    if hour_request.opportunity.host_id != current_user.id:
        abort(403)

    if hour_request.status != "pending":
        flash("That request has already been reviewed.")
        return redirect(url_for("hours.host_dashboard"))

    # The host can edit the hours; fall back to the shift length if the box is blank
    try:
        hours = float(request.form.get("hours") or hour_request.opportunity.shift_hours)
    except ValueError:
        flash("Hours must be a number.")
        return redirect(url_for("hours.host_dashboard"))

    if hours < 0 or hours > 24:
        flash("Hours must be between 0 and 24.")
        return redirect(url_for("hours.host_dashboard"))

    hour_request.status = "approved"
    hour_request.hours = hours
    hour_request.reviewed_at = datetime.now()
    db.session.commit()
    flash(f"Approved {hours:g} hours for {hour_request.user.name}.")
    return redirect(url_for("hours.host_dashboard"))


@hours_bp.route("/host/requests/<int:req_id>/deny", methods=["POST"])
@login_required
def deny(req_id):
    hour_request = db.get_or_404(HourRequest, req_id)
    if hour_request.opportunity.host_id != current_user.id:
        abort(403)

    if hour_request.status != "pending":
        flash("That request has already been reviewed.")
        return redirect(url_for("hours.host_dashboard"))

    hour_request.status = "denied"
    hour_request.host_note = request.form.get("host_note", "").strip() or None
    hour_request.reviewed_at = datetime.now()
    db.session.commit()
    flash(f"Denied the request from {hour_request.user.name}.")
    return redirect(url_for("hours.host_dashboard"))