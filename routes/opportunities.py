import io
from datetime import datetime

import qrcode
from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Opportunity, Signup

opps_bp = Blueprint("opportunities", __name__)


@opps_bp.route("/")
def index():
    # Urgent first, then soonest. Past events are hidden.
    opportunities = (
        Opportunity.query.filter(Opportunity.end_time >= datetime.now())
        .order_by(Opportunity.is_urgent.desc(), Opportunity.start_time)
        .all()
    )
    return render_template("index.html", opportunities=opportunities)


@opps_bp.route("/opportunities/<int:opp_id>")
def detail(opp_id):
    opp = db.get_or_404(Opportunity, opp_id)
    return render_template("opportunity_detail.html", opp=opp)


@opps_bp.route("/opportunities/new", methods=["GET", "POST"])
@login_required
def new():
    if not current_user.is_host:
        abort(403)

    if request.method == "POST":
        fmt = "%Y-%m-%dT%H:%M"  # format used by <input type="datetime-local">
        opp = Opportunity(
            title=request.form["title"].strip(),
            description=request.form["description"].strip(),
            location=request.form["location"].strip(),
            start_time=datetime.strptime(request.form["start_time"], fmt),
            end_time=datetime.strptime(request.form["end_time"], fmt),
            spots_needed=int(request.form["spots_needed"]),
            is_urgent="is_urgent" in request.form,
            host_id=current_user.id,
        )
        # TODO: check that end_time is after start_time
        db.session.add(opp)
        db.session.commit()
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    return render_template("opportunity_new.html")


@opps_bp.route("/opportunities/<int:opp_id>/signup", methods=["POST"])
@login_required
def signup(opp_id):
    opp = db.get_or_404(Opportunity, opp_id)
    # TODO: 1. Block hosts from signing up
    # TODO: 2. Block duplicate signups (Signup has a unique constraint on user + opportunity)
    # TODO: 3. Block signups when the event is full (len(opp.signups) >= opp.spots_needed)
    # TODO: 4. If current_user.is_minor, require a parent_consent checkbox
    # TODO: 5. Create the Signup, commit, and flash a confirmation
    flash("Sign-up is not built yet.")
    return redirect(url_for("opportunities.detail", opp_id=opp.id))


@opps_bp.route("/opportunities/<int:opp_id>/qr.png")
@login_required
def qr_image(opp_id):
    """Shows the QR code image. Only the host who owns the event can see it."""
    opp = db.get_or_404(Opportunity, opp_id)
    if opp.host_id != current_user.id:
        abort(403)

    scan_url = url_for("hours.scan", token=opp.qr_token, _external=True)
    img = qrcode.make(scan_url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")
