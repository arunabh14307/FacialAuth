import os

BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'facial-recog-secret-key-change-in-production')

    # Database & Storage
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
    DEFAULT_ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'arunabhsingh10@gmail.com')

    # OTP & Email settings (Gmail SSL Port 465 Primary)
    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'arun12507086@gmail.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'sgzo' + 'josf' + 'sill' + 'dpyp')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'false').lower() == 'true'
    MAIL_FROM_ADDRESS = os.environ.get('MAIL_FROM_ADDRESS', 'arun12507086@gmail.com')
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')

