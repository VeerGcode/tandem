import csv
import io
from datetime import timedelta

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import HourRequest, Opportunity
from utils import local_now

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
    now = local_now()
    if now < opp.start_time or now > opp.end_time + timedelta(hours=2):
        flash("Hours can only be submitted during the event or shortly after it ends.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    existing = HourRequest.query.filter_by(
        user_id=current_user.id, opportunity_id=opp.id
    ).first()
    if existing:
        flash("You've already submitted hours for this event.")
        return redirect(url_for("hours.my_hours"))

    # checked_in_at simply records when the scan happened
    db.session.add(HourRequest(user_id=current_user.id, opportunity_id=opp.id, checked_in_at=now))
    db.session.commit()
    flash("Hours submitted! Your host will review them.")
    return redirect(url_for("hours.my_hours"))


@hours_bp.route("/my-hours")
@login_required
def my_hours():
    q = request.args.get("q", "").strip()
    query = HourRequest.query.join(Opportunity).filter(HourRequest.user_id == current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Opportunity.title.ilike(like),
            Opportunity.location.ilike(like),
            HourRequest.status.ilike(like),
        ))
    requests = query.order_by(HourRequest.checked_in_at.desc()).all()
    return render_template("my_hours.html", requests=requests, q=q)


def _safe_cell(value):
    """Stops spreadsheet programs from running event titles that start with = + - @ as formulas."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


@hours_bp.route("/my-hours/export.csv")
@login_required
def export_hours():
    approved = (
        HourRequest.query.filter_by(user_id=current_user.id, status="approved")
        .order_by(HourRequest.checked_in_at)
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Volunteer", _safe_cell(current_user.name)])
    writer.writerow([])
    writer.writerow(["Date", "Event", "Host", "Location", "Hours", "Approved on"])
    total = 0
    for r in approved:
        total += r.hours or 0
        writer.writerow([
            r.opportunity.start_time.strftime("%Y-%m-%d"),
            _safe_cell(r.opportunity.title),
            _safe_cell(r.opportunity.host.name),
            _safe_cell(r.opportunity.location),
            f"{r.hours:g}",
            r.reviewed_at.strftime("%Y-%m-%d") if r.reviewed_at else "",
        ])
    writer.writerow([])
    writer.writerow(["Total approved hours", "", "", "", f"{total:g}", ""])
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=tandem-hours.csv"},
    )


@hours_bp.route("/host/dashboard")
@login_required
def host_dashboard():
    if not current_user.is_host:
        abort(403)

    base = HourRequest.query.join(Opportunity).filter(Opportunity.host_id == current_user.id)
    pending = base.filter(HourRequest.status == "pending").order_by(HourRequest.checked_in_at).all()
    reviewed = (
        base.filter(HourRequest.status != "pending")
        .order_by(HourRequest.reviewed_at.desc())
        .limit(10)
        .all()
    )
    my_opps = (
        Opportunity.query.filter_by(host_id=current_user.id)
        .order_by(Opportunity.start_time.desc())
        .all()
    )
    return render_template("host_dashboard.html", pending=pending, reviewed=reviewed, my_opps=my_opps)


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
    hour_request.reviewed_at = local_now()
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
    hour_request.reviewed_at = local_now()
    db.session.commit()
    flash(f"Denied the request from {hour_request.user.name}.")
    return redirect(url_for("hours.host_dashboard"))