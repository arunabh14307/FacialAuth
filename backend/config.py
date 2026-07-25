import os

BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'facial-recog-secret-key-change-in-production')

    # Database
    DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')


    # Face Recognition
    FACE_ENCODING_DIR = os.path.join(BASE_DIR, 'data', 'face_encodings')
    FACE_RECOGNITION_TOLERANCE = 0.6  # Lower = stricter matching
    FACE_RECOGNITION_MODEL = 'hog'    # 'hog' (CPU) or 'cnn' (GPU)

    # Gesture Detection
    GESTURE_TIMEOUT = 10              # Seconds allowed for gesture
    GESTURE_CONFIDENCE_THRESHOLD = 0.6
    SUPPORTED_GESTURES = ['smile', 'blink', 'look_left', 'look_right', 'look_up', 'look_down']

    # Security
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW = 300        # Seconds (5 minutes)

    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    # Admin defaults
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin123'
    DEFAULT_ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@faceguard.local')

    # OTP & Email settings
    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    SMTP_SERVER = os.environ.get('SMTP_SERVER', '')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    MAIL_FROM_ADDRESS = os.environ.get('MAIL_FROM_ADDRESS', 'noreply@faceguard.local')

