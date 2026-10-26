import os


class Config:
    # Set SECRET_KEY as an environment variable on your host. It signs login sessions,
    # so anyone who knows it can forge a login. The fallback is for local testing only.
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-change-me"

    # Relative sqlite paths go in the "instance" folder automatically.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///volunteer.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Comma-separated emails that can review host applications, e.g. "me@example.com"
    ADMIN_EMAILS = [
        e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()
    ]