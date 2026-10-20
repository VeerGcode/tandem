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
    is_signed_up = current_user.is_authenticated and any(
        s.user_id == current_user.id for s in opp.signups
    )
    return render_template("opportunity_detail.html", opp=opp, is_signed_up=is_signed_up)


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
        if opp.start_time >= opp.end_time:
            flash("Start time must be before end time.")
            return render_template("opportunity_new.html", opp=opp)
        db.session.add(opp)
        db.session.commit()
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    return render_template("opportunity_new.html")


@opps_bp.route("/opportunities/<int:opp_id>/signup", methods=["POST"])
@login_required
def signup(opp_id):
    opp = db.get_or_404(Opportunity, opp_id)
    if current_user.is_host:
        flash("Hosts cannot sign up for events.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))
    if any(s.user_id == current_user.id for s in opp.signups):
        flash("You are already signed up for this event.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))
    if len(opp.signups) >= opp.spots_needed:
        flash("This event is already full.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))
    if opp.end_time < datetime.now():
        flash("This event has already ended.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    consent = "parent_consent" in request.form
    if current_user.is_minor and not consent:
        flash("Because you're under 18, a parent or guardian must approve this sign-up.")
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    new_signup = Signup(user_id=current_user.id, opportunity_id=opp.id, parent_consent=consent)
    db.session.add(new_signup)
    db.session.commit()
    flash("You're signed up!")
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