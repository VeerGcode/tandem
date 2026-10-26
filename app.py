from flask import Flask, render_template

from config import Config
from extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config["SECRET_KEY"] == "dev-only-change-me":
        app.logger.warning("Using the default SECRET_KEY. Set SECRET_KEY before deploying.")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.auth import auth_bp
    from routes.hours import hours_bp
    from routes.opportunities import opps_bp
    from routes.verification import verification_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(opps_bp)
    app.register_blueprint(hours_bp)
    app.register_blueprint(verification_bp)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="You don't have access to that page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="We couldn't find that page."), 404

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)