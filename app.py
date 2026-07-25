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
    app.url_map.strict_slashes = False

    # Initialize database with fallback for read-only serverless environments (Vercel)
    db_path = app.config.get('DATABASE_PATH', Config.DATABASE_PATH)
    try:
        db = Database(db_path)
        db.init_db()
    except Exception as e:
        tmp_db_path = '/tmp/database.db'
        db = Database(tmp_db_path)
        db.init_db()

    app.config['DB_INSTANCE'] = db

    # Load persistent system settings (e.g. SMTP config) from database into app.config
    try:
        saved_settings = db.get_all_settings()
        for key, val in saved_settings.items():
            if key == 'SMTP_PORT':
                app.config[key] = int(val) if val and val.isdigit() else 587
            elif key == 'SMTP_USE_TLS':
                app.config[key] = val.lower() == 'true'
            else:
                app.config[key] = val
    except Exception:
        pass

    # Create default admin if none exists
    try:
        if not db.admin_exists():
            db.create_admin(Config.DEFAULT_ADMIN_USERNAME, Config.DEFAULT_ADMIN_PASSWORD, Config.DEFAULT_ADMIN_EMAIL)
            print(f"[INFO] Default admin created: {Config.DEFAULT_ADMIN_USERNAME} ({Config.DEFAULT_ADMIN_EMAIL})")
    except Exception:
        pass

    # Ensure required directories exist
    try:
        os.makedirs(app.config.get('FACE_ENCODING_DIR', 'data/face_encodings'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
    except Exception:
        pass

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app


# Top-level application export for WSGI deployment servers (Vercel, Render, Gunicorn, AWS)
app = create_app()
application = app
handler = app


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Facial Recognition Login System")
    print("  with Gesture-Based Authentication")
    print("=" * 60)
    print(f"  Server: http://127.0.0.1:5000")
    print(f"  Admin:  http://127.0.0.1:5000/admin/login")
    print("=" * 60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
