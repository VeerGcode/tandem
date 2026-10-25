import secrets
from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="volunteer")  # "volunteer" or "host"
    birthdate = db.Column(db.Date, nullable=True)

    opportunities = db.relationship("Opportunity", backref="host", lazy=True)
    signups = db.relationship("Signup", backref="user", lazy=True)
    hour_requests = db.relationship("HourRequest", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_host(self):
        return self.role == "host"

    @property
    def is_minor(self):
        if not self.birthdate:
            return False
        today = date.today()
        age = today.year - self.birthdate.year - (
            (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
        )
        return age < 18

    def total_hours(self):
        """Only approved requests count. Calculated, never stored, so it can't go out of sync."""
        return sum(r.hours or 0 for r in self.hour_requests if r.status == "approved")


class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    spots_needed = db.Column(db.Integer, nullable=False, default=1)
    is_urgent = db.Column(db.Boolean, default=False)
    host_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # This token is what the QR code points to. It identifies the event,
    # so it does not need to rotate. The host's approval is the trust check.
    qr_token = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(16)
    )

    signups = db.relationship("Signup", backref="opportunity", lazy=True)
    hour_requests = db.relationship("HourRequest", backref="opportunity", lazy=True)

    @property
    def shift_hours(self):
        return round((self.end_time - self.start_time).total_seconds() / 3600, 2)


class Signup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunity.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    parent_consent = db.Column(db.Boolean, default=False)  # needed when the user is a minor

    __table_args__ = (db.UniqueConstraint("user_id", "opportunity_id"),)


class HourRequest(db.Model):
    """Created when a volunteer scans the QR code. The host approves or denies it."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunity.id"), nullable=False)

    checked_in_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    checked_out_at = db.Column(db.DateTime, nullable=True)  # set on the second scan

    status = db.Column(db.String(20), nullable=False, default="pending")  # pending/approved/denied
    hours = db.Column(db.Float, nullable=True)  # set by the host when approving (can be edited)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    host_note = db.Column(db.String(255), nullable=True)

    __table_args__ = (db.UniqueConstraint("user_id", "opportunity_id"),)
