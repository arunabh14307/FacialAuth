"""
RESTful API Module — OpenAPI/Swagger Spec, Public & Authenticated Endpoints.
"""

from flask import Blueprint, jsonify, request, current_app
from backend.modules.security import sanitize_input
import time

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def get_db():
    """Get DB instance from app config."""
    return current_app.config['DB_INSTANCE']


@api_bp.route('/health', methods=['GET'])
def health_check():
    """System health check endpoint."""
    db = get_db()
    db_ok = True
    try:
        db.get_user_count()
    except Exception:
        db_ok = False

    return jsonify({
        'status': 'healthy' if db_ok else 'degraded',
        'timestamp': time.time(),
        'database_connected': db_ok,
        'version': '2.0.0-enterprise'
    }), 200 if db_ok else 500


@api_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Get facial access analytics."""
    db = get_db()
    summary = db.get_facial_access_summary()
    return jsonify({
        'success': True,
        'data': summary
    })


@api_bp.route('/users', methods=['GET'])
def list_users_api():
    """List active users endpoint."""
    db = get_db()
    search = request.args.get('search', '').strip()
    limit = min(request.args.get('limit', 50, type=int), 100)
    users = db.get_all_users(search_term=search, limit=limit)
    return jsonify({
        'success': True,
        'count': len(users),
        'users': users
    })


@api_bp.route('/docs', methods=['GET'])
def openapi_spec():
    """OpenAPI 3.0 Specification."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "FaceGuard Enterprise Authentication API",
            "version": "2.0.0",
            "description": "RESTful API for Facial Authentication, Liveness Verification, and Access Management."
        },
        "paths": {
            "/api/v1/health": {
                "get": {
                    "summary": "Check system health status",
                    "responses": {"200": {"description": "System operational"}}
                }
            },
            "/api/v1/analytics": {
                "get": {
                    "summary": "Get facial recognition statistics",
                    "responses": {"200": {"description": "Analytics payload"}}
                }
            },
            "/api/v1/users": {
                "get": {
                    "summary": "Fetch registered user directory",
                    "responses": {"200": {"description": "User list"}}
                }
            }
        }
    }
    return jsonify(spec)
