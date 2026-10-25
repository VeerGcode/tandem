import io
from datetime import datetime

import qrcode
from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Opportunity, Signup
from utils import local_now

opps_bp = Blueprint("opportunities", __name__)


@opps_bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    urgent_only = request.args.get("urgent") == "1"

    # Events that have ended are hidden
    query = Opportunity.query.filter(Opportunity.end_time >= local_now())
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Opportunity.title.ilike(like),
            Opportunity.description.ilike(like),
            Opportunity.location.ilike(like),
        ))
    if urgent_only:
        query = query.filter(Opportunity.is_urgent.is_(True))

    # Urgent first, then soonest
    opportunities = query.order_by(Opportunity.is_urgent.desc(), Opportunity.start_time).all()

    signed_up_ids = set()
    if current_user.is_authenticated and not current_user.is_host:
        signed_up_ids = {s.opportunity_id for s in current_user.signups}
    return render_template(
        "index.html",
        opportunities=opportunities,
        signed_up_ids=signed_up_ids,
        q=q,
        urgent_only=urgent_only,
    )


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
        form = request.form
        fmt = "%Y-%m-%dT%H:%M"  # format used by <input type="datetime-local">

        title = form.get("title", "").strip()
        description = form.get("description", "").strip()
        location = form.get("location", "").strip()

        error = None
        start_time = end_time = None
        spots_needed = 0
        try:
            start_time = datetime.strptime(form.get("start_time", ""), fmt)
            end_time = datetime.strptime(form.get("end_time", ""), fmt)
        except ValueError:
            error = "Enter a start and end time."
        try:
            spots_needed = int(form.get("spots_needed", ""))
        except ValueError:
            pass

        if not error:
            if not (title and description and location):
                error = "Fill in the title, description, and location."
            elif spots_needed < 1 or spots_needed > 500:
                error = "Volunteers needed must be between 1 and 500."
            elif start_time >= end_time:
                error = "The start time must be before the end time."
            elif end_time < local_now():
                error = "The end time is in the past."

        if error:
            flash(error)
            return render_template("opportunity_new.html", form=form)

        opp = Opportunity(
            title=title,
            description=description,
            location=location,
            start_time=start_time,
            end_time=end_time,
            spots_needed=spots_needed,
            is_urgent="is_urgent" in form,
            host_id=current_user.id,
        )
        db.session.add(opp)
        db.session.commit()
        return redirect(url_for("opportunities.detail", opp_id=opp.id))

    return render_template("opportunity_new.html", form={})


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
    if opp.end_time < local_now():
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