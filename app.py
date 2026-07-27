"""
Facial Recognition Login Access System with Gesture-Based Authentication
Enterprise Main Flask Application Entry Point
"""

import os
from flask import Flask, jsonify, request, render_template
from backend.config import Config
from backend.models.database import Database
from backend.modules.security import apply_security_headers
from backend.modules.logger import logger, log_security_event
from user.routes import auth_bp
from admin.routes import admin_bp
from api.routes import api_bp


def create_app():
    """Create and configure the enterprise Flask application."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'user', 'templates')
    static_dir = os.path.join(base_dir, 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Load configuration
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    app.config['FACE_ENCODING_DIR'] = Config.FACE_ENCODING_DIR
    app.config['FACE_RECOGNITION_TOLERANCE'] = Config.FACE_RECOGNITION_TOLERANCE
    app.url_map.strict_slashes = False

    # Security Response Headers Middleware
    @app.after_request
    def security_headers_middleware(response):
        return apply_security_headers(response)

    # Initialize database with fallback for temporary environments
    db_path = app.config.get('DATABASE_PATH', Config.DATABASE_PATH)
    try:
        db = Database(db_path)
        db.init_db()
    except Exception as e:
        logger.warning(f"Primary DB failed, using temporary DB fallback: {e}")
        tmp_db_path = '/tmp/database.db'
        db = Database(tmp_db_path)
        db.init_db()

    app.config['DB_INSTANCE'] = db

    # Load persistent system settings from database into app.config
    try:
        saved_settings = db.get_all_settings()
        for key, val in saved_settings.items():
            if val is not None and str(val).strip() != '':
                if key == 'SMTP_PORT':
                    app.config[key] = int(val) if str(val).isdigit() else 587
                elif key == 'SMTP_USE_TLS':
                    app.config[key] = str(val).lower() == 'true'
                else:
                    app.config[key] = val
    except Exception as e:
        logger.error(f"Error loading system settings: {e}")

    # Seed default admin if none exists
    try:
        if not db.admin_exists():
            db.create_admin(Config.DEFAULT_ADMIN_USERNAME, Config.DEFAULT_ADMIN_PASSWORD, Config.DEFAULT_ADMIN_EMAIL)
            logger.info(f"Default admin initialized: {Config.DEFAULT_ADMIN_USERNAME}")
    except Exception as e:
        logger.error(f"Error seeding default admin: {e}")

    # Ensure required directories exist
    try:
        os.makedirs(app.config.get('FACE_ENCODING_DIR', 'data/face_encodings'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'data', 'logs'), exist_ok=True)
    except Exception:
        pass

    # Centralized Error Handlers
    @app.errorhandler(404)
    def handle_404(e):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'message': 'Requested resource not found.'}), 404
        return render_template('base.html', error_title="404 - Page Not Found", error_msg="The page you requested does not exist."), 404

    @app.errorhandler(429)
    def handle_429(e):
        log_security_event("RATE_LIMIT_EXCEEDED", f"Path: {request.path}", ip_address=request.remote_addr)
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'message': 'Too many requests. Please try again later.'}), 429
        return jsonify({'success': False, 'message': 'Rate limit exceeded. Please wait a moment.'}), 429

    @app.errorhandler(500)
    def handle_500(e):
        logger.error(f"Internal server error on {request.path}: {e}")
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'message': 'An internal server error occurred.'}), 500
        return render_template('base.html', error_title="500 - Server Error", error_msg="An unexpected error occurred. Our security team has been notified."), 500

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    return app


# Top-level application export for WSGI production servers
app = create_app()
application = app
handler = app


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  FaceGuard Enterprise Access System")
    print("  with Facial & Gesture Authentication")
    print("=" * 60)
    print(f"  Server: http://127.0.0.1:5000")
    print(f"  Admin:  http://127.0.0.1:5000/admin/login")
    print("=" * 60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
