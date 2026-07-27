"""
Database Module — Dual SQLite/PostgreSQL Ready Manager for Users, Admin Accounts, Login Logs & Audit Trails.
"""

import sqlite3
import os
import pickle
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from backend.modules.security import encrypt_embedding, decrypt_embedding


class Database:
    """Enterprise Database Manager with auto-schema migrations, indexing, and encryption support."""

    def __init__(self, db_path):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception:
                pass

    def get_connection(self):
        """Get database connection with dict row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        """Initialize database tables, indexes, and schema migrations."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                face_encoding BLOB NOT NULL,
                face_image_path VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                failed_attempts INTEGER DEFAULT 0,
                locked_until DATETIME,
                last_login DATETIME,
                role VARCHAR(20) DEFAULT 'user',
                password_hash VARCHAR(255)
            )
        ''')

        # Schema migrations for users table if existing
        for col, col_type in [
            ('failed_attempts', 'INTEGER DEFAULT 0'),
            ('locked_until', 'DATETIME'),
            ('last_login', 'DATETIME'),
            ('role', "VARCHAR(20) DEFAULT 'user'"),
            ('password_hash', 'VARCHAR(255)')
        ]:
            try:
                cursor.execute(f'ALTER TABLE users ADD COLUMN {col} {col_type}')
            except sqlite3.OperationalError:
                pass

        # 2. Login Logs Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) NOT NULL,
                gesture_type VARCHAR(50),
                gesture_result VARCHAR(20),
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                device_type VARCHAR(50),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        ''')

        for col, col_type in [('user_agent', 'VARCHAR(255)'), ('device_type', 'VARCHAR(50)')]:
            try:
                cursor.execute(f'ALTER TABLE login_logs ADD COLUMN {col} {col_type}')
            except sqlite3.OperationalError:
                pass

        # 3. Admins Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100),
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                role VARCHAR(20) DEFAULT 'admin'
            )
        ''')

        try:
            cursor.execute('ALTER TABLE admins ADD COLUMN email VARCHAR(100)')
        except sqlite3.OperationalError:
            pass

        # 4. Audit Logs Table (Security & System Audit Trail)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action VARCHAR(100) NOT NULL,
                category VARCHAR(50) DEFAULT 'SECURITY',
                details TEXT,
                ip_address VARCHAR(45),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 5. Password Resets Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                reset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(100) NOT NULL,
                token VARCHAR(128) NOT NULL,
                expires_at DATETIME NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 6. System Settings Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value TEXT
            )
        ''')

        # Indexes for optimized query execution
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_logs_user_time ON login_logs(user_id, login_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)")

        # Seed default admin user ONLY if no admin accounts exist
        from backend.config import Config
        cursor.execute("SELECT COUNT(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            pwd_hash = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)
            default_email = Config.DEFAULT_ADMIN_EMAIL or 'admin@faceguard.local'
            cursor.execute(
                'INSERT INTO admins (username, password_hash, email) VALUES (?, ?, ?)',
                (Config.DEFAULT_ADMIN_USERNAME, pwd_hash, default_email)
            )

        # Initial default system settings
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

    def add_user(self, name, email, face_encoding, face_image_path=None, role='user', password=None):
        """Add a new user with encrypted face encoding."""
        conn = self.get_connection()
        try:
            encoding_blob = encrypt_embedding(face_encoding)
            password_hash = generate_password_hash(password) if password else None
            conn.execute(
                '''INSERT INTO users (name, email, face_encoding, face_image_path, role, password_hash)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (name, email, encoding_blob, face_image_path, role, password_hash)
            )
            conn.commit()
            new_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            self.log_audit_event(new_id, "USER_REGISTERED", "AUTH", f"User registered: {email}")
            return new_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_user_by_id(self, user_id):
        """Get user details by ID."""
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_email(self, email):
        """Get user details by email."""
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?)', (email.strip(),)).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_all_users(self, search_term=None, limit=100, offset=0):
        """Get users with optional search filter."""
        conn = self.get_connection()
        query = 'SELECT user_id, name, email, face_image_path, created_at, is_active, last_login, role FROM users WHERE 1=1'
        params = []
        if search_term:
            query += ' AND (LOWER(name) LIKE ? OR LOWER(email) LIKE ?)'
            params.extend([f'%{search_term.lower()}%', f'%{search_term.lower()}%'])
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        users = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(u) for u in users]

    def get_all_face_encodings(self):
        """Get all face encodings as dict {user_id: encoding} (decrypts encrypted and legacy blobs)."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT user_id, face_encoding FROM users WHERE is_active = 1'
        ).fetchall()
        conn.close()

        encodings = {}
        for row in rows:
            try:
                decoded = decrypt_embedding(row['face_encoding'])
                if decoded is not None:
                    encodings[row['user_id']] = decoded
            except Exception:
                continue
        return encodings

    def update_user_face(self, user_id, new_face_encoding, new_image_path=None):
        """Update face encoding for an existing user."""
        conn = self.get_connection()
        encoding_blob = encrypt_embedding(new_face_encoding)
        if new_image_path:
            conn.execute(
                'UPDATE users SET face_encoding = ?, face_image_path = ? WHERE user_id = ?',
                (encoding_blob, new_image_path, user_id)
            )
        else:
            conn.execute('UPDATE users SET face_encoding = ? WHERE user_id = ?', (encoding_blob, user_id))
        conn.commit()
        conn.close()
        self.log_audit_event(user_id, "FACE_REGISTRATION_UPDATED", "SECURITY", "User updated face embedding.")

    def delete_user(self, user_id):
        """Delete user by ID."""
        conn = self.get_connection()
        user = self.get_user_by_id(user_id)
        conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        if user:
            self.log_audit_event(user_id, "USER_DELETED", "SECURITY", f"Deleted user: {user.get('email')}")

    def toggle_user_status(self, user_id):
        """Toggle active status of a user."""
        conn = self.get_connection()
        conn.execute('UPDATE users SET is_active = NOT is_active WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        self.log_audit_event(user_id, "USER_STATUS_TOGGLED", "SECURITY", "Toggled active state.")

    def get_user_count(self, search_term=None):
        """Get user count."""
        conn = self.get_connection()
        query = 'SELECT COUNT(*) FROM users WHERE 1=1'
        params = []
        if search_term:
            query += ' AND (LOWER(name) LIKE ? OR LOWER(email) LIKE ?)'
            params.extend([f'%{search_term.lower()}%', f'%{search_term.lower()}%'])
        count = conn.execute(query, params).fetchone()[0]
        conn.close()
        return count

    # ─── Account Protection & Lockout ──────────────────

    def is_account_locked(self, email):
        """Check if account is locked out due to multiple failed login attempts."""
        user = self.get_user_by_email(email)
        if not user or not user.get('locked_until'):
            return False, 0
        try:
            locked_time = datetime.strptime(str(user['locked_until']).split('.')[0], '%Y-%m-%d %H:%M:%S')
            if datetime.now() < locked_time:
                remaining = int((locked_time - datetime.now()).total_seconds() / 60) + 1
                return True, remaining
        except Exception:
            pass
        return False, 0

    def increment_failed_attempts(self, email, max_attempts=5, lockout_minutes=15):
        """Increment failed attempts and lock account if limit reached."""
        user = self.get_user_by_email(email)
        if not user:
            return
        attempts = (user.get('failed_attempts') or 0) + 1
        locked_until = None
        if attempts >= max_attempts:
            locked_until = (datetime.now() + timedelta(minutes=lockout_minutes)).strftime('%Y-%m-%d %H:%M:%S')
            self.log_audit_event(user['user_id'], "ACCOUNT_LOCKED", "SECURITY", f"Account locked for {lockout_minutes} mins.")

        conn = self.get_connection()
        conn.execute(
            'UPDATE users SET failed_attempts = ?, locked_until = ? WHERE user_id = ?',
            (attempts, locked_until, user['user_id'])
        )
        conn.commit()
        conn.close()

    def reset_failed_attempts(self, user_id):
        """Reset failed login counters upon successful authentication."""
        conn = self.get_connection()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            'UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ? WHERE user_id = ?',
            (now_str, user_id)
        )
        conn.commit()
        conn.close()

    # ─── Login Log & Audit Operations ──────────────────

    def log_login_attempt(self, user_id, status, gesture_type=None, gesture_result=None, ip_address=None, user_agent=None, device_type=None):
        """Log authentication attempt with device metadata."""
        conn = self.get_connection()
        conn.execute(
            '''INSERT INTO login_logs (user_id, status, gesture_type, gesture_result, ip_address, user_agent, device_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, status, gesture_type, gesture_result, ip_address, user_agent, device_type)
        )
        conn.commit()
        conn.close()

    def get_login_logs(self, limit=50, offset=0, user_id=None, status=None):
        """Get login attempt history."""
        conn = self.get_connection()
        query = '''
            SELECT l.*, u.name as user_name, u.email as user_email
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

        query += ' ORDER BY l.login_time DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        logs = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(log) for log in logs]

    def log_audit_event(self, user_id, action, category='SECURITY', details=None, ip_address=None):
        """Record system/security audit log."""
        conn = self.get_connection()
        conn.execute(
            '''INSERT INTO audit_logs (user_id, action, category, details, ip_address)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, action, category, details, ip_address)
        )
        conn.commit()
        conn.close()

    def get_audit_logs(self, limit=100, offset=0, category=None):
        """Fetch audit log records."""
        conn = self.get_connection()
        query = 'SELECT a.*, u.email as user_email FROM audit_logs a LEFT JOIN users u ON a.user_id = u.user_id WHERE 1=1'
        params = []
        if category:
            query += ' AND a.category = ?'
            params.append(category)
        query += ' ORDER BY a.created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        logs = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(l) for l in logs]

    def get_today_login_count(self):
        """Get today's total login attempts."""
        conn = self.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now')").fetchone()[0]
        conn.close()
        return count

    def get_today_success_count(self):
        """Get today's successful logins."""
        conn = self.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now') AND status = 'Success'").fetchone()[0]
        conn.close()
        return count

    # ─── Admin Operations ─────────────────────────────

    def create_admin(self, username, password, email=None):
        """Create admin account."""
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
            return False
        finally:
            conn.close()

    def verify_admin(self, username, password):
        """Verify admin credentials."""
        conn = self.get_connection()
        admin = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin['password_hash'], password):
            return dict(admin)
        return None

    def admin_exists(self):
        """Check if admin exists."""
        conn = self.get_connection()
        count = conn.execute('SELECT COUNT(*) FROM admins').fetchone()[0]
        conn.close()
        return count > 0

    def get_admin_by_username(self, username):
        """Get admin by username."""
        conn = self.get_connection()
        admin = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
        conn.close()
        return dict(admin) if admin else None

    def get_admin_by_id(self, admin_id):
        """Get admin by ID."""
        conn = self.get_connection()
        admin = conn.execute('SELECT * FROM admins WHERE admin_id = ?', (admin_id,)).fetchone()
        conn.close()
        return dict(admin) if admin else None

    def update_admin_profile(self, admin_id, new_username, new_email):
        """Update admin username and email."""
        conn = self.get_connection()
        try:
            conn.execute(
                'UPDATE admins SET username = ?, email = ? WHERE admin_id = ?',
                (new_username, new_email, admin_id)
            )
            conn.commit()
            self.log_audit_event(admin_id, "ADMIN_PROFILE_UPDATED", "SECURITY", f"Admin profile updated: {new_email}")
            return True, "Admin profile and email updated successfully."
        except sqlite3.IntegrityError:
            return False, "Username is already taken by another admin account."
        except Exception as e:
            return False, f"Error updating profile: {str(e)}"
        finally:
            conn.close()

    def update_admin_password(self, admin_id, new_password):
        """Update admin password."""
        conn = self.get_connection()
        try:
            password_hash = generate_password_hash(new_password)
            conn.execute('UPDATE admins SET password_hash = ? WHERE admin_id = ?', (password_hash, admin_id))
            conn.commit()
            self.log_audit_event(admin_id, "ADMIN_PASSWORD_CHANGED", "SECURITY", "Admin changed account password.")
            return True, "Admin password updated successfully."
        except Exception as e:
            return False, f"Failed to update password: {str(e)}"
        finally:
            conn.close()

    def get_facial_access_summary(self):
        """Analytics summary of facial recognition access logs."""
        conn = self.get_connection()

        total_attempts = conn.execute('SELECT COUNT(*) FROM login_logs').fetchone()[0]
        total_success = conn.execute("SELECT COUNT(*) FROM login_logs WHERE status = 'Success'").fetchone()[0]
        total_failed = conn.execute("SELECT COUNT(*) FROM login_logs WHERE status = 'Failed'").fetchone()[0]
        success_rate = round((total_success / total_attempts * 100), 1) if total_attempts > 0 else 0.0

        total_face_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0]

        today_attempts = conn.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now')").fetchone()[0]
        today_success = conn.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_time) = DATE('now') AND status = 'Success'").fetchone()[0]
        today_success_rate = round((today_success / today_attempts * 100), 1) if today_attempts > 0 else 0.0

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
        """Get system settings."""
        conn = self.get_connection()
        rows = conn.execute('SELECT setting_key, setting_value FROM system_settings').fetchall()
        conn.close()
        return {r['setting_key']: r['setting_value'] for r in rows}

    def update_setting(self, key, value):
        """Insert or update setting."""
        conn = self.get_connection()
        conn.execute(
            'INSERT INTO system_settings (setting_key, setting_value) VALUES (?, ?) '
            'ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value',
            (key, str(value) if value is not None else '')
        )
        conn.commit()
        conn.close()
