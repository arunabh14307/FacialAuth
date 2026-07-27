"""
Database module — SQLite operations for users, login logs, and admin accounts.
"""

import sqlite3
import os
import pickle
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class Database:
    """SQLite database manager."""

    def __init__(self, db_path):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception:
                pass

    def get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                face_encoding BLOB NOT NULL,
                face_image_path VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # Login logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) NOT NULL,
                gesture_type VARCHAR(50),
                gesture_result VARCHAR(20),
                ip_address VARCHAR(45),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        ''')

        # Admin table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100),
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Auto-migrate email column for existing admins table if missing
        try:
            cursor.execute('ALTER TABLE admins ADD COLUMN email VARCHAR(100)')
        except sqlite3.OperationalError:
            pass  # Column already exists

        # System settings table (for SMTP host, port, username, password, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value TEXT
            )
        ''')

        # Seed default admin user ONLY if no admin accounts exist
        from backend.config import Config
        from werkzeug.security import generate_password_hash

        cursor.execute("SELECT COUNT(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            pwd_hash = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)
            default_email = Config.DEFAULT_ADMIN_EMAIL or 'admin@faceguard.local'
            cursor.execute(
                'INSERT INTO admins (username, password_hash, email) VALUES (?, ?, ?)',
                (Config.DEFAULT_ADMIN_USERNAME, pwd_hash, default_email)
            )

        # Seed initial system settings ONLY if key does not exist yet (INSERT OR IGNORE)
        initial_defaults = {
            'SMTP_SERVER': Config.SMTP_SERVER or 'smtp.gmail.com',
            'SMTP_PORT': str(Config.SMTP_PORT or '465'),
            'SMTP_USERNAME': Config.SMTP_USERNAME or '',
            'SMTP_PASSWORD': Config.SMTP_PASSWORD or '',
            'MAIL_FROM_ADDRESS': Config.MAIL_FROM_ADDRESS or '',
            'SMTP_USE_TLS': 'true' if Config.SMTP_USE_TLS else 'false'
        }
        for key, val in initial_defaults.items():
            cursor.execute(
                "INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
                (key, val)
            )

        conn.commit()
        conn.close()

    # ─── User Operations ──────────────────────────────

    def add_user(self, name, email, face_encoding, face_image_path=None):
        """Add a new user with their face encoding."""
        conn = self.get_connection()
        try:
            encoding_blob = pickle.dumps(face_encoding)
            conn.execute(
                '''INSERT INTO users (name, email, face_encoding, face_image_path)
                   VALUES (?, ?, ?, ?)''',
                (name, email, encoding_blob, face_image_path)
            )
            conn.commit()
            return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        except sqlite3.IntegrityError:
            return None  # Duplicate email
        finally:
            conn.close()

    def get_user_by_id(self, user_id):
        """Get user by ID."""
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_email(self, email):
        """Get user by email."""
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_all_users(self):
        """Get all active users."""
        conn = self.get_connection()
        users = conn.execute(
            'SELECT user_id, name, email, face_image_path, created_at, is_active FROM users ORDER BY created_at DESC'
        ).fetchall()
        conn.close()
        return [dict(u) for u in users]

    def get_all_face_encodings(self):
        """Get all face encodings as dict {user_id: encoding}."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT user_id, face_encoding FROM users WHERE is_active = 1'
        ).fetchall()
        conn.close()

        encodings = {}
        for row in rows:
            try:
                encodings[row['user_id']] = pickle.loads(row['face_encoding'])
            except Exception:
                continue
        return encodings

    def delete_user(self, user_id):
        """Delete a user by ID."""
        conn = self.get_connection()
        conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

    def toggle_user_status(self, user_id):
        """Toggle user active status."""
        conn = self.get_connection()
        conn.execute(
            'UPDATE users SET is_active = NOT is_active WHERE user_id = ?', (user_id,)
        )
        conn.commit()
        conn.close()

    def get_user_count(self):
        """Get total user count."""
        conn = self.get_connection()
        count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        conn.close()
        return count

    # ─── Login Log Operations ─────────────────────────

    def log_login_attempt(self, user_id, status, gesture_type=None, gesture_result=None, ip_address=None):
        """Log a login attempt."""
        conn = self.get_connection()
        conn.execute(
            '''INSERT INTO login_logs (user_id, status, gesture_type, gesture_result, ip_address)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, status, gesture_type, gesture_result, ip_address)
        )
        conn.commit()
        conn.close()

    def get_login_logs(self, limit=50, user_id=None, status=None):
        """Get login logs with optional filters."""
        conn = self.get_connection()
        query = '''
            SELECT l.*, u.name as user_name
            FROM login_logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            WHERE 1=1
        '''
        params = []

        if user_id:
            query += ' AND l.user_id = ?'
            params.append(user_id)
        if status:
            query += ' AND l.status = ?'
            params.append(status)

        query += ' ORDER BY l.login_time DESC LIMIT ?'
        params.append(limit)

        logs = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(log) for log in logs]

    def get_today_login_count(self):
        """Get today's login attempt count."""
        conn = self.get_connection()
        count = conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now')"
        ).fetchone()[0]
        conn.close()
        return count

    def get_today_success_count(self):
        """Get today's successful login count."""
        conn = self.get_connection()
        count = conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now') AND status = 'Success'"
        ).fetchone()[0]
        conn.close()
        return count

    # ─── Admin Operations ─────────────────────────────

    def create_admin(self, username, password, email=None):
        """Create an admin account."""
        conn = self.get_connection()
        try:
            password_hash = generate_password_hash(password)
            conn.execute(
                'INSERT INTO admins (username, password_hash, email) VALUES (?, ?, ?)',
                (username, password_hash, email)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Username exists
        finally:
            conn.close()

    def verify_admin(self, username, password):
        """Verify admin credentials."""
        conn = self.get_connection()
        admin = conn.execute(
            'SELECT * FROM admins WHERE username = ?', (username,)
        ).fetchone()
        conn.close()

        if admin and check_password_hash(admin['password_hash'], password):
            return dict(admin)
        return None

    def admin_exists(self):
        """Check if any admin account exists."""
        conn = self.get_connection()
        count = conn.execute('SELECT COUNT(*) FROM admins').fetchone()[0]
        conn.close()
        return count > 0

    def get_admin_by_username(self, username):
        """Get admin account details by username."""
        conn = self.get_connection()
        admin = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
        conn.close()
        return dict(admin) if admin else None

    def get_admin_by_id(self, admin_id):
        """Get admin account details by ID."""
        conn = self.get_connection()
        admin = conn.execute('SELECT * FROM admins WHERE admin_id = ?', (admin_id,)).fetchone()
        conn.close()
        return dict(admin) if admin else None

    def update_admin_profile(self, admin_id, new_username, new_email):
        """Update admin username and registered email address."""
        conn = self.get_connection()
        try:
            conn.execute(
                'UPDATE admins SET username = ?, email = ? WHERE admin_id = ?',
                (new_username, new_email, admin_id)
            )
            conn.commit()
            return True, "Admin profile and email updated successfully."
        except sqlite3.IntegrityError:
            return False, "Username is already taken by another admin account."
        except Exception as e:
            return False, f"Error updating profile: {str(e)}"
        finally:
            conn.close()

    def update_admin_password(self, admin_id, new_password):
        """Update admin password hash."""
        conn = self.get_connection()
        try:
            password_hash = generate_password_hash(new_password)
            conn.execute(
                'UPDATE admins SET password_hash = ? WHERE admin_id = ?',
                (password_hash, admin_id)
            )
            conn.commit()
            return True, "Admin password updated successfully."
        except Exception as e:
            return False, f"Failed to update password: {str(e)}"
        finally:
            conn.close()

    def get_facial_access_summary(self):
        """Get comprehensive analytics summary of facial recognition access logs."""
        conn = self.get_connection()

        # Overall attempt stats
        total_attempts = conn.execute('SELECT COUNT(*) FROM login_logs').fetchone()[0]
        total_success = conn.execute("SELECT COUNT(*) FROM login_logs WHERE status = 'Success'").fetchone()[0]
        total_failed = conn.execute("SELECT COUNT(*) FROM login_logs WHERE status = 'Failed'").fetchone()[0]
        success_rate = round((total_success / total_attempts * 100), 1) if total_attempts > 0 else 0.0

        # Registered face users
        total_face_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0]

        # Today metrics
        today_attempts = conn.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now')").fetchone()[0]
        today_success = conn.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now') AND status = 'Success'").fetchone()[0]
        today_success_rate = round((today_success / today_attempts * 100), 1) if today_attempts > 0 else 0.0

        # Gesture verification breakdown
        gesture_rows = conn.execute('''
            SELECT gesture_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN gesture_result = 'Verified' THEN 1 ELSE 0 END) as verified_count,
                   SUM(CASE WHEN gesture_result = 'Failed' THEN 1 ELSE 0 END) as failed_count
            FROM login_logs
            WHERE gesture_type IS NOT NULL AND gesture_type != ''
            GROUP BY gesture_type
            ORDER BY total DESC
        ''').fetchall()

        gesture_stats = []
        for row in gesture_rows:
            tot = row['total']
            ver = row['verified_count'] or 0
            rate = round((ver / tot * 100), 1) if tot > 0 else 0.0
            gesture_stats.append({
                'gesture': row['gesture_type'],
                'total': tot,
                'verified': ver,
                'failed': row['failed_count'] or 0,
                'pass_rate': rate
            })

        # Top facial access users
        user_rows = conn.execute('''
            SELECT u.user_id, u.name, u.email, u.created_at,
                   COUNT(l.log_id) as total_logins,
                   SUM(CASE WHEN l.status = 'Success' THEN 1 ELSE 0 END) as success_logins,
                   MAX(l.login_time) as last_access
            FROM users u
            LEFT JOIN login_logs l ON u.user_id = l.user_id
            GROUP BY u.user_id
            ORDER BY total_logins DESC, u.created_at DESC
            LIMIT 10
        ''').fetchall()

        user_facial_stats = [dict(u) for u in user_rows]

        # Recent facial access attempts
        recent_logs = conn.execute('''
            SELECT l.*, u.name as user_name, u.email as user_email
            FROM login_logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            ORDER BY l.login_time DESC
            LIMIT 10
        ''').fetchall()
        recent_facial_logs = [dict(log) for log in recent_logs]

        conn.close()

        return {
            'total_attempts': total_attempts,
            'total_success': total_success,
            'total_failed': total_failed,
            'success_rate': success_rate,
            'total_face_users': total_face_users,
            'today_attempts': today_attempts,
            'today_success': today_success,
            'today_success_rate': today_success_rate,
            'gesture_stats': gesture_stats,
            'user_facial_stats': user_facial_stats,
            'recent_facial_logs': recent_facial_logs
        }

    # ─── System Settings Operations ────────────────────

    def get_all_settings(self):
        """Get all system settings as dictionary."""
        conn = self.get_connection()
        rows = conn.execute('SELECT setting_key, setting_value FROM system_settings').fetchall()
        conn.close()
        return {r['setting_key']: r['setting_value'] for r in rows}

    def update_setting(self, key, value):
        """Insert or update a setting key/value pair."""
        conn = self.get_connection()
        conn.execute(
            'INSERT INTO system_settings (setting_key, setting_value) VALUES (?, ?) '
            'ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value',
            (key, str(value) if value is not None else '')
        )
        conn.commit()
        conn.close()


