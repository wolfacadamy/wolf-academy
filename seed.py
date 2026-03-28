"""
Seed script — run once to create the database and default admin user.

Usage:
    python seed.py
"""

from app import create_app
from models import db, User


def seed():
    app = create_app()

    with app.app_context():
        db.create_all()

        # Check if admin already exists
        if User.query.filter_by(username="admin").first():
            print("[OK] Admin user already exists. Skipping seed.")
            return

        admin = User(
            username="admin",
            email="admin@wolfacademy.com",
            role="admin",
        )
        admin.set_password("admin123")

        db.session.add(admin)
        db.session.commit()
        print("[OK] Database created successfully.")
        print("[OK] Default admin user created:")
        print("    Username: admin")
        print("    Password: admin123")


if __name__ == "__main__":
    seed()
