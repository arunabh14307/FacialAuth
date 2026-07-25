"""
Admin Routes — Admin login, dashboard, user management, and log viewing.
"""

import time
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from backend.modules.otp_service import generate_otp, send_otp_email

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')


def get_db():
    """Get database instance from app config."""
    return current_app.config['DB_INSTANCE']


def mask_email(email):
    """Mask email for display, e.g. ad***@domain.com."""
    if not email or '@' not in email:
        return 'registered email'
    name, domain = email.split('@', 1)
    if len(name) <= 2:
        masked_name = name[0] + '*'
    else:
        masked_name = name[:2] + '*' * (len(name) - 2)
    return f"{masked_name}@{domain}"


def admin_required(f):
    """Decorator to require admin login."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin login required.', 'warning')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)

    return decorated


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        admin = db.verify_admin(username, password)

        if admin:
            session['admin_logged_in'] = True
            session['admin_username'] = admin['username']
            flash('Welcome back, Admin!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Invalid credentials.', 'error')

    return render_template('admin/login.html')


@admin_bp.route('/verify-credentials', methods=['POST'])
def verify_credentials():
    """AJAX endpoint to verify admin credentials and send OTP email."""
    data = request.get_json(silent=True) or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400

    db = get_db()
    admin = db.verify_admin(username, password)

    if not admin:
        return jsonify({'success': False, 'message': 'Invalid admin credentials.'}), 401

    admin_email = admin.get('email') or current_app.config.get('DEFAULT_ADMIN_EMAIL', 'admin@faceguard.local')
    otp_code = generate_otp(6)

    # Store pending OTP in session
    session['pending_admin_otp'] = {
        'otp': otp_code,
        'username': admin['username'],
        'email': admin_email,
        'created_at': time.time()
    }

    # Refresh latest persistent system settings into config
    try:
        saved_settings = db.get_all_settings()
        for key, val in saved_settings.items():
            if key == 'SMTP_PORT':
                current_app.config[key] = int(val) if val and val.isdigit() else 587
            elif key == 'SMTP_USE_TLS':
                current_app.config[key] = val.lower() == 'true'
            else:
                current_app.config[key] = val
    except Exception:
        pass

    # Dispatch OTP email
    success, is_fallback, msg = send_otp_email(admin_email, otp_code, current_app.config)

    display_message = f"OTP sent to {mask_email(admin_email)}" if not is_fallback else f"OTP Status: {msg}"

    return jsonify({
        'success': True,
        'message': display_message,
        'masked_email': mask_email(admin_email),
        'is_fallback': is_fallback,
        'status_msg': msg
    })


@admin_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """AJAX endpoint to verify OTP and log in admin."""
    data = request.get_json(silent=True) or request.form
    submitted_otp = data.get('otp', '').strip()

    pending = session.get('pending_admin_otp')
    if not pending:
        return jsonify({'success': False, 'message': 'No pending OTP session found. Please re-authenticate.'}), 400

    expiry = current_app.config.get('OTP_EXPIRY_SECONDS', 300)
    if time.time() - pending.get('created_at', 0) > expiry:
        session.pop('pending_admin_otp', None)
        return jsonify({'success': False, 'message': 'OTP has expired. Please request a new one.'}), 400

    if submitted_otp != pending.get('otp'):
        return jsonify({'success': False, 'message': 'Invalid OTP code. Please try again.'}), 400

    # OTP Verified Successfully -> Authenticate Admin Session
    session['admin_logged_in'] = True
    session['admin_username'] = pending.get('username')
    session.pop('pending_admin_otp', None)

    return jsonify({
        'success': True,
        'message': 'OTP verified successfully!',
        'redirect_url': url_for('admin.admin_dashboard')
    })



@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with statistics."""
    db = get_db()

    stats = {
        'total_users': db.get_user_count(),
        'today_logins': db.get_today_login_count(),
        'today_success': db.get_today_success_count(),
        'success_rate': 0
    }

    if stats['today_logins'] > 0:
        stats['success_rate'] = round((stats['today_success'] / stats['today_logins']) * 100, 1)

    recent_logs = db.get_login_logs(limit=10)

    return render_template('admin/dashboard.html', stats=stats, logs=recent_logs)


@admin_bp.route('/users')
@admin_required
def admin_users():
    """User management page."""
    db = get_db()
    users = db.get_all_users()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user."""
    db = get_db()
    user = db.get_user_by_id(user_id)

    if user:
        # Delete face image file
        import os
        if user.get('face_image_path') and os.path.exists(user['face_image_path']):
            try:
                os.remove(user['face_image_path'])
            except OSError:
                pass

        db.delete_user(user_id)
        flash(f'User "{user["name"]}" has been deleted.', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    """Toggle user active status."""
    db = get_db()
    db.toggle_user_status(user_id)
    flash('User status updated.', 'success')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/logs')
@admin_required
def admin_logs():
    """View login logs."""
    db = get_db()

    # Get filter parameters
    status_filter = request.args.get('status', None)
    user_filter = request.args.get('user_id', None)
    limit = request.args.get('limit', 50, type=int)

    logs = db.get_login_logs(
        limit=limit,
        user_id=int(user_filter) if user_filter else None,
        status=status_filter if status_filter else None
    )

    users = db.get_all_users()

    return render_template('admin/logs.html', logs=logs, users=users,
                           current_status=status_filter, current_user=user_filter)


@admin_bp.route('/logout')
def admin_logout():
    """Admin logout."""
    next_dest = request.args.get('next', 'index')
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Admin logged out successfully.', 'info')
    if next_dest == 'admin':
        return redirect(url_for('admin.admin_login'))
    elif next_dest == 'user':
        return redirect(url_for('auth.login'))
    return redirect(url_for('auth.index'))


@admin_bp.route('/settings')
@admin_required
def admin_settings():
    """Admin settings page: Manage admin email, username, password, SMTP server & view facial access summary."""
    db = get_db()
    current_username = session.get('admin_username', 'admin')
    admin_info = db.get_admin_by_username(current_username)

    if not admin_info:
        # Fallback if session admin username not found
        admin_info = {
            'admin_id': 1,
            'username': current_username,
            'email': current_app.config.get('DEFAULT_ADMIN_EMAIL', 'admin@faceguard.local')
        }

    smtp_config = {
        'server': current_app.config.get('SMTP_SERVER', ''),
        'port': current_app.config.get('SMTP_PORT', 587),
        'username': current_app.config.get('SMTP_USERNAME', ''),
        'password': current_app.config.get('SMTP_PASSWORD', ''),
        'use_tls': current_app.config.get('SMTP_USE_TLS', True),
        'from_address': current_app.config.get('MAIL_FROM_ADDRESS', '')
    }

    facial_summary = db.get_facial_access_summary()

    return render_template(
        'admin/settings.html',
        admin=admin_info,
        smtp=smtp_config,
        summary=facial_summary
    )


@admin_bp.route('/settings/update-profile', methods=['POST'])
@admin_required
def update_profile():
    """Update admin username ID and registered email."""
    db = get_db()
    current_username = session.get('admin_username', 'admin')
    admin_info = db.get_admin_by_username(current_username)

    if not admin_info:
        flash('Admin account session invalid. Please log in again.', 'error')
        return redirect(url_for('admin.admin_settings'))

    new_username = request.form.get('username', '').strip()
    new_email = request.form.get('email', '').strip()

    if not new_username:
        flash('Username cannot be empty.', 'error')
        return redirect(url_for('admin.admin_settings'))

    if not new_email or '@' not in new_email:
        flash('Please provide a valid email address.', 'error')
        return redirect(url_for('admin.admin_settings'))

    success, message = db.update_admin_profile(admin_info['admin_id'], new_username, new_email)

    if success:
        session['admin_username'] = new_username
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('admin.admin_settings'))


@admin_bp.route('/settings/update-smtp', methods=['POST'])
@admin_required
def update_smtp():
    """Update SMTP email server settings for sending real OTP emails."""
    db = get_db()
    smtp_server = request.form.get('smtp_server', '').strip()
    if '@' in smtp_server:
        smtp_server = smtp_server.split('@')[-1]
    smtp_port = request.form.get('smtp_port', '587').strip()
    smtp_username = request.form.get('smtp_username', '').strip()
    smtp_password = request.form.get('smtp_password', '').strip()
    smtp_use_tls = 'smtp_use_tls' in request.form
    mail_from = request.form.get('mail_from_address', '').strip()

    # Save to database system_settings
    db.update_setting('SMTP_SERVER', smtp_server)
    db.update_setting('SMTP_PORT', smtp_port)
    db.update_setting('SMTP_USERNAME', smtp_username)
    db.update_setting('SMTP_PASSWORD', smtp_password)
    db.update_setting('SMTP_USE_TLS', 'true' if smtp_use_tls else 'false')
    db.update_setting('MAIL_FROM_ADDRESS', mail_from)

    # Update current app config live
    current_app.config['SMTP_SERVER'] = smtp_server
    current_app.config['SMTP_PORT'] = int(smtp_port) if smtp_port.isdigit() else 587
    current_app.config['SMTP_USERNAME'] = smtp_username
    current_app.config['SMTP_PASSWORD'] = smtp_password
    current_app.config['SMTP_USE_TLS'] = smtp_use_tls
    current_app.config['MAIL_FROM_ADDRESS'] = mail_from or smtp_username

    flash('SMTP Email Server configuration updated successfully!', 'success')
    return redirect(url_for('admin.admin_settings'))


@admin_bp.route('/settings/test-email', methods=['POST'])
@admin_required
def test_email_dispatch():
    """Send a test email to the registered admin email to verify SMTP settings."""
    db = get_db()
    current_username = session.get('admin_username', 'admin')
    admin_info = db.get_admin_by_username(current_username)

    if not admin_info or not admin_info.get('email'):
        return jsonify({'success': False, 'message': 'No registered email found for admin account.'}), 400

    target_email = admin_info['email']
    from backend.modules.otp_service import generate_otp, send_otp_email

    test_otp = generate_otp(6)
    success, is_fallback, msg = send_otp_email(target_email, test_otp, current_app.config)

    if not is_fallback:
        return jsonify({'success': True, 'message': f'Test email dispatched successfully to {target_email}!'})
    else:
        return jsonify({'success': False, 'message': f'Email dispatch fallback: {msg}'}), 400


@admin_bp.route('/settings/change-password', methods=['POST'])
@admin_required
def change_password():
    """Change admin password."""
    db = get_db()
    current_username = session.get('admin_username', 'admin')
    admin_info = db.get_admin_by_username(current_username)

    if not admin_info:
        flash('Admin account session invalid. Please log in again.', 'error')
        return redirect(url_for('admin.admin_settings'))

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Verify current password
    from werkzeug.security import check_password_hash
    if not check_password_hash(admin_info['password_hash'], current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('admin.admin_settings'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('admin.admin_settings'))

    if new_password != confirm_password:
        flash('New password and confirmation do not match.', 'error')
        return redirect(url_for('admin.admin_settings'))

    success, message = db.update_admin_password(admin_info['admin_id'], new_password)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('admin.admin_settings'))



