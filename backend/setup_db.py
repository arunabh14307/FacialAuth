"""
Database Setup Script — Initializes the database and creates required directories.
Run this script once before starting the application.
"""

import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from models.database import Database


def setup():
    """Initialize database and directories."""
    print("=" * 50)
    print("  Database Setup")
    print("=" * 50)

    # Create directories
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    os.makedirs(Config.FACE_ENCODING_DIR, exist_ok=True)
    print(f"[OK] Created data directories")

    # Initialize database
    db = Database(Config.DATABASE_PATH)
    db.init_db()
    print(f"[OK] Database initialized at: {Config.DATABASE_PATH}")

    # Create default admin
    if not db.admin_exists():
        db.create_admin(Config.DEFAULT_ADMIN_USERNAME, Config.DEFAULT_ADMIN_PASSWORD)
        print(f"[OK] Default admin created:")
        print(f"     Username: {Config.DEFAULT_ADMIN_USERNAME}")
        print(f"     Password: {Config.DEFAULT_ADMIN_PASSWORD}")
    else:
        print(f"[OK] Admin account already exists")

    print("=" * 50)
    print("  Setup complete! Run 'python app.py' to start.")
    print("=" * 50)


if __name__ == '__main__':
    setup()
