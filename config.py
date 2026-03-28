import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "wolf-academy-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI", "sqlite:///" + os.path.join(BASE_DIR, "lms.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PASS_THRESHOLD = 70  # percentage required to pass a quiz

    # SMTP settings for email invites
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_SENDER = os.environ.get("SMTP_SENDER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

    # Base URL for generating links in emails
    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
