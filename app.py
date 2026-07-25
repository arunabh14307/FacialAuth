"""
Facial Recognition Login Access System with Gesture-Based Authentication
Main Flask Application Entry Point
"""

import os
from flask import Flask
from backend.config import Config
from backend.models.database import Database
from user.routes import auth_bp
from admin.routes import admin_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder='user/templates')

    # Load configuration
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    app.config['FACE_ENCODING_DIR'] = Config.FACE_ENCODING_DIR
    app.config['FACE_RECOGNITION_TOLERANCE'] = Config.FACE_RECOGNITION_TOLERANCE

    # Initialize database
    db = Database(Config.DATABASE_PATH)
    db.init_db()
    app.config['DB_INSTANCE'] = db

    # Load persistent system settings (e.g. SMTP config) from database into app.config
    saved_settings = db.get_all_settings()
    for key, val in saved_settings.items():
        if key == 'SMTP_PORT':
            app.config[key] = int(val) if val and val.isdigit() else 587
        elif key == 'SMTP_USE_TLS':
            app.config[key] = val.lower() == 'true'
        else:
            app.config[key] = val

    # Create default admin if none exists
    if not db.admin_exists():
        db.create_admin(Config.DEFAULT_ADMIN_USERNAME, Config.DEFAULT_ADMIN_PASSWORD, Config.DEFAULT_ADMIN_EMAIL)
        print(f"[INFO] Default admin created: {Config.DEFAULT_ADMIN_USERNAME} ({Config.DEFAULT_ADMIN_EMAIL})")

    # Ensure required directories exist
    os.makedirs(Config.FACE_ENCODING_DIR, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    print("\n" + "=" * 60)
    print("  Facial Recognition Login System")
    print("  with Gesture-Based Authentication")
    print("=" * 60)
    print(f"  Server: http://127.0.0.1:5000")
    print(f"  Admin:  http://127.0.0.1:5000/admin/login")
    print("=" * 60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
