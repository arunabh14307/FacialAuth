import os
from datetime import timedelta

# Try loading .env if dotenv is present or read environment directly
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))


class Config:
    """Enterprise Application Configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'facial-recog-secret-key-change-in-production')
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '')

    # Session & Security Hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV', 'development') == 'production'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30)))
    REMEMBER_COOKIE_DURATION = timedelta(days=int(os.environ.get('REMEMBER_ME_DAYS', 7)))

    # Database & Storage
    DATABASE_URL = os.environ.get('DATABASE_URL')
    data_dir = os.environ.get('RENDER_DISK_PATH') or os.environ.get('DATA_DIR')
    if data_dir:
        DATABASE_PATH = os.path.join(data_dir, 'database.db')
        FACE_ENCODING_DIR = os.path.join(data_dir, 'face_encodings')
    elif os.environ.get('SERVERLESS') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        DATABASE_PATH = '/tmp/database.db'
        FACE_ENCODING_DIR = '/tmp/face_encodings'
    else:
        DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'database.db'))
        FACE_ENCODING_DIR = os.environ.get('FACE_ENCODING_DIR', os.path.join(BASE_DIR, 'data', 'face_encodings'))

    FACE_RECOGNITION_TOLERANCE = 0.32  # SFace Cosine Similarity Threshold (Optimal: 0.320)
    FACE_RECOGNITION_MODEL = 'hog'    # 'hog' (CPU) or 'cnn' (GPU)

    # Face Quality Controls
    MIN_BRIGHTNESS_THRESHOLD = 40.0   # Minimum acceptable lighting
    MAX_BLUR_THRESHOLD = 50.0         # Minimum Laplacian variance for sharpness

    # Gesture Detection
    GESTURE_TIMEOUT = 10              # Seconds allowed for gesture
    GESTURE_CONFIDENCE_THRESHOLD = 0.6
    SUPPORTED_GESTURES = ['smile', 'blink', 'look_left', 'look_right', 'look_up', 'look_down']

    # Account Protection
    MAX_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_MINUTES = 15
    LOGIN_ATTEMPT_WINDOW = 300        # Seconds (5 minutes)

    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    # Admin defaults
    DEFAULT_ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    DEFAULT_ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@faceguard.local')

    # OTP & Email settings
    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'false').lower() == 'true'
    MAIL_FROM_ADDRESS = os.environ.get('MAIL_FROM_ADDRESS', '')
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
