from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.")
            return render_template("register.html")

        birthdate = None
        if request.form.get("birthdate"):
            birthdate = datetime.strptime(request.form["birthdate"], "%Y-%m-%d").date()

        user = User(
            name=request.form["name"].strip(),
            email=email,
            role=request.form.get("role", "volunteer"),
            birthdate=birthdate,
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("opportunities.index"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"].strip().lower()).first()
        if user and user.check_password(request.form["password"]):
            login_user(user)
            # "next" brings people back to the QR scan page after they log in
            return redirect(request.args.get("next") or url_for("opportunities.index"))
        flash("Wrong email or password.")
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("opportunities.index"))
