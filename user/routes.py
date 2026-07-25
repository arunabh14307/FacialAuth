"""
Authentication Routes — Registration, Login, Dashboard, Logout.
"""

import os
import base64
import uuid
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from backend.modules.face_detection import detect_face, decode_base64_image
from backend.modules.face_recognition_mod import encode_face, match_face
from backend.modules.gesture_detection import detect_gesture, get_random_gesture, get_gesture_display_name, get_gesture_instruction

auth_bp = Blueprint('auth', __name__)


def get_db():
    """Get database instance from app config."""
    from flask import current_app
    return current_app.config['DB_INSTANCE']


@auth_bp.route('/')
def index():
    """Landing page."""
    return render_template('index.html')


@auth_bp.route('/register')
def register():
    """Registration page."""
    return render_template('register.html')


@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """
    Process user registration.
    Expects JSON: {name, email, image (base64)}
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    image_data = data.get('image', '')

    # Validate inputs
    if not name:
        return jsonify({'success': False, 'message': 'Name is required'}), 400
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400
    if not image_data:
        return jsonify({'success': False, 'message': 'Face image is required'}), 400

    # Check if email already exists
    db = get_db()
    if db.get_user_by_email(email):
        return jsonify({'success': False, 'message': 'Email already registered'}), 400

    # Decode the base64 image
    try:
        frame = decode_base64_image(image_data)
    except Exception as e:
        return jsonify({'success': False, 'message': 'Invalid image data'}), 400

    # Detect face
    success, face_locations, message = detect_face(frame)
    if not success:
        return jsonify({'success': False, 'message': message}), 400

    # Generate face encoding
    enc_success, encoding, enc_message = encode_face(frame)
    if not enc_success:
        return jsonify({'success': False, 'message': enc_message}), 400

    # Save face image
    from flask import current_app
    face_dir = current_app.config.get('FACE_ENCODING_DIR', 'data/face_encodings')
    os.makedirs(face_dir, exist_ok=True)

    image_filename = f"{uuid.uuid4().hex}.jpg"
    image_path = os.path.join(face_dir, image_filename)

    # Save cropped face image
    import cv2
    x, y, w_box, h_box = map(int, face_locations[0][:4])
    margin = 40
    h, w = frame.shape[:2]
    crop = frame[max(0, y-margin):min(h, y+h_box+margin), max(0, x-margin):min(w, x+w_box+margin)]
    cv2.imwrite(image_path, crop)

    # Add user to database
    user_id = db.add_user(name, email, encoding, image_path)
    if user_id is None:
        return jsonify({'success': False, 'message': 'Failed to register. Email may already exist.'}), 400

    return jsonify({
        'success': True,
        'message': f'Registration successful! Welcome, {name}.',
        'user_id': user_id
    })


@auth_bp.route('/login')
def login():
    """Login page."""
    return render_template('login.html')


@auth_bp.route('/api/login/detect', methods=['POST'])
def api_login_detect():
    """
    Step 1 of login: Detect and match face.
    Expects JSON: {image (base64)}
    Returns: matched user info + gesture challenge
    """
    data = request.get_json()
    if not data or not data.get('image'):
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    # Decode image
    try:
        frame = decode_base64_image(data['image'])
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid image data'}), 400

    # Detect face
    success, face_locations, message = detect_face(frame)
    if not success:
        return jsonify({'success': False, 'message': message}), 400

    # Encode detected face
    enc_success, encoding, enc_message = encode_face(frame)
    if not enc_success:
        return jsonify({'success': False, 'message': enc_message}), 400

    # Match against stored encodings
    db = get_db()
    stored_encodings = db.get_all_face_encodings()

    from flask import current_app
    tolerance = current_app.config.get('FACE_RECOGNITION_TOLERANCE', 0.6)
    matched, user_id, confidence, match_message = match_face(encoding, stored_encodings, tolerance)

    if not matched:
        # Log failed attempt
        db.log_login_attempt(None, 'Failed', None, None, request.remote_addr)
        return jsonify({'success': False, 'message': match_message}), 401

    # Face matched — generate gesture challenge
    gesture = get_random_gesture()
    session['login_user_id'] = user_id
    session['login_gesture'] = gesture
    session['login_confidence'] = confidence

    user = db.get_user_by_id(user_id)

    return jsonify({
        'success': True,
        'message': f'Face recognized! Hello, {user["name"]}.',
        'user_name': user['name'],
        'gesture': gesture,
        'gesture_display': get_gesture_display_name(gesture),
        'gesture_instruction': get_gesture_instruction(gesture),
        'confidence': round(confidence * 100, 1)
    })


@auth_bp.route('/api/login/gesture', methods=['POST'])
def api_login_gesture():
    """
    Step 2 of login: Verify gesture challenge.
    Expects JSON: {image (base64)}
    """
    # Check session
    user_id = session.get('login_user_id')
    target_gesture = session.get('login_gesture')

    if not user_id or not target_gesture:
        return jsonify({'success': False, 'message': 'Session expired. Please start login again.'}), 400

    data = request.get_json()
    if not data or not data.get('image'):
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    # Decode image
    try:
        frame = decode_base64_image(data['image'])
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid image data'}), 400

    # Detect gesture
    detected, confidence, message = detect_gesture(frame, target_gesture)

    db = get_db()

    if detected:
        # Gesture verified — grant access
        session['user_id'] = user_id
        session['logged_in'] = True

        # Clear login session data
        session.pop('login_user_id', None)
        session.pop('login_gesture', None)
        session.pop('login_confidence', None)

        # Log successful login
        db.log_login_attempt(user_id, 'Success', target_gesture, 'Verified', request.remote_addr)

        user = db.get_user_by_id(user_id)

        return jsonify({
            'success': True,
            'message': f'Authentication successful! Welcome, {user["name"]}.',
            'redirect': url_for('auth.dashboard')
        })
    else:
        # Gesture failed
        db.log_login_attempt(user_id, 'Failed', target_gesture, 'Failed', request.remote_addr)

        return jsonify({
            'success': False,
            'message': message,
            'gesture': target_gesture,
            'gesture_instruction': get_gesture_instruction(target_gesture)
        })


@auth_bp.route('/dashboard')
def dashboard():
    """Authenticated user dashboard."""
    if not session.get('logged_in'):
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    db = get_db()
    user = db.get_user_by_id(session['user_id'])

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # Get user's recent login logs
    logs = db.get_login_logs(limit=10, user_id=user['user_id'])

    return render_template('dashboard.html', user=user, logs=logs)


@auth_bp.route('/logout')
def logout():
    """Clear session and log out."""
    next_dest = request.args.get('next', 'index')
    session.clear()
    flash('You have been logged out.', 'info')
    if next_dest == 'admin':
        return redirect(url_for('admin.admin_login'))
    elif next_dest == 'user':
        return redirect(url_for('auth.login'))
    return redirect(url_for('auth.index'))

