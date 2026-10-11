from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import HourRequest, Opportunity

hours_bp = Blueprint("hours", __name__)


@hours_bp.route("/scan/<token>")
@login_required
def scan(token):
    """
    Opened when a volunteer scans the QR code with their phone camera.
    The QR code is just a link to this page, so no JavaScript scanner is needed.
    If they aren't logged in, login_required sends them to login and then back here.
    """
    opp = Opportunity.query.filter_by(qr_token=token).first_or_404()

    # TODO: 1. Hosts shouldn't be able to scan (flash a message and redirect)
    # TODO: 2. Look up an existing HourRequest for this user + opportunity
    # TODO: 3. If none exists, this is a CHECK-IN: create a pending HourRequest
    # TODO: 4. If one exists and checked_out_at is empty, this is a CHECK-OUT: set checked_out_at
    # TODO: 5. If it is already checked out, flash "already submitted"
    # TODO: 6. Optional: only allow scans within a window around the event time
    flash("Scanning is not built yet.")
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
    my_opps = Opportunity.query.filter_by(host_id=current_user.id).order_by(Opportunity.start_time.desc()).all()
    return render_template("host_dashboard.html", pending=pending, my_opps=my_opps)


@hours_bp.route("/host/requests/<int:req_id>/approve", methods=["POST"])
@login_required
def approve(req_id):
    hour_request = db.get_or_404(HourRequest, req_id)
    if hour_request.opportunity.host_id != current_user.id:
        abort(403)

    # TODO: 1. Read the hours from request.form["hours"] (default to the time between
    #          check-in and check-out, or the shift length, if the host leaves it unchanged)
    # TODO: 2. Set status = "approved", hours, reviewed_at = datetime.utcnow()
    # TODO: 3. Commit and flash a confirmation
    flash("Approve is not built yet.")
    return redirect(url_for("hours.host_dashboard"))


@hours_bp.route("/host/requests/<int:req_id>/deny", methods=["POST"])
@login_required
def deny(req_id):
    hour_request = db.get_or_404(HourRequest, req_id)
    if hour_request.opportunity.host_id != current_user.id:
        abort(403)

    # TODO: set status = "denied", save an optional host_note, commit, flash
    flash("Deny is not built yet.")
    return redirect(url_for("hours.host_dashboard"))
