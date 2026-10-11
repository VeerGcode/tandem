import os


class Config:
    # Change this before deploying. Set it as an environment variable on your host.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # Relative sqlite paths go in the "instance" folder automatically.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///volunteer.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
